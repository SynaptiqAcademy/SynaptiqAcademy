"""
Operations Center Router — Phase XXXV.6

Prefix: /api/ops

Endpoints:
  GET  /api/ops/health                  — aggregate health of all components
  GET  /api/ops/health/{component}      — single component health
  POST /api/ops/health/refresh          — force re-check all components
  GET  /api/ops/metrics                 — full metrics snapshot
  GET  /api/ops/metrics/{category}      — category metrics (api/ai/worker/mission/graph/twin/bus/db/cache/security)
  GET  /api/ops/traces                  — list recent traces
  GET  /api/ops/traces/{trace_id}       — trace detail + all spans
  GET  /api/ops/traces/{trace_id}/reconstruct — time travel rebuild
  GET  /api/ops/logs                    — searchable structured logs
  GET  /api/ops/audit                   — audit trail search
  GET  /api/ops/audit/{record_id}       — single audit record
  GET  /api/ops/alerts                  — list alerts
  POST /api/ops/alerts/evaluate         — evaluate alert rules now
  POST /api/ops/alerts/{id}/acknowledge — acknowledge alert
  POST /api/ops/alerts/{id}/resolve     — resolve alert
  GET  /api/ops/cost                    — cost totals
  GET  /api/ops/cost/breakdown          — cost by dimension
  GET  /api/ops/cost/recent             — recent cost records
  GET  /api/ops/security                — security events
  GET  /api/ops/security/summary        — security summary
  GET  /api/ops/profiler                — slow operations
  GET  /api/ops/profiler/recommendations — optimization hints
  GET  /api/ops/profiler/all            — all operation stats

All endpoints require super-admin authentication.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from db import get_db
from services.permissions import require_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ops",
    tags=["operations-center"],
    dependencies=[Depends(require_super_admin)],
)


# ── Lazy subsystem accessors ──────────────────────────────────────────────────

def _health(db):
    from obs.health import get_health_engine, init_health
    e = get_health_engine()
    return e if e else init_health(db)


def _metrics():
    from obs.metrics import get_metrics
    return get_metrics()


def _alerts(db):
    from obs.alerting import get_alert_engine, init_alerting
    e = get_alert_engine()
    return e if e else init_alerting(db)


def _tracer(db):
    from obs.tracer import get_tracer, init_tracer
    t = get_tracer()
    return t if t else init_tracer(db)


def _audit(db):
    from obs.audit import get_audit, init_audit
    a = get_audit()
    return a if a else init_audit(db)


def _cost(db):
    from obs.cost import get_cost_tracker, init_cost
    c = get_cost_tracker()
    return c if c else init_cost(db)


def _security(db):
    from obs.security import get_security_observer, init_security
    s = get_security_observer()
    return s if s else init_security(db)


def _time_travel(db):
    from obs.time_travel import get_time_traveler, init_time_travel
    t = get_time_traveler()
    return t if t else init_time_travel(db)


def _profiler():
    from obs.profiler import get_profiler
    return get_profiler()


def _log_buffer():
    from obs.logger import get_log_buffer
    return get_log_buffer()


# ── Schemas ───────────────────────────────────────────────────────────────────

class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = "admin"


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def get_health(db=Depends(get_db)):
    """Aggregate health status of all platform components."""
    engine  = _health(db)
    results = await engine.check_all()
    return engine.aggregate(results)


@router.get("/health/{component}")
async def get_component_health(component: str, db=Depends(get_db)):
    """Health check for a specific component."""
    engine = _health(db)
    if component not in engine.component_names:
        raise HTTPException(
            404,
            f"Unknown component: {component}. Known: {engine.component_names}"
        )
    result = await engine.check_component(component)
    return result.to_dict()


@router.post("/health/refresh")
async def refresh_health(db=Depends(get_db)):
    """Force a fresh health check of all components."""
    engine  = _health(db)
    results = await engine.check_all()
    return engine.aggregate(results)


# ── Metrics ───────────────────────────────────────────────────────────────────

_METRIC_CATEGORIES = {
    "api":      "api.",
    "ai":       "ai.",
    "worker":   "worker.",
    "mission":  "mission.",
    "graph":    "kg.",
    "twin":     "twin.",
    "bus":      "bus.",
    "db":       "db.",
    "cache":    "cache.",
    "security": "security.",
}


@router.get("/metrics")
async def get_all_metrics():
    """Full metrics snapshot across all subsystems."""
    return _metrics().snapshot()


@router.get("/metrics/{category}")
async def get_category_metrics(category: str):
    """Metrics for a specific category (api|ai|worker|mission|graph|twin|bus|db|cache|security)."""
    if category not in _METRIC_CATEGORIES:
        raise HTTPException(
            404,
            f"Unknown category '{category}'. Valid: {list(_METRIC_CATEGORIES)}"
        )
    return _metrics().category_snapshot(_METRIC_CATEGORIES[category])


# ── Traces ────────────────────────────────────────────────────────────────────

@router.get("/traces")
async def list_traces(
    limit:     int           = Query(50, ge=1, le=200),
    status:    Optional[str] = Query(None),
    user_id:   Optional[str] = Query(None),
    component: Optional[str] = Query(None),
    db=Depends(get_db),
):
    """List recent distributed traces."""
    return await _tracer(db).list_traces(
        limit=limit, status=status, user_id=user_id, component=component
    )


@router.get("/traces/{trace_id}/reconstruct")
async def reconstruct_trace(trace_id: str, db=Depends(get_db)):
    """Time-travel: reconstruct the full execution timeline for a trace."""
    result = await _time_travel(db).rebuild(trace_id)
    return result.to_dict()


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, db=Depends(get_db)):
    """Trace detail including all spans."""
    tracer = _tracer(db)
    trace  = await tracer.get_trace(trace_id)
    if not trace:
        raise HTTPException(404, f"Trace {trace_id} not found")
    spans = await tracer.get_spans(trace_id)
    return {"trace": trace, "spans": spans, "span_count": len(spans)}


# ── Logs ──────────────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_logs(
    level:     Optional[str] = Query(None, description="DEBUG|INFO|WARNING|ERROR|CRITICAL"),
    component: Optional[str] = Query(None),
    trace_id:  Optional[str] = Query(None),
    user_id:   Optional[str] = Query(None),
    from_ts:   Optional[str] = Query(None),
    to_ts:     Optional[str] = Query(None),
    limit:     int           = Query(100, ge=1, le=500),
    source:    str           = Query("buffer", description="buffer=in-memory | db=MongoDB WARNING+"),
    db=Depends(get_db),
):
    """Search structured logs (in-memory buffer or MongoDB for WARNING+)."""
    if source == "db":
        from obs.logger import search_logs_in_db
        return await search_logs_in_db(
            db=db, level=level, component=component, trace_id=trace_id,
            user_id=user_id, from_ts=from_ts, to_ts=to_ts, limit=limit,
        )
    return _log_buffer().query(
        level=level, component=component,
        trace_id=trace_id, user_id=user_id, limit=limit,
    )


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
async def get_audit_trail(
    user_id:       Optional[str] = Query(None),
    action:        Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    category:      Optional[str] = Query(None),
    trace_id:      Optional[str] = Query(None),
    mission_id:    Optional[str] = Query(None),
    from_ts:       Optional[str] = Query(None),
    to_ts:         Optional[str] = Query(None),
    status:        Optional[str] = Query(None),
    severity:      Optional[str] = Query(None),
    limit:         int           = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    """Search immutable audit trail."""
    return await _audit(db).query(
        user_id=user_id, action=action, resource_type=resource_type,
        category=category, trace_id=trace_id, mission_id=mission_id,
        from_ts=from_ts, to_ts=to_ts, status=status, severity=severity,
        limit=limit,
    )


@router.get("/audit/{record_id}")
async def get_audit_record(record_id: str, db=Depends(get_db)):
    """Get a specific audit record by ID."""
    record = await _audit(db).get_record(record_id)
    if not record:
        raise HTTPException(404, f"Audit record {record_id} not found")
    return record


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts")
async def get_alerts(
    status:   Optional[str] = Query(None, description="active|acknowledged|resolved"),
    severity: Optional[str] = Query(None, description="info|warning|critical"),
    category: Optional[str] = Query(None),
    limit:    int           = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    """List platform alerts."""
    return await _alerts(db).list_alerts(
        status=status, severity=severity, category=category, limit=limit
    )


@router.post("/alerts/evaluate")
async def evaluate_alerts(db=Depends(get_db)):
    """Manually trigger alert rule evaluation against current metrics."""
    engine = _alerts(db)
    fired  = await engine.evaluate()
    return {"triggered": len(fired), "alerts": [a.to_dict() for a in fired]}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    body:     AcknowledgeRequest,
    db=Depends(get_db),
):
    """Acknowledge an active alert."""
    updated = await _alerts(db).acknowledge(alert_id, body.acknowledged_by)
    if not updated:
        raise HTTPException(404, f"Alert {alert_id} not found or already acknowledged")
    return {"acknowledged": True, "alert_id": alert_id}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, db=Depends(get_db)):
    """Resolve an alert."""
    updated = await _alerts(db).resolve(alert_id)
    if not updated:
        raise HTTPException(404, f"Alert {alert_id} not found")
    return {"resolved": True, "alert_id": alert_id}


# ── Cost ──────────────────────────────────────────────────────────────────────

@router.get("/cost")
async def get_cost_totals(db=Depends(get_db)):
    """Current cost totals from in-memory running totals."""
    return _cost(db).totals()


@router.get("/cost/breakdown")
async def get_cost_breakdown(
    dimension: str           = Query("provider", description="user_id|workspace_id|institution|provider|model|mission_id|agent_name|prompt_key|job_type"),
    from_ts:   Optional[str] = Query(None),
    to_ts:     Optional[str] = Query(None),
    user_id:   Optional[str] = Query(None),
    limit:     int           = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    """Cost breakdown by any dimension, queried from MongoDB."""
    return await _cost(db).breakdown(
        dimension=dimension, from_ts=from_ts, to_ts=to_ts,
        user_id=user_id, limit=limit,
    )


@router.get("/cost/recent")
async def get_recent_costs(
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """Most recent AI cost records."""
    return await _cost(db).recent(limit=limit)


# ── Security ──────────────────────────────────────────────────────────────────

@router.get("/security")
async def get_security_events(
    event_type: Optional[str] = Query(None),
    severity:   Optional[str] = Query(None, description="LOW|MEDIUM|HIGH|CRITICAL"),
    user_id:    Optional[str] = Query(None),
    from_ts:    Optional[str] = Query(None),
    to_ts:      Optional[str] = Query(None),
    limit:      int           = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    """Search security events."""
    return await _security(db).query(
        event_type=event_type, severity=severity, user_id=user_id,
        from_ts=from_ts, to_ts=to_ts, limit=limit,
    )


@router.get("/security/summary")
async def get_security_summary(db=Depends(get_db)):
    """In-memory security event summary and counts by type."""
    return _security(db).summary()


# ── Profiler ──────────────────────────────────────────────────────────────────

@router.get("/profiler")
async def get_profiler_slow(
    component: Optional[str] = Query(None, description="api|db|ai|worker|graph|twin|mission"),
    limit:     int           = Query(20, ge=1, le=100),
):
    """Slow operations sorted by P95 latency descending."""
    p = _profiler()
    if component:
        return p.component_stats(component)
    return p.slow_operations(limit=limit)


@router.get("/profiler/recommendations")
async def get_profiler_recommendations():
    """Performance optimization recommendations for slow operations."""
    return _profiler().recommendations()


@router.get("/profiler/all")
async def get_all_profiler_stats():
    """All tracked operations with full statistics."""
    return _profiler().all_stats()
