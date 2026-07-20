"""Institution Hub — Publication Aggregator.

Aggregates all publications and manuscripts for an institution's members
from real MongoDB collections. No mock data.
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId


def _to_str(oid) -> str:
    if oid is None:
        return ""
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)


async def _get_member_ids(institution_id: str, db) -> list[str]:
    """Return approved member user_ids for the given institution."""
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved"},
        {"user_id": 1},
    ).to_list(5000)
    return [r["user_id"] for r in rows if r.get("user_id")]


async def get_institution_publications(
    institution_id: str,
    db,
    page: int = 1,
    limit: int = 20,
    search: str = "",
) -> dict:
    """Return paginated publications (and manuscripts) for all institution members."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return {"items": [], "total": 0, "page": page, "pages": 0}

    # Build filters
    pub_filter: dict = {"owner_id": {"$in": member_ids}}
    ms_filter: dict = {"user_id": {"$in": member_ids}}
    if search:
        regex = {"$regex": search, "$options": "i"}
        pub_filter["$or"] = [{"title": regex}, {"abstract": regex}]
        ms_filter["$or"] = [{"title": regex}, {"abstract": regex}]

    # Fetch publications and manuscripts in parallel, plus user lookup
    user_oids = []
    for uid in member_ids:
        try:
            user_oids.append(ObjectId(uid))
        except Exception:
            pass

    pubs_coro = db.publications.find(pub_filter).to_list(10000)
    mss_coro = db.manuscripts.find(ms_filter).to_list(10000)
    users_coro = db.users.find(
        {"_id": {"$in": user_oids}},
        {"_id": 1, "full_name": 1, "email": 1},
    ).to_list(5000)

    pubs_raw, mss_raw, users_raw = await asyncio.gather(pubs_coro, mss_coro, users_coro)

    # Build user lookup: str(uid) -> full_name
    user_map: dict[str, str] = {
        _to_str(u["_id"]): u.get("full_name") or u.get("email") or ""
        for u in users_raw
    }

    items: list[dict] = []

    for p in pubs_raw:
        owner_id = str(p.get("owner_id") or "")
        items.append({
            "_id": _to_str(p.get("_id")),
            "title": p.get("title") or "",
            "year": p.get("year"),
            "journal": p.get("journal") or "",
            "citation_count": int(p.get("citation_count") or 0),
            "owner_id": owner_id,
            "owner_name": user_map.get(owner_id, ""),
            "source": "publication",
            "pub_type": p.get("pub_type") or p.get("type") or "",
            "status": p.get("status") or "",
        })

    for m in mss_raw:
        owner_id = str(m.get("user_id") or "")
        # Derive year from created_at
        created_at = m.get("created_at")
        year = None
        if created_at:
            if isinstance(created_at, datetime):
                year = created_at.year
            elif isinstance(created_at, str) and len(created_at) >= 4:
                try:
                    year = int(created_at[:4])
                except ValueError:
                    pass
        items.append({
            "_id": _to_str(m.get("_id")),
            "title": m.get("title") or "",
            "year": year,
            "journal": m.get("journal") or "",
            "citation_count": int(m.get("citation_count") or 0),
            "owner_id": owner_id,
            "owner_name": user_map.get(owner_id, ""),
            "source": "manuscript",
            "pub_type": m.get("pub_type") or m.get("type") or "",
            "status": m.get("status") or "",
        })

    total = len(items)
    pages = math.ceil(total / limit) if limit > 0 else 0
    start = (page - 1) * limit
    end = start + limit
    page_items = items[start:end]

    return {"items": page_items, "total": total, "page": page, "pages": pages}


