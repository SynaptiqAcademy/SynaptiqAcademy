"""Institution Hub — Impact Engine.

Computes the Institution Impact Score (IIS, 0-10000) from real MongoDB data.
Results are cached in the `institution_impact` collection with a 1-hour TTL.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId


# ─── helpers ─────────────────────────────────────────────────────────────────

def _to_str(oid) -> str:
    if oid is None:
        return ""
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cap(value: float, ceiling: int) -> int:
    return min(ceiling, max(0, int(value)))


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


async def _get_member_ids(institution_id: str, db) -> list[str]:
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved"},
        {"user_id": 1},
    ).to_list(5000)
    return [r["user_id"] for r in rows if r.get("user_id")]


# ─── component queries ────────────────────────────────────────────────────────

async def _count_publications(member_ids: list[str], db) -> int:
    if not member_ids:
        return 0
    p, m = await asyncio.gather(
        db.publications.count_documents({"owner_id": {"$in": member_ids}}),
        db.manuscripts.count_documents({"user_id": {"$in": member_ids}}),
    )
    return p + m


async def _sum_citations(member_ids: list[str], db) -> int:
    if not member_ids:
        return 0
    agg = await db.publications.aggregate([
        {"$match": {"owner_id": {"$in": member_ids}}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$citation_count", 0]}}}},
    ]).to_list(1)
    return int((agg[0].get("total") or 0) if agg else 0)


async def _grant_counts(member_ids: list[str], db) -> tuple[int, int]:
    """Return (total_apps, approved_count)."""
    if not member_ids:
        return 0, 0
    apps = await db.grant_applications.find(
        {"user_id": {"$in": member_ids}},
        {"status": 1},
    ).to_list(50000)
    total = len(apps)
    approved = sum(1 for a in apps if (a.get("status") or "") in ("approved", "funded", "awarded"))
    return total, approved


async def _avg_reputation(member_ids: list[str], db) -> float:
    if not member_ids:
        return 0.0
    rows = await db.reputation_scores.find(
        {"user_id": {"$in": member_ids}},
        {"overall_score": 1, "overall": 1},
    ).to_list(5000)
    scores = []
    for r in rows:
        s = r.get("overall_score") or r.get("overall") or 0
        scores.append(float(s))
    return round(sum(scores) / len(scores), 4) if scores else 0.0


async def _collaboration_count(member_ids: list[str], db) -> int:
    if not member_ids:
        return 0
    return await db.collaborations.count_documents(
        {"$or": [
            {"requester_id": {"$in": member_ids}},
            {"recipient_id": {"$in": member_ids}},
            {"member_ids": {"$in": member_ids}},
        ]}
    )


async def _teaching_count(member_ids: list[str], db) -> int:
    if not member_ids:
        return 0
    return await db.teaching_lessons.count_documents({"user_id": {"$in": member_ids}})


async def _avg_h_index(member_ids: list[str], db) -> float:
    if not member_ids:
        return 0.0
    rows = await db.research_impact.find(
        {"user_id": {"$in": member_ids}},
        {"h_index": 1},
    ).to_list(5000)
    values = [float(r.get("h_index") or 0) for r in rows]
    return round(sum(values) / len(values), 4) if values else 0.0


# ─── main compute ─────────────────────────────────────────────────────────────

async def compute_institution_impact(institution_id: str, db) -> dict:
    """Compute IIS from scratch using real data."""
    member_ids = await _get_member_ids(institution_id, db)

    (
        total_pubs,
        total_citations,
        (total_grant_apps, approved_grants),
        avg_rep,
        collab_count,
        teaching_count,
        avg_h,
    ) = await asyncio.gather(
        _count_publications(member_ids, db),
        _sum_citations(member_ids, db),
        _grant_counts(member_ids, db),
        _avg_reputation(member_ids, db),
        _collaboration_count(member_ids, db),
        _teaching_count(member_ids, db),
        _avg_h_index(member_ids, db),
    )

    pub_vol = _cap(total_pubs * 5, 2000)
    cit_imp = _cap(total_citations * 2, 2500)
    grant_suc = _cap(
        (approved_grants / max(total_grant_apps, 1)) * 1500, 1500
    )
    mem_rep = _cap(avg_rep * 20, 2000)
    collab_sc = _cap(collab_count * 10, 1000)
    teach_imp = _cap(teaching_count * 2, 500)
    h_composite = _cap(avg_h * 10, 500)

    iis_total = pub_vol + cit_imp + grant_suc + mem_rep + collab_sc + teach_imp + h_composite

    return {
        "institution_id": institution_id,
        "iis_total": iis_total,
        "iis_label": _iis_label(iis_total),
        "components": {
            "publication_volume": pub_vol,
            "citation_impact": cit_imp,
            "grant_success": grant_suc,
            "member_reputation": mem_rep,
            "collaboration_score": collab_sc,
            "teaching_impact": teach_imp,
            "h_index_composite": h_composite,
        },
        "member_count": len(member_ids),
        "computed_at": _now_iso(),
    }


async def get_institution_impact(institution_id: str, db) -> dict:
    """Return cached IIS (1-hour TTL) or compute fresh."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    cached = await db.institution_impact.find_one(
        {"institution_id": institution_id},
    )
    if cached:
        computed_at = cached.get("computed_at")
        if isinstance(computed_at, datetime):
            if computed_at.tzinfo is None:
                computed_at = computed_at.replace(tzinfo=timezone.utc)
            if computed_at >= cutoff:
                cached["_id"] = _to_str(cached.get("_id"))
                return cached
        elif isinstance(computed_at, str):
            try:
                dt = datetime.fromisoformat(computed_at.replace("Z", "+00:00"))
                if dt >= cutoff:
                    cached["_id"] = _to_str(cached.get("_id"))
                    return cached
            except ValueError:
                pass

    # Compute fresh
    result = await compute_institution_impact(institution_id, db)

    await db.institution_impact.update_one(
        {"institution_id": institution_id},
        {"$set": result},
        upsert=True,
    )
    return result


async def get_top_researchers_in_institution(
    institution_id: str,
    db,
    limit: int = 10,
) -> list:
    """Return top researchers by SIS within the institution."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return []

    impact_rows = await db.research_impact.find(
        {"user_id": {"$in": member_ids}},
        {"user_id": 1, "sis_total": 1, "h_index": 1},
    ).sort("sis_total", -1).limit(limit).to_list(limit)

    if not impact_rows:
        return []

    top_user_ids = [r["user_id"] for r in impact_rows if r.get("user_id")]
    user_oids = []
    for uid in top_user_ids:
        try:
            user_oids.append(ObjectId(uid))
        except Exception:
            pass

    users_raw = await db.users.find(
        {"_id": {"$in": user_oids}},
        {"_id": 1, "full_name": 1, "email": 1},
    ).to_list(limit)

    user_map: dict[str, dict] = {_to_str(u["_id"]): u for u in users_raw}

    result = []
    for row in impact_rows:
        uid = str(row.get("user_id") or "")
        u = user_map.get(uid, {})
        result.append({
            "user_id": uid,
            "full_name": u.get("full_name") or u.get("email") or "",
            "email": u.get("email") or "",
            "sis_total": int(row.get("sis_total") or 0),
            "h_index": float(row.get("h_index") or 0),
        })

    return result
