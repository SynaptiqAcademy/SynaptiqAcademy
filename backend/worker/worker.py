"""
WorkerProcess and WorkerPool — the execution backbone of the Worker Platform.

WorkerProcess:
  - Registers with WorkerRegistry on start
  - Sends heartbeat every 30 s
  - Polls queues every 2 s, dequeues highest-priority eligible job
  - Executes via JobExecutor (controlled by asyncio.Semaphore)
  - Drains gracefully on shutdown (waits for active jobs to finish)
  - Stateless: all job state lives in MongoDB

WorkerPool:
  - Manages multiple WorkerProcess instances
  - Periodically checks for stale workers and re-queues their jobs
  - Periodically re-queues WAITING jobs whose dependencies are now met
  - Singleton via get_worker_pool()

Internal use of asyncio.create_task() here is intentional: it is the
worker's own task-management mechanics, not a business workflow.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from typing import Any

from .checkpoint     import CheckpointEngine
from .concurrency    import ConcurrencyManager
from .dependency     import DependencyGraph
from .dlq            import JobDLQ
from .executor       import JobExecutor
from .models         import (
    ALL_JOB_TYPES, ALL_QUEUES, Job, WorkerInfo,
    QUEUE_DEFAULT, QUEUE_AI, QUEUE_GRAPH, QUEUE_INGESTION, QUEUE_REPORTS,
)
from .observability  import get_job_observability
from .queue          import MongoQueueBackend
from .registry       import WorkerRegistry

logger = logging.getLogger(__name__)

_HEARTBEAT_S        = 30
_DEQUEUE_POLL_S     = 2
_STALE_CHECK_S      = 60
_DEP_CHECK_S        = 30
_CONCURRENT_JOBS    = 8     # per WorkerProcess


class WorkerProcess:
    """
    A single async worker — registers, polls, executes, heartbeats.
    Multiple instances can run in the same event loop (or across processes)
    because job dequeue is atomic at the MongoDB level.
    """

    def __init__(
        self,
        db:           Any,
        worker_id:    str,
        queue_names:  list[str],
        job_types:    list[str],
        concurrency:  int = _CONCURRENT_JOBS,
    ) -> None:
        self._db          = db
        self._worker_id   = worker_id
        self._queue_names = queue_names
        self._job_types   = job_types
        self._concurrency = concurrency
        self._running     = False

        self._queue    = MongoQueueBackend(db)
        self._registry = WorkerRegistry(db)
        self._conc_mgr = ConcurrencyManager(db)
        self._dlq      = JobDLQ(db)
        self._executor = JobExecutor(
            db=db,
            concurrency=self._conc_mgr,
            dlq=self._dlq,
            queue=self._queue,
        )
        self._semaphore    = asyncio.Semaphore(concurrency)
        self._active_tasks: set[asyncio.Task] = set()
        self._current_jobs: list[str]         = []

    async def start(self) -> None:
        self._running = True
        info = WorkerInfo(
            worker_id=self._worker_id,
            queue_names=self._queue_names,
            job_types=self._job_types,
            concurrency=self._concurrency,
            hostname=socket.gethostname(),
            pid=os.getpid(),
        )
        await self._registry.register(info)
        asyncio.create_task(self._heartbeat_loop(), name=f"hb-{self._worker_id}")
        asyncio.create_task(self._dequeue_loop(), name=f"dq-{self._worker_id}")
        logger.info(
            "WorkerProcess %s started (queues=%s, concurrency=%d)",
            self._worker_id, self._queue_names, self._concurrency,
        )

    async def stop(self, drain: bool = True) -> None:
        self._running = False
        if drain and self._active_tasks:
            logger.info("Worker %s draining %d tasks...", self._worker_id, len(self._active_tasks))
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        await self._registry.deregister(self._worker_id)
        logger.info("WorkerProcess %s stopped", self._worker_id)

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Loops ─────────────────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                load = len(self._current_jobs) / max(self._concurrency, 1)
                await self._registry.heartbeat(
                    self._worker_id, list(self._current_jobs), load
                )
            except Exception as exc:
                logger.debug("Heartbeat error: %s", exc)
            await asyncio.sleep(_HEARTBEAT_S)

    async def _dequeue_loop(self) -> None:
        while self._running:
            for q in self._queue_names:
                try:
                    # Only dequeue if we have capacity
                    if len(self._current_jobs) < self._concurrency:
                        job = await self._queue.dequeue(q, self._worker_id, self._job_types)
                        if job:
                            task = asyncio.create_task(
                                self._execute_one(job),
                                name=f"job-{job.job_id}",
                            )
                            self._active_tasks.add(task)
                            task.add_done_callback(self._active_tasks.discard)
                except Exception as exc:
                    logger.error("Dequeue error on %s: %s", q, exc)
            await asyncio.sleep(_DEQUEUE_POLL_S)

    async def _execute_one(self, job: Job) -> None:
        self._current_jobs.append(job.job_id)
        try:
            await self._executor.execute(job, self._worker_id)
        except Exception as exc:
            logger.error("Unhandled executor error for %s: %s", job.job_id, exc)
        finally:
            if job.job_id in self._current_jobs:
                self._current_jobs.remove(job.job_id)


# ── WorkerPool ────────────────────────────────────────────────────────────────


class WorkerPool:
    """
    Manages a set of WorkerProcess instances and platform-level background tasks.

    Default configuration:
      - 1 general worker  (all queues, all job types)
      - 1 AI worker       (ai queue only)
      - 1 graph worker    (graph queue only)
      - 1 ingestion worker (ingestion queue only)
    """

    def __init__(self, db: Any) -> None:
        self._db       = db
        self._workers: list[WorkerProcess] = []
        self._running  = False
        self._queue    = MongoQueueBackend(db)
        self._registry = WorkerRegistry(db)
        self._deps     = DependencyGraph(self._queue)

    async def start(self) -> None:
        self._running = True

        # Ensure all required indexes exist
        await self._queue.ensure_indexes()
        await self._registry.ensure_indexes()
        conc_mgr = ConcurrencyManager(self._db)
        await conc_mgr.ensure_indexes()
        dlq = JobDLQ(self._db)
        await dlq.ensure_indexes()

        # Recover any stale jobs from previous crash
        recovered = await self._registry.recover_stale_jobs(self._queue)
        if recovered:
            logger.info("Pool startup: recovered %d stale jobs", recovered)

        # Spawn workers
        workers_cfg = [
            ("worker-default",   ALL_QUEUES,            ALL_JOB_TYPES, 8),
            ("worker-ai",        [QUEUE_AI],             ["ai.execution", "mission.step", "memory.enrich"], 4),
            ("worker-graph",     [QUEUE_GRAPH],          ["kg.update", "graph.rebuild"], 2),
            ("worker-ingestion", [QUEUE_INGESTION],      ["orcid.sync", "orcid.weekly_sync", "citation.weekly_sync", "citation.monitor", "publication.monitor", "grant.discovery", "data.import"], 4),
        ]
        for worker_id, queues, jtypes, concurrency in workers_cfg:
            wp = WorkerProcess(
                db=self._db,
                worker_id=worker_id,
                queue_names=queues,
                job_types=jtypes,
                concurrency=concurrency,
            )
            await wp.start()
            self._workers.append(wp)

        # Platform-level maintenance tasks
        asyncio.create_task(self._stale_worker_loop(), name="pool-stale-check")
        asyncio.create_task(self._dependency_check_loop(), name="pool-dep-check")

        logger.info("WorkerPool started with %d workers", len(self._workers))

    async def stop(self, drain: bool = True) -> None:
        self._running = False
        for wp in self._workers:
            await wp.stop(drain=drain)
        self._workers.clear()
        logger.info("WorkerPool stopped")

    async def _stale_worker_loop(self) -> None:
        while self._running:
            await asyncio.sleep(_STALE_CHECK_S)
            try:
                recovered = await self._registry.recover_stale_jobs(self._queue)
                if recovered:
                    logger.info("Stale check: recovered %d jobs", recovered)
            except Exception as exc:
                logger.error("Stale check error: %s", exc)

    async def _dependency_check_loop(self) -> None:
        while self._running:
            await asyncio.sleep(_DEP_CHECK_S)
            try:
                re_queued = await self._deps.check_waiting_jobs()
                if re_queued:
                    logger.debug("Dep check: re-queued %d jobs", re_queued)
            except Exception as exc:
                logger.error("Dep check error: %s", exc)

    @property
    def worker_count(self) -> int:
        return len(self._workers)


# ── Singleton ─────────────────────────────────────────────────────────────────

_pool: WorkerPool | None = None


def get_worker_pool() -> WorkerPool | None:
    return _pool


def _set_worker_pool(pool: WorkerPool | None) -> None:
    global _pool
    _pool = pool
