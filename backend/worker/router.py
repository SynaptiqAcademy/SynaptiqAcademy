"""
Worker Platform Admin API — /api/worker/*

Endpoints provide full operational visibility and control:
  Workers, Queues, Jobs, Schedules, DLQ, Metrics, Circuit-Breakers
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/worker", tags=["worker-platform"])


# ── Lazy imports to avoid circular deps ──────────────────────────────────────

def _get_admin_user():
    from zt.deps import require_admin_dep
    return Depends(require_admin_dep)


def _get_db():
    from db import get_db
    return Depends(get_db)


def _get_pool():
    from worker import get_worker_pool
    pool = get_worker_pool()
    if pool is None:
        raise HTTPException(503, "Worker platform not started")
    return pool


def _get_queue(db: Any):
    from worker.queue import MongoQueueBackend
    return MongoQueueBackend(db)


def _get_registry(db: Any):
    from worker.registry import WorkerRegistry
    return WorkerRegistry(db)


def _get_scheduler():
    from worker import get_scheduler
    sched = get_scheduler()
    if sched is None:
        raise HTTPException(503, "Scheduler not started")
    return sched


def _get_dlq(db: Any):
    from worker.dlq import JobDLQ
    return JobDLQ(db)


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def worker_health(
    _=_get_admin_user(),
    db=_get_db(),
):
    try:
        pool = _get_pool()
    except HTTPException:
        return {"status": "not_started"}
    registry = _get_registry(db)
    workers  = await registry.list_healthy()
    return {
        "status":          "healthy" if workers else "degraded",
        "worker_count":    pool.worker_count,
        "healthy_workers": len(workers),
    }


# ── Workers ───────────────────────────────────────────────────────────────────

@router.get("/workers")
async def list_workers(
    _=_get_admin_user(),
    db=_get_db(),
):
    registry = _get_registry(db)
    workers  = await registry.list_all()
    return {"workers": [w.to_dict() for w in workers]}


@router.get("/workers/{worker_id}")
async def get_worker(
    worker_id: str,
    _=_get_admin_user(),
    db=_get_db(),
):
    registry = _get_registry(db)
    w = await registry.get(worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    return w.to_dict()


# ── Queues ────────────────────────────────────────────────────────────────────

@router.get("/queues")
async def queue_stats(
    _=_get_admin_user(),
    db=_get_db(),
):
    q = _get_queue(db)
    return {"stats": await q.stats()}


@router.get("/queues/{queue_name}/peek")
async def peek_queue(
    queue_name: str,
    limit: int = Query(10, ge=1, le=100),
    _=_get_admin_user(),
    db=_get_db(),
):
    q    = _get_queue(db)
    jobs = await q.peek(queue_name, limit=limit)
    return {"jobs": [j.to_dict() for j in jobs]}


@router.get("/queues/{queue_name}/length")
async def queue_length(
    queue_name: str,
    _=_get_admin_user(),
    db=_get_db(),
):
    q = _get_queue(db)
    return {"queue_name": queue_name, "length": await q.length(queue_name)}


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs(
    status:     str | None = Query(None),
    queue_name: str | None = Query(None),
    job_type:   str | None = Query(None),
    user_id:    str | None = Query(None),
    limit:      int        = Query(50, ge=1, le=500),
    _=_get_admin_user(),
    db=_get_db(),
):
    q    = _get_queue(db)
    jobs = await q.list_jobs(status=status, queue_name=queue_name, job_type=job_type, user_id=user_id, limit=limit)
    return {"jobs": [j.to_dict() for j in jobs]}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    _=_get_admin_user(),
    db=_get_db(),
):
    q   = _get_queue(db)
    job = await q.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.to_dict()


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    _=_get_admin_user(),
    db=_get_db(),
):
    q    = _get_queue(db)
    done = await q.cancel(job_id)
    if not done:
        raise HTTPException(409, "Job cannot be cancelled in its current state")
    return {"status": "cancelled", "job_id": job_id}


@router.post("/jobs/{job_id}/requeue")
async def requeue_job(
    job_id: str,
    _=_get_admin_user(),
    db=_get_db(),
):
    q    = _get_queue(db)
    done = await q.requeue(job_id)
    if not done:
        raise HTTPException(409, "Job cannot be re-queued in its current state")
    return {"status": "queued", "job_id": job_id}


# ── DLQ ───────────────────────────────────────────────────────────────────────

@router.get("/dlq")
async def list_dlq(
    status: str | None = Query(None),
    limit:  int        = Query(100, ge=1, le=500),
    _=_get_admin_user(),
    db=_get_db(),
):
    dlq   = _get_dlq(db)
    items = await dlq.list_all(status=status, limit=limit)
    return {"dlq": items, "count": len(items)}


@router.get("/dlq/count")
async def dlq_count(
    _=_get_admin_user(),
    db=_get_db(),
):
    dlq = _get_dlq(db)
    return {"pending": await dlq.pending_count()}


@router.post("/dlq/{job_id}/retry")
async def retry_dlq_entry(
    job_id: str,
    _=_get_admin_user(),
    db=_get_db(),
):
    dlq  = _get_dlq(db)
    item = await dlq.get(job_id)
    if not item:
        raise HTTPException(404, "DLQ entry not found")
    q    = _get_queue(db)
    done = await q.requeue(job_id)
    if done:
        await dlq.mark_resolved(job_id, "manually retried")
    return {"status": "requeued" if done else "not_found", "job_id": job_id}


@router.post("/dlq/{job_id}/resolve")
async def resolve_dlq_entry(
    job_id:     str,
    resolution: str = Query("manual"),
    _=_get_admin_user(),
    db=_get_db(),
):
    dlq = _get_dlq(db)
    await dlq.mark_resolved(job_id, resolution)
    return {"status": "resolved", "job_id": job_id}


@router.delete("/dlq/{job_id}")
async def delete_dlq_entry(
    job_id: str,
    _=_get_admin_user(),
    db=_get_db(),
):
    dlq  = _get_dlq(db)
    done = await dlq.delete(job_id)
    if not done:
        raise HTTPException(404, "DLQ entry not found")
    return {"status": "deleted", "job_id": job_id}


# ── Schedules ─────────────────────────────────────────────────────────────────

@router.get("/schedules")
async def list_schedules(
    _=_get_admin_user(),
):
    sched   = _get_scheduler()
    scheds  = await sched.list_schedules()
    return {"schedules": [s.to_dict() for s in scheds]}


@router.get("/schedules/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    _=_get_admin_user(),
):
    sched = _get_scheduler()
    s     = await sched.get(schedule_id)
    if not s:
        raise HTTPException(404, "Schedule not found")
    return s.to_dict()


@router.post("/schedules/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: str,
    _=_get_admin_user(),
):
    sched = _get_scheduler()
    await sched.pause(schedule_id)
    return {"status": "paused", "schedule_id": schedule_id}


@router.post("/schedules/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: str,
    _=_get_admin_user(),
):
    sched = _get_scheduler()
    await sched.resume(schedule_id)
    return {"status": "resumed", "schedule_id": schedule_id}


@router.delete("/schedules/{schedule_id}")
async def remove_schedule(
    schedule_id: str,
    _=_get_admin_user(),
):
    sched = _get_scheduler()
    await sched.remove(schedule_id)
    return {"status": "removed", "schedule_id": schedule_id}


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics")
async def worker_metrics(
    _=_get_admin_user(),
):
    from worker.observability import get_job_observability
    return get_job_observability().snapshot()


# ── Circuit Breakers ──────────────────────────────────────────────────────────

@router.get("/circuit-breakers")
async def circuit_breakers(
    _=_get_admin_user(),
):
    from worker.circuit_breaker import get_job_cb_registry
    return {"circuit_breakers": get_job_cb_registry().all_status()}


@router.post("/circuit-breakers/{dep}/reset")
async def reset_circuit_breaker(
    dep: str,
    _=_get_admin_user(),
):
    from worker.circuit_breaker import ExternalDep, get_job_cb_registry
    try:
        d = ExternalDep(dep)
    except ValueError:
        raise HTTPException(400, f"Unknown dependency: {dep}")
    get_job_cb_registry().reset(d)
    return {"status": "reset", "dep": dep}


# ── Handler Registry ──────────────────────────────────────────────────────────

@router.get("/handlers")
async def list_handlers(
    _=_get_admin_user(),
):
    from worker.handlers import get_handler_registry
    return {"handlers": get_handler_registry().registered_types()}
