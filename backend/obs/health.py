"""
Health Check Engine — Phase XXXV.6

Provides async health checkers for every subsystem. Each checker
returns a HealthResult(status, latency_ms, message, details).

Status values:
  healthy   — component is operating normally
  degraded  — component is partially impaired but functional
  unhealthy — component is unavailable or critically impaired

All checkers are independent and run concurrently. Failure in one
checker never prevents others from running.

Usage:
    engine = HealthEngine(db)
    results = await engine.check_all()
    summary = engine.aggregate(results)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class HealthResult:
    component:   str
    status:      str            # healthy | degraded | unhealthy
    latency_ms:  float = 0.0
    message:     str = ""
    details:     dict = field(default_factory=dict)
    checked_at:  str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "component":  self.component,
            "status":     self.status,
            "latency_ms": round(self.latency_ms, 1),
            "message":    self.message,
            "details":    self.details,
            "checked_at": self.checked_at,
        }


# ── Individual checkers ───────────────────────────────────────────────────────

async def _check_mongodb(db: Any) -> HealthResult:
    t0 = time.monotonic()
    try:
        await db.command("ping")
        latency = (time.monotonic() - t0) * 1000
        status = "healthy" if latency < 200 else "degraded"
        return HealthResult("mongodb", status, latency, f"ping {latency:.0f}ms")
    except Exception as exc:
        return HealthResult("mongodb", "unhealthy", (time.monotonic() - t0) * 1000, str(exc))


async def _check_redis() -> HealthResult:
    t0 = time.monotonic()
    try:
        from services.redis_client import get_redis
        client = get_redis()
        if client is None:
            return HealthResult("redis", "degraded", 0.0, "Redis client not initialised — running without cache")
        await client.ping()
        latency = (time.monotonic() - t0) * 1000
        status = "healthy" if latency < 50 else "degraded"
        return HealthResult("redis", status, latency, f"ping {latency:.0f}ms")
    except Exception as exc:
        return HealthResult("redis", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_worker_queue(db: Any) -> HealthResult:
    t0 = time.monotonic()
    try:
        from worker import get_worker_pool
        pool = get_worker_pool()
        if pool is None:
            return HealthResult("worker_queue", "degraded", 0.0, "Worker pool not started")
        count = await db["worker_jobs"].count_documents({"status": "queued"})
        latency = (time.monotonic() - t0) * 1000
        status = "healthy" if count < 1000 else "degraded"
        return HealthResult("worker_queue", status, latency, f"{count} queued jobs", {"queued": count})
    except Exception as exc:
        return HealthResult("worker_queue", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_scheduler() -> HealthResult:
    t0 = time.monotonic()
    try:
        from worker.scheduler import get_scheduler
        sched = get_scheduler()
        if sched is None:
            return HealthResult("scheduler", "degraded", 0.0, "Scheduler not started")
        running = sched._scheduler.running if sched._scheduler else False
        latency = (time.monotonic() - t0) * 1000
        if running:
            return HealthResult("scheduler", "healthy", latency, "APScheduler running")
        return HealthResult("scheduler", "degraded", latency, "APScheduler not running")
    except Exception as exc:
        return HealthResult("scheduler", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_workers() -> HealthResult:
    t0 = time.monotonic()
    try:
        from worker import get_worker_pool
        pool = get_worker_pool()
        if pool is None:
            return HealthResult("workers", "degraded", 0.0, "Worker pool not started")
        total_workers = len(pool._workers)
        running = sum(1 for w in pool._workers if w._running)
        latency = (time.monotonic() - t0) * 1000
        if running == total_workers and total_workers > 0:
            return HealthResult("workers", "healthy", latency, f"{running}/{total_workers} workers running",
                                {"running": running, "total": total_workers})
        if running > 0:
            return HealthResult("workers", "degraded", latency, f"Only {running}/{total_workers} workers running",
                                {"running": running, "total": total_workers})
        return HealthResult("workers", "unhealthy", latency, "No workers running",
                            {"running": 0, "total": total_workers})
    except Exception as exc:
        return HealthResult("workers", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_event_bus() -> HealthResult:
    t0 = time.monotonic()
    try:
        from events import get_bus
        bus = get_bus()
        latency = (time.monotonic() - t0) * 1000
        if bus._running:
            return HealthResult("event_bus", "healthy", latency, "Event bus running")
        return HealthResult("event_bus", "degraded", latency, "Event bus not running")
    except Exception as exc:
        return HealthResult("event_bus", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_ai_gateway() -> HealthResult:
    t0 = time.monotonic()
    try:
        from gateway.pipeline import get_pipeline
        pipeline = get_pipeline()
        latency = (time.monotonic() - t0) * 1000
        if pipeline:
            return HealthResult("ai_gateway", "healthy", latency, "Gateway pipeline active")
        return HealthResult("ai_gateway", "degraded", latency, "Gateway pipeline not initialised")
    except Exception as exc:
        return HealthResult("ai_gateway", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_llm_providers() -> HealthResult:
    t0 = time.monotonic()
    try:
        from worker.circuit_breaker import get_job_cb_registry, ExternalDep
        registry = get_job_cb_registry()
        open_cbs = []
        for dep in (ExternalDep.LLM_ANTHROPIC, ExternalDep.LLM_OPENAI, ExternalDep.LLM_GOOGLE):
            cb = get_job_cb(dep)
            if cb and cb.state == "open":
                open_cbs.append(dep.value)
        latency = (time.monotonic() - t0) * 1000
        if not open_cbs:
            return HealthResult("llm_providers", "healthy", latency, "All LLM circuit breakers closed")
        return HealthResult("llm_providers", "degraded", latency,
                            f"Open circuit breakers: {open_cbs}", {"open": open_cbs})
    except Exception as exc:
        return HealthResult("llm_providers", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_knowledge_graph(db: Any) -> HealthResult:
    t0 = time.monotonic()
    try:
        node_count = await db["kg_nodes"].count_documents({})
        latency = (time.monotonic() - t0) * 1000
        return HealthResult("knowledge_graph", "healthy", latency,
                            f"{node_count} nodes", {"node_count": node_count})
    except Exception as exc:
        return HealthResult("knowledge_graph", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_digital_twin(db: Any) -> HealthResult:
    t0 = time.monotonic()
    try:
        twin_count = await db["digital_twins"].count_documents({})
        latency = (time.monotonic() - t0) * 1000
        return HealthResult("digital_twin", "healthy", latency,
                            f"{twin_count} twins", {"twin_count": twin_count})
    except Exception as exc:
        return HealthResult("digital_twin", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_storage() -> HealthResult:
    t0 = time.monotonic()
    try:
        from services.storage_service import get_storage
        storage = get_storage()
        latency = (time.monotonic() - t0) * 1000
        if storage:
            return HealthResult("storage", "healthy", latency, "Storage service available")
        return HealthResult("storage", "degraded", latency, "Storage service not initialised")
    except Exception as exc:
        return HealthResult("storage", "degraded", (time.monotonic() - t0) * 1000, str(exc))


async def _check_api() -> HealthResult:
    return HealthResult("api", "healthy", 0.0, "FastAPI running — this endpoint responded")


# ── Health Engine ─────────────────────────────────────────────────────────────

# Map component name → checker coroutine factory
_CHECKERS: dict[str, Callable] = {
    "api":             lambda db: _check_api(),
    "mongodb":         lambda db: _check_mongodb(db),
    "redis":           lambda db: _check_redis(),
    "worker_queue":    lambda db: _check_worker_queue(db),
    "scheduler":       lambda db: _check_scheduler(),
    "workers":         lambda db: _check_workers(),
    "event_bus":       lambda db: _check_event_bus(),
    "ai_gateway":      lambda db: _check_ai_gateway(),
    "llm_providers":   lambda db: _check_llm_providers(),
    "knowledge_graph": lambda db: _check_knowledge_graph(db),
    "digital_twin":    lambda db: _check_digital_twin(db),
    "storage":         lambda db: _check_storage(),
}

_STATUS_RANK = {"healthy": 0, "degraded": 1, "unhealthy": 2}


class HealthEngine:

    def __init__(self, db: Any) -> None:
        self._db = db

    async def check_component(self, name: str) -> HealthResult:
        checker = _CHECKERS.get(name)
        if not checker:
            return HealthResult(name, "unhealthy", 0.0, f"Unknown component: {name}")
        try:
            return await asyncio.wait_for(checker(self._db), timeout=5.0)
        except asyncio.TimeoutError:
            return HealthResult(name, "unhealthy", 5000.0, "Health check timed out (5s)")
        except Exception as exc:
            return HealthResult(name, "unhealthy", 0.0, str(exc))

    async def check_all(self, components: list[str] | None = None) -> dict[str, HealthResult]:
        names = components or list(_CHECKERS.keys())
        tasks = {name: asyncio.create_task(self.check_component(name)) for name in names}
        results: dict[str, HealthResult] = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as exc:
                results[name] = HealthResult(name, "unhealthy", 0.0, str(exc))
        return results

    def aggregate(self, results: dict[str, HealthResult]) -> dict:
        statuses = [r.status for r in results.values()]
        if any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        elif any(s == "degraded" for s in statuses):
            overall = "degraded"
        else:
            overall = "healthy"
        return {
            "status":     overall,
            "checked_at": datetime.utcnow().isoformat(),
            "components": {name: r.to_dict() for name, r in results.items()},
            "summary": {
                "total":     len(results),
                "healthy":   statuses.count("healthy"),
                "degraded":  statuses.count("degraded"),
                "unhealthy": statuses.count("unhealthy"),
            },
        }

    @property
    def component_names(self) -> list[str]:
        return list(_CHECKERS.keys())


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: HealthEngine | None = None


def init_health(db: Any) -> HealthEngine:
    global _engine
    _engine = HealthEngine(db)
    return _engine


def get_health_engine() -> HealthEngine | None:
    return _engine


# Late import fix for circuit breaker used above
try:
    from worker.circuit_breaker import get_job_cb
except ImportError:
    def get_job_cb(dep):  # type: ignore
        return None
