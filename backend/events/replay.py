"""
Replay Engine — re-dispatch historical events to specific consumers.

Use cases:
  - Rebuild Knowledge Graph from all publication events
  - Rebuild Digital Twin from all research activity events
  - Regenerate Recommendations after algorithm change
  - Recompute Analytics after bug fix
  - Debug: trace what happened to a specific aggregate

The replay engine reads from EventStore (never touches production state
directly) and routes events to the targeted consumer handlers only.

A replay session is tracked in `event_replay_sessions`:
  - session_id, consumer_id, event_types, since, until
  - status: pending | running | completed | failed
  - replayed_count, failed_count, started_at, completed_at
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .models import DomainEvent

if TYPE_CHECKING:
    from .bus   import EnterpriseEventBus
    from .store import EventStore

logger = logging.getLogger(__name__)

COLLECTION = "event_replay_sessions"


@dataclass
class ReplaySession:
    session_id:     str
    consumer_id:    str
    event_types:    list[str]
    since:          datetime | None
    until:          datetime | None
    status:         str = "pending"
    replayed_count: int = 0
    failed_count:   int = 0
    started_at:     datetime | None = None
    completed_at:   datetime | None = None
    error:          str | None      = None


class ReplayEngine:
    """
    Replays historical events from the EventStore to specific consumers.

    Replay is always targeted at a specific consumer_id, so production
    state is not accidentally double-written by other consumers.
    """

    def __init__(self, store: "EventStore", bus: "EnterpriseEventBus", db) -> None:
        self._store = store
        self._bus   = bus
        self._db    = db
        self._col   = db[COLLECTION]
        self._active: dict[str, asyncio.Task] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    async def start_replay(
        self,
        *,
        consumer_id: str,
        event_types: list[str] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        batch_size: int = 100,
    ) -> str:
        """
        Start a replay session. Returns session_id.

        consumer_id: which handler to replay into
        event_types: if None, replay ALL event types
        since/until: time window (defaults: beginning of time / now)
        """
        session_id = str(uuid.uuid4())
        session    = ReplaySession(
            session_id=session_id,
            consumer_id=consumer_id,
            event_types=event_types or [],
            since=since,
            until=until,
        )
        await self._persist_session(session)

        task = asyncio.create_task(
            self._run_replay(session, batch_size)
        )
        self._active[session_id] = task
        logger.info(
            "ReplayEngine: started session %s for consumer %s",
            session_id, consumer_id,
        )
        return session_id

    async def get_session(self, session_id: str) -> dict | None:
        doc = await self._col.find_one({"session_id": session_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def list_sessions(self, limit: int = 20) -> list[dict]:
        cursor = self._col.find({}, sort=[("started_at", -1)]).limit(limit)
        docs   = await cursor.to_list(length=limit)
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    async def cancel(self, session_id: str) -> bool:
        task = self._active.get(session_id)
        if task and not task.done():
            task.cancel()
            await self._col.update_one(
                {"session_id": session_id},
                {"$set": {"status": "cancelled"}},
            )
            return True
        return False

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _run_replay(self, session: ReplaySession, batch_size: int) -> None:
        session.status     = "running"
        session.started_at = datetime.now(timezone.utc)
        await self._update_session(session)

        try:
            replayed = 0
            failed   = 0

            async for event in self._store.cursor(
                event_types=session.event_types or None,
                since=session.since,
                until=session.until,
                batch_size=batch_size,
            ):
                try:
                    await self._dispatch_to_consumer(session.consumer_id, event)
                    replayed += 1
                except Exception as exc:
                    logger.warning("Replay %s event error: %s", session.session_id, exc)
                    failed += 1

                # Periodic status update
                if (replayed + failed) % 100 == 0:
                    session.replayed_count = replayed
                    session.failed_count   = failed
                    await self._update_session(session)

            session.status         = "completed"
            session.replayed_count = replayed
            session.failed_count   = failed
            session.completed_at   = datetime.now(timezone.utc)
            logger.info(
                "ReplayEngine: session %s completed — %d replayed, %d failed",
                session.session_id, replayed, failed,
            )

        except asyncio.CancelledError:
            session.status = "cancelled"
            raise
        except Exception as exc:
            session.status = "failed"
            session.error  = str(exc)[:500]
            logger.error("ReplayEngine: session %s failed: %s", session.session_id, exc)
        finally:
            session.completed_at = session.completed_at or datetime.now(timezone.utc)
            await self._update_session(session)
            self._active.pop(session.session_id, None)

    async def _dispatch_to_consumer(self, consumer_id: str, event: DomainEvent) -> None:
        """Route the event only to the targeted consumer, bypassing circuit breaker."""
        reg = self._bus.registry.get_handlers(event.event_type)
        for r in reg:
            if r.consumer_id == consumer_id:
                await r.handler(event)
                return
        # Try wildcard handlers too
        for r in self._bus.registry._wildcards:
            if r.consumer_id == consumer_id:
                await r.handler(event)
                return

    async def _persist_session(self, session: ReplaySession) -> None:
        await self._col.insert_one({
            "session_id":     session.session_id,
            "consumer_id":    session.consumer_id,
            "event_types":    session.event_types,
            "since":          session.since,
            "until":          session.until,
            "status":         session.status,
            "replayed_count": session.replayed_count,
            "failed_count":   session.failed_count,
            "started_at":     session.started_at,
            "completed_at":   session.completed_at,
            "error":          session.error,
        })

    async def _update_session(self, session: ReplaySession) -> None:
        await self._col.update_one(
            {"session_id": session.session_id},
            {"$set": {
                "status":         session.status,
                "replayed_count": session.replayed_count,
                "failed_count":   session.failed_count,
                "started_at":     session.started_at,
                "completed_at":   session.completed_at,
                "error":          session.error,
            }},
        )