async def get_institution_publication_stats(institution_id: str, db) -> dict:
    """Return aggregate publication stats for the institution."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return {
            "total_publications": 0,
            "total_citations": 0,
            "avg_citations_per_pub": 0.0,
            "pubs_by_year": [],
            "pubs_by_type": {},
        }

    current_year = datetime.now(timezone.utc).year
    min_year = current_year - 10

    pubs_coro = db.publications.find(
        {"owner_id": {"$in": member_ids}},
        {"citation_count": 1, "year": 1, "pub_type": 1, "type": 1},
    ).to_list(50000)
    mss_coro = db.manuscripts.find(
        {"user_id": {"$in": member_ids}},
        {"citation_count": 1, "created_at": 1, "pub_type": 1, "type": 1},
    ).to_list(50000)

    pubs_raw, mss_raw = await asyncio.gather(pubs_coro, mss_coro)

    total_pubs = 0
    total_citations = 0
    by_year: dict[int, int] = {}
    by_type: dict[str, int] = {}

    for p in pubs_raw:
        total_pubs += 1
        total_citations += int(p.get("citation_count") or 0)
        yr = p.get("year")
        if yr:
            try:
                yr_int = int(yr)
                if min_year <= yr_int <= current_year:
                    by_year[yr_int] = by_year.get(yr_int, 0) + 1
            except (ValueError, TypeError):
                pass
        pt = p.get("pub_type") or p.get("type") or "unknown"
        by_type[pt] = by_type.get(pt, 0) + 1

    for m in mss_raw:
        total_pubs += 1
        total_citations += int(m.get("citation_count") or 0)
        created_at = m.get("created_at")
        if created_at:
            yr_int = None
            if isinstance(created_at, datetime):
                yr_int = created_at.year
            elif isinstance(created_at, str) and len(created_at) >= 4:
                try:
                    yr_int = int(created_at[:4])
                except ValueError:
                    pass
            if yr_int and min_year <= yr_int <= current_year:
                by_year[yr_int] = by_year.get(yr_int, 0) + 1
        pt = m.get("pub_type") or m.get("type") or "manuscript"
        by_type[pt] = by_type.get(pt, 0) + 1

    avg_citations = round(total_citations / total_pubs, 2) if total_pubs > 0 else 0.0
    pubs_by_year = [{"year": yr, "count": cnt} for yr, cnt in sorted(by_year.items())]

    return {
        "total_publications": total_pubs,
        "total_citations": total_citations,
        "avg_citations_per_pub": avg_citations,
        "pubs_by_year": pubs_by_year,
        "pubs_by_type": by_type,
    }


async def get_institution_citation_trends(institution_id: str, db) -> list:
    """Return citation trends (by year) for institution publications, last 10 years."""
    member_ids = await _get_member_ids(institution_id, db)
    if not member_ids:
        return []

    current_year = datetime.now(timezone.utc).year
    min_year = current_year - 10

    pubs_coro = db.publications.find(
        {"owner_id": {"$in": member_ids}},
        {"citation_count": 1, "year": 1},
    ).to_list(50000)
    mss_coro = db.manuscripts.find(
        {"user_id": {"$in": member_ids}},
        {"citation_count": 1, "created_at": 1},
    ).to_list(50000)

    pubs_raw, mss_raw = await asyncio.gather(pubs_coro, mss_coro)

    # year -> {citations, publications}
    trends: dict[int, dict] = {}

    def _add(yr_int: int, citations: int) -> None:
        if min_year <= yr_int <= current_year:
            if yr_int not in trends:
                trends[yr_int] = {"citations": 0, "publications": 0}
            trends[yr_int]["citations"] += citations
            trends[yr_int]["publications"] += 1

    for p in pubs_raw:
        yr = p.get("year")
        if yr:
            try:
                _add(int(yr), int(p.get("citation_count") or 0))
            except (ValueError, TypeError):
                pass

    for m in mss_raw:
        created_at = m.get("created_at")
        yr_int = None
        if isinstance(created_at, datetime):
            yr_int = created_at.year
        elif isinstance(created_at, str) and len(created_at) >= 4:
            try:
                yr_int = int(created_at[:4])
            except ValueError:
                pass
        if yr_int:
            _add(yr_int, int(m.get("citation_count") or 0))

    return [
        {"year": yr, "citations": v["citations"], "publications": v["publications"]}
        for yr, v in sorted(trends.items())
    ]
