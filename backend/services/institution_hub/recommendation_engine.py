"""Institution Hub — Recommendation Engine.

Produces institution-level recommendations: collaborating institutions,
funding opportunities, and researchers to recruit. All data from MongoDB.
"""
from __future__ import annotations

import ast
import asyncio
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId


def _to_str(oid) -> str:
    if oid is None:
        return ""
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)


def _parse_list(value) -> set:
    """Parse a field that might be a list or a string-encoded list."""
    if isinstance(value, list):
        return set(str(v).lower().strip() for v in value if v)
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return set(str(v).lower().strip() for v in parsed if v)
        except (ValueError, SyntaxError):
            # Treat as comma-separated
            return set(v.strip().lower() for v in value.split(",") if v.strip())
    return set()


def _jaccard(a: set, b: set) -> float:
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


async def _get_member_ids(institution_id: str, db) -> list[str]:
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved"},
        {"user_id": 1},
    ).to_list(5000)
    return [r["user_id"] for r in rows if r.get("user_id")]


async def _get_member_research_areas(member_ids: list[str], db) -> set:
    """Collect all unique research area keywords from institution members."""
    if not member_ids:
        return set()
    user_oids = []
    for uid in member_ids:
        try:
            user_oids.append(ObjectId(uid))
        except Exception:
            pass
    users = await db.users.find(
        {"_id": {"$in": user_oids}},
        {"research_interests": 1, "research_areas": 1},
    ).to_list(5000)
    areas: set = set()
    for u in users:
        areas |= _parse_list(u.get("research_interests") or u.get("research_areas") or [])
    return areas


async def recommend_collaborating_institutions(
    institution_id: str,
    db,
    limit: int = 10,
) -> list:
    """Recommend institutions with similar research areas using Jaccard similarity."""
    member_ids = await _get_member_ids(institution_id, db)
    own_areas = await _get_member_research_areas(member_ids, db)

    # Get all other institutions
    other_insts = await db.institutions.find(
        {},
        {"_id": 1, "name": 1},
    ).to_list(500)

    candidates = []
    for inst in other_insts:
        iid = _to_str(inst["_id"])
        if iid == institution_id:
            continue
        candidates.append((iid, inst.get("name") or ""))

    if not candidates:
        return []

    # Fetch member ids for each candidate institution
    async def _cand_areas(iid: str) -> set:
        mids = await _get_member_ids(iid, db)
        return await _get_member_research_areas(mids, db)

    cand_areas = await asyncio.gather(*[_cand_areas(iid) for iid, _ in candidates])

    results = []
    for (iid, iname), areas in zip(candidates, cand_areas):
        sim = _jaccard(own_areas, areas)
        shared = list(own_areas & areas)
        results.append({
            "institution_id": iid,
            "institution_name": iname,
            "similarity_score": round(sim, 4),
            "shared_areas": shared,
        })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:limit]


async def recommend_funding_opportunities(
    institution_id: str,
    db,
    limit: int = 10,
) -> list:
    """Recommend open grants matching institution member research areas."""
    member_ids = await _get_member_ids(institution_id, db)
    member_areas = await _get_member_research_areas(member_ids, db)

    now = datetime.now(timezone.utc)

    grants_raw = await db.grants.find(
        {
            "$and": [
                {"deadline": {"$gt": now}},
                {"status": {"$ne": "closed"}},
            ]
        },
        {"_id": 1, "title": 1, "funder": 1, "amount": 1, "deadline": 1,
         "research_areas": 1, "keywords": 1, "description": 1},
    ).to_list(1000)

    results = []
    for g in grants_raw:
        grant_areas = _parse_list(
            g.get("research_areas") or g.get("keywords") or []
        )
        # Also tokenize description for keyword matching
        desc = g.get("description") or g.get("title") or ""
        if isinstance(desc, str):
            desc_words = set(w.lower().strip(".,;:()[]") for w in desc.split() if len(w) > 3)
            grant_areas |= desc_words

        match_score = _jaccard(member_areas, grant_areas) if member_areas else 0.0

        deadline = g.get("deadline")
        deadline_str = deadline.isoformat() if isinstance(deadline, datetime) else str(deadline or "")

        results.append({
            "grant_id": _to_str(g["_id"]),
            "title": g.get("title") or "",
            "funder": g.get("funder") or "",
            "amount": float(g.get("amount") or 0),
            "deadline": deadline_str,
            "match_score": round(match_score, 4),
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:limit]


async def recommend_researchers_to_recruit(
    institution_id: str,
    db,
    limit: int = 10,
) -> list:
    """Recommend high-SIS researchers not already in this institution."""
    # Get existing member ids
    existing_member_ids = set(await _get_member_ids(institution_id, db))

    # Get top researchers by SIS
    impact_rows = await db.research_impact.find(
        {"sis_total": {"$exists": True}},
        {"user_id": 1, "sis_total": 1, "h_index": 1},
    ).sort("sis_total", -1).limit(limit * 5).to_list(limit * 5)

    # Filter out existing members
    candidates = [
        r for r in impact_rows
        if str(r.get("user_id") or "") not in existing_member_ids
    ]

    if not candidates:
        return []

    top_candidates = candidates[:limit]
    cand_user_ids = [str(r["user_id"]) for r in top_candidates if r.get("user_id")]

    user_oids = []
    for uid in cand_user_ids:
        try:
            user_oids.append(ObjectId(uid))
        except Exception:
            pass

    users_coro = db.users.find(
        {"_id": {"$in": user_oids}},
        {"_id": 1, "full_name": 1, "email": 1,
         "research_interests": 1, "research_areas": 1},
    ).to_list(limit)

    memberships_coro = db.institution_memberships.find(
        {"user_id": {"$in": cand_user_ids}, "status": "approved"},
        {"user_id": 1, "institution_id": 1},
    ).to_list(limit * 3)

    users_raw, memberships_raw = await asyncio.gather(users_coro, memberships_coro)

    user_map: dict[str, dict] = {_to_str(u["_id"]): u for u in users_raw}
    user_inst: dict[str, str] = {}
    for m in memberships_raw:
        uid = str(m.get("user_id") or "")
        if uid not in user_inst and m.get("institution_id"):
            user_inst[uid] = str(m["institution_id"])

    # Fetch institution names for candidates' current affiliations
    inst_ids = list(set(user_inst.values()))
    inst_oids = []
    for iid in inst_ids:
        try:
            inst_oids.append(ObjectId(iid))
        except Exception:
            pass

    institutions_raw = await db.institutions.find(
        {"_id": {"$in": inst_oids}},
        {"_id": 1, "name": 1},
    ).to_list(500)
    inst_map: dict[str, str] = {_to_str(i["_id"]): i.get("name") or "" for i in institutions_raw}

    result = []
    for row in top_candidates:
        uid = str(row.get("user_id") or "")
        u = user_map.get(uid, {})
        inst_id = user_inst.get(uid, "")
        research_areas = list(
            _parse_list(u.get("research_interests") or u.get("research_areas") or [])
        )
        result.append({
            "user_id": uid,
            "full_name": u.get("full_name") or u.get("email") or "",
            "sis_total": int(row.get("sis_total") or 0),
            "research_areas": research_areas,
            "institution_name": inst_map.get(inst_id, ""),
        })

    return result
