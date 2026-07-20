"""Institution Analytics — Grant Engine.

Analyses grant performance and funding trends for an institution's members.
All data sourced from real MongoDB collections: grant_applications + grants.
"""
from __future__ import annotations

import asyncio
from typing import Any


async def _get_member_ids(institution_id: str, db) -> list[str]:
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "active"},
        {"user_id": 1},
    ).to_list(5000)
    return [r["user_id"] for r in rows if r.get("user_id")]


async def get_grant_performance(institution_id: str, db) -> dict:
    """Comprehensive grant performance breakdown."""
    member_ids = await _get_member_ids(institution_id, db)

    if not member_ids:
        return _empty_grant_performance()

    apps = await db.grant_applications.find(
        {"user_id": {"$in": member_ids}},
        {
            "user_id": 1, "grant_id": 1, "status": 1,
            "amount_requested": 1, "amount_awarded": 1,
            "created_at": 1, "collaboration_id": 1,
        },
    ).to_list(10000)

    if not apps:
        return _empty_grant_performance()

    # Collect unique grant_ids to join with grants collection
    grant_ids = list({a["grant_id"] for a in apps if a.get("grant_id")})
    grants_docs = await db.grants.find(
        {"_id": {"$in": grant_ids}},
        {"title": 1, "funder": 1, "amount": 1, "research_areas": 1},
    ).to_list(len(grant_ids) + 1) if grant_ids else []
    grants_map = {str(g["_id"]): g for g in grants_docs}

    awarded_statuses = {"funded", "awarded", "approved"}

    total_applications = len(apps)
    total_awarded = sum(1 for a in apps if a.get("status") in awarded_statuses)
    success_rate = round((total_awarded / max(total_applications, 1)) * 100, 2)

    total_funding_secured = sum(
        float(a.get("amount_awarded") or 0)
        for a in apps
        if a.get("status") in awarded_statuses
    )

    # Funding by source (funder)
    funder_map: dict[str, dict[str, Any]] = {}
    for app in apps:
        grant_doc = grants_map.get(str(app.get("grant_id", "")), {})
        funder = grant_doc.get("funder") or "Unknown"
        entry = funder_map.setdefault(funder, {"funder": funder, "count": 0, "total_amount": 0.0})
        entry["count"] += 1
        if app.get("status") in awarded_statuses:
            entry["total_amount"] += float(app.get("amount_awarded") or 0)
    funding_by_source = sorted(funder_map.values(), key=lambda x: x["total_amount"], reverse=True)

    # Funding by year
    year_map: dict[int, dict[str, Any]] = {}
    for app in apps:
        created = app.get("created_at")
        yr = created.year if created and hasattr(created, "year") else 0
        if yr == 0:
            continue
        entry = year_map.setdefault(yr, {"year": yr, "applications": 0, "awarded": 0, "total_funding": 0.0})
        entry["applications"] += 1
        if app.get("status") in awarded_statuses:
            entry["awarded"] += 1
            entry["total_funding"] += float(app.get("amount_awarded") or 0)
    funding_by_year = sorted(year_map.values(), key=lambda x: x["year"])

    # Consortium count: apps with a collaboration_id
    consortium_count = sum(1 for a in apps if a.get("collaboration_id"))

    # Average grant size among awarded
    awarded_amounts = [float(a.get("amount_awarded") or 0) for a in apps if a.get("status") in awarded_statuses]
    avg_grant_size = round(sum(awarded_amounts) / max(len(awarded_amounts), 1), 2)

    return {
        "total_applications": total_applications,
        "total_awarded": total_awarded,
        "success_rate": success_rate,
        "total_funding_secured": round(total_funding_secured, 2),
        "funding_by_source": funding_by_source,
        "funding_by_year": funding_by_year,
        "consortium_count": consortium_count,
        "avg_grant_size": avg_grant_size,
    }


def _empty_grant_performance() -> dict:
    return {
        "total_applications": 0,
        "total_awarded": 0,
        "success_rate": 0.0,
        "total_funding_secured": 0.0,
        "funding_by_source": [],
        "funding_by_year": [],
        "consortium_count": 0,
        "avg_grant_size": 0.0,
    }


async def get_funding_trends(institution_id: str, db, years: int = 5) -> list:
    """Year-by-year funding secured trend."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return []

    apps = await db.grant_applications.find(
        {"user_id": {"$in": member_ids}},
        {"status": 1, "amount_awarded": 1, "created_at": 1},
    ).to_list(10000)

    awarded_statuses = {"funded", "awarded", "approved"}

    year_map: dict[int, dict[str, Any]] = {}
    for app in apps:
        created = app.get("created_at")
        yr = created.year if created and hasattr(created, "year") else 0
        if yr == 0:
            continue
        entry = year_map.setdefault(yr, {
            "year": yr,
            "applications": 0,
            "awarded": 0,
            "success_rate": 0.0,
            "total_funding": 0.0,
        })
        entry["applications"] += 1
        if app.get("status") in awarded_statuses:
            entry["awarded"] += 1
            entry["total_funding"] += float(app.get("amount_awarded") or 0)

    result = []
    for yr, data in sorted(year_map.items()):
        data["success_rate"] = round(
            (data["awarded"] / max(data["applications"], 1)) * 100, 2
        )
        data["total_funding"] = round(data["total_funding"], 2)
        result.append(data)

    # Limit to requested years from most recent
    return result[-years:] if len(result) > years else result
