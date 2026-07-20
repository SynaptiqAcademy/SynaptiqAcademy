"""Admin — Academic Recommendation Engine Analytics — Phase XXI.

Read-only analytics and operational controls for platform administrators.
All endpoints require admin or super_admin role.

Routes
------
GET  /api/admin/recommendations/stats               — platform-wide interaction totals
GET  /api/admin/recommendations/acceptance-rates    — per-type acceptance rates
GET  /api/admin/recommendations/top-areas           — top research areas in profiles
GET  /api/admin/recommendations/interactions        — paginated full interaction feed
GET  /api/admin/recommendations/profile-coverage    — profile build coverage stats
POST /api/admin/recommendations/refresh-all         — bulk profile refresh (≤200 users)
GET  /api/admin/recommendations/quality-metrics     — score quality and engagement rates
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

logger = logging.getLogger("synaptiq.admin_recommendations")

# ── Service layer import (graceful degradation) ───────────────────────────────
try:
    from services.recommendation.profiles import refresh_all_profiles
    _profiles_available = True
except ImportError as _import_err:
    logger.error("Recommendation profiles service unavailable: %s", _import_err)
    _profiles_available = False

router = APIRouter(prefix="/api/admin/recommendations", tags=["admin-recommendations"])

_ALL_TYPES = [
    "researchers", "projects", "journals", "conferences",
    "grants", "reviewers", "mentors",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_admin(user: dict) -> None:
    zt_check(user, "admin", "admin")


def _ser_doc(doc: dict) -> dict:
    """Serialize a MongoDB document: convert ObjectId fields to str."""
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _ser_doc(v)
        elif isinstance(v, list):
            out[k] = [
                _ser_doc(i) if isinstance(i, dict) else
                str(i) if isinstance(i, ObjectId) else i
                for i in v
            ]
        else:
            out[k] = v
    return out


# ── GET /stats ────────────────────────────────────────────────────────────────

@router.get("/stats")
async def recommendation_stats(user: dict = Depends(get_current_user)):
    """Platform-wide recommendation interaction totals, broken down by type."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    total_interactions = await db.recommendation_interactions.count_documents({})
    total_dismissals = await db.recommendation_interactions.count_documents({"action": "dismissed"})
    total_bookmarks = await db.recommendation_interactions.count_documents({"action": "bookmarked"})
    total_accepted = await db.recommendation_interactions.count_documents({"action": "accepted"})
    total_profiles_cached = await db.recommendation_profiles.count_documents({})
    total_scores_cached = await db.recommendation_scores.count_documents({})

    # Per-type breakdown
    type_pipeline = [
        {
            "$group": {
                "_id": "$recommendation_type",
                "interactions": {"$sum": 1},
                "dismissals": {
                    "$sum": {"$cond": [{"$eq": ["$action", "dismissed"]}, 1, 0]}
                },
                "accepted": {
                    "$sum": {"$cond": [{"$eq": ["$action", "accepted"]}, 1, 0]}
                },
            }
        }
    ]
    type_rows = await db.recommendation_interactions.aggregate(type_pipeline).to_list(20)
    type_map: dict = {row["_id"]: row for row in type_rows if row.get("_id")}

    by_type: dict = {}
    for t in _ALL_TYPES:
        row = type_map.get(t, {})
        interactions = row.get("interactions", 0)
        accepted = row.get("accepted", 0)
        acceptance_rate = round(accepted / interactions, 4) if interactions > 0 else 0.0
        by_type[t] = {
            "interactions": interactions,
            "dismissals": row.get("dismissals", 0),
            "acceptance_rate": acceptance_rate,
        }

    # Top dismissed users (most dismissal events)
    dismissed_pipeline = [
        {"$match": {"action": "dismissed"}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    dismissed_rows = await db.recommendation_interactions.aggregate(dismissed_pipeline).to_list(10)
    top_dismissed_users = [
        {"user_id": str(r["_id"]), "count": r["count"]}
        for r in dismissed_rows
    ]

    return {
        "total_interactions": total_interactions,
        "total_dismissals": total_dismissals,
        "total_bookmarks": total_bookmarks,
        "total_accepted": total_accepted,
        "total_profiles_cached": total_profiles_cached,
        "total_scores_cached": total_scores_cached,
        "by_type": by_type,
        "top_dismissed_users": top_dismissed_users,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── GET /acceptance-rates ─────────────────────────────────────────────────────

@router.get("/acceptance-rates")
async def acceptance_rates(user: dict = Depends(get_current_user)):
    """Per-type acceptance rates: accepted / total interactions."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
        {
            "$group": {
                "_id": "$recommendation_type",
                "total": {"$sum": 1},
                "accepted": {
                    "$sum": {"$cond": [{"$eq": ["$action", "accepted"]}, 1, 0]}
                },
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await db.recommendation_interactions.aggregate(pipeline).to_list(20)

    result: dict = {}
    for row in rows:
        rec_type = row.get("_id") or "unknown"
        total = row.get("total", 0)
        accepted = row.get("accepted", 0)
        result[rec_type] = {
            "total_interactions": total,
            "accepted": accepted,
            "acceptance_rate": round(accepted / total, 4) if total > 0 else 0.0,
        }
    # Ensure all canonical types appear in the response
    for t in _ALL_TYPES:
        if t not in result:
            result[t] = {"total_interactions": 0, "accepted": 0, "acceptance_rate": 0.0}

    return result


# ── GET /top-areas ────────────────────────────────────────────────────────────

@router.get("/top-areas")
async def top_areas(user: dict = Depends(get_current_user)):
    """Top 20 research areas appearing across recommendation profiles."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
        {"$unwind": "$research_areas"},
        {
            "$group": {
                "_id": "$research_areas",
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 20},
        {"$project": {"area": "$_id", "count": 1, "_id": 0}},
    ]
    rows = await db.recommendation_profiles.aggregate(pipeline).to_list(20)
    return {"top_areas": rows}


# ── GET /interactions ─────────────────────────────────────────────────────────

@router.get("/interactions")
async def all_interactions(
    rec_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """Paginated feed of all recommendation interactions across all users."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    query: dict = {}
    if rec_type:
        query["recommendation_type"] = rec_type
    if action:
        query["action"] = action

    skip = (page - 1) * limit

    # Join with users to surface name + email
    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {
            "$addFields": {
                "user_id_obj": {
                    "$cond": {
                        "if": {"$regexMatch": {"input": "$user_id", "regex": "^[0-9a-fA-F]{24}$"}},
                        "then": {"$toObjectId": "$user_id"},
                        "else": None,
                    }
                }
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id_obj",
                "foreignField": "_id",
                "as": "_user",
            }
        },
        {
            "$addFields": {
                "user_name": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$_user"}, 0]},
                        "then": {
                            "$concat": [
                                {"$ifNull": [{"$arrayElemAt": ["$_user.first_name", 0]}, ""]},
                                " ",
                                {"$ifNull": [{"$arrayElemAt": ["$_user.last_name", 0]}, ""]},
                            ]
                        },
                        "else": None,
                    }
                },
                "user_email": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$_user"}, 0]},
                        "then": {"$arrayElemAt": ["$_user.email", 0]},
                        "else": None,
                    }
                },
            }
        },
        {"$project": {"_user": 0, "user_id_obj": 0}},
    ]

    docs = await db.recommendation_interactions.aggregate(pipeline).to_list(limit)
    total = await db.recommendation_interactions.count_documents(query)

    return {
        "items": [_ser_doc(d) for d in docs],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
    }


# ── GET /profile-coverage ─────────────────────────────────────────────────────

@router.get("/profile-coverage")
async def profile_coverage(user: dict = Depends(get_current_user)):
    """Coverage stats: how many users have recommendation profiles."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    total_users = await db.users.count_documents({})
    profiles_built = await db.recommendation_profiles.count_documents({})

    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    profiles_fresh = await db.recommendation_profiles.count_documents(
        {"updated_at": {"$gt": cutoff_24h}}
    )
    profiles_stale = profiles_built - profiles_fresh
    coverage_pct = round((profiles_built / total_users) * 100, 2) if total_users > 0 else 0.0

    return {
        "total_users": total_users,
        "profiles_built": profiles_built,
        "coverage_pct": coverage_pct,
        "profiles_stale": profiles_stale,
        "profiles_fresh": profiles_fresh,
    }


# ── POST /refresh-all ─────────────────────────────────────────────────────────

@router.post("/refresh-all")
async def admin_refresh_all(user: dict = Depends(get_current_user)):
    """Trigger a bulk rebuild of up to 200 recommendation profiles."""
    _require_admin(user)
    if not _profiles_available:
        raise HTTPException(
            status_code=503,
            detail="Recommendation profiles service is temporarily unavailable.",
        )
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        refreshed = await refresh_all_profiles(db, limit=200)
        return {"refreshed": refreshed}
    except Exception as exc:
        logger.exception("Error during bulk profile refresh (triggered by admin %s)", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /quality-metrics ──────────────────────────────────────────────────────

@router.get("/quality-metrics")
async def quality_metrics(user: dict = Depends(get_current_user)):
    """Score quality and engagement rates derived from interaction and score collections."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    # Average score per type from cached result sets.
    # recommendation_scores documents are expected to have:
    #   { category: str, results: [ { score: float, ... }, ... ] }
    avg_score_pipeline = [
        {"$unwind": "$results"},
        {
            "$group": {
                "_id": "$category",
                "avg_score": {"$avg": "$results.score"},
            }
        },
    ]
    score_rows = await db.recommendation_scores.aggregate(avg_score_pipeline).to_list(20)
    avg_score_by_type: dict = {r["_id"]: round(r["avg_score"] or 0, 4) for r in score_rows if r.get("_id")}
    for t in _ALL_TYPES:
        avg_score_by_type.setdefault(t, 0.0)

    # Total recommendations served = total documents across all score result sets
    served_pipeline = [
        {"$project": {"result_count": {"$size": {"$ifNull": ["$results", []]}}}},
        {"$group": {"_id": None, "total_served": {"$sum": "$result_count"}}},
    ]
    served_rows = await db.recommendation_scores.aggregate(served_pipeline).to_list(1)
    total_served = (served_rows[0]["total_served"] if served_rows else 0) or 0

    total_interactions = await db.recommendation_interactions.count_documents({})
    total_dismissed = await db.recommendation_interactions.count_documents({"action": "dismissed"})
    total_bookmarked = await db.recommendation_interactions.count_documents({"action": "bookmarked"})

    interaction_rate = round(total_interactions / total_served, 4) if total_served > 0 else 0.0
    dismissal_rate = round(total_dismissed / total_served, 4) if total_served > 0 else 0.0
    bookmark_rate = round(total_bookmarked / total_served, 4) if total_served > 0 else 0.0

    return {
        "avg_score_by_type": avg_score_by_type,
        "interaction_rate": interaction_rate,
        "dismissal_rate": dismissal_rate,
        "bookmark_rate": bookmark_rate,
    }
