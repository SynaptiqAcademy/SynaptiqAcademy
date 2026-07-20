"""
Enterprise Scheduler — drives all time-based job execution.

Uses APScheduler (already installed) for reliable cron/interval scheduling
with MongoDB as the persistence store for schedule definitions.

Modes:
  once            — run at a specific datetime (idempotent: won't re-run)
  recurring       — run every interval_s seconds
  cron            — run on a cron expression (uses APScheduler CronTrigger)
  event_triggered — subscribed via EnterpriseEventBus; enqueues on matching event

The Scheduler's internal APScheduler instance manages timezone-aware triggers.
All schedule state (enabled, last_run_at, next_run_at, run_count) persists to
MongoDB so schedules survive server restarts.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron     import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date     import DateTrigger

from .models import Job, Priority, Schedule, QUEUE_DEFAULT

logger = logging.getLogger(__name__)

_COL       = "worker_schedules"
_LOCK_COL  = "worker_schedule_locks"


class Scheduler:
    """
    Manages all scheduled job definitions and drives APScheduler.

    Usage:
        scheduler = Scheduler(db, queue_backend)
        await scheduler.start()

        # Schedule a recurring ORCID sync every Sunday at 02:00 UTC
        sid = await scheduler.add_cron(
            job_type="orcid.weekly_sync",
            payload={},
            cron_expr="0 2 * * 0",
            schedule_id="orcid_weekly",
        )
    """

    def __init__(self, db: Any, queue_backend: Any) -> None:
        self._db      = db
        self._queue   = queue_backend
        self._aps     = AsyncIOScheduler(timezone="UTC")
        self._started = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        await self._ensure_indexes()
        await self._restore_from_db()
        self._aps.start()
        self._started = True
        logger.info("Scheduler started")

    async def stop(self) -> None:
        if self._started:
            self._aps.shutdown(wait=False)
            self._started = False
        logger.info("Scheduler stopped")

    # ── Public API ────────────────────────────────────────────────────────────

    async def add_once(
        self,
        job_type: str,
        payload: dict,
        run_at: datetime,
        *,
        schedule_id: str | None = None,
        priority: Priority = Priority.NORMAL,
        queue_name: str = QUEUE_DEFAULT,
        max_attempts: int = 3,
        user_id: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        sid = schedule_id or str(uuid.uuid4())
        sched = Schedule(
            schedule_id=sid,
            job_type=job_type,
            payload=payload,
            mode="once",
            run_at=run_at,
            priority=priority,
            queue_name=queue_name,
            max_attempts=max_attempts,
            user_id=user_id,
            tags=tags or [],
        )
        sched.next_run_at = run_at
        await self._persist(sched)
        self._register_once(sched)
        return sid

    async def add_cron(
        self,
        job_type: str,
        payload: dict,
        cron_expr: str,
        *,
        schedule_id: str | None = None,
        timezone: str = "UTC",
        priority: Priority = Priority.NORMAL,
        queue_name: str = QUEUE_DEFAULT,
        max_attempts: int = 3,
        user_id: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        sid = schedule_id or str(uuid.uuid4())
        sched = Schedule(
            schedule_id=sid,
            job_type=job_type,
            payload=payload,
            mode="cron",
            cron_expr=cron_expr,
            timezone=timezone,
            priority=priority,
            queue_name=queue_name,
            max_attempts=max_attempts,
            user_id=user_id,
            tags=tags or [],
        )
        await self._persist(sched)
        self._register_cron(sched)
        return sid

    async def add_recurring(
        self,
        job_type: str,
        payload: dict,
        interval_s: int,
        *,
        schedule_id: str | None = None,
        priority: Priority = Priority.NORMAL,
        queue_name: str = QUEUE_DEFAULT,
        max_attempts: int = 3,
        user_id: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        sid = schedule_id or str(uuid.uuid4())
        sched = Schedule(
            schedule_id=sid,
            job_type=job_type,
            payload=payload,
            mode="recurring",
            interval_s=interval_s,
            priority=priority,
            queue_name=queue_name,
            max_attempts=max_attempts,
            user_id=user_id,
            tags=tags or [],
        )
        await self._persist(sched)
        self._register_interval(sched)
        return sid

    async def pause(self, schedule_id: str) -> None:
        self._aps.pause_job(schedule_id)
        await self._db[_COL].update_one(
            {"schedule_id": schedule_id}, {"$set": {"enabled": False}}
        )

    async def resume(self, schedule_id: str) -> None:
        self._aps.resume_job(schedule_id)
        await self._db[_COL].update_one(
            {"schedule_id": schedule_id}, {"$set": {"enabled": True}}
        )

    async def remove(self, schedule_id: str) -> None:
        try:
            self._aps.remove_job(schedule_id)
        except Exception:
            pass
        await self._db[_COL].delete_one({"schedule_id": schedule_id})

    async def list_schedules(self) -> list[Schedule]:
        docs = await self._db[_COL].find({}).to_list(500)
        return [Schedule.from_dict(d) for d in docs]

    async def get(self, schedule_id: str) -> Schedule | None:
        doc = await self._db[_COL].find_one({"schedule_id": schedule_id})
        return Schedule.from_dict(doc) if doc else None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _make_enqueue_fn(self, sched: Schedule):
        """Return a sync callable that APScheduler will call on trigger."""
        db    = self._db
        queue = self._queue
        s     = sched

        def _enqueue():
            asyncio.ensure_future(_async_enqueue(db, queue, s))

        async def _async_enqueue(db, queue, s: Schedule):
            # Distributed dedup: prevent duplicate fires when multiple instances run.
            # Uses an atomic MongoDB insert to claim a per-window lock.
            # Only the first instance that wins the insert proceeds; others skip.
            if s.mode in ("cron", "recurring"):
                window_s = max(30, (s.interval_s or 60) // 2) if s.mode == "recurring" else 30
                bucket   = int(datetime.utcnow().timestamp() / window_s)
                try:
                    await db[_LOCK_COL].insert_one({
                        "schedule_id": s.schedule_id,
                        "bucket":      bucket,
                        "fired_at":    datetime.utcnow(),
                    })
                except Exception as exc:
                    if "E11000" in str(exc) or "duplicate key" in str(exc).lower():
                        logger.debug(
                            "Scheduler dedup: skipping %s bucket=%d (fired by another instance)",
                            s.schedule_id, bucket,
                        )
                        return
                    # Non-dedup error (e.g. transient MongoDB failure) — proceed anyway
                    logger.warning("Scheduler dedup check failed for %s: %s", s.schedule_id, exc)

            job = Job(
                job_type=s.job_type,
                payload=s.payload,
                priority=s.priority,
                queue_name=s.queue_name,
                max_attempts=s.max_attempts,
                user_id=s.user_id,
                tags=list(s.tags),
                correlation_id=s.schedule_id,
            )
            try:
                await queue.enqueue(job)
                now = datetime.utcnow()
                await db[_COL].update_one(
                    {"schedule_id": s.schedule_id},
                    {"$set": {"last_run_at": now.isoformat()}, "$inc": {"run_count": 1}},
                )
                logger.debug("Scheduler enqueued %s (schedule=%s)", s.job_type, s.schedule_id)
            except Exception as exc:
                logger.error("Scheduler enqueue error for %s: %s", s.schedule_id, exc)

        return _enqueue

    def _register_once(self, sched: Schedule) -> None:
        if not sched.run_at:
            return
        self._aps.add_job(
            self._make_enqueue_fn(sched),
            trigger=DateTrigger(run_date=sched.run_at, timezone="UTC"),
            id=sched.schedule_id,
            replace_existing=True,
        )

    def _register_cron(self, sched: Schedule) -> None:
        if not sched.cron_expr:
            return
        parts = sched.cron_expr.split()
        # cron: minute hour day month day_of_week
        minute, hour, day, month, day_of_week = (parts + ["*"] * 5)[:5]
        self._aps.add_job(
            self._make_enqueue_fn(sched),
            trigger=CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=sched.timezone,
            ),
            id=sched.schedule_id,
            replace_existing=True,
        )

    def _register_interval(self, sched: Schedule) -> None:
        if not sched.interval_s:
            return
        self._aps.add_job(
            self._make_enqueue_fn(sched),
            trigger=IntervalTrigger(seconds=sched.interval_s, timezone="UTC"),
            id=sched.schedule_id,
            replace_existing=True,
        )

    async def _persist(self, sched: Schedule) -> None:
        await self._db[_COL].update_one(
            {"schedule_id": sched.schedule_id},
            {"$set": sched.to_dict()},
            upsert=True,
        )

    async def _restore_from_db(self) -> None:
        """Re-register all enabled schedules after a server restart."""
        docs = await self._db[_COL].find({"enabled": True}).to_list(500)
        for doc in docs:
            sched = Schedule.from_dict(doc)
            try:
                if sched.mode == "once":
                    if sched.run_at and sched.run_at > datetime.utcnow():
                        self._register_once(sched)
                elif sched.mode == "cron":
                    self._register_cron(sched)
                elif sched.mode == "recurring":
                    self._register_interval(sched)
            except Exception as exc:
                logger.warning("Failed to restore schedule %s: %s", sched.schedule_id, exc)
        logger.info("Scheduler restored %d schedules from DB", len(docs))

    async def _ensure_indexes(self) -> None:
        col = self._db[_COL]
        await col.create_index("schedule_id", unique=True)
        await col.create_index("job_type")
        await col.create_index("mode")
        await col.create_index("enabled")

        # Distributed dedup lock index: unique per (schedule, time-bucket).
        # TTL index auto-removes locks after 1 hour so the collection stays small.
        lock_col = self._db[_LOCK_COL]
        await lock_col.create_index(
            [("schedule_id", 1), ("bucket", 1)], unique=True
        )
        await lock_col.create_index(
            "fired_at", expireAfterSeconds=3600
        )
