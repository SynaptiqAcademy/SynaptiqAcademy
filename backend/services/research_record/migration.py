"""Idempotent startup migration for the Academic Research Record (Phase 1).

Two independent, additive fixes — safe to run on every boot:

1. owner_id/user_id/author_ids alias backfill. Audit finding: `publications`
   is written exclusively with `owner_id` (services/orcid/sync.py,
   services/citations/sync_service.py), but roughly 15 reader modules
   (services/iip/*, services/sie/*, services/timeline/*, services/
   verification/*, routers/analytics.py, routers/admin_aos.py's own
   integrity checker) query `user_id` or `author_ids` instead — fields
   nothing ever wrote. Those reads have always silently returned empty
   results. Rather than editing ~15 call sites (each needing its own
   verification), every publications document gets `user_id` and
   `author_ids` backfilled as aliases of `owner_id` — the safest, least
   disruptive fix: no reader code changes, and every currently-broken
   reader starts working. `owner_id` remains authoritative.

2. `origin` backfill for pre-existing rows: every publications document
   that predates this migration was ORCID/OpenAlex-sourced (there was no
   other write path), so `origin="external"` is not a guess — it's the
   only value that was ever possible before this phase.

This does NOT add the unique DOI index (server.py handles indexes) — that
is explicitly gated on a production duplicate-DOI audit per the approved
design, not performed here.

Implementation note: this deliberately avoids aggregation-pipeline update
syntax (`update_many(filter, [{"$set": ...}])`) — repo/shim.py's DBProxy
(the security-wrapping layer every collection access in this codebase goes
through) only handles plain `{"$set": ...}` update documents in its
`_enrich_update()` helper; a list-form pipeline update crashes it
(confirmed in production: `AttributeError: 'dict' object has no attribute
'startswith'`, repo/shim.py:210 trying to iterate pipeline stages as if
they were dict keys). A plain per-document find+update loop sidesteps that
limitation entirely and needs no change to shared proxy code.
"""
from __future__ import annotations

import logging

log = logging.getLogger("synaptiq.research_record")


async def ensure_publications_backward_compat(db) -> dict:
    user_id_backfilled = 0
    author_ids_backfilled = 0

    cursor = db.publications.find(
        {"owner_id": {"$exists": True}},
        {"owner_id": 1, "user_id": 1, "author_ids": 1},
    )
    async for doc in cursor:
        updates: dict = {}
        if "user_id" not in doc:
            updates["user_id"] = doc["owner_id"]
        if "author_ids" not in doc:
            updates["author_ids"] = [doc["owner_id"]]
        if updates:
            await db.publications.update_one({"_id": doc["_id"]}, {"$set": updates})
            if "user_id" in updates:
                user_id_backfilled += 1
            if "author_ids" in updates:
                author_ids_backfilled += 1

    # `source` is left untouched — it's already populated correctly by the
    # existing writers (orcid/sync.py sets "orcid", the OpenAlex citation
    # sync sets "openalex"); only the new `origin` field is backfilled.
    origin_result = await db.publications.update_many(
        {"origin": {"$exists": False}},
        {"$set": {"origin": "external"}},
    )
    report = {
        "user_id_backfilled": user_id_backfilled,
        "author_ids_backfilled": author_ids_backfilled,
        "origin_backfilled": origin_result.modified_count,
    }
    log.info("Academic Research Record backward-compat migration: %s", report)
    return report
