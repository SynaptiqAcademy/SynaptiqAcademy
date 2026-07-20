"""Institution Analytics — Researcher Engine.

Provides researcher-level analytics: top performers, fastest growing,
most collaborative, and trajectory distributions.
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


async def get_top_researchers(institution_id: str, db, limit: int = 20) -> list:
    """Return top researchers by SIS total, enriched with profile data."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return []

    impact_rows = await db.research_impact.find(
        {"user_id": {"$in": member_ids}},
        {"user_id": 1, "sis_total": 1, "h_index": 1, "publication_count": 1},
    ).sort("sis_total", -1).limit(limit).to_list(limit)

    if not impact_rows:
        return []

    top_user_ids = [r["user_id"] for r in impact_rows]

    user_ids_as_oid = []
    for uid in top_user_ids:
        if ObjectId.is_valid(uid):
            user_ids_as_oid.append(ObjectId(uid))
        else:
            user_ids_as_oid.append(uid)

    users_list, profiles_list = await asyncio.gather(
        db.users.find(
            {"_id": {"$in": user_ids_as_oid}},
            {"full_name": 1, "institution": 1, "avatar_url": 1},
        ).to_list(limit),
        db.public_profiles.find(
            {"user_id": {"$in": top_user_ids}},
            {"user_id": 1, "slug": 1},
        ).to_list(limit),
    )

    users_map = {str(u["_id"]): u for u in users_list}
    profiles_map = {p["user_id"]: p.get("slug", "") for p in profiles_list}

    result = []
    for row in impact_rows:
        uid = row["user_id"]
        user = users_map.get(uid, {})
        result.append({
            "user_id": uid,
            "full_name": user.get("full_name", ""),
            "institution": user.get("institution", ""),
            "avatar_url": user.get("avatar_url", ""),
            "sis_total": row.get("sis_total", 0),
            "h_index": row.get("h_index", 0),
            "publication_count": row.get("publication_count", 0),
            "slug": profiles_map.get(uid, ""),
        })
    return result


async def get_fastest_growing_researchers(institution_id: str, db, limit: int = 10) -> list:
    """Return researchers with highest publication growth (current vs previous year)."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return []

    current_year = _now_year()
    prev_year = current_year - 1

    # Aggregate: per (author_id, year) publication count
    agg_rows = await db.publications.aggregate([
        {"$match": {
            "author_ids": {"$in": member_ids},
            "year": {"$in": [current_year, prev_year]},
        }},
        {"$unwind": "$author_ids"},
        {"$match": {"author_ids": {"$in": member_ids}}},
        {"$group": {
            "_id": {"user_id": "$author_ids", "year": "$year"},
            "count": {"$sum": 1},
        }},
    ]).to_list(len(member_ids) * 2 + 10)

    # Build per-user year→count map
    user_year_map: dict[str, dict[int, int]] = {}
    for row in agg_rows:
        uid = row["_id"]["user_id"]
        yr = row["_id"]["year"]
        user_year_map.setdefault(uid, {})[yr] = row["count"]

    growth_list = []
    for uid, yr_counts in user_year_map.items():
        current_pubs = yr_counts.get(current_year, 0)
        prev_pubs = yr_counts.get(prev_year, 0)
        growth_rate = round((current_pubs - prev_pubs) / max(prev_pubs, 1) * 100, 2)
        growth_list.append({
            "user_id": uid,
            "current_year_pubs": current_pubs,
            "prev_year_pubs": prev_pubs,
            "growth_rate": growth_rate,
        })

    growth_list.sort(key=lambda x: x["growth_rate"], reverse=True)
    top = growth_list[:limit]

    if not top:
        return []

    top_ids = [r["user_id"] for r in top]
    user_ids_as_oid = [ObjectId(uid) if ObjectId.is_valid(uid) else uid for uid in top_ids]
    users_list = await db.users.find(
        {"_id": {"$in": user_ids_as_oid}},
        {"full_name": 1, "institution": 1},
    ).to_list(limit)
    users_map = {str(u["_id"]): u for u in users_list}

    result = []
    for row in top:
        uid = row["user_id"]
        user = users_map.get(uid, {})
        result.append({
            "user_id": uid,
            "full_name": user.get("full_name", ""),
            "institution": user.get("institution", ""),
            "current_year_pubs": row["current_year_pubs"],
            "prev_year_pubs": row["prev_year_pubs"],
            "growth_rate": row["growth_rate"],
        })
    return result


async def get_most_collaborative_researchers(institution_id: str, db, limit: int = 10) -> list:
    """Return researchers with most collaboration activity."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return []

    collab_rows = await db.collaborations.find(
        {"$or": [
            {"created_by": {"$in": member_ids}},
            {"participants": {"$in": member_ids}},
        ]},
        {"created_by": 1, "participants": 1},
    ).to_list(5000)

    # Count per user_id
    user_collab_count: dict[str, int] = {}
    member_set = set(member_ids)
    for row in collab_rows:
        creator = row.get("created_by", "")
        if creator in member_set:
            user_collab_count[creator] = user_collab_count.get(creator, 0) + 1
        for participant in (row.get("participants") or []):
            if participant in member_set and participant != creator:
                user_collab_count[participant] = user_collab_count.get(participant, 0) + 1

    sorted_users = sorted(user_collab_count.items(), key=lambda x: x[1], reverse=True)[:limit]
    if not sorted_users:
        return []

    top_ids = [uid for uid, _ in sorted_users]
    user_ids_as_oid = [ObjectId(uid) if ObjectId.is_valid(uid) else uid for uid in top_ids]
    users_list = await db.users.find(
        {"_id": {"$in": user_ids_as_oid}},
        {"full_name": 1, "institution": 1},
    ).to_list(limit)
    users_map = {str(u["_id"]): u for u in users_list}

    return [
        {
            "user_id": uid,
            "full_name": users_map.get(uid, {}).get("full_name", ""),
            "institution": users_map.get(uid, {}).get("institution", ""),
            "collaboration_count": count,
        }
        for uid, count in sorted_users
    ]


async def get_researcher_trajectories(institution_id: str, db) -> dict:
    """Return distribution of researchers across reputation and reviewer levels."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return {"reputation_distribution": [], "reviewer_level_distribution": []}

    rep_rows, reviewer_rows = await asyncio.gather(
        db.research_reputation.aggregate([
            {"$match": {"user_id": {"$in": member_ids}}},
            {"$group": {"_id": "$level_number", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(20),
        db.reviewer_profiles.aggregate([
            {"$match": {"user_id": {"$in": member_ids}}},
            {"$group": {"_id": "$reviewer_level", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(20),
    )

    reputation_distribution = [
        {"level": row["_id"], "count": row["count"]}
        for row in rep_rows
        if row["_id"] is not None
    ]
    reviewer_level_distribution = [
        {"level": row["_id"], "count": row["count"]}
        for row in reviewer_rows
        if row["_id"] is not None
    ]

    return {
        "reputation_distribution": reputation_distribution,
        "reviewer_level_distribution": reviewer_level_distribution,
    }
