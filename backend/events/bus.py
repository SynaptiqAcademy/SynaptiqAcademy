"""
EnterpriseEventBus — the central communication backbone of Synaptiq.

All domain events flow through here. No module calls another module directly.

Architecture:
  Publisher → bus.publish(event)
    → EventStore.append()         (persist immediately)
    → dispatch_direct(event)
      → HandlerRegistry.get_handlers()
      → [parallel] HandlerExecutor.execute() for each handler
        → idempotency check
        → circuit breaker check
        → timeout
        → retry (transient errors)
        → DLQ (on exhaustion)

For transactional publishing (Outbox Pattern):
  Publisher → outbox.write(event, session=tx.session)
    → OutboxRelay picks up async → bus.dispatch_direct(event)

Usage:
    from events import get_bus

    bus = get_bus()

    # Subscribe
    bus.subscribe("publication.created", my_handler, consumer_id="kg_updater")

    # Publish
    event = PublicationCreated(aggregate_id=pub_id, user_id=user_id, payload={...})
    await bus.publish(event)
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Awaitable, Callable

from .circuit_breaker import all_circuit_breaker_status, reset_circuit_breaker
from .dlq             import DeadLetterQueue, ensure_indexes as dlq_indexes
from .handlers        import HandlerExecutor, HandlerRegistration, HandlerRegistry
from .models          import DomainEvent
from .observability   import get_observability
from .outbox          import OutboxPublisher, OutboxRelay, ensure_indexes as outbox_indexes
from .replay          import ReplayEngine
from .retry           import HandlerRetryPolicy, DEFAULT_RETRY_POLICY
from .store           import EventStore, ensure_indexes as store_indexes

logger = logging.getLogger(__name__)

Handler = Callable[[DomainEvent], Awaitable[None]]


class EnterpriseEventBus:
    """
    Enterprise event bus with at-least-once delivery, idempotency, and full observability.

    Lifecycle:
        bus = EnterpriseEventBus()
        await bus.start(db)        # called once at server startup
        ...
        await bus.stop()           # called at shutdown
    """

    def __init__(self) -> None:
        self.registry  = HandlerRegistry()
        self._store:   EventStore | None      = None
        self._dlq:     DeadLetterQueue | None = None
        self._outbox:  OutboxPublisher | None = None
        self._relay:   OutboxRelay | None     = None
        self._replay:  ReplayEngine | None    = None
        self._executor: HandlerExecutor | None = None
        self._obs      = get_observability()
        self._started  = False
        self._lock     = threading.Lock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, db) -> None:
        """Initialize all sub-systems and start background loops."""
        if self._started:
            return

        # Setup indexes
        await store_indexes(db)
        await dlq_indexes(db)
        await outbox_indexes(db)

        # Instantiate sub-systems
        self._store    = EventStore(db)
        self._dlq      = DeadLetterQueue(db)
        self._outbox   = OutboxPublisher(db)
        self._relay    = OutboxRelay(db, self)
        self._replay   = ReplayEngine(self._store, self, db)
        self._executor = HandlerExecutor(self._store, self._dlq)

        # Recover stuck outbox events from previous server run
        await self._relay.recover()

        # Start background outbox relay
        await self._relay.start()

        self._started = True
        logger.info("EnterpriseEventBus started")

    async def stop(self) -> None:
        if not self._started:
            return
        if self._relay:
            await self._relay.stop()
        self._started = False
        logger.info("EnterpriseEventBus stopped")

    # ── Publish ───────────────────────────────────────────────────────────────

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event.

        Persists to EventStore immediately, then dispatches to handlers.
        For transactional publishing, use publish_via_outbox() instead.
        """
        self._obs.record_published(event.event_type)
        try:
            from obs.metrics import get_metrics, M_BUS_PUBLISHED
            get_metrics().inc(M_BUS_PUBLISHED, tags={"event_type": event.event_type})
        except Exception:
            pass

        # Persist (best-effort — never block publishing on store failure)
        if self._store:
            try:
                await self._store.append(event)
            except Exception as exc:
                logger.warning("EventStore.append error (non-fatal): %s", exc)

        await self.dispatch_direct(event)

    async def publish_many(self, events: list[DomainEvent]) -> None:
        """Publish multiple events in order."""
        for event in events:
            await self.publish(event)

    def publish_sync(self, event: DomainEvent) -> None:
        """
        Schedule publish as a fire-and-forget background task.

        Use from synchronous code that cannot await. Requires a running event loop.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(event))
        except RuntimeError:
            pass

    async def publish_via_outbox(self, event: DomainEvent, *, session=None) -> None:
        """
        Write event to outbox (inside the caller's transaction).

        The OutboxRelay will pick it up and dispatch asynchronously.
        Use this when you need atomic "write + emit" guarantees.
        """
        if self._outbox:
            await self._outbox.write(event, session=session)
        else:
            # Fallback: publish directly (non-transactional)
            await self.publish(event)

    # ── Subscribe ─────────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: str,
        handler: Handler,
        *,
        consumer_id: str,
        timeout_s: float = 30.0,
        retry_policy: HandlerRetryPolicy | None = None,
        idempotent: bool = True,
        description: str = "",
    ) -> None:
        """
        Register an async handler for an event type.

        event_type = "*" subscribes to ALL events (wildcard).
        consumer_id must be unique per handler — used for idempotency + circuit breaker.
        """
        self.registry.register(HandlerRegistration(
            consumer_id=consumer_id,
            event_type=event_type,
            handler=handler,
            timeout_s=timeout_s,
            retry_policy=retry_policy or DEFAULT_RETRY_POLICY,
            idempotent=idempotent,
            description=description,
        ))

    def unsubscribe(self, consumer_id: str, event_type: str | None = None) -> int:
        """Remove handler registrations. Returns count of removed registrations."""
        return self.registry.unregister(consumer_id, event_type)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def dispatch_direct(self, event: DomainEvent) -> None:
        """
        Dispatch an event to all registered handlers in parallel.

        Failures in one handler never block others.
        """
        handlers = self.registry.get_handlers(event.event_type)
        if not handlers:
            return

        self._obs.record_dispatched(event.event_type)
        try:
            from obs.metrics import get_metrics, M_BUS_CONSUMED
            get_metrics().inc(M_BUS_CONSUMED, tags={"event_type": event.event_type})
        except Exception:
            pass

        if self._executor:
            tasks = [self._executor.execute(reg, event) for reg in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Not yet started (test mode or early startup) — call handlers directly
            for reg in handlers:
                try:
                    await asyncio.wait_for(reg.handler(event), timeout=reg.timeout_s)
                except Exception as exc:
                    logger.warning("Bus (no executor): handler %s failed: %s", reg.consumer_id, exc)

    # ── Admin / Observability ─────────────────────────────────────────────────

    def metrics(self) -> dict:
        return self._obs.snapshot()

    def circuit_breakers(self) -> list[dict]:
        return all_circuit_breaker_status()

    def reset_circuit_breaker(self, consumer_id: str) -> None:
        reset_circuit_breaker(consumer_id)

    def all_handlers(self) -> list[dict]:
        return self.registry.all_registrations()

    async def dlq_entries(self, *, consumer_id: str | None = None, limit: int = 50) -> list[dict]:
        if not self._dlq:
            return []
        return await self._dlq.get_all(consumer_id=consumer_id, limit=limit)

    async def retry_dlq_entry(self, event_id: str, consumer_id: str) -> bool:
        if not (self._dlq and self._store):
            return False
        event = await self._store.get_by_id(event_id)
        if not event:
            return False
        await self._dlq.mark_retrying(event_id, consumer_id)
        handlers = [r for r in self.registry.get_handlers(event.event_type) if r.consumer_id == consumer_id]
        for reg in handlers:
            if self._executor:
                await self._executor.execute(reg, event)
                await self._dlq.mark_resolved(event_id, consumer_id)
                return True
        return False

    async def recent_events(self, *, limit: int = 50, event_type: str | None = None) -> list[dict]:
        if not self._store:
            return []
        return await self._store.get_recent(limit=limit, event_type=event_type)

    async def start_replay(
        self,
        *,
        consumer_id: str,
        event_types: list[str] | None = None,
        since=None,
        until=None,
    ) -> str:
        if not self._replay:
            raise RuntimeError("Bus not started")
        return await self._replay.start_replay(
            consumer_id=consumer_id,
            event_types=event_types,
            since=since,
            until=until,
        )

    async def replay_sessions(self, limit: int = 20) -> list[dict]:
        if not self._replay:
            return []
        return await self._replay.list_sessions(limit=limit)

    async def outbox_status(self) -> dict:
        if not self._relay:
            return {"pending": 0, "failed": 0}
        return {
            "pending": await self._relay.pending_count(),
            "failed":  await self._relay.failed_count(),
        }


# ── Module-level singleton ─────────────────────────────────────────────────────

_bus: EnterpriseEventBus | None = None
_bus_lock = threading.Lock()


def get_bus() -> EnterpriseEventBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EnterpriseEventBus()
    return _bus


def reset_bus() -> None:
    """For testing only — resets the singleton."""
    global _bus
    with _bus_lock:
        _bus = None
