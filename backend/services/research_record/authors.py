"""Publication <-> Synaptiq-user relationship — the "smallest appropriate
structure" called for by the design (Step 3): a publication is a single
global bibliographic record; a Synaptiq user's relationship to it (author,
owner, co-author) is a separate, many-to-one concept, held in its own
lightweight collection rather than duplicating the whole bibliographic
record per user.

This is NOT a second publications collection — it has no bibliographic
fields at all, only the relationship.

Collection: `publication_authors`
  { _id, publication_id, synaptiq_user_id, role, source, linked_at }
  role   : "owner" | "author" | "co_author"
  source : "orcid" | "manual" | "synaptiq" | "orcid_match"

Author-identity rules (Step 3, non-negotiable):
  1. Never link a person to a Synaptiq account based on name similarity alone.
  2. Prefer verified ORCID matching (author.orcid_id == users.orcid.orcid_id).
  3. An external author with no confident match stays external
     (is_external=True, synaptiq_user_id=None) — never guessed.
  4. Manual linking only through an explicit user/admin action.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def link_user_to_publication(
    db, publication_id: str, synaptiq_user_id: str,
    *, role: str = "author", source: str = "manual",
) -> dict:
    """Idempotent — linking the same (publication, user) pair twice updates
    role/source rather than creating a duplicate relationship row."""
    existing = await db.publication_authors.find_one({
        "publication_id": publication_id, "synaptiq_user_id": synaptiq_user_id,
    })
    if existing:
        await db.publication_authors.update_one(
            {"_id": existing["_id"]}, {"$set": {"role": role, "source": source}})
        return {**existing, "role": role, "source": source}
    doc = {
        "publication_id": publication_id,
        "synaptiq_user_id": synaptiq_user_id,
        "role": role,
        "source": source,
        "linked_at": _now_iso(),
    }
    res = await db.publication_authors.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def is_user_linked(db, publication_id: str, synaptiq_user_id: str) -> bool:
    return await db.publication_authors.count_documents({
        "publication_id": publication_id, "synaptiq_user_id": synaptiq_user_id,
    }) > 0


async def get_publication_ids_for_user(db, synaptiq_user_id: str) -> list[str]:
    rows = await db.publication_authors.find(
        {"synaptiq_user_id": synaptiq_user_id}, {"publication_id": 1}
    ).to_list(2000)
    return [r["publication_id"] for r in rows]


async def count_publications_for_user(db, synaptiq_user_id: str) -> int:
    """Distinct publication count for a user — the canonical relationship
    is publication_authors, but services/orcid/sync.py (the primary real
    writer of `publications`) sets `owner_id` directly and never creates a
    publication_authors row, so a real ORCID-imported publication would be
    invisible to a publication_authors-only count. Union both paths,
    deduplicated by publication id, so a doc reachable through either (or
    both) is counted exactly once — never double-counted for co-authorship
    rows on the same publication.
    """
    linked_ids = set(await get_publication_ids_for_user(db, synaptiq_user_id))
    owned_ids = await db.publications.distinct("_id", {"owner_id": synaptiq_user_id})
    linked_ids.update(str(oid) for oid in owned_ids)
    return len(linked_ids)


async def get_users_for_publication(db, publication_id: str) -> list[dict]:
    return await db.publication_authors.find(
        {"publication_id": publication_id}
    ).to_list(200)


async def resolve_author_identities(db, authors: list[dict]) -> list[dict]:
    """For each author dict lacking a synaptiq_user_id, check whether its
    orcid_id matches a Synaptiq user's own VERIFIED linked ORCID iD. Only
    that confident match sets is_external=False — never a name-based guess.
    """
    resolved: list[dict] = []
    for a in authors:
        a = dict(a)
        if a.get("synaptiq_user_id"):
            a["is_external"] = False
            resolved.append(a)
            continue
        orcid_id = a.get("orcid_id")
        if orcid_id:
            match = await db.users.find_one(
                {"orcid.orcid_id": orcid_id}, {"_id": 1})
            if match:
                a["synaptiq_user_id"] = str(match["_id"])
                a["is_external"] = False
                resolved.append(a)
                continue
        a.setdefault("synaptiq_user_id", None)
        a["is_external"] = True
        resolved.append(a)
    return resolved


async def link_confidently_resolved_authors(db, publication_id: str, authors: list[dict]) -> int:
    """Create/refresh publication_authors rows for every author that
    resolve_author_identities() confidently matched to a Synaptiq user.
    Returns the number linked."""
    linked = 0
    for a in authors:
        if a.get("synaptiq_user_id") and not a.get("is_external"):
            await link_user_to_publication(
                db, publication_id, a["synaptiq_user_id"],
                role="author", source="orcid_match",
            )
            linked += 1
    return linked
