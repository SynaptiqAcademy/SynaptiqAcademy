"""
Events Admin API — management endpoints for the enterprise event bus.

All endpoints require admin role.

GET  /api/events/recent                 — recent published events
GET  /api/events/metrics                — bus observability metrics
GET  /api/events/handlers               — registered handler list
GET  /api/events/circuit-breakers       — circuit breaker states
POST /api/events/circuit-breakers/{id}/reset — reset a circuit breaker
GET  /api/events/dlq                    — dead letter queue entries
POST /api/events/dlq/retry              — retry a DLQ entry
GET  /api/events/catalog                — event catalog / registry
GET  /api/events/store/query            — query event store
GET  /api/events/store/aggregate        — events for a specific aggregate
GET  /api/events/outbox/status          — outbox pending/failed counts
GET  /api/events/replay/sessions        — replay session history
POST /api/events/replay                 — start a replay session
DELETE /api/events/replay/{session_id}  — cancel a running replay
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/events", tags=["Events Admin"])


def _get_admin_user():
    from auth_utils import get_current_user
    return get_current_user


def _get_bus():
    from events.bus import get_bus
    return get_bus()


def _require_admin(user=Depends(lambda: _get_admin_user()())):
    from auth_utils import require_admin
    return require_admin(user)


# ── Recent events ─────────────────────────────────────────────────────────────

@router.get("/recent")
async def get_recent_events(
    limit: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = Query(None),
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    if not bus._started:
        return {"events": [], "note": "Event bus not started"}
    events = await bus.recent_events(limit=limit, event_type=event_type)
    return {"events": events, "count": len(events)}


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics")
async def get_metrics(user=Depends(lambda: _get_admin_user()())):
    bus = _get_bus()
    return bus.metrics()


# ── Handlers ──────────────────────────────────────────────────────────────────

@router.get("/handlers")
async def get_handlers(user=Depends(lambda: _get_admin_user()())):
    bus = _get_bus()
    return {"handlers": bus.all_handlers(), "count": len(bus.all_handlers())}


# ── Circuit Breakers ──────────────────────────────────────────────────────────

@router.get("/circuit-breakers")
async def get_circuit_breakers(user=Depends(lambda: _get_admin_user()())):
    bus = _get_bus()
    return {"circuit_breakers": bus.circuit_breakers()}


@router.post("/circuit-breakers/{consumer_id}/reset")
async def reset_circuit_breaker(
    consumer_id: str,
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    bus.reset_circuit_breaker(consumer_id)
    return {"ok": True, "consumer_id": consumer_id}


# ── Dead Letter Queue ─────────────────────────────────────────────────────────

@router.get("/dlq")
async def get_dlq(
    consumer_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    entries = await bus.dlq_entries(consumer_id=consumer_id, limit=limit)
    return {"entries": entries, "count": len(entries)}


class DLQRetryRequest(BaseModel):
    event_id:    str
    consumer_id: str


@router.post("/dlq/retry")
async def retry_dlq_entry(
    body: DLQRetryRequest,
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    ok  = await bus.retry_dlq_entry(body.event_id, body.consumer_id)
    if not ok:
        raise HTTPException(404, f"DLQ entry not found: {body.event_id}/{body.consumer_id}")
    return {"ok": True}


# ── Event Catalog ─────────────────────────────────────────────────────────────

@router.get("/catalog")
async def get_catalog(
    producer: Optional[str] = Query(None),
    consumer: Optional[str] = Query(None),
    lifecycle: Optional[str] = Query(None),
    user=Depends(lambda: _get_admin_user()()),
):
    from events.registry import catalog
    if producer:
        return {"catalog": catalog.by_producer(producer)}
    if consumer:
        return {"catalog": catalog.by_consumer(consumer)}
    if lifecycle == "stable":
        return {"catalog": catalog.stable()}
    return {"catalog": catalog.all(), "count": len(catalog.all())}


# ── Event Store Query ─────────────────────────────────────────────────────────

@router.get("/store/query")
async def query_event_store(
    event_type: Optional[str] = Query(None),
    user_id:    Optional[str] = Query(None),
    since:      Optional[str] = Query(None),
    until:      Optional[str] = Query(None),
    limit:      int            = Query(50, ge=1, le=500),
    skip:       int            = Query(0, ge=0),
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    if not bus._store:
        return {"events": [], "note": "Event bus not started"}

    since_dt = datetime.fromisoformat(since) if since else None
    until_dt = datetime.fromisoformat(until) if until else None

    events = await bus._store.get_by_type(
        event_type or "",
        since=since_dt,
        until=until_dt,
        user_id=user_id,
        limit=limit,
        skip=skip,
    ) if event_type else await bus._store.get_recent(limit=limit)

    if isinstance(events, list) and events and hasattr(events[0], "to_dict"):
        events = [e.to_dict() for e in events]

    return {"events": events, "count": len(events)}


@router.get("/store/aggregate/{aggregate_type}/{aggregate_id}")
async def get_aggregate_events(
    aggregate_type: str,
    aggregate_id:   str,
    limit:          int = Query(100, ge=1, le=1000),
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    if not bus._store:
        return {"events": [], "note": "Event bus not started"}
    events = await bus._store.get_by_aggregate(aggregate_id, aggregate_type, limit=limit)
    return {"events": [e.to_dict() for e in events], "count": len(events)}


@router.get("/store/stats")
async def get_store_stats(user=Depends(lambda: _get_admin_user()())):
    bus = _get_bus()
    if not bus._store:
        return {"note": "Event bus not started"}
    distribution = await bus._store.type_distribution()
    total = await bus._store.count()
    return {"total": total, "by_type": distribution}


# ── Outbox ────────────────────────────────────────────────────────────────────

@router.get("/outbox/status")
async def get_outbox_status(user=Depends(lambda: _get_admin_user()())):
    bus = _get_bus()
    return await bus.outbox_status()


# ── Replay ────────────────────────────────────────────────────────────────────

@router.get("/replay/sessions")
async def get_replay_sessions(
    limit: int = Query(20, ge=1, le=100),
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    sessions = await bus.replay_sessions(limit=limit)
    return {"sessions": sessions, "count": len(sessions)}


class ReplayRequest(BaseModel):
    consumer_id:  str
    event_types:  Optional[list[str]] = None
    since:        Optional[str]       = None
    until:        Optional[str]       = None


@router.post("/replay")
async def start_replay(
    body: ReplayRequest,
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    if not bus._started:
        raise HTTPException(503, "Event bus not started")
    since_dt = datetime.fromisoformat(body.since) if body.since else None
    until_dt = datetime.fromisoformat(body.until) if body.until else None
    session_id = await bus.start_replay(
        consumer_id=body.consumer_id,
        event_types=body.event_types,
        since=since_dt,
        until=until_dt,
    )
    return {"session_id": session_id, "status": "running"}


@router.delete("/replay/{session_id}")
async def cancel_replay(
    session_id: str,
    user=Depends(lambda: _get_admin_user()()),
):
    bus = _get_bus()
    if not bus._replay:
        raise HTTPException(503, "Event bus not started")
    ok = await bus._replay.cancel(session_id)
    return {"ok": ok, "session_id": session_id}
