"""
Mission Execution Queue — priority queue with Redis backing and in-process fallback.

Supports:
  FIFO within each priority level
  Priority-based ordering (EMERGENCY executes before BACKGROUND)
  Delayed enqueueing (run after N seconds)
  Dead Letter Queue for permanently failed missions

Redis implementation:
  Ready queue:   ara:queue:ready   (sorted set, score = priority * 1e12 + epoch_ms)
  Delayed queue: ara:queue:delayed (sorted set, score = run_after epoch_ms)
  Dead letter:   ara:queue:dead    (sorted set, value = JSON{mission_id, reason, ts})

In-process fallback:
  asyncio.PriorityQueue with (priority, enqueue_ts, mission_id) tuples.
  Used when Redis is unavailable. Does NOT survive restarts (acceptable degraded mode).

Future: swap Redis adapter for Celery, RabbitMQ, or Kafka without changing callers.
"""
from __future__ import annotations

import asyncio
import heapq
import json
import logging
import time
from enum import IntEnum

logger = logging.getLogger("ara.engine.queue")

_KEY_READY   = "ara:queue:ready"
_KEY_DELAYED = "ara:queue:delayed"
_KEY_DEAD    = "ara:queue:dead"


class Priority(IntEnum):
    EMERGENCY  = 1
    HIGH       = 2
    NORMAL     = 5
    LOW        = 7
    BACKGROUND = 9


def _score(priority: int) -> float:
    """Lower score → dequeued first. Priority 1 (EMERGENCY) gets score ~1e12."""
    return priority * 1e12 + time.time() * 1000


class ExecutionQueue:
    """
    Priority queue abstraction. Callers never depend on the backing implementation.
    Redis is used when available; falls back to in-process heap otherwise.
    """

    def __init__(self):
        self._heap: list[tuple] = []  # (score, mission_id) — in-process fallback
        self._dead: list[dict]  = []  # in-process dead letter

    # ── Enqueue ───────────────────────────────────────────────────────────────

    async def enqueue(
        self,
        mission_id: str,
        priority: int = Priority.NORMAL,
        delay_seconds: float = 0.0,
    ) -> None:
        """Add mission to the ready (or delayed) queue."""
        r = await _get_redis()
        score = _score(priority)

        if r:
            try:
                if delay_seconds > 0:
                    run_at = time.time() + delay_seconds
                    await r.zadd(_KEY_DELAYED, {mission_id: run_at})
                else:
                    await r.zadd(_KEY_READY, {mission_id: score})
                logger.debug("enqueued mission=%s priority=%d delay=%.0fs", mission_id, priority, delay_seconds)
                return
            except Exception as exc:
                logger.debug("Redis enqueue failed, using in-process: %s", exc)

        # In-process fallback
        heapq.heappush(self._heap, (score, mission_id))

    # ── Dequeue ───────────────────────────────────────────────────────────────

    async def dequeue(self) -> str | None:
        """Pop the highest-priority mission_id, or None if queue is empty."""
        # First: promote any delayed items that are now due
        await self._promote_delayed()

        r = await _get_redis()
        if r:
            try:
                # ZPOPMIN returns [(member, score), ...]
                items = await r.zpopmin(_KEY_READY, 1)
                if items:
                    return items[0][0] if isinstance(items[0], tuple) else items[0]
                return None
            except Exception as exc:
                logger.debug("Redis dequeue failed, using in-process: %s", exc)

        if self._heap:
            _, mission_id = heapq.heappop(self._heap)
            return mission_id
        return None

    # ── Remove ────────────────────────────────────────────────────────────────

    async def remove(self, mission_id: str) -> None:
        """Remove a mission from the queue (e.g. on cancellation)."""
        r = await _get_redis()
        if r:
            try:
                await r.zrem(_KEY_READY, mission_id)
                await r.zrem(_KEY_DELAYED, mission_id)
                return
            except Exception:
                pass
        self._heap = [(s, m) for s, m in self._heap if m != mission_id]
        heapq.heapify(self._heap)

    # ── Requeue ───────────────────────────────────────────────────────────────

    async def requeue(
        self,
        mission_id: str,
        delay_seconds: float = 0.0,
        priority: int = Priority.NORMAL,
    ) -> None:
        """Re-add a mission (after failure / recovery)."""
        await self.remove(mission_id)
        await self.enqueue(mission_id, priority=priority, delay_seconds=delay_seconds)

    # ── Peek ──────────────────────────────────────────────────────────────────

    async def peek(self, limit: int = 10) -> list[str]:
        """Return next `limit` mission_ids without removing them."""
        r = await _get_redis()
        if r:
            try:
                items = await r.zrange(_KEY_READY, 0, limit - 1)
                return list(items)
            except Exception:
                pass
        return [m for _, m in sorted(self._heap)[:limit]]

    # ── Size ──────────────────────────────────────────────────────────────────

    async def size(self) -> int:
        r = await _get_redis()
        if r:
            try:
                return await r.zcard(_KEY_READY)
            except Exception:
                pass
        return len(self._heap)

    # ── Dead Letter Queue ─────────────────────────────────────────────────────

    async def dead_letter(self, mission_id: str, reason: str) -> None:
        """Move a permanently-failed mission to the DLQ."""
        await self.remove(mission_id)
        entry = json.dumps({"mission_id": mission_id, "reason": reason, "ts": time.time()})
        r = await _get_redis()
        if r:
            try:
                await r.zadd(_KEY_DEAD, {entry: time.time()})
                return
            except Exception:
                pass
        self._dead.append({"mission_id": mission_id, "reason": reason})

    async def list_dead_letter(self) -> list[dict]:
        r = await _get_redis()
        if r:
            try:
                items = await r.zrange(_KEY_DEAD, 0, -1)
                return [json.loads(i) for i in items]
            except Exception:
                pass
        return list(self._dead)

    # ── Delayed promotion ─────────────────────────────────────────────────────

    async def _promote_delayed(self) -> None:
        """Move delayed items whose run_at has passed into the ready queue."""
        r = await _get_redis()
        if r:
            try:
                now = time.time()
                due = await r.zrangebyscore(_KEY_DELAYED, 0, now)
                if due:
                    await r.zrem(_KEY_DELAYED, *due)
                    mapping = {m: _score(Priority.NORMAL) for m in due}
                    await r.zadd(_KEY_READY, mapping)
            except Exception:
                pass


# ── Redis accessor ─────────────────────────────────────────────────────────────

async def _get_redis():
    try:
        from services.redis_client import get_redis
        return await get_redis()
    except Exception:
        return None


# ── Process-level singleton ───────────────────────────────────────────────────

_queue: ExecutionQueue | None = None


def get_queue() -> ExecutionQueue:
    global _queue
    if _queue is None:
        _queue = ExecutionQueue()
    return _queue
