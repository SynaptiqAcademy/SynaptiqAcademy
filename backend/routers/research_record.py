"""Academic Research Record — Phase 1 consolidation.

One canonical bibliographic record per real-world academic work (the
existing `publications` collection, extended — see services/research_record/
for the underlying logic), combining pre-Synaptiq work (ORCID/Crossref/
OpenAlex/DOI/manual) with work created inside Synaptiq (an explicitly
published manuscript).

Endpoints:
  GET  /api/research-record/doi-preview        — validate + look up a DOI,
                                                  never persists anything
  POST /api/research-record/doi-confirm        — explicit confirm; creates
                                                  or converges onto the
                                                  canonical publication
  GET  /api/research-record/mine               — the caller's linked
                                                  publications (via the
                                                  publication_authors
                                                  relationship, plus legacy
                                                  owner_id-owned rows)
  POST /api/manuscripts/{id}/publish-to-research-record — explicit
                                                  manuscript -> Research
                                                  Record publish action

Deterministic only — no AI/LLM calls, no AI-credit consumption (Step 15:
this phase intentionally does not touch credibility/matching/discovery).
"""
from __future__ import annotations

import logging

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

from services.research_record.doi_lookup import lookup_doi
from services.research_record.doi_normalize import normalize_doi
from services.research_record.dedup import find_by_doi, find_candidate_by_title, NON_DOI_AUTO_MERGE_THRESHOLD
from services.research_record.authors import (
    link_user_to_publication, get_publication_ids_for_user, resolve_author_identities,
    link_confidently_resolved_authors,
)
from services.research_record.manuscript_link import publish_manuscript_to_research_record

log = logging.getLogger("synaptiq.research_record")
router = APIRouter(prefix="/api/research-record", tags=["research-record"])


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _norm_title(title: str) -> str:
    import re
    return re.sub(r"\s+", " ", (title or "").lower().strip())


# ── DOI preview (stateless, no persistence) ─────────────────────────────────

@router.get("/doi-preview")
async def doi_preview(doi: str = Query(...), user: dict = Depends(get_current_user)):
    try:
        preview = await lookup_doi(doi)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return preview


# ── DOI confirm (explicit persistence step) ─────────────────────────────────

class DoiConfirmBody(BaseModel):
    doi: str
    title: str | None = None
    journal: str | None = None
    publisher: str | None = None
    year: int | None = None
    url: str | None = None
    record_type: str | None = None
    authors: list[dict] | None = None


@router.post("/doi-confirm")
async def doi_confirm(body: DoiConfirmBody, user: dict = Depends(get_current_user)):
    normalized_doi = normalize_doi(body.doi)
    if not normalized_doi:
        raise HTTPException(status_code=400, detail=f"Invalid DOI format: {body.doi!r}")

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    uid = user["id"]

    # Global lookup by DOI only — never owner_id-scoped (Step 1 CRITICAL rule):
    # this is what lets a second Synaptiq user's confirmation of the SAME DOI
    # converge onto the same canonical record instead of creating a copy.
    existing = await find_by_doi(db, normalized_doi)

    authors = await resolve_author_identities(db, body.authors or [])

    if existing:
        pub_id = str(existing["_id"])
        # Fill gaps only — never silently overwrite already-present trusted
        # metadata with whatever this confirmation happened to carry
        # (Step 7 merge policy: Crossref/OpenAlex/prior confirmation wins;
        # this call only backfills fields the existing record doesn't have).
        fill: dict = {}
        for field, value in (
            ("title", body.title), ("journal", body.journal),
            ("publisher", body.publisher), ("year", body.year),
            ("url", body.url), ("record_type", body.record_type),
        ):
            if value and not existing.get(field):
                fill[field] = value
        if fill:
            fill["updated_at"] = _now_iso()
            await db.publications.update_one({"_id": existing["_id"]}, {"$set": fill})
        created = False
    else:
        doc = {
            "origin": "external",
            "source": "manual",
            "record_type": body.record_type or "other",
            "verification_status": "user_confirmed",
            "title": body.title or "",
            "title_norm": _norm_title(body.title or ""),
            "doi": normalized_doi,
            "journal": body.journal or "",
            "publisher": body.publisher or "",
            "year": body.year,
            "url": body.url or f"https://doi.org/{normalized_doi}",
            "authors": authors,
            "owner_id": uid,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        res = await db.publications.insert_one(doc)
        pub_id = str(res.inserted_id)
        created = True

    await link_user_to_publication(db, pub_id, uid, role="author", source="manual")
    await link_confidently_resolved_authors(db, pub_id, authors)

    return {"publication_id": pub_id, "created": created}


# ── Caller's linked publications ────────────────────────────────────────────

@router.get("/mine")
async def my_research_record(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    uid = user["id"]

    linked_ids = set(await get_publication_ids_for_user(db, uid))
    owned = await db.publications.find({"owner_id": uid}, {"_id": 1}).to_list(500)
    linked_ids.update(str(d["_id"]) for d in owned)

    if not linked_ids:
        return {"items": [], "total": 0}

    oids = [ObjectId(i) for i in linked_ids if ObjectId.is_valid(i)]
    items = await db.publications.find({"_id": {"$in": oids}}).sort("year", -1).to_list(500)
    for it in items:
        it["_id"] = str(it["_id"])
    return {"items": items, "total": len(items)}
