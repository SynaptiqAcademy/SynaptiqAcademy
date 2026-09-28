"""The explicit manuscripts -> Academic Research Record publish action.

`manuscripts` stays the authoritative store for in-progress Synaptiq-created
work and is never merged into `publications`, and a manuscript is NEVER
auto-promoted just because its status becomes "published" (Step 10). This
module only runs when a caller (the router, after a user/admin confirms)
explicitly invokes it.

Convergence (Step 11): if a `publications` document already exists for the
supplied DOI (e.g. ORCID discovered it independently, before or after this
call), this links onto that SAME document rather than creating a second,
unrelated one — and never silently flips an already-set `origin` away from
what it was.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from bson import ObjectId

from services.research_record.doi_normalize import normalize_doi
from services.research_record.dedup import find_by_doi
from services.research_record.authors import link_user_to_publication

_MANUSCRIPT_TYPE_MAP = {
    "journal article":         "journal_article",
    "conference paper":        "conference_paper",
    "book chapter":            "book_chapter",
    "review paper":            "journal_article",
    "systematic review":       "journal_article",
    "meta-analysis":           "journal_article",
    "research proposal":       "other",
    "grant proposal":          "grant",
    "doctoral thesis chapter": "other",
    "white paper":             "other",
}


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").lower().strip())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def publish_manuscript_to_research_record(
    db, manuscript_id: str, *, doi: str | None = None,
) -> dict:
    """Explicit publish action. Returns {"publication_id": str, "created": bool}.

    Caller is responsible for the permission check (lead author / admin) —
    this function only performs the linking/creation, matching the existing
    pattern in routers/manuscripts.py where authorization happens at the
    route layer.
    """
    manuscript = await db.manuscripts.find_one({"_id": ObjectId(manuscript_id)})
    if not manuscript:
        raise ValueError(f"Manuscript {manuscript_id} not found")

    normalized_doi = normalize_doi(doi) if doi else None

    existing_pub = None
    if normalized_doi:
        existing_pub = await find_by_doi(db, normalized_doi)
    if existing_pub is None:
        # Back-compat: manuscript may already carry a link from a prior
        # ORCID-side match (services/orcid/sync.py::_link_to_manuscript) or
        # a previous call to this function.
        prior_link = manuscript.get("research_record_id") or manuscript.get("orcid_publication_id")
        if prior_link:
            existing_pub = await db.publications.find_one({"_id": ObjectId(prior_link)})

    manuscript_ref = {"collection": "manuscripts", "id": manuscript_id}

    if existing_pub:
        pub_id = str(existing_pub["_id"])
        update: dict = {"synaptiq_work_ref": manuscript_ref, "updated_at": _now_iso()}
        # Never silently change an already-set origin (Step 11) — only fill
        # it in if this is a legacy row that never had one.
        if not existing_pub.get("origin"):
            update["origin"] = "synaptiq"
        if normalized_doi and not existing_pub.get("doi"):
            update["doi"] = normalized_doi
        await db.publications.update_one({"_id": existing_pub["_id"]}, {"$set": update})
        created = False
    else:
        title = manuscript.get("title", "")
        m_type = (manuscript.get("manuscript_type") or "").strip().lower()
        doc = {
            "origin": "synaptiq",
            "source": "synaptiq",
            "record_type": _MANUSCRIPT_TYPE_MAP.get(m_type, "other"),
            "verification_status": "synaptiq_published",
            "title": title,
            "title_norm": _norm_title(title),
            "doi": normalized_doi,
            "journal": None,
            "year": None,
            "url": f"https://doi.org/{normalized_doi}" if normalized_doi else None,
            "authors": [],
            "owner_id": manuscript.get("lead_author_id"),
            "synaptiq_work_ref": manuscript_ref,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        res = await db.publications.insert_one(doc)
        pub_id = str(res.inserted_id)
        created = True

    # Every real Synaptiq co-author of the manuscript is a confidently-known
    # identity already (no ORCID/name-matching needed) — link them all.
    for author_uid in (manuscript.get("authors") or []):
        await link_user_to_publication(db, pub_id, str(author_uid), role="author", source="synaptiq")

    # Keep both the new and the legacy field name in sync (Step 13
    # back-compat — services/orcid/sync.py::_link_to_manuscript and any
    # existing reader of orcid_publication_id must keep working).
    await db.manuscripts.update_one(
        {"_id": manuscript["_id"]},
        {"$set": {"research_record_id": pub_id, "orcid_publication_id": pub_id}},
    )

    return {"publication_id": pub_id, "created": created}
