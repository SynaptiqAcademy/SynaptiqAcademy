"""SYNAPTIQ Discovery Suite — ingest orchestrator.

Pulls batches from one or more providers, normalizes, deduplicates by
`entity_key`, and upserts into the canonical collection (journals/conferences/
grants). Per-(kind,source) cursors are persisted in `ingest_state` so subsequent
runs continue where the previous left off.

Run modes:
  - bounded: stop after `max_records` upserts (default — used for live sync).
  - to-completion: continue until provider returns next_cursor=None.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from pymongo import UpdateOne

from db import get_db
from services.discovery.base import BaseDiscoveryProvider
from services.discovery.registry import providers_for
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.discovery.ingest")

KIND_TO_COLLECTION = {"journal": "journals", "conference": "conferences", "grant": "grants"}


@dataclass
class IngestResult:
    kind: str
    source: str
    fetched: int = 0
    upserted: int = 0
    inserted: int = 0
    modified: int = 0
    errored: int = 0
    started_at: str = ""
    finished_at: str = ""
    cursor_before: Optional[str] = None
    cursor_after: Optional[str] = None
    error_log: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _load_cursor(kind: str, source: str) -> Optional[str]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    row = await db.ingest_state.find_one({"kind": kind, "source": source})
    return (row or {}).get("cursor")


async def _save_cursor(kind: str, source: str, cursor: Optional[str]) -> None:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.ingest_state.update_one(
        {"kind": kind, "source": source},
        {"$set": {"cursor": cursor, "updated_at": _now_iso()}},
        upsert=True,
    )


async def _persist_audit(result: IngestResult) -> None:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    payload = {
        "kind": result.kind, "source": result.source,
        "started_at": result.started_at, "finished_at": result.finished_at,
        "fetched": result.fetched, "upserted": result.upserted,
        "inserted": result.inserted, "modified": result.modified, "errored": result.errored,
        "cursor_before": result.cursor_before, "cursor_after": result.cursor_after,
        "error_log": result.error_log[-20:],
    }
    await db.ingest_runs.insert_one(payload)


async def _upsert_batch(coll_name: str, records: list[dict]) -> tuple[int, int, int]:
    """Returns (upserted, inserted, modified). All keyed on entity_key."""
    if not records: return (0, 0, 0)
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    ops = []
    now = _now_iso()
    for r in records:
        if not r.get("entity_key"): continue
        # last-write-wins for soft fields, but never overwrite to null
        clean = {k: v for k, v in r.items() if v not in (None, "", [], {})}
        clean["updated_at"] = now
        ops.append(UpdateOne(
            {"entity_key": r["entity_key"]},
            {"$set": clean,
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        ))
    if not ops: return (0, 0, 0)
    res = await db[coll_name].bulk_write(ops, ordered=False)
    return (res.upserted_count + res.modified_count, res.upserted_count, res.modified_count)


async def run_provider(provider: BaseDiscoveryProvider, *, max_records: int = 5000,
                        page_size: int = 200, reset_cursor: bool = False,
                        max_wall_seconds: int = 90) -> IngestResult:
    coll = KIND_TO_COLLECTION[provider.kind]
    result = IngestResult(kind=provider.kind, source=provider.name, started_at=_now_iso())
    cursor: Optional[str] = None if reset_cursor else (await _load_cursor(provider.kind, provider.name))
    result.cursor_before = cursor
    deadline = time.monotonic() + max_wall_seconds
    try:
        while result.upserted < max_records and time.monotonic() < deadline:
            try:
                records, next_cursor = await provider.fetch_batch(cursor, page_size)
            except Exception as e:
                result.error_log.append(f"fetch: {e}")
                result.errored += 1
                break
            if not records and not next_cursor:
                break
            result.fetched += len(records)
            up, ins, mod = await _upsert_batch(coll, records)
            result.upserted += up; result.inserted += ins; result.modified += mod
            cursor = next_cursor
            if not next_cursor:
                break
        result.cursor_after = cursor
        await _save_cursor(provider.kind, provider.name, cursor)
    finally:
        result.finished_at = _now_iso()
        try: await _persist_audit(result)
        except Exception as e: logger.warning("audit persist failed: %s", e)
    return result


async def run_kind(kind: str, *, providers: list[str] | None = None,
                    max_records_per_source: int = 5000, reset_cursor: bool = False,
                    max_wall_seconds_per_source: int = 90) -> list[IngestResult]:
    selected = providers_for(kind, names=providers)
    if providers is None:
        selected = providers_for(kind, only_default=True)
    results: list[IngestResult] = []
    for p in selected:
        logger.info("[ingest] start kind=%s source=%s max=%s", kind, p.name, max_records_per_source)
        try:
            res = await run_provider(p, max_records=max_records_per_source,
                                     reset_cursor=reset_cursor,
                                     max_wall_seconds=max_wall_seconds_per_source)
            results.append(res)
            logger.info("[ingest] done kind=%s source=%s upserted=%s fetched=%s",
                        kind, p.name, res.upserted, res.fetched)
        except Exception as e:
            logger.exception("[ingest] provider failed kind=%s source=%s err=%s", kind, p.name, e)
    return results


# ----------------------------- index maintenance -----------------------------
async def ensure_indexes() -> None:
    """Create / refresh indexes for the discovery collections. Idempotent."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    # Journals
    await db.journals.create_index("entity_key", unique=True, sparse=True)
    await db.journals.create_index([("title", "text"), ("publisher", "text"),
                                    ("subjects", "text"), ("scope_keywords", "text")],
                                    name="journals_text", default_language="english")
    await db.journals.create_index("external_ids.issn_l")
    await db.journals.create_index("external_ids.openalex")
    await db.journals.create_index("quartile")
    await db.journals.create_index("open_access")
    await db.journals.create_index([("popularity_score", -1)])
    await db.journals.create_index([("works_count", -1)])
    # Conferences
    await db.conferences.create_index("entity_key", unique=True, sparse=True)
    await db.conferences.create_index([("name", "text"), ("acronym", "text"),
                                       ("topics", "text"), ("research_areas", "text")],
                                       name="conferences_text", default_language="english")
    await db.conferences.create_index("submission_deadline")
    await db.conferences.create_index("rank")
    # Grants
    await db.grants.create_index("entity_key", unique=True, sparse=True)
    await db.grants.create_index([("title", "text"), ("sponsor", "text"),
                                  ("research_areas", "text"), ("keywords", "text"),
                                  ("abstract_text", "text")],
                                  name="grants_text", default_language="english")
    await db.grants.create_index("deadline")
    await db.grants.create_index("country")
    await db.grants.create_index("sponsor")
    # Submissions
    await db.submissions.create_index("manuscript_id")
    await db.submissions.create_index("author_id")
    await db.submissions.create_index([("author_id", 1), ("stage", 1)])
    # Audit
    await db.ingest_runs.create_index([("kind", 1), ("source", 1), ("started_at", -1)])
    await db.ingest_state.create_index([("kind", 1), ("source", 1)], unique=True)
    # AI requests audit
    await db.ai_requests.create_index([("user_id", 1), ("created_at", -1)])
    await db.ai_requests.create_index([("kind", 1), ("created_at", -1)])
    await db.chat_sessions.create_index([("user_id", 1), ("updated_at", -1)])
    await db.chat_sessions.create_index([("entity_kind", 1), ("entity_id", 1)])
    await db.chat_messages.create_index([("session_id", 1), ("created_at", 1)])
    await db.saved_searches.create_index([("user_id", 1), ("created_at", -1)])
    await db.saved_searches.create_index("frequency")
    logger.info("Discovery indexes ensured")
