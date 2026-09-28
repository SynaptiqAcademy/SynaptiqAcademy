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
"""
from __future__ import annotations

import logging

log = logging.getLogger("synaptiq.research_record")


async def ensure_publications_backward_compat(db) -> dict:
    alias_result = await db.publications.update_many(
        {"owner_id": {"$exists": True}, "user_id": {"$exists": False}},
        [{"$set": {"user_id": "$owner_id"}}],
    )
    author_ids_result = await db.publications.update_many(
        {"owner_id": {"$exists": True}, "author_ids": {"$exists": False}},
        [{"$set": {"author_ids": ["$owner_id"]}}],
    )
    # `source` is left untouched — it's already populated correctly by the
    # existing writers (orcid/sync.py sets "orcid", the OpenAlex citation
    # sync sets "openalex"); only the new `origin` field is backfilled.
    origin_result = await db.publications.update_many(
        {"origin": {"$exists": False}},
        {"$set": {"origin": "external"}},
    )
    report = {
        "user_id_backfilled": alias_result.modified_count,
        "author_ids_backfilled": author_ids_result.modified_count,
        "origin_backfilled": origin_result.modified_count,
    }
    log.info("Academic Research Record backward-compat migration: %s", report)
    return report
