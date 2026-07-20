"""
Job Dead Letter Queue — permanently failed jobs awaiting manual inspection.

When a job exhausts all retry attempts it moves here.
Admin can: list, inspect, retry (re-queue), resolve (mark handled), or delete.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .models import Job

logger = logging.getLogger(__name__)

_COL = "worker_dlq"


class JobDLQ:

    def __init__(self, db: Any) -> None:
        self._db = db

    async def ensure_indexes(self) -> None:
        col = self._db[_COL]
        await col.create_index("job_id", unique=True)
        await col.create_index("job_type")
        await col.create_index("status")
        await col.create_index("failed_at")
        await col.create_index("user_id")

    async def enqueue(self, job: Job, error: str, attempt: int) -> None:
        doc = {
            **job.to_dict(),
            "dlq_id":    job.job_id,
            "error":     error,
            "attempt":   attempt,
            "status":    "pending",
            "failed_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution": None,
        }
        try:
            await self._db[_COL].insert_one(doc)
            logger.warning("Job %s (%s) moved to DLQ: %s", job.job_id, job.job_type, error)
        except Exception as exc:
            if "E11000" in str(exc):
                return   # already in DLQ
            raise

    async def list_pending(self, limit: int = 100) -> list[dict]:
        docs = (
            await self._db[_COL]
            .find({"status": "pending"})
            .sort("failed_at", -1)
            .limit(limit)
            .to_list(limit)
        )
        for d in docs:
            d.pop("_id", None)
        return docs

    async def list_all(self, status: str | None = None, limit: int = 100) -> list[dict]:
        filt = {}
        if status:
            filt["status"] = status
        docs = (
            await self._db[_COL]
            .find(filt)
            .sort("failed_at", -1)
            .limit(limit)
            .to_list(limit)
        )
        for d in docs:
            d.pop("_id", None)
        return docs

    async def get(self, job_id: str) -> dict | None:
        doc = await self._db[_COL].find_one({"job_id": job_id})
        if doc:
            doc.pop("_id", None)
        return doc

    async def pending_count(self) -> int:
        return await self._db[_COL].count_documents({"status": "pending"})

    async def mark_resolved(self, job_id: str, resolution: str = "") -> None:
        await self._db[_COL].update_one(
            {"job_id": job_id},
            {"$set": {
                "status":      "resolved",
                "resolved_at": datetime.utcnow().isoformat(),
                "resolution":  resolution,
            }},
        )

    async def delete(self, job_id: str) -> bool:
        r = await self._db[_COL].delete_one({"job_id": job_id})
        return r.deleted_count > 0

    async def get_for_retry(self, limit: int = 50) -> list[dict]:
        docs = (
            await self._db[_COL]
            .find({"status": "pending"})
            .sort("failed_at", 1)
            .limit(limit)
            .to_list(limit)
        )
        for d in docs:
            d.pop("_id", None)
        return docs
