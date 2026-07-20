"""
Worker Registry — tracks all registered workers, their health, and heartbeats.

Workers self-register on startup and send heartbeats every 30 s.
Workers that miss 3 consecutive heartbeats (>90 s) are marked unhealthy and
their running jobs are re-queued by the recover_stale_jobs() routine.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from .models import WorkerInfo

logger = logging.getLogger(__name__)

_COL = "worker_registry"

# A worker is considered stale if its heartbeat is older than this
STALE_THRESHOLD_S = 90


class WorkerRegistry:

    def __init__(self, db: Any) -> None:
        self._db = db

    async def ensure_indexes(self) -> None:
        col = self._db[_COL]
        await col.create_index("worker_id", unique=True)
        await col.create_index("status")
        await col.create_index("heartbeat")

    async def register(self, info: WorkerInfo) -> None:
        d = info.to_dict()
        await self._db[_COL].update_one(
            {"worker_id": info.worker_id},
            {"$set": d},
            upsert=True,
        )
        logger.info("Worker registered: %s (queues=%s)", info.worker_id, info.queue_names)

    async def deregister(self, worker_id: str) -> None:
        await self._db[_COL].delete_one({"worker_id": worker_id})
        logger.info("Worker deregistered: %s", worker_id)

    async def heartbeat(
        self,
        worker_id: str,
        current_jobs: list[str],
        load: float,
    ) -> None:
        await self._db[_COL].update_one(
            {"worker_id": worker_id},
            {"$set": {
                "heartbeat":    datetime.utcnow().isoformat(),
                "current_jobs": current_jobs,
                "load":         round(load, 2),
                "status":       "healthy",
            }},
        )

    async def list_all(self) -> list[WorkerInfo]:
        docs = await self._db[_COL].find({}).to_list(500)
        return [WorkerInfo.from_dict(d) for d in docs]

    async def list_healthy(self) -> list[WorkerInfo]:
        cutoff = (datetime.utcnow() - timedelta(seconds=STALE_THRESHOLD_S)).isoformat()
        docs = await self._db[_COL].find(
            {"heartbeat": {"$gte": cutoff}, "status": "healthy"}
        ).to_list(500)
        return [WorkerInfo.from_dict(d) for d in docs]

    async def mark_unhealthy(self, worker_id: str) -> None:
        await self._db[_COL].update_one(
            {"worker_id": worker_id},
            {"$set": {"status": "unhealthy"}},
        )

    async def recover_stale_jobs(self, queue_backend) -> int:
        """
        Find workers that have missed heartbeats, mark them unhealthy, and
        re-queue any RUNNING jobs they had claimed.
        """
        cutoff = (datetime.utcnow() - timedelta(seconds=STALE_THRESHOLD_S)).isoformat()
        stale_docs = await self._db[_COL].find(
            {"heartbeat": {"$lt": cutoff}, "status": "healthy"}
        ).to_list(100)

        total_recovered = 0
        for doc in stale_docs:
            worker_id = doc["worker_id"]
            await self.mark_unhealthy(worker_id)
            recovered = await queue_backend.reset_stale(worker_id)
            if recovered:
                logger.warning(
                    "Worker %s stale — re-queued %d jobs", worker_id, recovered
                )
            total_recovered += recovered

        return total_recovered

    async def get(self, worker_id: str) -> WorkerInfo | None:
        doc = await self._db[_COL].find_one({"worker_id": worker_id})
        return WorkerInfo.from_dict(doc) if doc else None
