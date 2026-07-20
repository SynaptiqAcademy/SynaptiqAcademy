"""
Handler Framework — async execution of event handlers with full resilience.

Every handler registration includes:
  - consumer_id: unique identifier for this handler within the bus
  - handler:     async callable (event: DomainEvent) -> None
  - timeout_s:   max seconds before cancellation (default 30)
  - retry_policy: HandlerRetryPolicy (default 3 attempts, exponential backoff)
  - idempotent:  whether to check EventStore before executing (default True)

Execution guarantees:
  1. Idempotency check (mark_processed before calling handler)
  2. Circuit breaker (skip if too many recent failures)
  3. Timeout (asyncio.wait_for)
  4. Retry with backoff (transient errors only)
  5. DLQ (on permanent failure or exhausted retries)

One failed handler NEVER stops execution of other handlers for the same event.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from .circuit_breaker import get_circuit_breaker
from .models          import DomainEvent
from .observability   import get_observability
from .retry           import HandlerRetryPolicy, DEFAULT_RETRY_POLICY, execute_with_retry

logger = logging.getLogger(__name__)

Handler = Callable[[DomainEvent], Awaitable[None]]


@dataclass
class HandlerRegistration:
    consumer_id:   str
    event_type:    str          # "*" = wildcard (all events)
    handler:       Handler
    timeout_s:     float        = 30.0
    retry_policy:  HandlerRetryPolicy = field(default_factory=lambda: DEFAULT_RETRY_POLICY)
    idempotent:    bool         = True
    description:   str          = ""


class HandlerRegistry:
    """Stores and retrieves handler registrations by event type."""

    def __init__(self) -> None:
        self._by_type:  dict[str, list[HandlerRegistration]] = {}
        self._wildcards: list[HandlerRegistration]            = []

    def register(self, reg: HandlerRegistration) -> None:
        if reg.event_type == "*":
            self._wildcards.append(reg)
        else:
            self._by_type.setdefault(reg.event_type, []).append(reg)
        logger.debug("EventBus: registered %s → %s", reg.event_type, reg.consumer_id)

    def unregister(self, consumer_id: str, event_type: str | None = None) -> int:
        removed = 0
        if event_type:
            lst = self._by_type.get(event_type, [])
            before = len(lst)
            self._by_type[event_type] = [r for r in lst if r.consumer_id != consumer_id]
            removed += before - len(self._by_type[event_type])
        else:
            for etype in list(self._by_type):
                lst = self._by_type[etype]
                before = len(lst)
                self._by_type[etype] = [r for r in lst if r.consumer_id != consumer_id]
                removed += before - len(self._by_type[etype])
            before = len(self._wildcards)
            self._wildcards = [r for r in self._wildcards if r.consumer_id != consumer_id]
            removed += before - len(self._wildcards)
        return removed

    def get_handlers(self, event_type: str) -> list[HandlerRegistration]:
        return self._by_type.get(event_type, []) + self._wildcards

    def all_registrations(self) -> list[dict]:
        result = []
        for regs in self._by_type.values():
            for r in regs:
                result.append({
                    "consumer_id": r.consumer_id,
                    "event_type":  r.event_type,
                    "timeout_s":   r.timeout_s,
                    "description": r.description,
                })
        for r in self._wildcards:
            result.append({
                "consumer_id": r.consumer_id,
                "event_type":  "*",
                "timeout_s":   r.timeout_s,
                "description": r.description,
            })
        return result


class HandlerExecutor:
    """
    Executes a single handler registration for an event with full resilience.

    Handles:
      - Idempotency guard (via EventStore)
      - Circuit breaker (via CircuitBreakerRegistry)
      - Timeout wrapper
      - Retry with backoff
      - DLQ on exhaustion
    """

    def __init__(self, store, dlq) -> None:
        self._store = store    # EventStore
        self._dlq   = dlq      # DeadLetterQueue
        self._obs   = get_observability()

    async def execute(self, reg: HandlerRegistration, event: DomainEvent) -> None:
        """Execute one handler registration. Never raises — captures all errors."""
        cb = get_circuit_breaker(reg.consumer_id)

        if not cb.allow_request():
            logger.debug(
                "EventBus: skip %s for %s (circuit OPEN)",
                event.event_type, reg.consumer_id,
            )
            self._obs.record_skipped(reg.consumer_id)
            return

        # Idempotency guard
        if reg.idempotent and self._store:
            try:
                already = await self._store.is_processed(event.event_id, reg.consumer_id)
                if already:
                    logger.debug(
                        "EventBus: skip %s / %s (already processed)",
                        event.event_id, reg.consumer_id,
                    )
                    return
            except Exception as exc:
                logger.debug("Idempotency check error (non-fatal): %s", exc)

        # Wrap handler with optional timeout into a callable for execute_with_retry
        timeout_s = reg.timeout_s

        async def _call(ev):
            if timeout_s > 0:
                await asyncio.wait_for(reg.handler(ev), timeout=timeout_s)
            else:
                await reg.handler(ev)

        start = time.monotonic()
        try:
            await execute_with_retry(
                _call,
                event,
                policy=reg.retry_policy,
                consumer_id=reg.consumer_id,
                on_retry=lambda _: self._obs.record_retry(event.event_type),
            )

            latency_ms = (time.monotonic() - start) * 1000
            cb.record_success()
            self._obs.record_success(event.event_type, reg.consumer_id, latency_ms)

            # Mark idempotency record
            if reg.idempotent and self._store:
                try:
                    await self._store.mark_processed(event.event_id, reg.consumer_id)
                except Exception:
                    pass

        except Exception as exc:
            cb.record_failure()
            self._obs.record_failure(event.event_type, reg.consumer_id)
            self._obs.record_dlq(event.event_type, reg.consumer_id)

            logger.error(
                "EventBus: handler %s failed for %s: %s",
                reg.consumer_id, event.event_type, exc,
            )

            if self._dlq:
                try:
                    await self._dlq.enqueue(
                        event,
                        consumer_id=reg.consumer_id,
                        error=str(exc),
                        attempt=reg.retry_policy.max_attempts,
                    )
                except Exception as dlq_exc:
                    logger.error("DLQ enqueue error: %s", dlq_exc)


# ── Convenience: execute_with_retry adapter ───────────────────────────────────
# The retry module's execute_with_retry expects a coroutine-returning callable,
# but we may pass a coroutine directly. Wrap it:

async def _wrap_coro(coro_or_callable, event):
    if asyncio.iscoroutine(coro_or_callable):
        await coro_or_callable
    else:
        await coro_or_callable(event)
