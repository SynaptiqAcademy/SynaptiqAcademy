"""Batched publication-title evidence for a candidate pool — §15/§26.

Exactly three queries regardless of pool size (publication_authors links,
owner_id fallback, then the publications themselves) — never one query per
candidate. Reuses the canonical authorship union that
services/research_record/authors.py's get_publication_ids_for_user() already
defines (publication_authors rows + publications.owner_id fallback, since
services/orcid/sync.py writes owner_id directly without a relationship row)
— this module just does that union in batch instead of per-user.

Exposes only publication `title` into evidence. Never claims authorship
beyond what publication_authors/owner_id already establish, and never
returns any other publication field (journal, DOI, url, full author list)
into evidence — title overlap with a Research Need term is the only claim
made here.
"""
from __future__ import annotations

from bson import ObjectId


async def batch_publication_titles(db, candidate_ids: list[str]) -> dict[str, list[str]]:
    """Returns {candidate_id: [title, ...]} for whichever candidates have at
    least one titled publication. Candidates with none are simply absent —
    callers must not assume every id is a key."""
    if not candidate_ids:
        return {}

    by_user: dict[str, set[str]] = {}

    linked = await db.publication_authors.find(
        {"synaptiq_user_id": {"$in": candidate_ids}},
        {"publication_id": 1, "synaptiq_user_id": 1},
    ).to_list(5000)
    for row in linked:
        by_user.setdefault(row["synaptiq_user_id"], set()).add(row["publication_id"])

    owned = await db.publications.find(
        {"owner_id": {"$in": candidate_ids}}, {"_id": 1, "owner_id": 1},
    ).to_list(5000)
    for row in owned:
        by_user.setdefault(row["owner_id"], set()).add(str(row["_id"]))

    all_pub_ids = {pid for pids in by_user.values() for pid in pids}
    if not all_pub_ids:
        return {}

    oids = [ObjectId(p) for p in all_pub_ids if ObjectId.is_valid(p)]
    pubs = await db.publications.find({"_id": {"$in": oids}}, {"title": 1}).to_list(5000)
    title_by_id = {str(p["_id"]): (p.get("title") or "").strip() for p in pubs}

    result: dict[str, list[str]] = {}
    for uid, pids in by_user.items():
        titles = sorted({title_by_id.get(pid) for pid in pids if title_by_id.get(pid)})
        if titles:
            result[uid] = titles
    return result
