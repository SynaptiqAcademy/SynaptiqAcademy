"""Institution Analytics — KPI Engine.

Computes comprehensive KPIs for an institution from real MongoDB data.
Results are cached in `institution_kpis` collection with a 2-hour TTL.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId


def _to_str(oid) -> str:
    if oid is None:
        return ""
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_member_ids(institution_id: str, db) -> list[str]:
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "active"},
        {"user_id": 1},
    ).to_list(5000)
    return [r["user_id"] for r in rows if r.get("user_id")]


async def compute_institution_kpis(institution_id: str, db) -> dict:
    """Compute all KPIs for the institution from live MongoDB data."""
    member_ids = await _get_member_ids(institution_id, db)
    total_members = len(member_ids)

    if not member_ids:
        result = _empty_kpis(institution_id, total_members)
        await _cache_kpis(institution_id, result, db)
        return result

    # Parallel queries
    (
        active_researchers_count,
        pub_docs,
        impact_doc,
        projects_created,
        projects_member,
        collab_created,
        collab_participants,
        grant_apps_all,
        grant_apps_awarded,
        reviewer_agg,
        impact_agg,
        reputation_agg,
        h_index_agg,
        lessons_count,
    ) = await asyncio.gather(
        db.users.count_documents({
            "_id": {"$in": [ObjectId(uid) if ObjectId.is_valid(uid) else uid for uid in member_ids]},
            "research_interests": {"$exists": True, "$not": {"$size": 0}},
        }),
        db.publications.aggregate([
            {"$match": {"author_ids": {"$in": member_ids}}},
            {"$group": {"_id": None, "count": {"$sum": 1}, "citations": {"$sum": {"$ifNull": ["$citation_count", 0]}}}},
        ]).to_list(1),
        db.institution_impact.find_one({"institution_id": institution_id}),
        db.projects.count_documents({"created_by": {"$in": member_ids}}),
        db.projects.count_documents({"members.user_id": {"$in": member_ids}}),
        db.collaborations.count_documents({"created_by": {"$in": member_ids}}),
        db.collaborations.count_documents({"participants": {"$in": member_ids}}),
        db.grant_applications.count_documents({"user_id": {"$in": member_ids}}),
        db.grant_applications.count_documents({
            "user_id": {"$in": member_ids},
            "status": {"$in": ["funded", "awarded", "approved"]},
        }),
        db.reviewer_profiles.aggregate([
            {"$match": {"user_id": {"$in": member_ids}}},
            {"$group": {"_id": None, "total_reviews": {"$sum": {"$ifNull": ["$reviews_completed", 0]}}}},
        ]).to_list(1),
        db.research_impact.aggregate([
            {"$match": {"user_id": {"$in": member_ids}}},
            {"$group": {"_id": None, "avg_sis": {"$avg": {"$ifNull": ["$sis_total", 0]}}}},
        ]).to_list(1),
        db.research_reputation.aggregate([
            {"$match": {"user_id": {"$in": member_ids}}},
            {"$group": {"_id": None, "avg_rep": {"$avg": {"$ifNull": ["$overall_score", 0]}}}},
        ]).to_list(1),
        db.research_impact.aggregate([
            {"$match": {"user_id": {"$in": member_ids}}},
            {"$group": {"_id": None, "top_h": {"$max": {"$ifNull": ["$h_index", 0]}}}},
        ]).to_list(1),
        db.teaching_lessons.count_documents({"created_by": {"$in": member_ids}}),
    )

    # Derived values
    pub_row = pub_docs[0] if pub_docs else {}
    total_publications = int(pub_row.get("count", 0))
    total_citations = int(pub_row.get("citations", 0))

    h_index_composite = 0
    if impact_doc and impact_doc.get("components"):
        h_index_composite = impact_doc["components"].get("h_index_composite", 0)

    total_projects = projects_created + projects_member
    total_collaborations = collab_created + collab_participants

    grant_success_rate = round(
        (grant_apps_awarded / max(grant_apps_all, 1)) * 100, 2
    )
    total_reviews = int(reviewer_agg[0].get("total_reviews", 0)) if reviewer_agg else 0
    avg_impact_score = round(float(impact_agg[0].get("avg_sis", 0.0)), 2) if impact_agg else 0.0
    avg_reputation = round(float(reputation_agg[0].get("avg_rep", 0.0)), 2) if reputation_agg else 0.0
    top_h_index = int(h_index_agg[0].get("top_h", 0)) if h_index_agg else 0

    result: dict[str, Any] = {
        "institution_id": institution_id,
        "total_members": total_members,
        "active_researchers": active_researchers_count,
        "total_publications": total_publications,
        "total_citations": total_citations,
        "h_index_composite": h_index_composite,
        "total_projects": total_projects,
        "total_collaborations": total_collaborations,
        "grant_applications_count": grant_apps_all,
        "grants_awarded_count": grant_apps_awarded,
        "grant_success_rate": grant_success_rate,
        "total_reviews": total_reviews,
        "avg_impact_score": avg_impact_score,
        "avg_reputation": avg_reputation,
        "top_h_index": top_h_index,
        "total_lessons": lessons_count,
        "computed_at": _now().isoformat(),
    }

    await _cache_kpis(institution_id, result, db)
    return result


def _empty_kpis(institution_id: str, total_members: int) -> dict:
    return {
        "institution_id": institution_id,
        "total_members": total_members,
        "active_researchers": 0,
        "total_publications": 0,
        "total_citations": 0,
        "h_index_composite": 0,
        "total_projects": 0,
        "total_collaborations": 0,
        "grant_applications_count": 0,
        "grants_awarded_count": 0,
        "grant_success_rate": 0.0,
        "total_reviews": 0,
        "avg_impact_score": 0.0,
        "avg_reputation": 0.0,
        "top_h_index": 0,
        "total_lessons": 0,
        "computed_at": _now().isoformat(),
    }


async def _cache_kpis(institution_id: str, kpis: dict, db) -> None:
    await db.institution_kpis.update_one(
        {"institution_id": institution_id},
        {"$set": {**kpis, "cached_at": _now()}},
        upsert=True,
    )


async def get_institution_kpis(institution_id: str, db) -> dict:
    """Return cached KPIs if fresh (< 2h), otherwise recompute."""
    cached = await db.institution_kpis.find_one({"institution_id": institution_id})
    if cached:
        cached_at = cached.get("cached_at")
        if cached_at and isinstance(cached_at, datetime):
            age = _now() - cached_at.replace(tzinfo=timezone.utc) if cached_at.tzinfo is None else _now() - cached_at
            if age < timedelta(hours=2):
                cached.pop("_id", None)
                cached.pop("cached_at", None)
                return cached
    return await compute_institution_kpis(institution_id, db)


async def get_kpi_history(institution_id: str, db, months: int = 12) -> list:
    """Return historical KPI snapshots sorted by snapshot_date descending."""
    rows = await db.institution_analytics_history.find(
        {"institution_id": institution_id},
        {"_id": 0, "snapshot_date": 1, "kpis": 1},
    ).sort("snapshot_date", -1).limit(months).to_list(months)
    return rows
