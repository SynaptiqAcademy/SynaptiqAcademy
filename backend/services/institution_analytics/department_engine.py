"""Institution Analytics — Department Engine.

Groups institution members by department and aggregates per-department metrics:
publications, citations, grants, and impact scores.
"""
from __future__ import annotations

import asyncio
from typing import Any

from bson import ObjectId

_DEFAULT_DEPARTMENT = "General Research"


async def _get_members_with_departments(institution_id: str, db) -> list[dict]:
    """Return list of {user_id, department} for active members."""
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "active"},
        {"user_id": 1, "department": 1},
    ).to_list(5000)
    return rows


async def _enrich_with_user_department(member_rows: list[dict], db) -> list[dict]:
    """For members without department in membership, fall back to users.department."""
    missing = [r for r in member_rows if not r.get("department")]
    if not missing:
        return member_rows

    missing_ids = [r["user_id"] for r in missing if r.get("user_id")]
    user_ids_as_oid = [ObjectId(uid) if ObjectId.is_valid(uid) else uid for uid in missing_ids]

    user_rows = await db.users.find(
        {"_id": {"$in": user_ids_as_oid}},
        {"department": 1},
    ).to_list(len(missing_ids))
    user_dept_map = {str(u["_id"]): u.get("department", "") for u in user_rows}

    enriched = []
    for row in member_rows:
        dept = row.get("department") or user_dept_map.get(row.get("user_id", ""), "") or _DEFAULT_DEPARTMENT
        enriched.append({**row, "department": dept})
    return enriched


async def _compute_dept_stats(dept_name: str, dept_member_ids: list[str], db) -> dict:
    """Compute stats for a single department."""
    if not dept_member_ids:
        return {
            "department": dept_name,
            "member_count": 0,
            "total_publications": 0,
            "total_citations": 0,
            "grants_awarded": 0,
            "avg_impact_score": 0.0,
        }

    (
        pub_agg,
        grants_awarded,
        impact_agg,
    ) = await asyncio.gather(
        db.publications.aggregate([
            {"$match": {"author_ids": {"$in": dept_member_ids}}},
            {"$group": {
                "_id": None,
                "count": {"$sum": 1},
                "citations": {"$sum": {"$ifNull": ["$citation_count", 0]}},
            }},
        ]).to_list(1),
        db.grant_applications.count_documents({
            "user_id": {"$in": dept_member_ids},
            "status": {"$in": ["funded", "awarded", "approved"]},
        }),
        db.research_impact.aggregate([
            {"$match": {"user_id": {"$in": dept_member_ids}}},
            {"$group": {"_id": None, "avg_sis": {"$avg": {"$ifNull": ["$sis_total", 0]}}}},
        ]).to_list(1),
    )

    pub_row = pub_agg[0] if pub_agg else {}
    return {
        "department": dept_name,
        "member_count": len(dept_member_ids),
        "total_publications": int(pub_row.get("count", 0)),
        "total_citations": int(pub_row.get("citations", 0)),
        "grants_awarded": grants_awarded,
        "avg_impact_score": round(float(impact_agg[0].get("avg_sis", 0.0)), 2) if impact_agg else 0.0,
    }


async def get_department_analytics(institution_id: str, db) -> list:
    """Return per-department analytics sorted by total_publications descending."""
    member_rows = await _get_members_with_departments(institution_id, db)
    if not member_rows:
        return []

    enriched = await _enrich_with_user_department(member_rows, db)

    # Group by department
    dept_map: dict[str, list[str]] = {}
    for row in enriched:
        dept = row.get("department") or _DEFAULT_DEPARTMENT
        uid = row.get("user_id", "")
        if uid:
            dept_map.setdefault(dept, []).append(uid)

    # Compute stats for all departments in parallel
    dept_names = list(dept_map.keys())
    stats_list = await asyncio.gather(*[
        _compute_dept_stats(name, dept_map[name], db)
        for name in dept_names
    ])

    return sorted(stats_list, key=lambda x: x["total_publications"], reverse=True)


async def compare_departments(institution_id: str, db) -> dict:
    """Return department data formatted for side-by-side comparison."""
    departments = await get_department_analytics(institution_id, db)
    return {
        "departments": departments,
        "metrics": ["members", "publications", "citations", "grants", "avg_impact"],
    }
