"""Institution Hub — Leaderboard Engine.

Global institution rankings and researcher leaderboards from real MongoDB data.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from bson import ObjectId


def _to_str(oid) -> str:
    if oid is None:
        return ""
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)


def _iis_label(total: int) -> str:
    if total >= 9501:
        return "World-Class"
    if total >= 8001:
        return "Elite"
    if total >= 6001:
        return "Leading"
    if total >= 4001:
        return "Recognized"
    if total >= 2501:
        return "Established"
    if total >= 1001:
        return "Developing"
    return "Emerging"


async def get_global_institution_leaderboard(db, limit: int = 50) -> list:
    """Return global institution ranking sorted by IIS."""
    from services.institution_hub.impact_engine import compute_institution_impact

    impact_docs = await db.institution_impact.find(
        {"iis_total": {"$exists": True}},
        {"institution_id": 1, "iis_total": 1, "iis_label": 1, "member_count": 1},
    ).sort("iis_total", -1).limit(limit).to_list(limit)

    if not impact_docs:
        # Compute on-the-fly for up to 20 institutions
        all_institutions = await db.institutions.find(
            {},
            {"_id": 1, "name": 1},
        ).limit(20).to_list(20)

        compute_tasks = [
            compute_institution_impact(str(inst["_id"]), db)
            for inst in all_institutions
        ]
        computed = await asyncio.gather(*compute_tasks, return_exceptions=True)

        rows = []
        for inst, result in zip(all_institutions, computed):
            if isinstance(result, Exception):
                continue
            rows.append({
                "institution_id": str(inst["_id"]),
                "institution_name": inst.get("name") or "",
                "iis_total": result.get("iis_total", 0),
                "iis_label": result.get("iis_label", "Emerging"),
                "member_count": result.get("member_count", 0),
            })

        rows.sort(key=lambda x: x["iis_total"], reverse=True)
        for i, row in enumerate(rows):
            row["rank"] = i + 1
        return rows[:limit]

    # Join institution names
    institution_ids = [doc.get("institution_id") for doc in impact_docs if doc.get("institution_id")]
    inst_oids = []
    for iid in institution_ids:
        try:
            inst_oids.append(ObjectId(iid))
        except Exception:
            pass

    institutions_raw = await db.institutions.find(
        {"_id": {"$in": inst_oids}},
        {"_id": 1, "name": 1},
    ).to_list(limit)
    inst_map: dict[str, str] = {_to_str(i["_id"]): i.get("name") or "" for i in institutions_raw}

    result = []
    for rank, doc in enumerate(impact_docs, start=1):
        iid = str(doc.get("institution_id") or "")
        result.append({
            "rank": rank,
            "institution_id": iid,
            "institution_name": inst_map.get(iid, ""),
            "iis_total": int(doc.get("iis_total") or 0),
            "iis_label": doc.get("iis_label") or _iis_label(int(doc.get("iis_total") or 0)),
            "member_count": int(doc.get("member_count") or 0),
        })
    return result


async def get_institution_unit_rankings(institution_id: str, db) -> list:
    """Return unit rankings within an institution by publication count."""
    units_raw = await db.units.find(
        {"institution_id": institution_id},
        {"_id": 1, "name": 1},
    ).to_list(500)

    if not units_raw:
        return []

    unit_ids = [_to_str(u["_id"]) for u in units_raw]

    # Fetch memberships per unit
    memberships = await db.institution_memberships.find(
        {"institution_id": institution_id, "unit_id": {"$in": unit_ids}},
        {"user_id": 1, "unit_id": 1},
    ).to_list(50000)

    # Build unit -> user_ids map
    unit_users: dict[str, list[str]] = {uid: [] for uid in unit_ids}
    for m in memberships:
        uid_str = str(m.get("unit_id") or "")
        user_id = m.get("user_id")
        if uid_str in unit_users and user_id:
            unit_users[uid_str].append(user_id)

    # For each unit, count publications
    async def _unit_pub_count(unit_id: str) -> int:
        uids = unit_users.get(unit_id, [])
        if not uids:
            return 0
        p, ms = await asyncio.gather(
            db.publications.count_documents({"owner_id": {"$in": uids}}),
            db.manuscripts.count_documents({"user_id": {"$in": uids}}),
        )
        return p + ms

    counts = await asyncio.gather(*[_unit_pub_count(uid) for uid in unit_ids])

    rows = []
    for unit, count in zip(units_raw, counts):
        uid_str = _to_str(unit["_id"])
        rows.append({
            "unit_id": uid_str,
            "unit_name": unit.get("name") or "",
            "member_count": len(unit_users.get(uid_str, [])),
            "publication_count": count,
        })

    rows.sort(key=lambda x: x["publication_count"], reverse=True)
    return rows


async def get_top_researchers_global(db, limit: int = 50) -> list:
    """Return globally top researchers by SIS with institution affiliation."""
    impact_rows = await db.research_impact.find(
        {"sis_total": {"$exists": True}},
        {"user_id": 1, "sis_total": 1, "h_index": 1},
    ).sort("sis_total", -1).limit(limit).to_list(limit)

    if not impact_rows:
        return []

    top_user_ids = [str(r.get("user_id") or "") for r in impact_rows if r.get("user_id")]

    user_oids = []
    for uid in top_user_ids:
        try:
            user_oids.append(ObjectId(uid))
        except Exception:
            pass

    users_coro = db.users.find(
        {"_id": {"$in": user_oids}},
        {"_id": 1, "full_name": 1, "email": 1},
    ).to_list(limit)

    memberships_coro = db.institution_memberships.find(
        {"user_id": {"$in": top_user_ids}, "status": "approved"},
        {"user_id": 1, "institution_id": 1},
    ).to_list(limit * 3)

    users_raw, memberships_raw = await asyncio.gather(users_coro, memberships_coro)

    user_map: dict[str, dict] = {_to_str(u["_id"]): u for u in users_raw}

    # user_id -> institution_id (first match)
    user_inst: dict[str, str] = {}
    for m in memberships_raw:
        uid = str(m.get("user_id") or "")
        if uid not in user_inst and m.get("institution_id"):
            user_inst[uid] = str(m["institution_id"])

    # Fetch institution names
    inst_ids_needed = list(set(user_inst.values()))
    inst_oids = []
    for iid in inst_ids_needed:
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
    for rank, row in enumerate(impact_rows, start=1):
        uid = str(row.get("user_id") or "")
        u = user_map.get(uid, {})
        inst_id = user_inst.get(uid, "")
        result.append({
            "rank": rank,
            "user_id": uid,
            "full_name": u.get("full_name") or u.get("email") or "",
            "institution_name": inst_map.get(inst_id, ""),
            "sis_total": int(row.get("sis_total") or 0),
            "h_index": float(row.get("h_index") or 0),
        })

    return result
