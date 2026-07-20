"""
Job Executor — the full enterprise execution pipeline for a single job.

Pipeline for every job:
  1.  Load handler for job_type
  2.  Check dependency graph (re-queue as WAITING if deps unmet)
  3.  Acquire concurrency lock (semaphore + optional distributed singleton lock)
  4.  Run handler with idempotent checkpoint support
  5.  On success: ack, record metrics, publish domain event
  6.  On transient failure: nack with retry_at (re-scheduled in queue)
  7.  On permanent failure / exhausted retries: move to DLQ
  8.  Release locks always (finally block)

Each step is wrapped so a crash anywhere is contained to this job only.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .checkpoint    import CheckpointEngine
from .circuit_breaker import ExternalDep, get_job_cb
from .concurrency   import ConcurrencyManager
from .dependency    import DependencyGraph
from .dlq           import JobDLQ
from .handlers      import HandlerContext, get_handler_registry
from .models        import Job, JobStatus
from .observability import get_job_observability
from .retry         import DEFAULT_JOB_RETRY_POLICY, JobRetryPolicy, classify_error, should_retry, compute_retry_at

logger = logging.getLogger(__name__)


class JobExecutor:
    """
    Executes a single dequeued job end-to-end.

    Instantiate once per WorkerProcess; reused across all jobs.
    """

    def __init__(
        self,
        db:          Any,
        concurrency: ConcurrencyManager,
        dlq:         JobDLQ,
        queue:       Any,
    ) -> None:
        self._db          = db
        self._concurrency = concurrency
        self._dlq         = dlq
        self._queue       = queue
        self._obs         = get_job_observability()
        self._registry    = get_handler_registry()
        self._checkpoint  = CheckpointEngine(queue)
        self._deps        = DependencyGraph(queue)

    async def execute(self, job: Job, worker_id: str) -> None:
        """Execute job end-to-end. Never raises — captures all errors."""
        obs = self._obs

        # ── Step 1: Find handler ─────────────────────────────────────────────
        handler = self._registry.get(job.job_type)
        if handler is None:
            logger.error("No handler for job_type=%s, job_id=%s", job.job_type, job.job_id)
            await self._queue.mark_failed(job.job_id, f"No handler for {job.job_type}")
            obs.record_failure(job.job_type, worker_id)
            return

        # ── Step 2: Dependency check ─────────────────────────────────────────
        if job.depends_on:
            if not await self._deps.all_satisfied(job):
                logger.debug("Job %s waiting on deps: %s", job.job_id, job.depends_on)
                await self._queue.mark_waiting(job.job_id)
                return

        # ── Step 3: Singleton distributed lock (if required) ─────────────────
        lock_key: str | None = None
        if self._concurrency.needs_singleton_lock(job.job_type):
            lock_key = self._concurrency.singleton_lock_key(job.job_type)
            acquired = await self._concurrency.acquire_distributed_lock(lock_key)
            if not acquired:
                # Another worker is running this singleton; defer
                logger.debug("Singleton lock held for %s, deferring %s", job.job_type, job.job_id)
                await self._queue.nack(job.job_id, "singleton lock held — deferred", retry_at=compute_retry_at(0, DEFAULT_JOB_RETRY_POLICY))
                return

        # ── Step 4: In-process semaphore (cap per-type concurrency) ──────────
        sem = self._concurrency.get_semaphore(job.job_type)

        obs.record_start(job.job_type, worker_id)
        start = time.monotonic()

        try:
            ctx = HandlerContext(
                db=self._db,
                checkpoint=self._checkpoint,
                publish=self._noop_publish,
            )

            # Wire event bus publish if available
            try:
                from events import get_bus
                ctx.publish = get_bus().publish_sync
            except Exception:
                pass

            async def _run():
                if sem:
                    async with sem:
                        return await handler(job, ctx)
                else:
                    return await handler(job, ctx)

            result = await _run()

            # ── Step 5: Success ───────────────────────────────────────────────
            latency_ms = (time.monotonic() - start) * 1000
            await self._checkpoint.clear(job.job_id)
            await self._queue.ack(job.job_id, observability={
                "duration_ms": round(latency_ms, 1),
                "cost_usd":    result.cost_usd,
                "tokens_used": result.tokens,
                "provider":    result.provider,
                "model":       result.model,
            })
            obs.record_success(
                job.job_type, worker_id, latency_ms,
                cost_usd=result.cost_usd, tokens=result.tokens,
            )
            logger.debug(
                "Job completed: %s (%s) in %.0fms", job.job_id, job.job_type, latency_ms
            )

        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            error_msg  = str(exc)
            attempt    = job.attempt + 1  # current attempt (0-indexed in DB)

            if should_retry(exc, attempt, DEFAULT_JOB_RETRY_POLICY):
                retry_at = compute_retry_at(attempt, DEFAULT_JOB_RETRY_POLICY)
                await self._queue.nack(job.job_id, error_msg, retry_at=retry_at)
                obs.record_retry(job.job_type)
                logger.warning(
                    "Job %s (%s) failed (attempt %d) — retry at %s: %s",
                    job.job_id, job.job_type, attempt, retry_at, exc,
                )
            else:
                # Exhausted retries or permanent error → DLQ
                await self._queue.mark_failed(job.job_id, error_msg)
                await self._dlq.enqueue(job, error_msg, attempt)
                obs.record_failure(job.job_type, worker_id)
                obs.record_dlq(job.job_type)
                logger.error(
                    "Job %s (%s) permanently failed (attempt %d): %s",
                    job.job_id, job.job_type, attempt, exc,
                )

        finally:
            if lock_key:
                await self._concurrency.release_distributed_lock(lock_key)

    @staticmethod
    async def _noop_publish(event: Any) -> None:
        pass
