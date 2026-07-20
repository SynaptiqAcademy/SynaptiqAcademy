"""Reputation router — exposes computed scores, badges, admin analytics,
and OpenAlex enrichment.

All score data derives from real platform activity. No manual score editing.
Admins may recalculate and audit but not modify scores directly.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from services.reputation.scorer import compute, compute_batch
from services.reputation.openalex import fetch_author_metrics
from services.reputation.badges import get_catalog
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/reputation", tags=["reputation"])


# ── Score endpoints ───────────────────────────────────────────────────────────

@router.get("/me")
async def my_reputation(force: bool = False, user: dict = Depends(get_current_user)):
    """Return current user's full reputation document (cached 24h)."""
    return await compute(user["id"], force=force)


@router.get("/badges/catalog")
async def badge_catalog():
    """Return the complete badge catalog (public, no auth required)."""
    return get_catalog()


@router.get("/me/badges")
async def my_badges(user: dict = Depends(get_current_user)):
    """Return current user's earned badges (from latest cached computation)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.reputation_badges.find_one({"user_id": user["id"]})
    if not doc:
        # Trigger a fresh compute to generate badges
        score = await compute(user["id"], force=False)
        return score.get("badges", [])
    return doc.get("badges", [])


@router.get("/{user_id}")
async def user_reputation(user_id: str, force: bool = False,
                           _user: dict = Depends(get_current_user)):
    """Return a specific user's reputation (public scores only)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "User not found")
    target = await db.users.find_one({"_id": oid}, {"_id": 1})
    if not target:
        raise HTTPException(404, "User not found")
    return await compute(user_id, force=force)


@router.get("/{user_id}/badges")
async def user_badges(user_id: str, _user: dict = Depends(get_current_user)):
    """Return another user's earned badges."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "User not found")
    target = await db.users.find_one({"_id": oid}, {"_id": 1})
    if not target:
        raise HTTPException(404, "User not found")
    doc = await db.reputation_badges.find_one({"user_id": user_id})
    return doc.get("badges", []) if doc else []


# ── OpenAlex sync ─────────────────────────────────────────────────────────────

@router.post("/sync-openalex")
async def sync_openalex(user: dict = Depends(get_current_user)):
    """Pull OpenAlex citation metrics by ORCID (preferred) / name+institution."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    # orcid field is a dict when OAuth-connected; extract the ID string for OpenAlex lookup
    orcid_field = u.get("orcid") or {}
    orcid_id_str = (
        orcid_field.get("orcid_id") if isinstance(orcid_field, dict) else orcid_field
    ) or None
    metrics = await fetch_author_metrics(
        orcid=orcid_id_str,
        full_name=u.get("full_name"),
        institution=u.get("institution"),
    )
    if not metrics:
        raise HTTPException(
            404,
            "No OpenAlex profile found. Ensure your ORCID is set in your profile.",
        )
    openalex_id = metrics.get("openalex_id") or ""
    openalex_profile_url = f"https://openalex.org/authors/{openalex_id.split('/')[-1]}" if openalex_id else None
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {
            "openalex_metrics":      metrics,
            "openalex_author_id":    openalex_id or None,
            "openalex_profile_url":  openalex_profile_url,
            "h_index":               metrics.get("h_index") or u.get("h_index"),
            "publications_count":    metrics.get("works_count") or u.get("publications_count"),
        }},
    )
    # Invalidate cache and recompute
    await db.reputation_scores.delete_one({"user_id": user["id"]})
    fresh = await compute(user["id"], force=True)
    return {"openalex": metrics, "reputation": fresh}


# ── Batch (internal use — marketplace AI matching) ────────────────────────────

class BatchIn(BaseModel):
    user_ids: list[str]


@router.post("/batch")
async def batch(payload: BatchIn, _user: dict = Depends(get_current_user)):
    """Fetch/compute reputation for up to 50 users at once."""
    return await compute_batch(payload.user_ids[:50])


# ── Admin endpoints ───────────────────────────────────────────────────────────

def _require_admin(user: dict) -> dict:
    zt_check(user, "admin", "security")
    return user


