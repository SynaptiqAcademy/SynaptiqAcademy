"""
Enterprise Worker Platform — public API.

Usage in FastAPI routers (replaces BackgroundTasks):

    from worker import enqueue_job
    from worker.models import Job, Priority

    async def my_endpoint(...):
        job = Job(
            job_type="integrity.analysis",
            payload={"user_id": str(user["_id"])},
            user_id=str(user["_id"]),
            priority=Priority.NORMAL,
        )
        await enqueue_job(job, db)
        return {"status": "analysis_started", "job_id": job.job_id}

Lifecycle (called from server.py):

    await start_worker_platform(db)
    ...
    await stop_worker_platform()
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .models      import (
    ALL_JOB_TYPES, ALL_QUEUES, Job, JobStatus, Priority, Schedule, WorkerInfo,
    JOB_AI_EXECUTION, JOB_CITATION_MONITOR, JOB_CITATION_WEEKLY_SYNC,
    JOB_DATA_IMPORT, JOB_GRANT_DISCOVERY, JOB_GRAPH_REBUILD,
    JOB_INSTITUTION_ANALYTICS, JOB_INTEGRITY_ANALYSIS, JOB_KG_UPDATE,
    JOB_MARKETPLACE_PROCESS, JOB_MEMORY_ENRICH, JOB_MISSION_STEP,
    JOB_NOTIFICATION_DELIVER, JOB_ORCID_SYNC, JOB_ORCID_WEEKLY_SYNC,
    JOB_PUBLICATION_MONITOR, JOB_RECOMMENDATION_GEN, JOB_REPORT_GENERATE,
    JOB_TEACHING_ANALYTICS, JOB_TWIN_UPDATE,
    JOB_EMAIL_SEND, JOB_EMAIL_GETTING_STARTED_CHECK,
    QUEUE_AI, QUEUE_DEFAULT, QUEUE_GRAPH, QUEUE_INGESTION, QUEUE_REPORTS,
)
from .worker      import WorkerPool, _set_worker_pool, get_worker_pool
from .scheduler   import Scheduler
from .queue       import MongoQueueBackend

logger = logging.getLogger(__name__)

__all__ = [
    "start_worker_platform",
    "stop_worker_platform",
    "start_worker_platform_supervisor",
    "stop_worker_platform_supervisor",
    "is_worker_platform_running",
    "enqueue_job",
    "get_worker_pool",
    "get_scheduler",
    # models
    "Job", "JobStatus", "Priority", "Schedule", "WorkerInfo",
    # job type constants
    "JOB_AI_EXECUTION", "JOB_MISSION_STEP", "JOB_KG_UPDATE", "JOB_TWIN_UPDATE",
    "JOB_RECOMMENDATION_GEN", "JOB_GRANT_DISCOVERY", "JOB_PUBLICATION_MONITOR",
    "JOB_CITATION_MONITOR", "JOB_ORCID_SYNC", "JOB_ORCID_WEEKLY_SYNC",
    "JOB_CITATION_WEEKLY_SYNC", "JOB_INSTITUTION_ANALYTICS", "JOB_TEACHING_ANALYTICS",
    "JOB_MARKETPLACE_PROCESS", "JOB_NOTIFICATION_DELIVER", "JOB_DATA_IMPORT",
    "JOB_GRAPH_REBUILD", "JOB_REPORT_GENERATE", "JOB_INTEGRITY_ANALYSIS",
    "JOB_MEMORY_ENRICH", "JOB_EMAIL_SEND", "JOB_EMAIL_GETTING_STARTED_CHECK",
    # queue constants
    "QUEUE_DEFAULT", "QUEUE_AI", "QUEUE_GRAPH", "QUEUE_INGESTION", "QUEUE_REPORTS",
]

_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler | None:
    return _scheduler


async def start_worker_platform(db: Any) -> None:
    """
    Start the full Worker Platform:
      1. Start WorkerPool (4 workers, all queues)
      2. Start Scheduler (APScheduler + MongoDB persistence)
      3. Register recurring schedules (ORCID weekly, citation weekly)
    """
    global _scheduler

    # WorkerPool
    pool = WorkerPool(db)
    await pool.start()
    _set_worker_pool(pool)

    # Scheduler
    queue   = MongoQueueBackend(db)
    sched   = Scheduler(db, queue)
    await sched.start()
    _scheduler = sched

    # Register weekly scheduled jobs (idempotent — won't duplicate if schedule_id exists)
    await _register_built_in_schedules(sched)

    logger.info("Enterprise Worker Platform started")


async def stop_worker_platform() -> None:
    """Graceful shutdown: drain workers, stop scheduler."""
    global _scheduler

    pool = get_worker_pool()
    if pool:
        await pool.stop(drain=True)
        _set_worker_pool(None)

    if _scheduler:
        await _scheduler.stop()
        _scheduler = None

    logger.info("Enterprise Worker Platform stopped")


# ── Auto-recovery supervisor ──────────────────────────────────────────────────
# RC production blocker fix: start_worker_platform() previously only ran once,
# at server startup, inside an `if is_db_down(): return` guard — if Mongo
# happened to be unreachable at that exact moment (a startup race, a brief
# Atlas blip during deploy), the entire background-job system silently
# disabled itself for the rest of the process's life. Queued jobs (emails,
# scheduled tasks) would sit at status=queued forever with no operator-visible
# error, and the only fix was a manual server restart timed to land while
# Mongo happened to be up.
#
# This supervisor runs for the whole process lifetime: it starts the platform
# as soon as Mongo is reachable, and if the platform ever stops unexpectedly
# (pool/scheduler died), it restarts it — with exponential backoff between
# attempts so a sustained outage doesn't spin hot, capped and reset on
# success. No manual restart is ever required.
_supervisor_task: "asyncio.Task | None" = None
_platform_ready: bool = False

_SUPERVISOR_MIN_BACKOFF = 2.0
_SUPERVISOR_MAX_BACKOFF = 60.0
_SUPERVISOR_HEALTHY_INTERVAL = 15.0


def is_worker_platform_running() -> bool:
    """True if the worker pool and scheduler are both up right now."""
    return _platform_ready and get_worker_pool() is not None and get_scheduler() is not None


async def _worker_platform_supervisor() -> None:
    from db import get_db, is_db_down

    global _platform_ready
    backoff = _SUPERVISOR_MIN_BACKOFF
    while True:
        try:
            if not is_worker_platform_running():
                _platform_ready = False
                if is_db_down():
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _SUPERVISOR_MAX_BACKOFF)
                    continue
                db = get_db()
                await start_worker_platform(db)
                _platform_ready = True
                backoff = _SUPERVISOR_MIN_BACKOFF
                await asyncio.sleep(_SUPERVISOR_HEALTHY_INTERVAL)
            else:
                await asyncio.sleep(_SUPERVISOR_HEALTHY_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Worker platform supervisor: (re)start attempt failed, will retry in %.0fs: %s",
                           backoff, exc)
            _platform_ready = False
            try:
                from services.realtime import manager
                await manager.broadcast_admin({"type": "job_failed", "scope": "worker_platform_supervisor", "error": str(exc)})
            except Exception:
                pass
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _SUPERVISOR_MAX_BACKOFF)


def start_worker_platform_supervisor() -> None:
    """Call once at app startup (non-blocking). Idempotent — a second call
    is a no-op if the supervisor is already running."""
    global _supervisor_task
    if _supervisor_task and not _supervisor_task.done():
        return
    _supervisor_task = asyncio.create_task(_worker_platform_supervisor())
    logger.info("Worker platform supervisor started (auto-recovers on Mongo/Redis reconnect)")


async def stop_worker_platform_supervisor() -> None:
    """Call at app shutdown — cancels the supervisor loop, then stops the
    platform itself if it's currently running."""
    global _supervisor_task, _platform_ready
    if _supervisor_task:
        _supervisor_task.cancel()
        try:
            await _supervisor_task
        except asyncio.CancelledError:
            pass
        _supervisor_task = None
    _platform_ready = False
    if get_worker_pool() is not None or get_scheduler() is not None:
        await stop_worker_platform()


