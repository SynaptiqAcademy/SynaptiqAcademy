"""
Mission Scheduler — manage recurring/scheduled missions.

Stores schedule templates in ara_schedules.
Actual execution is triggered by /api/ara/scheduler/run endpoint
(or a background process calling check_due()).

Supported intervals: daily, weekly, monthly (simple — no full cron parser).

NOTE: The enterprise scheduler at ara/engine/scheduler.py supersedes this for
new code. This module is retained for backward-compatibility with ara/__init__.py
re-exports and existing callers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from . import mission_store

logger = logging.getLogger("ara.scheduler")

Interval = Literal["daily", "weekly", "monthly"]

_INTERVAL_HOURS: dict[str, int] = {
    "daily":   24,
    "weekly":  168,
    "monthly": 720,
}


async def create_schedule(db, user_id: str, title: str, description: str,
                          mission_type: str, autonomy_level: int,
                          interval: Interval, params: dict) -> str:
    schedule = {
        "title":          title,
        "description":    description,
        "mission_type":   mission_type,
        "autonomy_level": autonomy_level,
        "interval":       interval,
        "params":         params,
        "next_run_at":    datetime.now(timezone.utc),
    }
    return await mission_store.create_schedule(db, user_id, schedule)


async def check_due(db, user_id: str) -> list[dict]:
    """Return schedules that are due to run (next_run_at <= now)."""
    now       = datetime.now(timezone.utc)
    schedules = await mission_store.list_schedules(db, user_id)
    due       = []
    for s in schedules:
        if not s.get("active"):
            continue
        next_run = s.get("next_run_at")
        if isinstance(next_run, str):
            from datetime import datetime as _dt
            next_run = _dt.fromisoformat(next_run.replace("Z", "+00:00"))
        if next_run and next_run <= now:
            due.append(s)
    return due


async def mark_run(db, schedule_id: str, interval: str) -> None:
    """Advance next_run_at by the interval after a successful trigger."""
    hours    = _INTERVAL_HOURS.get(interval, 24)
    next_run = datetime.now(timezone.utc) + timedelta(hours=hours)
    from bson import ObjectId
    await db["ara_schedules"].update_one(
        {"_id": ObjectId(schedule_id)},
        {"$set": {"last_run": datetime.now(timezone.utc), "next_run_at": next_run}},
    )