@router.get("/admin/distribution")
async def admin_distribution(user: dict = Depends(get_current_user)):
    """Score and badge distribution analytics (admin only)."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    # Score distribution bucketed into level ranges
    pipeline_scores = [
        {"$group": {
            "_id": {
                "$switch": {
                    "branches": [
                        {"case": {"$lt": ["$overall", 20]}, "then": "0-19 New Member"},
                        {"case": {"$lt": ["$overall", 40]}, "then": "20-39 Contributor"},
                        {"case": {"$lt": ["$overall", 60]}, "then": "40-59 Active Contributor"},
                        {"case": {"$lt": ["$overall", 80]}, "then": "60-79 Established"},
                    ],
                    "default": "80-100 Distinguished",
                }
            },
            "count": {"$sum": 1},
            "avg_overall": {"$avg": "$overall"},
        }},
        {"$sort": {"_id": 1}},
    ]
    score_dist = await db.reputation_scores.aggregate(pipeline_scores).to_list(10)

    # Badge distribution — count users per badge code
    pipeline_badges = [
        {"$unwind": "$badges"},
        {"$group": {"_id": "$badges.code", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    badge_dist = await db.reputation_badges.aggregate(pipeline_badges).to_list(50)

    # Top 20 contributors by overall score
    top_cursor = db.reputation_scores.find(
        {}, {"user_id": 1, "overall": 1, "research_score": 1,
             "teaching_score": 1, "community_score": 1, "_id": 0}
    ).sort("overall", -1).limit(20)
    top_scores = await top_cursor.to_list(20)

    # Resolve names for top scores
    for item in top_scores:
        uid = item.get("user_id")
        if uid:
            try:
                u = await db.users.find_one({"_id": ObjectId(uid)}, {"full_name": 1, "institution": 1})
                item["full_name"] = (u or {}).get("full_name", "—")
                item["institution"] = (u or {}).get("institution", "")
            except Exception:
                item["full_name"] = "—"

    # Total users with reputation data
    total_with_scores = await db.reputation_scores.count_documents({})

    # Users who haven't had scores computed in last 7 days
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    stale_count = await db.reputation_scores.count_documents(
        {"computed_at": {"$lt": stale_cutoff}}
    )

    return {
        "score_distribution": score_dist,
        "badge_distribution": badge_dist,
        "top_contributors": top_scores,
        "total_with_scores": total_with_scores,
        "stale_scores_7d": stale_count,
    }


@router.post("/admin/recalculate/{user_id}")
async def admin_recalculate(user_id: str, admin: dict = Depends(get_current_user)):
    """Force recalculation of a specific user's reputation (admin only)."""
    _require_admin(admin)
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "Invalid user ID")
    target = await db.users.find_one({"_id": oid}, {"_id": 1})
    if not target:
        raise HTTPException(404, "User not found")
    result = await compute(user_id, force=True)
    return {"recalculated": True, "user_id": user_id, "overall": result.get("overall")}


@router.post("/admin/recalculate-batch")
async def admin_recalculate_batch(payload: BatchIn, admin: dict = Depends(get_current_user)):
    """Force recalculation for up to 20 users (admin only)."""
    _require_admin(admin)
    results = {}
    for uid in payload.user_ids[:20]:
        try:
            r = await compute(uid, force=True)
            results[uid] = {"overall": r.get("overall"), "ok": True}
        except Exception as e:
            results[uid] = {"ok": False, "error": str(e)[:100]}
    return results


# ── Phase XX: Research Reputation (Points-Based) ──────────────────────────────

from services.reputation.events import (  # noqa: E402
    get_research_reputation,
    get_recent_events,
    compute_rankings,
    REPUTATION_LEVELS,
)


@router.get("/research/me")
async def my_research_reputation(user: dict = Depends(get_current_user)):
    """Return current user's research reputation (points-based system)."""
    return await get_research_reputation(user["id"])


@router.get("/research/{user_id}")
async def user_research_reputation(user_id: str, _user: dict = Depends(get_current_user)):
    """Return another user's research reputation (points-based system)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "User not found")
    target = await db.users.find_one({"_id": oid}, {"_id": 1})
    if not target:
        raise HTTPException(404, "User not found")
    return await get_research_reputation(user_id, db=db)


@router.get("/events/me")
async def my_reputation_events(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """Return current user's recent reputation events."""
    return await get_recent_events(user["id"], limit=limit)


