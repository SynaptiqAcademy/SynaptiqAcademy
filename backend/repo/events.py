"""
Repository Events — domain events emitted after successful mutations.

Events decouple repositories from downstream side-effects (sending
notifications, updating reputation scores, triggering agent workflows, etc.).

Pattern:
  - Repositories emit events via `repo_event_bus.emit()`
  - Listeners register with `repo_event_bus.subscribe()`
  - Events are async; failures in one listener never block others

This is a lightweight in-process pub/sub.  For cross-service scenarios
the events are also persisted to `repo_events` collection.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

# ── Event types ───────────────────────────────────────────────────────────────

# Users
USER_CREATED            = "user.created"
USER_UPDATED            = "user.updated"
USER_DELETED            = "user.deleted"

# Missions
MISSION_CREATED         = "mission.created"
MISSION_QUEUED          = "mission.queued"
MISSION_COMPLETED       = "mission.completed"
MISSION_FAILED          = "mission.failed"
MISSION_STEP_COMPLETED  = "mission.step_completed"
MISSION_APPROVAL_NEEDED = "mission.approval_needed"

# Publications
PUBLICATION_CREATED     = "publication.created"
PUBLICATION_SUBMITTED   = "publication.submitted"
PUBLICATION_PUBLISHED   = "publication.published"

# Grants
GRANT_CREATED           = "grant.created"
GRANT_SUBMITTED         = "grant.submitted"
GRANT_AWARDED           = "grant.awarded"

# Institutions
INSTITUTION_MEMBER_ADDED    = "institution.member_added"
INSTITUTION_MEMBER_REMOVED  = "institution.member_removed"

# Knowledge Graph
KG_NODE_CREATED         = "kg.node_created"
KG_EDGE_CREATED         = "kg.edge_created"

# Notifications
NOTIFICATION_CREATED    = "notification.created"


@dataclass
class RepoEvent:
    """A domain event emitted by a repository after a successful mutation."""
    type:        str
    payload:     dict                   = field(default_factory=dict)
    emitted_at:  datetime               = field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id:    str                    = ""
    request_id:  str                    = ""
    collection:  str                    = ""
    doc_id:      str | None             = None


Handler = Callable[[RepoEvent], Awaitable[None]]


class RepoEventBus:
    """In-process async pub/sub for repository events."""

    def __init__(self, db=None) -> None:
        self._handlers:  dict[str, list[Handler]] = {}
        self._wildcards: list[Handler]             = []
        self._db = db

    def set_db(self, db) -> None:
        self._db = db

    # ── Subscribe ─────────────────────────────────────────────────────────────

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Register a handler for a specific event type."""
        if event_type == "*":
            self._wildcards.append(handler)
        else:
            self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        if event_type == "*":
            self._wildcards = [h for h in self._wildcards if h is not handler]
        else:
            lst = self._handlers.get(event_type, [])
            self._handlers[event_type] = [h for h in lst if h is not handler]

    # ── Emit ──────────────────────────────────────────────────────────────────

    def emit(self, event: RepoEvent) -> None:
        """Schedule event dispatch (non-blocking, fire-and-forget)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._dispatch(event))
        except RuntimeError:
            pass  # No event loop — skip (test context)

    async def emit_async(self, event: RepoEvent) -> None:
        """Awaitable emit — use when you need to ensure delivery before continuing."""
        await self._dispatch(event)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _dispatch(self, event: RepoEvent) -> None:
        handlers = self._handlers.get(event.type, []) + self._wildcards
        tasks = [self._call(h, event) for h in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Persist to MongoDB (best-effort)
        if self._db:
            asyncio.create_task(self._persist(event))

    @staticmethod
    async def _call(handler: Handler, event: RepoEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.warning("RepoEvent handler error (%s): %s", event.type, exc)

    async def _persist(self, event: RepoEvent) -> None:
        try:
            await self._db["repo_events"].insert_one({
                "type":       event.type,
                "payload":    event.payload,
                "emitted_at": event.emitted_at,
                "actor_id":   event.actor_id,
                "request_id": event.request_id,
                "collection": event.collection,
                "doc_id":     event.doc_id,
            })
        except Exception as exc:
            logger.debug("RepoEvent persist error: %s", exc)


# ── Module-level singleton ─────────────────────────────────────────────────────

_bus: RepoEventBus | None = None


def get_event_bus() -> RepoEventBus:
    global _bus
    if _bus is None:
        _bus = RepoEventBus()
    return _bus


def init_event_bus(db) -> RepoEventBus:
    global _bus
    _bus = RepoEventBus(db)
    return _bus
