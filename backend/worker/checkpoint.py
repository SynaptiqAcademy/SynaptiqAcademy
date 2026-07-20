"""
Checkpoint Engine — persist mid-execution state so jobs can resume after crash.

Checkpoints are stored directly in the job document's `checkpoint` field.
After each meaningful step the handler calls save(); on restart load()
retrieves the last known good state so work isn't repeated.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CheckpointEngine:

    def __init__(self, queue_backend: Any) -> None:
        self._queue = queue_backend

    async def save(self, job_id: str, checkpoint: dict) -> None:
        """Persist checkpoint for a running job."""
        try:
            await self._queue.update_checkpoint(job_id, checkpoint)
            logger.debug("Checkpoint saved for job %s: keys=%s", job_id, list(checkpoint))
        except Exception as exc:
            logger.error("Checkpoint save error for %s: %s", job_id, exc)

    async def load(self, job_id: str) -> dict:
        """Load the last checkpoint for a job (empty dict if none)."""
        try:
            job = await self._queue.get_job(job_id)
            return job.checkpoint if job else {}
        except Exception as exc:
            logger.error("Checkpoint load error for %s: %s", job_id, exc)
            return {}

    async def clear(self, job_id: str) -> None:
        """Clear checkpoint after successful completion."""
        try:
            await self._queue.update_checkpoint(job_id, {})
        except Exception:
            pass
