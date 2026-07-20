"""Background indexing queue — processes IndexingJob items via asyncio queue."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from services.knowledge.models import IndexingJob
from services.knowledge.telemetry import get_knowledge_telemetry

if TYPE_CHECKING:
    from services.knowledge.ingestion.pipeline import IngestionPipeline

logger = logging.getLogger(__name__)

_MAX_QUEUE = 500


class BackgroundIndexer:
    """Single-worker async queue for document indexing.

    Multiple documents can be queued; they are processed one at a time to avoid
    overwhelming the embedding service. Increase concurrency by running multiple
    workers if throughput is a bottleneck.
    """

    def __init__(self, pipeline: "IngestionPipeline", db, max_queue: int = _MAX_QUEUE) -> None:
        self._pipeline = pipeline
        self._db = db
        self._queue: asyncio.Queue[IndexingJob] = asyncio.Queue(maxsize=max_queue)
        self._worker_task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._worker_task = loop.create_task(self._worker())
                logger.info("BackgroundIndexer started")
            except RuntimeError:
                # No running event loop (e.g. unit tests); worker won't run
                self._running = False

    def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            logger.info("BackgroundIndexer stopped")

    async def enqueue(self, job: IndexingJob) -> None:
        """Add a job to the queue. Raises QueueFull if at capacity."""
        if self._queue.full():
            raise RuntimeError("Indexing queue is full; retry later")
        await self._queue.put(job)
        get_knowledge_telemetry().set_queue_size(self._queue.qsize())

        # Mark document as indexing in MongoDB
        await self._db["knowledge_documents"].update_one(
            {"_id": job.document_id},
            {"$set": {"status": "indexing", "error": ""}},
            upsert=True,
        )

    def queue_size(self) -> int:
        return self._queue.qsize()

    async def _worker(self) -> None:
        logger.info("Indexing worker running")
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                doc = await self._pipeline.ingest(job)
                # Persist document record
                await self._db["knowledge_documents"].update_one(
                    {"_id": job.document_id},
                    {"$set": doc.to_dict()},
                    upsert=True,
                )
                logger.info("Indexed document %s (%s chunks)", job.document_id, doc.chunk_count)
            except Exception as exc:
                logger.error("Failed to index %s: %s", job.filename, exc)
                await self._db["knowledge_documents"].update_one(
                    {"_id": job.document_id},
                    {"$set": {"status": "failed", "error": str(exc)[:500]}},
                    upsert=True,
                )
                get_knowledge_telemetry().record_failed()
            finally:
                self._queue.task_done()
                get_knowledge_telemetry().set_queue_size(self._queue.qsize())
