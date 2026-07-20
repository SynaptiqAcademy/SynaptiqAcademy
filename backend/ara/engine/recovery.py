"""
Recovery Engine — restores interrupted missions after server restart or worker crash.

On startup:
  1. Find all missions with status = running | retrying where heartbeat > EXPIRY_S ago
  2. Force-release their distributed locks (the old worker is gone)
  3. Requeue them in the execution queue (they'll resume from checkpoint)

On heartbeat expiry (called by HeartbeatMonitor):
  1. Find missions with stale heartbeat
  2. Same recovery procedure

The worker skips already-completed steps via the CheckpointEngine — so
recovery is always safe to run, even if the worker never actually died.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from repo.shim import make_db_proxy
from events import get_bus, HeartbeatExpired
from .locking import get_lock
from .queue import Priority

logger = logging.getLogger("ara.engine.recovery")

HEARTBEAT_EXPIRY_S = 60   # missions with heartbeat older than this are considered orphaned


class RecoveryEngine:

    async def startup_recovery(self, db, queue) -> int:
        """
        Run on server startup. Returns count of missions recovered.
        Safe to call multiple times (idempotent).
        """
        db = make_db_proxy(db, system=True)
        orphaned = await self.find_orphaned_missions(db)
        count = 0
        for mission in orphaned:
            recovered = await self.recover_mission(db, queue, mission["_id"])
            if recovered:
                count += 1

        if count:
            logger.info("Startup recovery: requeued %d orphaned missions", count)
        else:
            logger.info("Startup recovery: no orphaned missions found")
        return count

    async def find_orphaned_missions(self, db) -> list[dict]:
        """
        Find missions stuck in running/retrying state with an expired heartbeat.
        Also find missions stuck in 'queued' state for > 5 minutes (worker died
        after dequeue but before lock acquisition).
        """
        # AUTH-BUG-003: this runs on every heartbeat tick (every 15s). During a
        # real Mongo outage it was observed retrying continuously, each attempt
        # paying the full server-selection timeout and competing with real user
        # requests (including login) for Motor's executor thread pool. Skip the
        # attempt entirely while the circuit breaker already knows Mongo is down.
        from db import is_db_down, mark_db_down
        if is_db_down():
            logger.debug("find_orphaned_missions skipped — circuit breaker open")
            return []
        db = make_db_proxy(db, system=True)
        from datetime import timedelta
        now     = datetime.now(timezone.utc)
        expired = now - timedelta(seconds=HEARTBEAT_EXPIRY_S)
        stuck_queued = now - timedelta(minutes=5)

        orphaned = []
        try:
            # Stuck in running/retrying with expired heartbeat
            cursor = db["ara_missions"].find(
                {
                    "status": {"$in": ["running", "retrying"]},
                    "$or": [
                        {"heartbeat": {"$lt": expired}},
                        {"heartbeat": None},
                    ],
                },
                {"_id": 1, "user_id": 1, "status": 1, "heartbeat": 1, "retry_count": 1},
            )
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                orphaned.append(doc)

            # Stuck in queued (dequeued but lock never acquired)
            cursor2 = db["ara_missions"].find(
                {
                    "status": "queued",
                    "queued_at": {"$lt": stuck_queued},
                },
                {"_id": 1, "user_id": 1, "status": 1, "queued_at": 1, "retry_count": 1},
            )
            async for doc in cursor2:
                doc["_id"] = str(doc["_id"])
                orphaned.append(doc)

        except Exception as exc:
            mark_db_down(exc)
            logger.error("find_orphaned_missions failed: %s", exc)

        return orphaned

    async def recover_mission(self, db, queue, mission_id: str) -> bool:
        """
        Recover a single orphaned mission: release lock, clear worker, requeue.
        Returns True on success.
        """
        db = make_db_proxy(db, system=True)
        try:
            from ara import mission_store

            # Force-release the distributed lock (old worker is gone)
            await get_lock().force_release(mission_id)

            # Emit heartbeat_expired event
            await get_bus().publish(HeartbeatExpired(
                aggregate_id=mission_id,
                payload={"recovery": "startup"},
            ))

            # Update mission: clear worker, reset to queued
            await mission_store.update_mission(db, mission_id, {
                "worker_id":      None,
                "execution_token": None,
                "heartbeat":      None,
                "status":         "queued",
                "queued_at":      datetime.now(timezone.utc),
            })
            await mission_store.append_log(
                db, mission_id, "recovery_engine", "recovered",
                "Mission recovered after worker crash/restart. Resuming from checkpoint.",
            )
            # Requeue with HIGH priority (it was already in progress)
            await queue.enqueue(mission_id, priority=Priority.HIGH)
            logger.info("Mission %s recovered and requeued", mission_id)
            return True

        except Exception as exc:
            logger.error("recover_mission failed (mission=%s): %s", mission_id, exc)
            return False


# ── Singleton ──────────────────────────────────────────────────────────────────

_recovery: RecoveryEngine | None = None


def get_recovery_engine() -> RecoveryEngine:
    global _recovery
    if _recovery is None:
        _recovery = RecoveryEngine()
    return _recovery
