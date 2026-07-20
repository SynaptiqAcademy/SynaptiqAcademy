"""
Dead Letter Queue — stores events that failed all retry attempts.

A failed event lands in the DLQ when:
  - A handler exhausted max retries without success
  - An unrecoverable error was raised

DLQ entries can be:
  - Inspected via the admin API
  - Retried manually (admin action)
  - Purged after investigation

Collection: `event_dlq`
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .models import DomainEvent

logger = logging.getLogger(__name__)

COLLECTION = "event_dlq"


async def ensure_indexes(db) -> None:
    try:
        col = db[COLLECTION]
        await col.create_index("event_id")
        await col.create_index("consumer_id")
        await col.create_index([("failed_at", -1)])
        await col.create_index("status")
    except Exception as exc:
        logger.debug("DLQ index setup: %s", exc)


class DeadLetterQueue:
    def __init__(self, db) -> None:
        self._db  = db
        self._col = db[COLLECTION]

    # ── Write ─────────────────────────────────────────────────────────────────

    async def enqueue(
        self,
        event: DomainEvent,
        *,
        consumer_id: str,
        error: str,
        attempt: int,
    ) -> None:
        """Move a failed event to the DLQ."""
        doc = {
            "event_id":    event.event_id,
            "event_type":  event.event_type,
            "event_data":  event.to_dict(),
            "consumer_id": consumer_id,
            "error":       str(error)[:2000],
            "attempt":     attempt,
            "status":      "pending",
            "failed_at":   datetime.now(timezone.utc),
            "retried_at":  None,
            "resolved_at": None,
        }
        try:
            await self._col.insert_one(doc)
            logger.warning(
                "DLQ: event %s → consumer %s after %d attempts: %s",
                event.event_id, consumer_id, attempt, str(error)[:200],
            )
        except Exception as exc:
            logger.error("DLQ.enqueue failed: %s", exc)

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_all(
        self,
        *,
        consumer_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        filt: dict = {}
        if consumer_id:
            filt["consumer_id"] = consumer_id
        if status:
            filt["status"] = status
        cursor = self._col.find(filt, sort=[("failed_at", -1)]).limit(limit)
        docs   = await cursor.to_list(length=limit)
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    async def get_pending_count(self) -> int:
        return await self._col.count_documents({"status": "pending"})

    # ── Actions ───────────────────────────────────────────────────────────────

    async def mark_retrying(self, event_id: str, consumer_id: str) -> None:
        await self._col.update_one(
            {"event_id": event_id, "consumer_id": consumer_id},
            {"$set": {"status": "retrying", "retried_at": datetime.now(timezone.utc)}},
        )

    async def mark_resolved(self, event_id: str, consumer_id: str) -> None:
        await self._col.update_one(
            {"event_id": event_id, "consumer_id": consumer_id},
            {"$set": {"status": "resolved", "resolved_at": datetime.now(timezone.utc)}},
        )

    async def mark_failed_permanently(self, event_id: str, consumer_id: str, error: str) -> None:
        await self._col.update_one(
            {"event_id": event_id, "consumer_id": consumer_id},
            {"$set": {"status": "failed_permanently", "last_error": str(error)[:2000]}},
        )

    async def get_for_retry(self, consumer_id: str | None = None) -> list[dict]:
        """Return pending DLQ entries ready for manual retry."""
        filt: dict = {"status": "pending"}
        if consumer_id:
            filt["consumer_id"] = consumer_id
        cursor = self._col.find(filt, sort=[("failed_at", 1)]).limit(100)
        docs   = await cursor.to_list(length=100)
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs
