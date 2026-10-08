"""Cross-process coordination on MongoDB: leases and run-once job keys.

Production runs several worker processes (gunicorn WORKERS) and may run
several replicas. Anything scheduled must run in exactly one of them, and an
email job must never run twice for the same period. MongoDB is the one
dependency every process already shares, so coordination lives there (Redis is
optional and may be absent).

  LeaseLock     — one holder at a time, with expiry. The holder renews it; if
                  the holder dies, the lease expires and another process takes
                  over on its next attempt.
  run_once()    — claims "<job>:<window>" with a unique insert before a job
                  runs. A second claim for the same window (another scheduler,
                  a retry, a restart mid-window) is refused, so the job body
                  runs at most once per window.
"""
from __future__ import annotations

import logging
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional

from pymongo.errors import DuplicateKeyError

logger = logging.getLogger("synaptiq.coordination")

LEASES = "coordination_leases"
JOB_RUNS = "job_runs"
_JOB_RUN_RETENTION_DAYS = 45

_PROCESS_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"


def process_id() -> str:
    return _PROCESS_ID


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _db(db=None):
    if db is not None:
        return db
    from db import get_db
    return get_db()


async def ensure_indexes(db=None) -> None:
    d = _db(db)
    await d[LEASES].create_index("expires_at")
    await d[JOB_RUNS].create_index("started_at", expireAfterSeconds=_JOB_RUN_RETENTION_DAYS * 86400)


class LeaseLock:
    """A named lease. acquire() and renew() are the same atomic operation:
    take the lease if it is free, expired, or already ours."""

    def __init__(self, name: str, ttl_seconds: int = 300, db=None, holder: Optional[str] = None):
        self.name = name
        self.ttl = ttl_seconds
        self._db = db
        self.holder = holder or _PROCESS_ID

    async def acquire(self) -> bool:
        d = _db(self._db)
        now = _now()
        try:
            doc = await d[LEASES].find_one_and_update(
                {"_id": self.name, "$or": [{"expires_at": {"$lte": now}}, {"holder": self.holder}]},
                {"$set": {"holder": self.holder, "expires_at": now + timedelta(seconds=self.ttl),
                          "renewed_at": now}},
                upsert=True, return_document=True,
            )
        except DuplicateKeyError:
            return False  # held by someone else and not expired
        return bool(doc) and doc.get("holder") == self.holder

    renew = acquire

    async def release(self) -> None:
        await _db(self._db)[LEASES].delete_one({"_id": self.name, "holder": self.holder})

    async def holder_of(self) -> Optional[str]:
        doc = await _db(self._db)[LEASES].find_one({"_id": self.name})
        if not doc or doc.get("expires_at") is None:
            return None
        exp = doc["expires_at"]
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return doc.get("holder") if exp > _now() else None


async def claim_run(job_id: str, window: str, db=None) -> bool:
    """True if this process may run job_id for this window (first claimant)."""
    try:
        await _db(db)[JOB_RUNS].insert_one({
            "_id": f"{job_id}:{window}", "job_id": job_id, "window": window,
            "holder": _PROCESS_ID, "status": "running", "started_at": _now(),
        })
        return True
    except DuplicateKeyError:
        return False


async def finish_run(job_id: str, window: str, status: str, error: str = "", db=None) -> None:
    await _db(db)[JOB_RUNS].update_one(
        {"_id": f"{job_id}:{window}"},
        {"$set": {"status": status, "finished_at": _now(), "error": error[:500]}},
    )


async def run_once(job_id: str, window: str, fn: Callable[[], Awaitable[Any]], db=None,
                   alert_on_failure: bool = True) -> Optional[str]:
    """Run fn() at most once per (job_id, window) across all processes.
    Returns "skipped", "completed" or "failed"."""
    if not await claim_run(job_id, window, db=db):
        logger.info("[coordination] %s for %s already claimed — skipping", job_id, window)
        return "skipped"
    try:
        await fn()
    except Exception as exc:
        logger.exception("[coordination] job %s (%s) failed", job_id, window)
        await finish_run(job_id, window, "failed", type(exc).__name__, db=db)
        if alert_on_failure:
            from services.alerts import send_alert
            await send_alert("job_failed", f"Scheduled job {job_id} failed for {window}: {type(exc).__name__}",
                             severity="error", dedup_key=f"job_failed:{job_id}:{window}")
        return "failed"
    await finish_run(job_id, window, "completed", db=db)
    return "completed"


def day_window(now: Optional[datetime] = None) -> str:
    return (now or _now()).strftime("%Y-%m-%d")


def iso_week_window(now: Optional[datetime] = None) -> str:
    y, w, _ = (now or _now()).isocalendar()
    return f"{y}-W{w:02d}"


def hour_window(now: Optional[datetime] = None, every_hours: int = 1) -> str:
    n = now or _now()
    return f"{n.strftime('%Y-%m-%d')}T{(n.hour // every_hours) * every_hours:02d}"
