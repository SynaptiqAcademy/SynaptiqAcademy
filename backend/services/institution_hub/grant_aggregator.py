"""Institution Hub — Grant Aggregator.

Aggregates grant applications for all institution members from real MongoDB
collections (grant_applications + grants). No mock data.
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone

from bson import ObjectId


def _to_str(oid) -> str:
    if oid is None:
        return ""
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)


async def _get_member_ids(institution_id: str, db) -> list[str]:
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved"},
        {"user_id": 1},
    ).to_list(5000)
    return [r["user_id"] for r in rows if r.get("user_id")]


async def get_institution_grants(
    institution_id: str,
    db,
    page: int = 1,
    limit: int = 20,
    status: str = "",
) -> dict:
    """Return paginated grant applications for all institution members."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return {"items": [], "total": 0, "page": page, "pages": 0}

    app_filter: dict = {"user_id": {"$in": member_ids}}
    if status:
        app_filter["status"] = status

    apps_coro = db.grant_applications.find(app_filter).to_list(10000)

    user_oids = []
    for uid in member_ids:
        try:
            user_oids.append(ObjectId(uid))
        except Exception:
            pass

    users_coro = db.users.find(
        {"_id": {"$in": user_oids}},
        {"_id": 1, "full_name": 1, "email": 1},
    ).to_list(5000)

    apps_raw, users_raw = await asyncio.gather(apps_coro, users_coro)

    # Build user lookup
    user_map: dict[str, str] = {
        _to_str(u["_id"]): u.get("full_name") or u.get("email") or ""
        for u in users_raw
    }

    # Collect grant_ids for batch fetch
    grant_ids = []
    for app in apps_raw:
        gid = app.get("grant_id")
        if gid:
            try:
                grant_ids.append(ObjectId(gid))
            except Exception:
                try:
                    grant_ids.append(gid)
                except Exception:
                    pass

    grants_raw = await db.grants.find(
        {"_id": {"$in": grant_ids}},
        {"_id": 1, "title": 1, "amount": 1, "funder": 1, "deadline": 1},
    ).to_list(10000)

    grant_map: dict[str, dict] = {_to_str(g["_id"]): g for g in grants_raw}

    items: list[dict] = []
    for app in apps_raw:
        gid_str = _to_str(app.get("grant_id")) if app.get("grant_id") else ""
        grant_info = grant_map.get(gid_str, {})
        applicant_id = str(app.get("user_id") or "")
        submitted_at = app.get("submitted_at") or app.get("created_at")
        items.append({
            "application_id": _to_str(app.get("_id")),
            "grant_id": gid_str,
            "grant_title": grant_info.get("title") or app.get("grant_title") or "",
            "applicant_name": user_map.get(applicant_id, ""),
            "status": app.get("status") or "",
            "amount_requested": float(app.get("amount_requested") or app.get("requested_budget") or 0),
            "submitted_at": submitted_at.isoformat() if isinstance(submitted_at, datetime) else str(submitted_at or ""),
        })

    total = len(items)
    pages = math.ceil(total / limit) if limit > 0 else 0
    start = (page - 1) * limit
    end = start + limit

    return {"items": items[start:end], "total": total, "page": page, "pages": pages}


async def get_institution_grant_stats(institution_id: str, db) -> dict:
    """Return aggregate grant statistics for the institution."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return {
            "total_applications": 0,
            "by_status": {},
            "total_amount_requested": 0.0,
            "total_amount_awarded": 0.0,
            "success_rate": 0.0,
            "applications_by_month": [],
        }

    apps_raw = await db.grant_applications.find(
        {"user_id": {"$in": member_ids}},
        {"status": 1, "amount_requested": 1, "requested_budget": 1,
         "submitted_at": 1, "created_at": 1},
    ).to_list(50000)

    total = len(apps_raw)
    by_status: dict[str, int] = {}
    total_requested = 0.0
    total_awarded = 0.0

    # Month buckets: last 12 months
    now = datetime.now(timezone.utc)
    month_buckets: dict[str, int] = {}
    for i in range(12):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        key = f"{y:04d}-{m:02d}"
        month_buckets[key] = 0

    for app in apps_raw:
        st = app.get("status") or "unknown"
        by_status[st] = by_status.get(st, 0) + 1

        amount = float(app.get("amount_requested") or app.get("requested_budget") or 0)
        total_requested += amount

        if st in ("approved", "funded", "awarded"):
            total_awarded += amount

        # Month bucketing
        dt = app.get("submitted_at") or app.get("created_at")
        if isinstance(dt, datetime):
            key = f"{dt.year:04d}-{dt.month:02d}"
            if key in month_buckets:
                month_buckets[key] = month_buckets.get(key, 0) + 1

    approved_count = sum(
        v for k, v in by_status.items() if k in ("approved", "funded", "awarded")
    )
    success_rate = round((approved_count / total) * 100, 2) if total > 0 else 0.0

    apps_by_month = [
        {"month": k, "count": v}
        for k, v in sorted(month_buckets.items())
    ]

    return {
        "total_applications": total,
        "by_status": by_status,
        "total_amount_requested": round(total_requested, 2),
        "total_amount_awarded": round(total_awarded, 2),
        "success_rate": success_rate,
        "applications_by_month": apps_by_month,
    }
