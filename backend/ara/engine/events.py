"""
Mission Event Bus — async pub/sub with MongoDB audit trail.

Every state change in the mission lifecycle emits an event.
No module polls mission status — everything reacts to events.

Event persistence: ara_events collection (immutable, append-only).
In-process dispatch: asyncio-based subscriber registry.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

logger = logging.getLogger("ara.engine.events")

# ── Event type constants ───────────────────────────────────────────────────────

MISSION_CREATED      = "mission.created"
MISSION_QUEUED       = "mission.queued"
MISSION_STARTED      = "mission.started"
MISSION_PAUSED       = "mission.paused"
MISSION_RESUMED      = "mission.resumed"
MISSION_FAILED       = "mission.failed"
MISSION_COMPLETED    = "mission.completed"
MISSION_CANCELLED    = "mission.cancelled"
MISSION_ARCHIVED     = "mission.archived"
STEP_STARTED         = "step.started"
STEP_COMPLETED       = "step.completed"
STEP_FAILED          = "step.failed"
APPROVAL_REQUIRED    = "approval.required"
APPROVAL_RESOLVED    = "approval.resolved"
VALIDATION_FAILED    = "validation.failed"
RETRY_SCHEDULED      = "retry.scheduled"
HEARTBEAT_EXPIRED    = "heartbeat.expired"
CHECKPOINT_SAVED     = "checkpoint.saved"


@dataclass
class MissionEvent:
    type:       str
    mission_id: str
    data:       dict = field(default_factory=dict)
    worker_id:  str | None = None
    step_id:    str | None = None
    timestamp:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MissionEventBus:
    """
    In-process pub/sub + MongoDB audit trail.

    Subscribers are in-process only (restart-safe for reactive logic).
    All events are persisted to ara_events for auditing and replay.
    """

    def __init__(self):
        self._subs: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subs.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        if event_type in self._subs:
            self._subs[event_type] = [h for h in self._subs[event_type] if h is not handler]

    async def emit(self, event: MissionEvent, db=None) -> None:
        """Dispatch to subscribers + persist to MongoDB (fire-and-forget)."""
        # In-process dispatch
        for handler in self._subs.get(event.type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as exc:
                logger.warning("Event handler error (%s): %s", event.type, exc)

        # Wildcard subscribers
        for handler in self._subs.get("*", []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as exc:
                logger.warning("Wildcard event handler error: %s", exc)

        # Persist
        if db is not None:
            asyncio.create_task(_persist_event(event, db))

        logger.debug("event:%s mission=%s step=%s", event.type, event.mission_id, event.step_id or "-")


async def _persist_event(event: MissionEvent, db) -> None:
    try:
        await db["ara_events"].insert_one({
            "type":       event.type,
            "mission_id": event.mission_id,
            "step_id":    event.step_id,
            "worker_id":  event.worker_id,
            "data":       event.data,
            "timestamp":  datetime.now(timezone.utc),
        })
    except Exception as exc:
        logger.debug("ara_events persist failed: %s", exc)


# ── Process-level singleton ───────────────────────────────────────────────────

_bus: MissionEventBus | None = None


def get_event_bus() -> MissionEventBus:
    global _bus
    if _bus is None:
        _bus = MissionEventBus()
    return _bus
