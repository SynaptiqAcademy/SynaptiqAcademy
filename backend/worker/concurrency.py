"""
Concurrency Manager — distributed locks and per-job-type rate limits.

Two layers:
  1. In-process asyncio.Semaphore   — caps concurrent executions per worker
  2. Distributed MongoDB lock       — prevents duplicate execution across workers
     (e.g. only one ORCID weekly sync at a time, regardless of worker count)

Job types that need singleton execution (at most one instance at a time):
  orcid.weekly_sync, citation.weekly_sync, graph.rebuild, data.import
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_COL = "worker_locks"

# Job types that enforce singleton execution via distributed lock
SINGLETON_JOB_TYPES: set[str] = {
    "orcid.weekly_sync",
    "citation.weekly_sync",
    "graph.rebuild",
    "data.import",
}

# Per-job-type in-process concurrency limits (0 = unlimited)
JOB_TYPE_CONCURRENCY: dict[str, int] = {
    "ai.execution":       4,
    "mission.step":       4,
    "kg.update":          2,
    "graph.rebuild":      1,
    "report.generate":    3,
    "data.import":        1,
    "orcid.weekly_sync":  1,
    "citation.weekly_sync": 1,
}


class ConcurrencyManager:

    def __init__(self, db: Any) -> None:
        self._db = db
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    async def ensure_indexes(self) -> None:
        col = self._db[_COL]
        await col.create_index("lock_key", unique=True)
        await col.create_index("expires_at", expireAfterSeconds=0)

    def _semaphore_for(self, job_type: str) -> asyncio.Semaphore | None:
        limit = JOB_TYPE_CONCURRENCY.get(job_type, 0)
        if limit <= 0:
            return None
        if job_type not in self._semaphores:
            self._semaphores[job_type] = asyncio.Semaphore(limit)
        return self._semaphores[job_type]

    async def acquire_distributed_lock(
        self, lock_key: str, ttl_s: int = 3600
    ) -> bool:
        """
        Try to acquire a named distributed lock.
        Returns True if lock acquired, False if already held.
        Uses MongoDB upsert with unique index for atomicity.
        """
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_s)
        try:
            await self._db[_COL].insert_one({
                "lock_key":   lock_key,
                "acquired_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at,
            })
            return True
        except Exception as exc:
            if "E11000" in str(exc):
                return False
            raise

    async def release_distributed_lock(self, lock_key: str) -> None:
        await self._db[_COL].delete_one({"lock_key": lock_key})

    async def is_locked(self, lock_key: str) -> bool:
        doc = await self._db[_COL].find_one({"lock_key": lock_key})
        return doc is not None

    def get_semaphore(self, job_type: str) -> asyncio.Semaphore | None:
        return self._semaphore_for(job_type)

    def needs_singleton_lock(self, job_type: str) -> bool:
        return job_type in SINGLETON_JOB_TYPES

    def singleton_lock_key(self, job_type: str) -> str:
        return f"singleton:{job_type}"
