"""Admin Reputation Analytics — Phase XX.

Read-only analytics for platform administrators. No score modification.
Fraud detection, level distribution, fastest-growing researchers.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from services.reputation.events import compute_rankings
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/admin/reputation", tags=["admin-reputation"])


def _require_admin(user: dict) -> None:
    zt_check(user, "admin", "admin")


@router.get("/stats")
async def reputation_stats(user: dict = Depends(get_current_user)):
    """Platform-wide reputation stats: totals, averages, score distribution."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    total_users = await db.research_reputation.count_documents({})
    total_events = await db.research_reputation_events.count_documents({})

    # Average overall score
    avg_pipeline = [
        {"$group": {"_id": None, "avg_score": {"$avg": "$overall_score"}}},
    ]
    avg_result = await db.research_reputation.aggregate(avg_pipeline).to_list(1)
    avg_score = round((avg_result[0]["avg_score"] if avg_result else 0) or 0, 1)

    # Score distribution by level
    dist_pipeline = [
        {
            "$group": {
                "_id": "$reputation_level",
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$overall_score"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    score_dist = await db.research_reputation.aggregate(dist_pipeline).to_list(10)

    return {
        "total_users_with_scores": total_users,
        "total_reputation_events": total_events,
        "average_overall_score": avg_score,
        "score_distribution_by_level": [
            {
                "level": r["_id"],
                "count": r["count"],
                "avg_score": round((r["avg_score"] or 0), 1),
            }
            for r in score_dist
        ],
    }


@router.get("/top-researchers")
async def top_researchers(
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """Top N researchers globally with user details."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
        {"$sort": {"overall_score": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "users",
                "let": {"uid": "$user_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$uid"]}}},
                    {
                        "$project": {
                            "full_name": 1,
                            "email": 1,
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

    rows = await db.research_reputation.aggregate(pipeline).to_list(limit)
    results = []
    for i, r in enumerate(rows):
        ui = r.get("user_info") or {}
        results.append({
            "rank": r.get("rank_global") or (i + 1),
            "user_id": r["user_id"],
            "full_name": ui.get("full_name", "—"),
            "email": ui.get("email"),
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

    return {"total": len(results), "researchers": results}


@router.get("/badge-distribution")
async def badge_distribution(user: dict = Depends(get_current_user)):
    """Count of each badge type awarded across all users."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
        {"$unwind": "$badges"},
        {
            "$group": {
                "_id": "$badges.code",
                "count": {"$sum": 1},
                "label": {"$first": "$badges.label"},
                "rarity": {"$first": "$badges.rarity"},
            }
        },
        {"$sort": {"count": -1}},
    ]

    rows = await db.research_reputation_badges.aggregate(pipeline).to_list(50)
    return {
        "total_badge_types": len(rows),
        "distribution": [
            {
                "code": r["_id"],
                "label": r.get("label", r["_id"]),
                "rarity": r.get("rarity", "common"),
                "awarded_count": r["count"],
            }
            for r in rows
        ],
    }


@router.get("/events")
async def recent_platform_events(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """Recent platform-wide reputation events (paginated)."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    skip = (page - 1) * limit
    cursor = db.research_reputation_events.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit)

    events = await cursor.to_list(limit)
    total = await db.research_reputation_events.count_documents({})

    # Enrich with user names
    for ev in events:
        uid = ev.get("user_id")
        if uid:
            try:
                u = await db.users.find_one(
                    {"_id": ObjectId(uid)}, {"full_name": 1, "email": 1}
                )
                ev["full_name"] = (u or {}).get("full_name", "—")
                ev["email"] = (u or {}).get("email")
            except Exception:
                ev["full_name"] = "—"

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "events": events,
    }


@router.get("/fraud-alerts")
async def fraud_alerts(user: dict = Depends(get_current_user)):
    """Users with suspicious reputation activity patterns."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    cutoff_1d = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    # Users with >50 events in the last 7 days
    pipeline_7d = [
        {"$match": {"created_at": {"$gte": cutoff_7d}}},
        {"$group": {"_id": "$user_id", "event_count_7d": {"$sum": 1}}},
        {"$match": {"event_count_7d": {"$gt": 50}}},
        {"$sort": {"event_count_7d": -1}},
    ]
    high_volume = await db.research_reputation_events.aggregate(pipeline_7d).to_list(100)

    # Users with >5 events of the same type in one day
    pipeline_same_type = [
        {"$match": {"created_at": {"$gte": cutoff_1d}}},
        {
            "$group": {
                "_id": {"user_id": "$user_id", "event_type": "$event_type"},
                "count": {"$sum": 1},
            }
        },
        {"$match": {"count": {"$gt": 5}}},
        {"$sort": {"count": -1}},
    ]
    same_type_spam = await db.research_reputation_events.aggregate(pipeline_same_type).to_list(100)

    # Collect flagged user_ids
    flagged: dict[str, dict] = {}

    for r in high_volume:
        uid = r["_id"]
        flagged[uid] = flagged.get(uid, {
            "user_id": uid,
            "total_events_7d": 0,
            "flags": [],
        })
        flagged[uid]["total_events_7d"] = r["event_count_7d"]
        flagged[uid]["flags"].append(f"High volume: {r['event_count_7d']} events in 7 days")

    for r in same_type_spam:
        uid = r["_id"]["user_id"]
        etype = r["_id"]["event_type"]
        flagged[uid] = flagged.get(uid, {
            "user_id": uid,
            "total_events_7d": 0,
            "flags": [],
        })
        flagged[uid]["flags"].append(
            f"Spam: {r['count']} '{etype}' events in 24h"
        )

    # Enrich with user info
    alerts = []
    for uid, info in flagged.items():
        try:
            u = await db.users.find_one(
                {"_id": ObjectId(uid)}, {"full_name": 1, "email": 1}
            )
            info["full_name"] = (u or {}).get("full_name", "—")
            info["email"] = (u or {}).get("email")
        except Exception:
            info["full_name"] = "—"
        info["flag_reason"] = "; ".join(info.pop("flags", []))
        alerts.append(info)

    return {
        "total_flagged": len(alerts),
        "alerts": sorted(alerts, key=lambda x: x.get("total_events_7d", 0), reverse=True),
    }


@router.get("/level-distribution")
async def level_distribution(user: dict = Depends(get_current_user)):
    """Count of users at each reputation level (1-7)."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    from services.reputation.events import REPUTATION_LEVELS

    pipeline = [
        {
            "$group": {
                "_id": "$reputation_level",
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$overall_score"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await db.research_reputation.aggregate(pipeline).to_list(10)
    row_map = {r["_id"]: r for r in rows}

    distribution = []
    for lvl in REPUTATION_LEVELS:
        level_num = lvl["level"]
        row = row_map.get(level_num, {})
        distribution.append({
            "level": level_num,
            "label": lvl["label"],
            "min_score": lvl["min"],
            "max_score": lvl["max"],
            "user_count": row.get("count", 0),
            "avg_score": round((row.get("avg_score") or 0), 1),
        })

    return {
        "total_levels": len(REPUTATION_LEVELS),
        "distribution": distribution,
    }


@router.get("/fastest-growing")
async def fastest_growing(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    """Users with most points gained in the last N days."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": "$user_id",
                "points_gained": {"$sum": "$points"},
                "event_count": {"$sum": 1},
            }
        },
        {"$sort": {"points_gained": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "users",
                "let": {"uid": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$uid"]}}},
                    {"$project": {"full_name": 1, "email": 1, "institution": 1}},
                ],
                "as": "user_info",
            }
        },
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
    ]

    rows = await db.research_reputation_events.aggregate(pipeline).to_list(limit)
    results = []
    for i, r in enumerate(rows):
        ui = r.get("user_info") or {}
        results.append({
            "rank": i + 1,
            "user_id": r["_id"],
            "full_name": ui.get("full_name", "—"),
            "email": ui.get("email"),
            "institution": ui.get("institution"),
            "points_gained": r["points_gained"],
            "event_count": r["event_count"],
        })

    return {
        "period_days": days,
        "total": len(results),
        "fastest_growing": results,
    }


@router.post("/rankings/compute")
async def admin_compute_rankings(user: dict = Depends(get_current_user)):
    """Admin trigger for full ranking recomputation."""
    _require_admin(user)
    result = await compute_rankings()
    return {**result, "triggered_by": user.get("id"), "admin": True}
