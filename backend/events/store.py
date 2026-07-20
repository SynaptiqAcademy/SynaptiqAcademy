"""
EventStore — durable persistence for every domain event.

Supports:
  - append (with idempotency guard on event_id)
  - query by type, aggregate, user, time range, correlation
  - replay cursor for ReplayEngine
  - time-travel: get state at a point in time

Collection: `event_store`
Indexes:
  - event_id (unique)
  - event_type + timestamp
  - aggregate_type + aggregate_id + timestamp
  - user_id + timestamp
  - correlation_id
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import AsyncIterator

from .models import DomainEvent, event_from_dict

logger = logging.getLogger(__name__)

COLLECTION = "event_store"
IDEMPOTENCY_COLLECTION = "event_processed"   # tracks (event_id, consumer_id) pairs


async def ensure_indexes(db) -> None:
    try:
        col = db[COLLECTION]
        await col.create_index("event_id", unique=True, sparse=False)
        await col.create_index([("event_type", 1), ("timestamp", -1)])
        await col.create_index([("aggregate_type", 1), ("aggregate_id", 1), ("timestamp", 1)])
        await col.create_index([("user_id", 1), ("timestamp", -1)])
        await col.create_index("correlation_id")
        await col.create_index("timestamp")

        idem = db[IDEMPOTENCY_COLLECTION]
        await idem.create_index([("event_id", 1), ("consumer_id", 1)], unique=True)
        await idem.create_index("processed_at", expireAfterSeconds=86400 * 30)  # 30-day TTL
    except Exception as exc:
        logger.debug("EventStore index setup: %s", exc)


class EventStore:
    def __init__(self, db) -> None:
        self._db  = db
        self._col = db[COLLECTION]

    # ── Write ─────────────────────────────────────────────────────────────────

    async def append(self, event: DomainEvent) -> bool:
        """
        Persist event. Returns True if new, False if duplicate (idempotent).
        """
        doc = event.to_dict()
        try:
            await self._col.insert_one(doc)
            return True
        except Exception as exc:
            if "duplicate" in str(exc).lower() or "E11000" in str(exc):
                return False   # already stored — idempotent
            logger.warning("EventStore.append error: %s", exc)
            return False

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, event_id: str) -> DomainEvent | None:
        doc = await self._col.find_one({"event_id": event_id})
        return event_from_dict(doc) if doc else None

    async def get_by_aggregate(
        self,
        aggregate_id: str,
        aggregate_type: str,
        *,
        since: datetime | None = None,
        limit: int = 200,
    ) -> list[DomainEvent]:
        filt: dict = {"aggregate_id": aggregate_id, "aggregate_type": aggregate_type}
        if since:
            filt["timestamp"] = {"$gte": since.isoformat() if isinstance(since, datetime) else since}
        cursor = self._col.find(filt, sort=[("timestamp", 1)]).limit(limit)
        docs   = await cursor.to_list(length=limit)
        return [event_from_dict(d) for d in docs]

    async def get_by_type(
        self,
        event_type: str,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        user_id: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[DomainEvent]:
        filt: dict = {"event_type": event_type}
        ts_filter: dict = {}
        if since:
            ts_filter["$gte"] = since.isoformat() if isinstance(since, datetime) else since
        if until:
            ts_filter["$lte"] = until.isoformat() if isinstance(until, datetime) else until
        if ts_filter:
            filt["timestamp"] = ts_filter
        if user_id:
            filt["user_id"] = user_id
        cursor = (
            self._col.find(filt, sort=[("timestamp", -1)])
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [event_from_dict(d) for d in docs]

    async def get_by_correlation(self, correlation_id: str) -> list[DomainEvent]:
        cursor = self._col.find(
            {"correlation_id": correlation_id},
            sort=[("timestamp", 1)],
        )
        docs = await cursor.to_list(length=500)
        return [event_from_dict(d) for d in docs]

    async def get_recent(self, *, limit: int = 50, event_type: str | None = None) -> list[dict]:
        filt = {}
        if event_type:
            filt["event_type"] = event_type
        cursor = self._col.find(filt, sort=[("timestamp", -1)]).limit(limit)
        docs   = await cursor.to_list(length=limit)
        for d in docs:
            d.pop("_id", None)
        return docs

    async def count(
        self,
        *,
        event_type: str | None = None,
        since: datetime | None = None,
    ) -> int:
        filt: dict = {}
        if event_type:
            filt["event_type"] = event_type
        if since:
            filt["timestamp"] = {"$gte": since.isoformat() if isinstance(since, datetime) else since}
        return await self._col.count_documents(filt)

    # ── Replay cursor ─────────────────────────────────────────────────────────

    async def cursor(
        self,
        *,
        event_types: list[str] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        aggregate_type: str | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[DomainEvent]:
        """
        Async generator for replay — yields events in chronological order.
        """
        filt: dict = {}
        if event_types:
            filt["event_type"] = {"$in": event_types}
        if aggregate_type:
            filt["aggregate_type"] = aggregate_type
        ts_filter: dict = {}
        if since:
            ts_filter["$gte"] = since.isoformat() if isinstance(since, datetime) else since
        if until:
            ts_filter["$lte"] = until.isoformat() if isinstance(until, datetime) else until
        if ts_filter:
            filt["timestamp"] = ts_filter

        cursor = self._col.find(filt, sort=[("timestamp", 1)]).batch_size(batch_size)
        async for doc in cursor:
            yield event_from_dict(doc)

    # ── Idempotency ───────────────────────────────────────────────────────────

    async def mark_processed(self, event_id: str, consumer_id: str) -> bool:
        """
        Record that consumer_id has processed event_id.
        Returns True if newly marked, False if already processed.
        """
        try:
            await self._db[IDEMPOTENCY_COLLECTION].insert_one({
                "event_id":    event_id,
                "consumer_id": consumer_id,
                "processed_at": datetime.now(timezone.utc),
            })
            return True
        except Exception as exc:
            if "duplicate" in str(exc).lower() or "E11000" in str(exc):
                return False
            logger.warning("mark_processed error: %s", exc)
            return False

    async def is_processed(self, event_id: str, consumer_id: str) -> bool:
        doc = await self._db[IDEMPOTENCY_COLLECTION].find_one({
            "event_id":    event_id,
            "consumer_id": consumer_id,
        })
        return doc is not None

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def type_distribution(self) -> list[dict]:
        pipeline = [
            {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 50},
        ]
        cursor  = self._col.aggregate(pipeline)
        results = await cursor.to_list(length=50)
        return [{"event_type": r["_id"], "count": r["count"]} for r in results]
