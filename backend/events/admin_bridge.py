"""Admin OS realtime bridge — forwards a curated subset of domain events to the
live admin WebSocket channel (services.realtime.manager.broadcast_admin), so the
Admin OS updates without polling.

Registered once via register(bus) alongside the other subscriptions in
events/subscriptions.py. Best-effort: a broadcast failure here never affects the
event bus's own delivery guarantees for other handlers.
"""
from __future__ import annotations

import logging

from .bus import EnterpriseEventBus
from .models import (
    DomainEvent,
    MISSION_FAILED,
    STEP_FAILED,
    HEARTBEAT_EXPIRED,
    GRANT_SUBMITTED,
    GRANT_AWARDED,
    PUBLICATION_PUBLISHED,
    USER_VERIFIED,
    INSTITUTION_MEMBER_ADDED,
)

logger = logging.getLogger("synaptiq.events.admin_bridge")

# Events worth surfacing live in the Admin OS. Deliberately a small, curated
# subset of the full event catalogue — this is a notification feed for
# operators, not a firehose.
_ADMIN_RELEVANT = {
    MISSION_FAILED,
    STEP_FAILED,
    HEARTBEAT_EXPIRED,
    GRANT_SUBMITTED,
    GRANT_AWARDED,
    PUBLICATION_PUBLISHED,
    USER_VERIFIED,
    INSTITUTION_MEMBER_ADDED,
}


async def _on_any__admin_relay(event: DomainEvent) -> None:
    if event.event_type not in _ADMIN_RELEVANT:
        return
    try:
        from services.realtime import manager
        await manager.broadcast_admin({
            "type": "domain_event",
            "event_type": event.event_type,
            "aggregate_id": event.aggregate_id,
            "aggregate_type": event.aggregate_type,
            "user_id": event.user_id,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        })
    except Exception as exc:
        logger.warning("Admin realtime relay failed for %s: %s", event.event_type, exc)


def register(bus: EnterpriseEventBus) -> None:
    bus.subscribe(
        "*",
        _on_any__admin_relay,
        consumer_id="admin.realtime_relay",
        description="Forward curated domain events to the live Admin OS WebSocket channel",
        timeout_s=5.0,
        idempotent=False,
    )
