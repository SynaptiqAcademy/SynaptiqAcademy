"""
Queue Abstraction Layer.

Provides QueueBackend (ABC) with a default MongoQueueBackend implementation.
Business logic never depends on queue technology — swap backends by changing
get_queue_backend(backend_type=...) without touching any handler.

Atomic dequeue uses MongoDB's find_one_and_update so multiple workers can
safely compete for the same queue without race conditions.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from .models import Job, JobStatus, Priority, QUEUE_DEFAULT

logger = logging.getLogger(__name__)

# MongoDB collection name
_JOBS_COL = "worker_jobs"


class QueueBackend(ABC):
    """Abstract queue backend. Implementations must be safe for concurrent workers."""

    @abstractmethod
    async def enqueue(self, job: Job) -> None: ...

    @abstractmethod
    async def dequeue(
        self, queue_name: str, worker_id: str, job_types: list[str]
    ) -> Job | None: ...

    @abstractmethod
    async def ack(self, job_id: str, observability: dict | None = None) -> None: ...

    @abstractmethod
    async def nack(
        self, job_id: str, error: str, retry_at: datetime | None = None
    ) -> None: ...

    @abstractmethod
    async def cancel(self, job_id: str) -> bool: ...

    @abstractmethod
    async def get_job(self, job_id: str) -> Job | None: ...

    @abstractmethod
    async def update_checkpoint(self, job_id: str, checkpoint: dict) -> None: ...

    @abstractmethod
    async def list_jobs(
        self,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[Job]: ...

    @abstractmethod
    async def peek(self, queue_name: str, limit: int = 10) -> list[Job]: ...

    @abstractmethod
    async def length(self, queue_name: str) -> int: ...

    @abstractmethod
    async def stats(self) -> dict: ...

    @abstractmethod
    async def requeue(self, job_id: str) -> bool: ...

    @abstractmethod
    async def mark_failed(self, job_id: str, error: str) -> None: ...

    @abstractmethod
    async def reset_stale(self, worker_id: str) -> int: ...


class MongoQueueBackend(QueueBackend):
    """
    MongoDB-backed job queue.

    Atomic dequeue: find_one_and_update with priority ASC + scheduled_at ASC.
    Workers compete safely — only one worker wins the atomic update.
    """

    def __init__(self, db: Any) -> None:
        self._db = db

    async def ensure_indexes(self) -> None:
        col = self._db[_JOBS_COL]
        await col.create_index(
            [("status", 1), ("queue_name", 1), ("priority", 1), ("scheduled_at", 1)]
        )
        await col.create_index("job_id", unique=True)
        await col.create_index("user_id")
        await col.create_index("worker_id")
        await col.create_index("job_type")
        await col.create_index("correlation_id")
        # Auto-expire completed/archived jobs after 30 days
        await col.create_index(
            "completed_at",
            expireAfterSeconds=60 * 60 * 24 * 30,
            sparse=True,
        )

    async def enqueue(self, job: Job) -> None:
        job.status    = JobStatus.QUEUED
        job.queued_at = datetime.utcnow()
        if not job.scheduled_at:
            job.scheduled_at = job.queued_at
        d = job.to_dict()
        try:
            await self._db[_JOBS_COL].insert_one(d)
        except Exception as exc:
            if "E11000" in str(exc):
                logger.debug("Job %s already enqueued (idempotent)", job.job_id)
                return
            raise

    async def dequeue(
        self, queue_name: str, worker_id: str, job_types: list[str]
    ) -> Job | None:
        now = datetime.utcnow()
        filt: dict = {
            "status":      {"$in": [JobStatus.QUEUED.value, JobStatus.RETRYING.value]},
            "queue_name":  queue_name,
            "scheduled_at": {"$lte": now.isoformat()},
        }
        if job_types:
            filt["job_type"] = {"$in": job_types}

        doc = await self._db[_JOBS_COL].find_one_and_update(
            filt,
            {"$set": {
                "status":     JobStatus.RUNNING.value,
                "worker_id":  worker_id,
                "started_at": now.isoformat(),
            }},
            sort=[("priority", 1), ("scheduled_at", 1)],
            return_document=True,
        )
        if doc is None:
            return None
        return Job.from_dict(doc)

    async def ack(self, job_id: str, observability: dict | None = None) -> None:
        now = datetime.utcnow()
        updates: dict = {
            "status":       JobStatus.COMPLETED.value,
            "completed_at": now.isoformat(),
        }
        if observability:
            updates.update(observability)
        await self._db[_JOBS_COL].update_one({"job_id": job_id}, {"$set": updates})

    async def nack(
        self, job_id: str, error: str, retry_at: datetime | None = None
    ) -> None:
        updates: dict = {"last_error": error}
        if retry_at:
            updates["status"]       = JobStatus.RETRYING.value
            updates["next_retry_at"] = retry_at.isoformat()
            updates["scheduled_at"]  = retry_at.isoformat()
        else:
            updates["status"] = JobStatus.FAILED.value
        await self._db[_JOBS_COL].update_one(
            {"job_id": job_id},
            {"$set": updates, "$inc": {"attempt": 1}},
        )

    async def cancel(self, job_id: str) -> bool:
        r = await self._db[_JOBS_COL].update_one(
            {
                "job_id": job_id,
                "status": {"$in": [
                    JobStatus.PENDING.value, JobStatus.QUEUED.value,
                    JobStatus.WAITING.value, JobStatus.RETRYING.value,
                ]},
            },
            {"$set": {"status": JobStatus.CANCELLED.value}},
        )
        return r.modified_count > 0

    async def get_job(self, job_id: str) -> Job | None:
        doc = await self._db[_JOBS_COL].find_one({"job_id": job_id})
        return Job.from_dict(doc) if doc else None

    async def update_checkpoint(self, job_id: str, checkpoint: dict) -> None:
        await self._db[_JOBS_COL].update_one(
            {"job_id": job_id},
            {"$set": {"checkpoint": checkpoint}},
        )

    async def list_jobs(
        self,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[Job]:
        filt: dict = {}
        if status:
            filt["status"] = status
        if queue_name:
            filt["queue_name"] = queue_name
        if job_type:
            filt["job_type"] = job_type
        if user_id:
            filt["user_id"] = user_id
        docs = (
            await self._db[_JOBS_COL]
            .find(filt)
            .sort("scheduled_at", -1)
            .limit(limit)
            .to_list(limit)
        )
        return [Job.from_dict(d) for d in docs]

    async def peek(self, queue_name: str, limit: int = 10) -> list[Job]:
        docs = (
            await self._db[_JOBS_COL]
            .find({"status": JobStatus.QUEUED.value, "queue_name": queue_name})
            .sort([("priority", 1), ("scheduled_at", 1)])
            .limit(limit)
            .to_list(limit)
        )
        return [Job.from_dict(d) for d in docs]

    async def length(self, queue_name: str) -> int:
        return await self._db[_JOBS_COL].count_documents(
            {"status": JobStatus.QUEUED.value, "queue_name": queue_name}
        )

    async def stats(self) -> dict:
        pipeline = [
            {
                "$group": {
                    "_id":   {"status": "$status", "queue_name": "$queue_name"},
                    "count": {"$sum": 1},
                }
            }
        ]
        results = await self._db[_JOBS_COL].aggregate(pipeline).to_list(200)
        out: dict = {}
        for r in results:
            key = f"{r['_id']['queue_name']}:{r['_id']['status']}"
            out[key] = r["count"]
        return out

    async def requeue(self, job_id: str) -> bool:
        now = datetime.utcnow()
        r = await self._db[_JOBS_COL].update_one(
            {
                "job_id": job_id,
                "status": {"$in": [JobStatus.FAILED.value, JobStatus.CANCELLED.value]},
            },
            {"$set": {
                "status":       JobStatus.QUEUED.value,
                "queued_at":    now.isoformat(),
                "scheduled_at": now.isoformat(),
                "last_error":   None,
                "worker_id":    None,
                "attempt":      0,
            }},
        )
        return r.modified_count > 0

    async def mark_failed(self, job_id: str, error: str) -> None:
        await self._db[_JOBS_COL].update_one(
            {"job_id": job_id},
            {"$set": {
                "status":     JobStatus.FAILED.value,
                "last_error": error,
            }},
        )

    async def mark_waiting(self, job_id: str) -> None:
        """Mark job as WAITING (dependency not yet satisfied)."""
        await self._db[_JOBS_COL].update_one(
            {"job_id": job_id},
            {"$set": {"status": JobStatus.WAITING.value}},
        )

    async def get_waiting_jobs(self) -> list[Job]:
        docs = (
            await self._db[_JOBS_COL]
            .find({"status": JobStatus.WAITING.value})
            .limit(200)
            .to_list(200)
        )
        return [Job.from_dict(d) for d in docs]

    async def reset_stale(self, worker_id: str) -> int:
        """Re-queue RUNNING jobs abandoned by a dead worker."""
        now = datetime.utcnow()
        r = await self._db[_JOBS_COL].update_many(
            {"status": JobStatus.RUNNING.value, "worker_id": worker_id},
            {"$set": {
                "status":       JobStatus.QUEUED.value,
                "worker_id":    None,
                "scheduled_at": now.isoformat(),
            }},
        )
        return r.modified_count


# ── Factory ───────────────────────────────────────────────────────────────────

def get_queue_backend(db: Any, backend_type: str = "mongo") -> QueueBackend:
    """
    Return a queue backend by type.

    Defaults to MongoDB. Future: "redis", "celery", "sqs", "rabbitmq".
    """
    if backend_type == "mongo":
        return MongoQueueBackend(db)
    raise NotImplementedError(
        f"Queue backend '{backend_type}' not yet implemented. "
        f"Extend QueueBackend and register here."
    )
