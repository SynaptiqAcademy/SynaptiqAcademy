"""Institution Analytics — Research Performance Engine.

Aggregates publication trends, research area distribution, and performance
indicators from real MongoDB data.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


def _now_year() -> int:
    return datetime.now(timezone.utc).year


async def _get_member_ids(institution_id: str, db) -> list[str]:
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "active"},
        {"user_id": 1},
    ).to_list(5000)
    return [r["user_id"] for r in rows if r.get("user_id")]


async def get_research_performance(institution_id: str, db) -> dict:
    """Comprehensive research performance breakdown."""
    member_ids = await _get_member_ids(institution_id, db)

    if not member_ids:
        return _empty_performance()

    current_year = _now_year()
    cutoff_year = current_year - 10

    (
        pubs_by_year_raw,
        users_raw,
        pub_summary,
        intl_pubs,
        recent_pubs,
    ) = await asyncio.gather(
        # Publications by year (last 10 years)
        db.publications.aggregate([
            {"$match": {
                "author_ids": {"$in": member_ids},
                "status": "published",
                "year": {"$gte": cutoff_year},
            }},
            {"$group": {
                "_id": "$year",
                "count": {"$sum": 1},
                "citations": {"$sum": {"$ifNull": ["$citation_count", 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]).to_list(20),
        # Users for research interests
        db.users.find(
            {"_id": {"$in": [ObjectId(uid) if ObjectId.is_valid(uid) else uid for uid in member_ids]}},
            {"research_interests": 1},
        ).to_list(5000),
        # Total publications + citations
        db.publications.aggregate([
            {"$match": {"author_ids": {"$in": member_ids}}},
            {"$group": {
                "_id": None,
                "count": {"$sum": 1},
                "citations": {"$sum": {"$ifNull": ["$citation_count", 0]}},
            }},
        ]).to_list(1),
        # International publications: has at least one author NOT in member_ids
        db.publications.count_documents({
            "author_ids": {
                "$in": member_ids,
                "$not": {"$all": member_ids},  # not exclusively members
            },
        }),
        # Publications in last 12 months (approximated by year)
        db.publications.count_documents({
            "author_ids": {"$in": member_ids},
            "year": {"$gte": current_year - 1},
        }),
    )

    # Build publications_by_year list
    publications_by_year = [
        {"year": row["_id"], "count": row["count"], "citations": row["citations"]}
        for row in pubs_by_year_raw
        if row["_id"] is not None
    ]

    # Aggregate research_interests
    interest_counts: dict[str, int] = {}
    for user in users_raw:
        for interest in (user.get("research_interests") or []):
            if interest:
                interest_counts[str(interest)] = interest_counts.get(str(interest), 0) + 1
    top_research_areas = sorted(
        [{"area": k, "count": v} for k, v in interest_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    pub_row = pub_summary[0] if pub_summary else {}
    total_publications = int(pub_row.get("count", 0))
    total_citations = int(pub_row.get("citations", 0))

    international_rate = round((intl_pubs / max(total_publications, 1)) * 100, 2)
    avg_citations_per_paper = round(total_citations / max(total_publications, 1), 2)
    publication_velocity = round(recent_pubs / max(len(member_ids), 1), 2)

    return {
        "publications_by_year": publications_by_year,
        "top_research_areas": top_research_areas,
        "international_rate": international_rate,
        "avg_citations_per_paper": avg_citations_per_paper,
        "publication_velocity": publication_velocity,
        "total_publications": total_publications,
        "total_citations": total_citations,
    }


def _empty_performance() -> dict:
    return {
        "publications_by_year": [],
        "top_research_areas": [],
        "international_rate": 0.0,
        "avg_citations_per_paper": 0.0,
        "publication_velocity": 0.0,
        "total_publications": 0,
        "total_citations": 0,
    }


async def get_publication_trends(institution_id: str, db, years: int = 5) -> list:
    """Year-by-year publication and citation trends with growth rates."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return []

    current_year = _now_year()
    cutoff_year = current_year - years

    rows = await db.publications.aggregate([
        {"$match": {
            "author_ids": {"$in": member_ids},
            "year": {"$gte": cutoff_year},
        }},
        {"$group": {
            "_id": "$year",
            "publications": {"$sum": 1},
            "citations": {"$sum": {"$ifNull": ["$citation_count", 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(years + 2)

    result: list[dict[str, Any]] = []
    prev_pubs = None
    for row in rows:
        if row["_id"] is None:
            continue
        pubs = row["publications"]
        growth_rate = 0.0
        if prev_pubs is not None:
            growth_rate = round((pubs - prev_pubs) / max(prev_pubs, 1) * 100, 2)
        result.append({
            "year": row["_id"],
            "publications": pubs,
            "citations": row["citations"],
            "growth_rate": growth_rate,
        })
        prev_pubs = pubs

    return result
