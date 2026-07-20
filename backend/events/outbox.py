"""
Outbox Pattern — transactional event publishing.

Problem: if you write to MongoDB AND publish an event in separate operations,
a crash between the two leaves state inconsistent (write succeeded, event lost).

Solution: write the event to the `event_outbox` collection in the SAME
transaction as the business data. A background relay loop then reads from
the outbox, dispatches events to the bus, and marks them delivered.

This guarantees at-least-once delivery: every committed business write will
eventually emit its domain event, even across server restarts.

Outbox schema:
  - event_data:    serialized DomainEvent
  - status:        "pending" | "delivered" | "failed"
  - created_at:    datetime
  - delivered_at:  datetime | None
  - attempts:      int
  - last_error:    str | None

Collection: `event_outbox`
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .models import DomainEvent, event_from_dict

if TYPE_CHECKING:
    from .bus import EnterpriseEventBus

logger = logging.getLogger(__name__)

COLLECTION = "event_outbox"
_RELAY_INTERVAL_S = 5      # how often the relay loop polls
_MAX_ATTEMPTS     = 5      # before marking as failed


async def ensure_indexes(db) -> None:
    try:
        col = db[COLLECTION]
        await col.create_index([("status", 1), ("created_at", 1)])
        await col.create_index("event_id", unique=True)
    except Exception as exc:
        logger.debug("Outbox index setup: %s", exc)


class OutboxPublisher:
    """
    Writes events to the outbox transactionally.

    Usage (with a MongoDB session for atomicity):
        async with Tx(db) as tx:
            # ... business write ...
            await outbox.write(event, session=tx.session)
    """

    def __init__(self, db) -> None:
        self._col = db[COLLECTION]

    async def write(self, event: DomainEvent, *, session=None) -> None:
        """Write event to outbox. Should be called inside the same transaction
        as the business write that produced this event."""
        doc = {
            "event_id":     event.event_id,
            "event_type":   event.event_type,
            "event_data":   event.to_dict(),
            "status":       "pending",
            "created_at":   datetime.now(timezone.utc),
            "delivered_at": None,
            "attempts":     0,
            "last_error":   None,
        }
        try:
            await self._col.insert_one(doc, session=session)
        except Exception as exc:
            if "duplicate" not in str(exc).lower():
                raise

    async def write_many(self, events: list[DomainEvent], *, session=None) -> None:
        for event in events:
            await self.write(event, session=session)


class OutboxRelay:
    """
    Background loop that relays pending outbox events to the enterprise bus.

    - Polls `event_outbox` for pending events
    - Dispatches each via bus.dispatch_direct()
    - Marks delivered or failed
    - On startup, recovers undelivered events from previous server runs
    """

    def __init__(self, db, bus: "EnterpriseEventBus") -> None:
        self._db   = db
        self._col  = db[COLLECTION]
        self._bus  = bus
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task    = asyncio.create_task(self._loop())
        logger.info("OutboxRelay started (poll interval %ds)", _RELAY_INTERVAL_S)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def recover(self) -> int:
        """
        On server startup, find events that were written to the outbox in a
        previous server run but never delivered. Requeue them for dispatch.
        Returns count of recovered events.
        """
        result = await self._col.update_many(
            {"status": "delivering"},
            {"$set": {"status": "pending"}},
        )
        count = result.modified_count
        if count:
            logger.info("OutboxRelay: recovered %d stuck events from previous run", count)
        return count

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._relay_batch()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("OutboxRelay loop error: %s", exc)
            await asyncio.sleep(_RELAY_INTERVAL_S)

    async def _relay_batch(self) -> None:
        # Pick up to 50 pending events in FIFO order
        cursor = self._col.find(
            {"status": "pending"},
            sort=[("created_at", 1)],
        ).limit(50)
        docs = await cursor.to_list(length=50)
        if not docs:
            return

        for doc in docs:
            await self._relay_one(doc)

    async def _relay_one(self, doc: dict) -> None:
        event_id = doc.get("event_id", "")

        # Mark as delivering (optimistic lock — prevents double-delivery in multi-worker)
        result = await self._col.find_one_and_update(
            {"event_id": event_id, "status": "pending"},
            {"$set": {"status": "delivering"}, "$inc": {"attempts": 1}},
        )
        if not result:
            return   # another worker got it first

        try:
            event = event_from_dict(doc["event_data"])
            await self._bus.dispatch_direct(event)

            await self._col.update_one(
                {"event_id": event_id},
                {"$set": {"status": "delivered", "delivered_at": datetime.now(timezone.utc)}},
            )
        except Exception as exc:
            attempts = doc.get("attempts", 0) + 1
            if attempts >= _MAX_ATTEMPTS:
                await self._col.update_one(
                    {"event_id": event_id},
                    {"$set": {"status": "failed", "last_error": str(exc)[:500]}},
                )
                logger.error("Outbox: event %s failed permanently: %s", event_id, exc)
            else:
                await self._col.update_one(
                    {"event_id": event_id},
                    {"$set": {"status": "pending", "last_error": str(exc)[:500]}},
                )
                logger.warning("Outbox: event %s retry %d/%d: %s", event_id, attempts, _MAX_ATTEMPTS, exc)

    async def pending_count(self) -> int:
        return await self._col.count_documents({"status": "pending"})

    async def failed_count(self) -> int:
        return await self._col.count_documents({"status": "failed"})
