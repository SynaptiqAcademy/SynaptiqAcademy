"""Admin Impact Analytics — Phase XXII.

Platform-wide research impact statistics for administrators.

Endpoints:
  GET  /api/admin/impact/stats             — platform-wide SIS stats
  GET  /api/admin/impact/top-researchers   — top N researchers by metric
  GET  /api/admin/impact/top-institutions  — top 20 institutions by avg SIS
  GET  /api/admin/impact/top-countries     — top 20 countries by avg SIS
  GET  /api/admin/impact/growth-trends     — monthly SIS averages across all users
  GET  /api/admin/impact/research-areas    — top areas by avg impact score
  POST /api/admin/impact/refresh-all       — background recompute for all users
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger("synaptiq.admin_impact")
router = APIRouter(prefix="/api/admin/impact", tags=["admin-impact"])

# ─────────────────────────── service imports ─────────────────────────────────

try:
    from services.impact.snapshot_service import (
        get_platform_impact_summary,
        compute_and_store_research_impact,
    )
    _snapshot_service_available = True
except ImportError:
    _snapshot_service_available = False
    log.warning("services.impact.snapshot_service not available (admin_impact)")


# ─────────────────────────── helpers ─────────────────────────────────────────

def _require_admin(user: dict) -> None:
    zt_check(user, "admin", "admin")


def _oid_to_str(doc: dict) -> dict:
    """Recursively convert ObjectId and datetime values in a dict to JSON-safe types."""
    if not isinstance(doc, dict):
        return doc
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _oid_to_str(v)
        elif isinstance(v, list):
            out[k] = [
                _oid_to_str(i) if isinstance(i, dict)
                else (str(i) if isinstance(i, ObjectId)
                      else (i.isoformat() if isinstance(i, datetime) else i))
                for i in v
            ]
        else:
            out[k] = v
    return out


_SIS_BUCKETS = [
    (0,    499,  "New Researcher (0-499)"),
    (500,  1499, "Emerging Scholar (500-1499)"),
    (1500, 2999, "Established Researcher (1500-2999)"),
    (3000, 4999, "Senior Researcher (3000-4999)"),
    (5000, 6999, "Principal Investigator (5000-6999)"),
    (7000, 8999, "Distinguished Scholar (7000-8999)"),
    (9000, None, "Eminent Researcher (9000+)"),
]

_VALID_METRICS = {"sis", "citations", "h_index", "collaborations"}

_METRIC_FIELD_MAP = {
    "sis":            "total",
    "citations":      "total_citations",
    "h_index":        "h_index",
    "collaborations": "collaboration_count",
}


# ─────────────────────────── endpoints ───────────────────────────────────────

@router.get("/stats")
async def platform_impact_stats(user: dict = Depends(get_current_user)):
    """Platform-wide impact statistics."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    if _snapshot_service_available:
        try:
            summary = await get_platform_impact_summary(db)
            return _oid_to_str(summary)
        except Exception as exc:
            log.warning("get_platform_impact_summary failed, falling back: %s", exc)

    # Fallback: compute directly from research_impact collection.
    total_scored = await db.research_impact.count_documents({})

    agg_pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_sis": {"$avg": {"$ifNull": ["$total", "$sis_score"]}},
                "total_publications": {"$sum": {"$ifNull": ["$publication_count", 0]}},
                "total_citations": {"$sum": {"$ifNull": ["$total_citations", 0]}},
                "avg_h_index": {"$avg": {"$ifNull": ["$h_index", 0]}},
                "avg_collaboration_count": {"$avg": {"$ifNull": ["$collaboration_count", 0]}},
            }
        }
    ]
    agg_result = await db.research_impact.aggregate(agg_pipeline).to_list(1)
    agg = agg_result[0] if agg_result else {}

    # SIS bucket distribution.
    bucket_counts = []
    for lo, hi, label in _SIS_BUCKETS:
        if hi is None:
            match_filter = {"$gte": lo}
        else:
            match_filter = {"$gte": lo, "$lte": hi}

        count = await db.research_impact.count_documents(
            {"$or": [
                {"total": match_filter},
                {"sis_score": match_filter},
            ]}
        )
        bucket_counts.append({"label": label, "count": count})

    return {
        "total_researchers_scored": total_scored,
        "avg_sis": round(float(agg.get("avg_sis") or 0), 2),
        "total_publications": int(agg.get("total_publications") or 0),
        "total_citations": int(agg.get("total_citations") or 0),
        "avg_h_index": round(float(agg.get("avg_h_index") or 0), 2),
        "avg_collaboration_count": round(float(agg.get("avg_collaboration_count") or 0), 2),
        "by_sis_bucket": bucket_counts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/top-researchers")
async def top_researchers(
    metric: str = Query("sis", regex=r"^(sis|citations|h_index|collaborations)$"),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """Top researchers by specified metric, joined with user details."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    sort_field = _METRIC_FIELD_MAP.get(metric, "total")

    pipeline = [
        {"$sort": {sort_field: -1}},
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
        {
            "$project": {
                "user_id": 1,
                "total_sis": {"$ifNull": ["$total", "$sis_score"]},
                "h_index": 1,
                "total_citations": 1,
                "collaboration_count": 1,
                "publication_count": 1,
                "label": 1,
                "computed_at": 1,
                "full_name": "$user_info.full_name",
                "email": "$user_info.email",
                "institution": "$user_info.institution",
                "country": "$user_info.country",
                "academic_role": "$user_info.academic_role",
                "avatar_url": "$user_info.avatar_url",
            }
        },
    ]

    rows = await db.research_impact.aggregate(pipeline).to_list(limit)
    return [_oid_to_str(r) for r in rows]


@router.get("/top-institutions")
async def top_institutions(user: dict = Depends(get_current_user)):
    """Top 20 institutions by average SIS, with researcher count and publications."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
        # Join with recommendation_profiles for research institution field,
        # then fall back to users.institution.
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
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {
            "$group": {
                "_id": "$user_info.institution",
                "researcher_count": {"$sum": 1},
                "avg_sis": {"$avg": {"$ifNull": ["$total", "$sis_score"]}},
                "total_publications": {"$sum": {"$ifNull": ["$publication_count", 0]}},
            }
        },
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"avg_sis": -1}},
        {"$limit": 20},
        {
            "$project": {
                "_id": 0,
                "institution": "$_id",
                "researcher_count": 1,
                "avg_sis": {"$round": ["$avg_sis", 2]},
                "total_publications": 1,
            }
        },
    ]

    rows = await db.research_impact.aggregate(pipeline).to_list(20)
    return rows


@router.get("/top-countries")
async def top_countries(user: dict = Depends(get_current_user)):
    """Top 20 countries by average SIS."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
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
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {
            "$group": {
                "_id": "$user_info.country",
                "researcher_count": {"$sum": 1},
                "avg_sis": {"$avg": {"$ifNull": ["$total", "$sis_score"]}},
                "total_publications": {"$sum": {"$ifNull": ["$publication_count", 0]}},
            }
        },
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"avg_sis": -1}},
        {"$limit": 20},
        {
            "$project": {
                "_id": 0,
                "country": "$_id",
                "researcher_count": 1,
                "avg_sis": {"$round": ["$avg_sis", 2]},
                "total_publications": 1,
            }
        },
    ]

    rows = await db.research_impact.aggregate(pipeline).to_list(20)
    return rows


@router.get("/growth-trends")
async def growth_trends(user: dict = Depends(get_current_user)):
    """Month-by-month aggregate of average SIS across all users from history."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
        {
            "$addFields": {
                "month_str": {
                    "$cond": {
                        "if": {"$eq": [{"$type": "$created_at"}, "date"]},
                        "then": {
                            "$dateToString": {
                                "format": "%Y-%m",
                                "date": "$created_at",
                            }
                        },
                        "else": {
                            "$substr": [
                                {"$ifNull": ["$created_at", ""]},
                                0, 7
                            ]
                        },
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$month_str",
                "avg_sis": {"$avg": {"$ifNull": ["$total", "$sis_score"]}},
                "count": {"$sum": 1},
            }
        },
        {"$match": {"_id": {"$ne": "", "$ne": None}}},
        {"$sort": {"_id": 1}},
        {
            "$project": {
                "_id": 0,
                "month": "$_id",
                "avg_sis": {"$round": ["$avg_sis", 2]},
                "count": 1,
            }
        },
    ]

    rows = await db.research_impact_history.aggregate(pipeline).to_list(120)
    return {"months": rows}


@router.get("/research-areas")
async def top_research_areas(user: dict = Depends(get_current_user)):
    """Top 20 research areas by average SIS."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
        {
            "$lookup": {
                "from": "recommendation_profiles",
                "let": {"uid": "$user_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$user_id", "$$uid"]}}},
                    {"$project": {"research_areas": 1}},
                ],
                "as": "rec_profile",
            }
        },
        {"$unwind": {"path": "$rec_profile", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "areas": {"$ifNull": ["$rec_profile.research_areas", []]},
            }
        },
        {"$unwind": {"path": "$areas", "preserveNullAndEmptyArrays": False}},
        {
            "$group": {
                "_id": "$areas",
                "researcher_count": {"$sum": 1},
                "avg_sis": {"$avg": {"$ifNull": ["$total", "$sis_score"]}},
            }
        },
        {"$match": {"_id": {"$ne": None, "$ne": ""}}},
        {"$sort": {"avg_sis": -1}},
        {"$limit": 20},
        {
            "$project": {
                "_id": 0,
                "area": "$_id",
                "researcher_count": 1,
                "avg_sis": {"$round": ["$avg_sis", 2]},
            }
        },
    ]

    rows = await db.research_impact.aggregate(pipeline).to_list(20)
    return {"research_areas": rows}


@router.post("/refresh-all")
async def refresh_all_users(user: dict = Depends(get_current_user)):
    """Trigger background recompute for up to 100 users with existing impact docs."""
    _require_admin(user)

    if not _snapshot_service_available:
        raise HTTPException(
            status_code=503,
            detail="Snapshot service not available. Cannot trigger refresh.",
        )

    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    # Collect up to 100 users who already have a research_impact document.
    docs = await db.research_impact.find(
        {},
        {"user_id": 1},
    ).limit(100).to_list(100)

    user_ids = [d["user_id"] for d in docs if d.get("user_id")]

    async def _recompute_all(uid_list: list[str]) -> None:
        for uid in uid_list:
            try:
                await compute_and_store_research_impact(uid, db)
            except Exception as exc:
                log.warning("Background refresh failed for user %s: %s", uid, exc)

    asyncio.create_task(_recompute_all(user_ids))

    return {"queued": len(user_ids)}
