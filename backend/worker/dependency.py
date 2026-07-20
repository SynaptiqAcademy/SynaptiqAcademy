"""
Dependency Graph — resolves job dependencies before execution.

If a job declares `depends_on: [job_id, ...]`, all listed jobs must be
in COMPLETED status before this job can run.

When a dequeued job has unsatisfied dependencies, the executor re-marks it
as WAITING and a background checker re-queues it when dependencies complete.
"""
from __future__ import annotations

import logging
from typing import Any

from .models import Job, JobStatus

logger = logging.getLogger(__name__)


class DependencyGraph:

    def __init__(self, queue_backend: Any) -> None:
        self._queue = queue_backend

    async def all_satisfied(self, job: Job) -> bool:
        """Return True if all depends_on jobs are COMPLETED."""
        if not job.depends_on:
            return True
        for dep_id in job.depends_on:
            dep = await self._queue.get_job(dep_id)
            if dep is None or dep.status != JobStatus.COMPLETED:
                return False
        return True

    async def check_waiting_jobs(self) -> int:
        """
        Re-queue any WAITING jobs whose dependencies are now satisfied.
        Called periodically by the WorkerPool.
        """
        waiting = await self._queue.get_waiting_jobs()
        re_queued = 0
        for job in waiting:
            try:
                if await self.all_satisfied(job):
                    await self._queue.requeue(job.job_id)
                    re_queued += 1
                    logger.debug("Dep satisfied — re-queued job %s (%s)", job.job_id, job.job_type)
            except Exception as exc:
                logger.error("Dependency check error for %s: %s", job.job_id, exc)
        return re_queued