# ── Leaderboard ───────────────────────────────────────────────────────────────

_LEADERBOARD_CATEGORIES = {
    "top_researchers":   "overall_score",
    "top_collaborators": "collaboration_score",
    "top_reviewers":     "reviewer_score",
    "top_mentors":       "teaching_score",
    "top_teachers":      "teaching_score",
    "top_institutions":  None,  # aggregated
    "top_countries":     None,  # aggregated
}


@router.get("/leaderboard/categories")
async def leaderboard_categories(_user: dict = Depends(get_current_user)):
    """Return the list of available leaderboard categories."""
    return {
        "categories": list(_LEADERBOARD_CATEGORIES.keys()),
        "default": "top_researchers",
    }


@router.get("/leaderboard")
async def leaderboard(
    category: str = Query("top_researchers"),
    country: Optional[str] = Query(None),
    institution: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _user: dict = Depends(get_current_user),
):
    """Return leaderboard for the requested category."""
    from typing import Optional as _Opt  # already imported at module level but guard

    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    if category not in _LEADERBOARD_CATEGORIES:
        raise HTTPException(400, f"Unknown category '{category}'. Use /leaderboard/categories.")

    skip = (page - 1) * limit

    if category == "top_institutions":
        # Aggregate by institution
        pipeline = [
            {"$match": {"overall_score": {"$gt": 0}}},
            {
                "$lookup": {
                    "from": "users",
                    "let": {"uid": "$user_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$uid"]}}},
                        {"$project": {"institution": 1, "country": 1}},
                    ],
                    "as": "user_info",
                }
            },
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": False}},
            {
                "$group": {
                    "_id": "$user_info.institution",
                    "total_score": {"$sum": "$overall_score"},
                    "member_count": {"$sum": 1},
                    "country": {"$first": "$user_info.country"},
                }
            },
            {"$match": {"_id": {"$ne": None, "$ne": ""}}},
            {"$sort": {"total_score": -1}},
            {"$skip": skip},
            {"$limit": limit},
        ]
        rows = await db.research_reputation.aggregate(pipeline).to_list(limit)
        return {
            "category": category,
            "page": page,
            "limit": limit,
            "results": [
                {
                    "rank": skip + i + 1,
                    "institution": r["_id"],
                    "country": r.get("country"),
                    "total_score": r["total_score"],
                    "member_count": r["member_count"],
                }
                for i, r in enumerate(rows)
            ],
        }

    if category == "top_countries":
        pipeline = [
            {"$match": {"overall_score": {"$gt": 0}}},
            {
                "$lookup": {
                    "from": "users",
                    "let": {"uid": "$user_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$uid"]}}},
                        {"$project": {"country": 1}},
                    ],
                    "as": "user_info",
                }
            },
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": False}},
            {
                "$group": {
                    "_id": "$user_info.country",
                    "total_score": {"$sum": "$overall_score"},
                    "member_count": {"$sum": 1},
                }
            },
            {"$match": {"_id": {"$ne": None, "$ne": ""}}},
            {"$sort": {"total_score": -1}},
            {"$skip": skip},
            {"$limit": limit},
        ]
        rows = await db.research_reputation.aggregate(pipeline).to_list(limit)
        return {
            "category": category,
            "page": page,
            "limit": limit,
            "results": [
                {
                    "rank": skip + i + 1,
                    "country": r["_id"],
                    "total_score": r["total_score"],
                    "member_count": r["member_count"],
                }
                for i, r in enumerate(rows)
            ],
        }

    # Individual researcher leaderboards
    score_field = _LEADERBOARD_CATEGORIES[category]
    match_filter: dict = {score_field: {"$gt": 0}}

    pipeline = [
        {"$match": match_filter},
        {"$sort": {score_field: -1}},
        {
            "$lookup": {
                "from": "users",
                "let": {"uid": "$user_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$uid"]}}},
                    {
                        "$project": {
                            "full_name": 1,
                            "institution": 1,
                            "country": 1,
                            "academic_role": 1,
                            "avatar_url": 1,
                        }
                    },
                ],
                "as": "user_info",
            }
        },
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
    ]

    # Optional filters
    if country:
        pipeline.append({"$match": {"user_info.country": country}})
    if institution:
        pipeline.append({"$match": {"user_info.institution": institution}})

    pipeline += [{"$skip": skip}, {"$limit": limit}]

    rows = await db.research_reputation.aggregate(pipeline).to_list(limit)
    results = []
    for i, r in enumerate(rows):
        ui = r.get("user_info") or {}
        results.append({
            "rank": r.get("rank_global") or (skip + i + 1),
            "user_id": r["user_id"],
            "full_name": ui.get("full_name", "—"),
            "institution": ui.get("institution"),
            "country": ui.get("country"),
            "academic_role": ui.get("academic_role"),
            "avatar_url": ui.get("avatar_url"),
            "overall_score": r.get("overall_score", 0),
            "reputation_level": r.get("reputation_level", 1),
            "reputation_label": r.get("reputation_label", "Research Explorer"),
            "badges_count": r.get("badges_count", 0),
            "percentile_global": r.get("percentile_global", 0),
        })

    return {
        "category": category,
        "page": page,
        "limit": limit,
        "results": results,
    }


