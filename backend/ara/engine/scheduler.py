"""
Enterprise Mission Scheduler — first-class scheduled execution.

Replaces the stub ara/scheduler.py (which had check_due() with zero callers).
The scheduler's tick() IS called by HeartbeatMonitor on its regular cadence.

Supported schedule types:
  interval  — every N hours (daily / weekly / monthly / custom)
  cron      — cron expression (future: requires croniter)
  trigger   — event-driven (ORCID sync, publication, grant submission)
  once      — run at a specific datetime

Schedule stored in ara_schedules collection (existing collection, backward-compat).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from events import get_bus, MissionCreated

logger = logging.getLogger("ara.engine.scheduler")

_SC = "ara_schedules"

_INTERVAL_HOURS: dict[str, int] = {
    "daily":      24,
    "weekly":     168,
    "monthly":    720,
    "quarterly":  2160,
    "hourly":     1,
}


class MissionScheduler:
    """
    Polls ara_schedules and creates+enqueues missions when due.
    Called by HeartbeatMonitor.tick() (not a separate loop).
    """

    async def tick(self, db, queue) -> int:
        """
        Create missions for all schedules that are now due.
        Returns count of missions created.
        """
        due = await self.get_due_schedules(db)
        count = 0
        for schedule in due:
            try:
                mission_id = await self._create_scheduled_mission(db, schedule)
                if mission_id:
                    await queue.enqueue(mission_id, priority=5)
                    await self._advance(db, schedule["_id"], schedule.get("interval", "daily"))
                    count += 1
            except Exception as exc:
                logger.error("Scheduler tick error (schedule %s): %s", schedule.get("_id"), exc)
        return count

    async def get_due_schedules(self, db) -> list[dict]:
        """Return schedules whose next_run_at is in the past."""
        now = datetime.now(timezone.utc)
        try:
            docs = await db[_SC].find(
                {"active": True, "next_run_at": {"$lte": now}},
                {"_id": 1, "user_id": 1, "title": 1, "description": 1,
                 "mission_type": 1, "autonomy_level": 1, "params": 1,
                 "interval": 1, "next_run_at": 1},
            ).to_list(50)
            for d in docs:
                d["_id"] = str(d["_id"])
            return docs
        except Exception as exc:
            logger.debug("get_due_schedules failed: %s", exc)
            return []

    async def create(
        self,
        db,
        user_id:       str,
        title:         str,
        description:   str,
        mission_type:  str,
        autonomy_level: int,
        interval:      str,
        params:        dict,
        run_after:     datetime | None = None,
    ) -> str:
        """Create a new schedule (thin wrapper kept for backward compat with ara/scheduler.py)."""
        from ara import mission_store
        schedule = {
            "title":          title,
            "description":    description,
            "mission_type":   mission_type,
            "autonomy_level": autonomy_level,
            "interval":       interval,
            "params":         params,
            "next_run_at":    run_after or datetime.now(timezone.utc),
        }
        return await mission_store.create_schedule(db, user_id, schedule)

    async def cancel(self, db, schedule_id: str, user_id: str) -> bool:
        from ara import mission_store
        return await mission_store.delete_schedule(db, schedule_id, user_id)

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _create_scheduled_mission(self, db, schedule: dict) -> str | None:
        """Instantiate a mission from a schedule template."""
        from ara import mission_store
        try:
            mission_id = await mission_store.create_mission(
                db,
                user_id=schedule["user_id"],
                title=f"Scheduled: {schedule['title']}",
                description=schedule.get("description", ""),
                autonomy_level=schedule.get("autonomy_level", 1),
                mission_type=schedule.get("mission_type", "general"),
                params={**schedule.get("params", {}), "scheduler_id": schedule["_id"]},
            )
            # Immediate plan generation (planner runs synchronously here)
            from ara.mission_planner import generate_plan
            await generate_plan(
                db, mission_id,
                description=schedule.get("description", ""),
                mission_type=schedule.get("mission_type", "general"),
                params=schedule.get("params", {}),
                user_context={},
            )
            await mission_store.update_mission(db, mission_id, {
                "status":       "queued",
                "scheduler_id": schedule["_id"],
            })
            await get_bus().publish(MissionCreated(
                aggregate_id=mission_id,
                payload={"source": "scheduler", "schedule_id": schedule["_id"]},
            ))
            logger.info("Scheduled mission created: %s from schedule %s", mission_id, schedule["_id"])
            return mission_id
        except Exception as exc:
            logger.error("_create_scheduled_mission failed: %s", exc)
            return None

    async def _advance(self, db, schedule_id: str, interval: str) -> None:
        """Move next_run_at forward by the interval."""
        hours    = _INTERVAL_HOURS.get(interval, 24)
        next_run = datetime.now(timezone.utc) + timedelta(hours=hours)
        try:
            from bson import ObjectId
            await db[_SC].update_one(
                {"_id": ObjectId(schedule_id)},
                {"$set": {"last_run": datetime.now(timezone.utc), "next_run_at": next_run}},
            )
        except Exception as exc:
            logger.debug("Schedule advance failed: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────────

_sched: MissionScheduler | None = None


def get_scheduler() -> MissionScheduler:
    global _sched
    if _sched is None:
        _sched = MissionScheduler()
    return _sched