async def enqueue_job(job: Job, db: Any) -> str:
    """
    Enqueue a job for background execution.

    Replaces BackgroundTasks.add_task() and asyncio.create_task() for
    all business workflows. Returns the job_id for status tracking.
    """
    queue = MongoQueueBackend(db)
    await queue.enqueue(job)

    from .observability import get_job_observability
    get_job_observability().record_enqueued(job.job_type)

    logger.debug("Enqueued %s (job_id=%s, priority=%s)", job.job_type, job.job_id, job.priority.name)
    return job.job_id


async def _register_built_in_schedules(sched: Scheduler) -> None:
    """Register all platform-level recurring schedules."""
    built_ins = [
        # ORCID sync every Sunday 02:00 UTC
        dict(
            job_type="orcid.weekly_sync",
            payload={},
            cron_expr="0 2 * * 0",
            schedule_id="builtin:orcid_weekly",
            priority=Priority.LOW,
        ),
        # Citation sync every Sunday 03:00 UTC
        dict(
            job_type="citation.weekly_sync",
            payload={},
            cron_expr="0 3 * * 0",
            schedule_id="builtin:citation_weekly",
            priority=Priority.LOW,
        ),
        # Publication monitoring every 6 hours
        dict(
            job_type="publication.monitor",
            payload={},
            cron_expr="0 */6 * * *",
            schedule_id="builtin:publication_monitor",
            priority=Priority.BACKGROUND,
        ),
    ]
    for cfg in built_ins:
        try:
            # Check if schedule already exists to avoid duplicates
            existing = await sched.get(cfg["schedule_id"])
            if existing is None:
                await sched.add_cron(**cfg)
        except Exception as exc:
            logger.warning("Could not register built-in schedule %s: %s", cfg["schedule_id"], exc)
            try:
                from services.realtime import manager
                await manager.broadcast_admin({"type": "job_failed", "scope": "schedule_registration", "schedule_id": cfg["schedule_id"], "error": str(exc)})
            except Exception:
                pass