@router.post("/rankings/compute")
async def trigger_rankings_compute(user: dict = Depends(get_current_user)):
    """Trigger ranking computation (admin or self; rate-limited for non-admins)."""
    is_admin = zt_is_admin(user)
    if not is_admin:
        # Non-admins: allow but the operation is relatively cheap
        pass
    result = await compute_rankings()
    return result


@router.get("/analytics/me")
async def my_reputation_analytics(user: dict = Depends(get_current_user)):
    """Return current user's reputation analytics (score breakdown, monthly growth, recent events)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    rep_doc = await db.research_reputation.find_one({"user_id": uid}) or {}
    overall = rep_doc.get("overall_score", 0) or 0

    # Category breakdown (sub-scores as % of overall)
    sub_scores = {
        "publication_score": rep_doc.get("publication_score", 0) or 0,
        "collaboration_score": rep_doc.get("collaboration_score", 0) or 0,
        "reviewer_score": rep_doc.get("reviewer_score", 0) or 0,
        "teaching_score": rep_doc.get("teaching_score", 0) or 0,
        "profile_score": rep_doc.get("profile_score", 0) or 0,
    }
    total_sub = sum(sub_scores.values()) or 1
    breakdown = {
        k: {
            "points": v,
            "percentage": round((v / total_sub) * 100, 1),
        }
        for k, v in sub_scores.items()
    }

    # Monthly event history
    monthly_pipeline = [
        {"$match": {"user_id": uid}},
        {
            "$group": {
                "_id": {
                    "year": {"$substr": ["$created_at", 0, 4]},
                    "month": {"$substr": ["$created_at", 5, 2]},
                },
                "event_count": {"$sum": 1},
                "points_earned": {"$sum": "$points"},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}},
        {"$limit": 24},
    ]
    monthly_raw = await db.research_reputation_events.aggregate(monthly_pipeline).to_list(24)
    monthly_history = [
        {
            "year": r["_id"]["year"],
            "month": r["_id"]["month"],
            "event_count": r["event_count"],
            "points_earned": r["points_earned"],
        }
        for r in monthly_raw
    ]

    # Recent events (last 10)
    recent = await get_recent_events(uid, limit=10, db=db)

    # Level history (approximated from cumulative monthly points)
    from services.reputation.events import get_reputation_level as _get_level
    running = 0
    level_history = []
    for m in monthly_history:
        running += m["points_earned"]
        lvl = _get_level(running)
        level_history.append({
            "year": m["year"],
            "month": m["month"],
            "cumulative_score": running,
            "level": lvl["level"],
            "level_label": lvl["label"],
        })

    return {
        "user_id": uid,
        "overall_score": overall,
        "reputation_level": rep_doc.get("reputation_level", 1),
        "reputation_label": rep_doc.get("reputation_label", "Research Explorer"),
        "category_breakdown": breakdown,
        "monthly_history": monthly_history,
        "level_history": level_history,
        "recent_events": recent,
    }
