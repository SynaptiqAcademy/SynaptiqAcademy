"""Citation Analytics Data Layer.

Provides reusable aggregation services for future institutional, department, and
faculty analytics dashboards. NO API endpoints are created here — these are pure
data functions callable from any router.

Standardised output schema (CitationAggregateResult) is versioned so downstream
dashboard code can depend on stable field names.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId


# ─────────────────────────── output schema ───────────────────────────────────

def _make_aggregate(
    *,
    entity_type:      str,          # "user" | "institution" | "department" | "faculty"
    entity_id:        str,
    entity_name:      str,
    researcher_count: int = 0,
    publication_count: int = 0,
    total_citations:  int = 0,
    h_index:          int = 0,
    avg_citations_per_pub: float = 0.0,
    top_publications: list[dict] = None,
    area_breakdown:   list[dict] = None,
    computed_at:      Optional[str] = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "entity_type":         entity_type,
        "entity_id":           entity_id,
        "entity_name":         entity_name,
        "researcher_count":    researcher_count,
        "publication_count":   publication_count,
        "total_citations":     total_citations,
        "h_index":             h_index,
        "avg_citations_per_pub": avg_citations_per_pub,
        "top_publications":    top_publications or [],
        "area_breakdown":      area_breakdown   or [],
        "computed_at":         computed_at or now,
    }


# ─────────────────────────── user-level ──────────────────────────────────────

async def aggregate_user_impact(db, user_id: str) -> dict:
    """Aggregate citation impact for a single researcher."""
    u_doc = await db.users.find_one(
        {"_id": ObjectId(user_id)},
        {"full_name": 1, "openalex_metrics": 1},
    )
    oam          = (u_doc or {}).get("openalex_metrics") or {}
    total_cites  = int(oam.get("citations") or 0)
    h_index      = int(oam.get("h_index")   or 0)
    works_count  = int(oam.get("works_count") or 0)

    pub_docs = await db.publications.find(
        {"owner_id": user_id},
        {"title": 1, "year": 1, "citations": 1, "concepts": 1, "topics": 1},
    ).sort("citations", -1).limit(5).to_list(5)

    top_pubs = [{"id": str(p["_id"]), "title": p.get("title"), "citations": int(p.get("citations") or 0)}
                for p in pub_docs]

    avg_per_pub = round(total_cites / max(1, works_count), 1)

    return _make_aggregate(
        entity_type="user",
        entity_id=user_id,
        entity_name=(u_doc or {}).get("full_name") or "Unknown",
        publication_count=works_count,
        total_citations=total_cites,
        h_index=h_index,
        avg_citations_per_pub=avg_per_pub,
        top_publications=top_pubs,
    )


# ─────────────────────────── institution-level ───────────────────────────────

async def aggregate_institution_impact(db, institution_id: str) -> dict:
    """Aggregate citation impact for all researchers at an institution.

    Future: used by /admin/institutions/:id/impact endpoint.
    """
    inst = await db.institutions.find_one({"_id": ObjectId(institution_id)}, {"name": 1})
    inst_name = (inst or {}).get("name") or "Unknown Institution"

    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved"},
        {"user_id": 1},
    ).to_list(5000)
    member_ids = [r["user_id"] for r in rows]
    if not member_ids:
        return _make_aggregate(entity_type="institution", entity_id=institution_id, entity_name=inst_name)

    users = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in member_ids]}, "openalex_metrics": {"$exists": True}},
        {"openalex_metrics": 1},
    ).to_list(5000)

    total_cites  = sum(int((u.get("openalex_metrics") or {}).get("citations") or 0) for u in users)
    h_values     = [int((u.get("openalex_metrics") or {}).get("h_index") or 0) for u in users]
    h_index      = max(h_values) if h_values else 0
    works_total  = sum(int((u.get("openalex_metrics") or {}).get("works_count") or 0) for u in users)

    pub_docs = await db.publications.find(
        {"owner_id": {"$in": member_ids}},
        {"title": 1, "year": 1, "citations": 1, "owner_id": 1},
    ).sort("citations", -1).limit(10).to_list(10)
    top_pubs = [{"id": str(p["_id"]), "title": p.get("title"), "citations": int(p.get("citations") or 0)}
                for p in pub_docs]

    avg_per_pub = round(total_cites / max(1, works_total), 1)

    return _make_aggregate(
        entity_type="institution",
        entity_id=institution_id,
        entity_name=inst_name,
        researcher_count=len(users),
        publication_count=works_total,
        total_citations=total_cites,
        h_index=h_index,
        avg_citations_per_pub=avg_per_pub,
        top_publications=top_pubs,
    )


# ─────────────────────────── department-level ─────────────────────────────────

async def aggregate_department_impact(db, department: str, institution_id: str) -> dict:
    """Aggregate citation impact for a specific department within an institution.

    Future: used by department-level analytics pages.
    """
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "department": department, "status": "approved"},
        {"user_id": 1},
    ).to_list(2000)
    member_ids = [r["user_id"] for r in rows]
    if not member_ids:
        return _make_aggregate(entity_type="department", entity_id=department,
                               entity_name=department)

    users = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in member_ids]}, "openalex_metrics": {"$exists": True}},
        {"openalex_metrics": 1},
    ).to_list(2000)

    total_cites = sum(int((u.get("openalex_metrics") or {}).get("citations") or 0) for u in users)
    h_values    = [int((u.get("openalex_metrics") or {}).get("h_index") or 0) for u in users]
    h_index     = max(h_values) if h_values else 0
    works_total = sum(int((u.get("openalex_metrics") or {}).get("works_count") or 0) for u in users)

    avg_per_pub = round(total_cites / max(1, works_total), 1)

    return _make_aggregate(
        entity_type="department",
        entity_id=f"{institution_id}:{department}",
        entity_name=department,
        researcher_count=len(users),
        publication_count=works_total,
        total_citations=total_cites,
        h_index=h_index,
        avg_citations_per_pub=avg_per_pub,
    )
