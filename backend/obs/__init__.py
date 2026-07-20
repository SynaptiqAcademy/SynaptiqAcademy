"""
Enterprise Observability Platform — Phase XXXV.6

Public API for the `obs` package. Import from here to access all
observability subsystems.

Lifecycle:
    # server.py startup
    await init_observability(db)

    # server.py shutdown
    await stop_observability()

Subsystems:
    tracer      — distributed tracing via contextvars
    logger      — structured logging with MongoDB persistence
    metrics     — Counter/Gauge/Histogram platform
    health      — async health checks for all components
    audit       — immutable audit log
    alerting    — rule-based alert engine
    profiler    — slow operation detector
    cost        — AI cost tracker by dimension
    security    — security event observer
    time_travel — trace-based timeline reconstruction
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

_log = logging.getLogger(__name__)

# ── Public re-exports ─────────────────────────────────────────────────────────

from .tracer import (
    TraceContext,
    Span,
    new_trace_id,
    new_request_id,
    set_trace_context,
    get_trace_context,
    get_trace_id,
    get_context_dict,
    create_span,
    get_tracer,
)

from .logger import (
    get_logger,
    get_log_buffer,
    install_structured_handler,
    flush_logs,
)

from .metrics import (
    get_metrics,
    reset_metrics,
    # Metric name constants
    M_API_REQUESTS, M_API_ERRORS, M_API_LATENCY,
    M_AI_REQUESTS, M_AI_ERRORS, M_AI_LATENCY,
    M_AI_TOKENS_IN, M_AI_TOKENS_OUT, M_AI_COST,
    M_AI_CACHE_HITS, M_AI_RETRIES,
    M_WORKER_JOBS_ENQ, M_WORKER_JOBS_DONE, M_WORKER_JOBS_FAIL, M_WORKER_JOBS_DLQ,
    M_WORKER_LATENCY, M_WORKER_ACTIVE, M_WORKER_QUEUE_D,
    M_MISSION_STARTED, M_MISSION_DONE, M_MISSION_FAILED, M_MISSION_LATENCY,
    M_KG_NODES, M_KG_EDGES, M_KG_UPDATES, M_KG_LATENCY,
    M_TWIN_UPDATES, M_TWIN_SIMULATIONS, M_TWIN_LATENCY,
    M_BUS_PUBLISHED, M_BUS_CONSUMED, M_BUS_DLQ, M_BUS_RETRIES,
    M_DB_LATENCY, M_DB_ERRORS, M_CACHE_HITS, M_CACHE_MISSES,
    M_SEC_FAILED_LOGIN, M_SEC_VIOLATIONS, M_SEC_INJECTIONS,
)

from .health import get_health_engine

from .audit import get_audit

from .alerting import get_alert_engine

from .profiler import get_profiler

from .cost import get_cost_tracker

from .security import (
    get_security_observer,
    EVT_FAILED_LOGIN, EVT_PERMISSION_VIOLATION, EVT_PROMPT_INJECTION,
    EVT_SUSPICIOUS_AI, EVT_RATE_LIMIT, EVT_ABNORMAL_USAGE,
    EVT_DATA_EXPORT, EVT_PRIVILEGE_ESCALATION,
    SEV_LOW, SEV_MEDIUM, SEV_HIGH, SEV_CRITICAL,
)

from .time_travel import get_time_traveler


# ── Lifecycle ─────────────────────────────────────────────────────────────────

_log_flush_task: asyncio.Task | None = None


async def init_observability(db: Any) -> None:
    """
    Initialise all observability subsystems.
    Called from server.py @app.on_event("startup").
    """
    global _log_flush_task

    from .tracer     import init_tracer
    from .logger     import install_structured_handler
    from .metrics    import init_metrics
    from .health     import init_health
    from .audit      import init_audit
    from .alerting   import init_alerting
    from .profiler   import init_profiler
    from .cost       import init_cost
    from .security   import init_security
    from .time_travel import init_time_travel

    init_tracer(db)
    install_structured_handler(db)
    init_metrics()
    init_health(db)
    init_audit(db)
    init_alerting(db)
    init_profiler()
    init_cost(db)
    init_security(db)
    init_time_travel(db)

    # Ensure MongoDB indexes for observability collections
    await _ensure_indexes(db)

    # Background task: flush WARNING+ logs to MongoDB every 30s
    _log_flush_task = asyncio.create_task(_log_flush_loop(db))

    _log.info("Observability platform initialised (Phase XXXV.6)")


async def stop_observability() -> None:
    """Gracefully stop background tasks. Called from server.py shutdown."""
    global _log_flush_task
    if _log_flush_task and not _log_flush_task.done():
        _log_flush_task.cancel()
        try:
            await _log_flush_task
        except asyncio.CancelledError:
            pass
    _log_flush_task = None
    _log.info("Observability platform stopped")


async def _log_flush_loop(db: Any) -> None:
    """Periodically persist WARNING+ log records to MongoDB."""
    from .logger import flush_logs
    while True:
        try:
            await asyncio.sleep(30)
            await flush_logs(db)
        except asyncio.CancelledError:
            # Final flush on shutdown
            try:
                await flush_logs(db)
            except Exception:
                pass
            raise
        except Exception as exc:
            _log.debug("Log flush error: %s", exc)


async def _ensure_indexes(db: Any) -> None:
    """Create MongoDB indexes for all observability collections."""
    try:
        from .tracer   import Tracer
        from .audit    import AuditLogger
        from .cost     import CostTracker
        from .security import SecurityObserver
        await Tracer(db).ensure_indexes()
        await AuditLogger(db).ensure_indexes()
        await CostTracker(db).ensure_indexes()
        await SecurityObserver(db).ensure_indexes()
        # obs_logs index
        try:
            await db["obs_logs"].create_index("timestamp")
            await db["obs_logs"].create_index("trace_id")
            await db["obs_logs"].create_index("user_id")
            await db["obs_logs"].create_index("level")
        except Exception:
            pass
    except Exception as exc:
        _log.debug("Observability index creation (non-fatal): %s", exc)
