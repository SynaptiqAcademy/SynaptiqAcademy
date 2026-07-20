"""PriorityRequestQueue — asyncio priority queue with timeout, retry, dead-letter."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass(order=True)
class _QueueItem:
    priority_score: int        # lower = higher priority (asyncio.PriorityQueue is min-heap)
    enqueued_at: float = field(compare=False, default_factory=time.monotonic)
    request_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))
    feature: str = field(compare=False, default="")
    user_id: str = field(compare=False, default="")
    payload: Any = field(compare=False, default=None)
    max_wait_ms: int = field(compare=False, default=10000)
    retries_remaining: int = field(compare=False, default=2)
    cancelled: bool = field(compare=False, default=False)
    future: asyncio.Future | None = field(compare=False, default=None)


class _DeadLetterQueue:
    def __init__(self, max_size: int = 500) -> None:
        self._items: list[dict] = []
        self._max = max_size

    def add(self, item: _QueueItem, reason: str) -> None:
        if len(self._items) >= self._max:
            self._items.pop(0)
        self._items.append({
            "request_id": item.request_id,
            "feature": item.feature,
            "priority_score": item.priority_score,
            "reason": reason,
            "enqueued_at": item.enqueued_at,
            "failed_at": time.monotonic(),
        })

    def list_items(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._items))[:limit]

    def size(self) -> int:
        return len(self._items)


class PriorityRequestQueue:
    """Async priority queue for AI requests with cancellation and dead-letter support."""

    def __init__(self, max_size: int = 1000) -> None:
        self._queue: asyncio.PriorityQueue[_QueueItem] = asyncio.PriorityQueue(maxsize=max_size)
        self._dlq = _DeadLetterQueue()
        self._active: dict[str, _QueueItem] = {}
        self._total_enqueued = 0
        self._total_completed = 0
        self._total_timed_out = 0
        self._total_cancelled = 0
        self._total_dead_lettered = 0

    async def enqueue(
        self,
        feature: str,
        priority_score: int,
        payload: Any,
        user_id: str = "",
        max_wait_ms: int = 10000,
        retries: int = 2,
    ) -> tuple[str, asyncio.Future]:
        """Add a request to the queue. Returns (request_id, future)."""
        if self._queue.full():
            raise asyncio.QueueFull("Request queue is full")

        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        item = _QueueItem(
            priority_score=priority_score,
            feature=feature,
            user_id=user_id,
            payload=payload,
            max_wait_ms=max_wait_ms,
            retries_remaining=retries,
            future=future,
        )
        await self._queue.put(item)
        self._total_enqueued += 1
        return item.request_id, future

    async def dequeue(self, timeout_s: float = 5.0) -> _QueueItem | None:
        """Get the next item from the queue (highest priority first)."""
        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=timeout_s)
        except asyncio.TimeoutError:
            return None

        if item.cancelled:
            self._total_cancelled += 1
            self._queue.task_done()
            return None

        # Check if the item has exceeded its max wait time
        wait_ms = (time.monotonic() - item.enqueued_at) * 1000
        if wait_ms > item.max_wait_ms:
            self._total_timed_out += 1
            self._dlq.add(item, f"wait_timeout: {wait_ms:.0f}ms > {item.max_wait_ms}ms")
            if item.future and not item.future.done():
                item.future.set_exception(asyncio.TimeoutError(f"Queue wait exceeded {item.max_wait_ms}ms"))
            self._queue.task_done()
            return None

        self._active[item.request_id] = item
        return item

    def complete(self, request_id: str, result: Any) -> None:
        """Mark a request as complete and resolve its future."""
        item = self._active.pop(request_id, None)
        if item is None:
            return
        self._total_completed += 1
        if item.future and not item.future.done():
            item.future.set_result(result)
        try:
            self._queue.task_done()
        except ValueError:
            pass

    def fail(self, request_id: str, error: Exception) -> None:
        """Mark a request as failed. Requeue if retries remain."""
        item = self._active.pop(request_id, None)
        if item is None:
            return
        if item.retries_remaining > 0:
            item.retries_remaining -= 1
            item.enqueued_at = time.monotonic()  # reset wait timer for retry
            try:
                self._queue.put_nowait(item)
            except asyncio.QueueFull:
                self._dlq.add(item, "queue_full_on_retry")
                if item.future and not item.future.done():
                    item.future.set_exception(error)
                self._total_dead_lettered += 1
        else:
            self._dlq.add(item, str(error)[:200])
            if item.future and not item.future.done():
                item.future.set_exception(error)
            self._total_dead_lettered += 1
        try:
            self._queue.task_done()
        except ValueError:
            pass

    def cancel(self, request_id: str) -> bool:
        """Mark a queued request for cancellation."""
        item = self._active.get(request_id)
        if item:
            item.cancelled = True
            self._total_cancelled += 1
            return True
        return False

    def queue_size(self) -> int:
        return self._queue.qsize()

    def active_count(self) -> int:
        return len(self._active)

    def stats(self) -> dict:
        return {
            "queue_size": self.queue_size(),
            "active_requests": self.active_count(),
            "total_enqueued": self._total_enqueued,
            "total_completed": self._total_completed,
            "total_timed_out": self._total_timed_out,
            "total_cancelled": self._total_cancelled,
            "total_dead_lettered": self._total_dead_lettered,
            "dead_letter_queue_size": self._dlq.size(),
        }

    def dead_letter_items(self, limit: int = 50) -> list[dict]:
        return self._dlq.list_items(limit)
