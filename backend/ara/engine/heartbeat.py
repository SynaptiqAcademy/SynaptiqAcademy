"""
Heartbeat Monitor — detects stale workers and triggers recovery.

Every running mission is expected to update its heartbeat every
HEARTBEAT_INTERVAL_S seconds. If HEARTBEAT_EXPIRY_S passes without
an update, the worker is assumed crashed and the mission is recovered.

The monitor also drives:
  - Delayed queue promotion (ara:queue:delayed → ara:queue:ready)
  - Scheduler ticks (check for due scheduled missions)

This is the single background clock for the ARA engine.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("ara.engine.heartbeat")

HEARTBEAT_INTERVAL_S = 10   # worker updates heartbeat this often
HEARTBEAT_EXPIRY_S   = 60   # after this many seconds without HB, mission is orphaned
MONITOR_TICK_S       = 15   # how often the monitor checks for stale missions
SCHEDULER_TICK_S     = 60   # how often we check for due scheduled missions


class HeartbeatMonitor:
    """
    Background loop that:
      1. Every MONITOR_TICK_S:  find stale missions → recover them
      2. Every SCHEDULER_TICK_S: tick the mission scheduler
    """

    def __init__(self):
        self._running  = False
        self._task: asyncio.Task | None = None
        self._tick_count = 0

    async def start(self, db, queue) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(db, queue))
        logger.info("HeartbeatMonitor started (tick=%ds expiry=%ds)", MONITOR_TICK_S, HEARTBEAT_EXPIRY_S)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HeartbeatMonitor stopped")

    async def update(self, mission_id: str, db) -> None:
        """Called by the worker every HEARTBEAT_INTERVAL_S during execution."""
        try:
            from ara import mission_store
            await mission_store.update_heartbeat(db, mission_id)
        except Exception as exc:
            logger.debug("Heartbeat update failed for mission %s: %s", mission_id, exc)

    async def check_and_recover(self, db, queue) -> list[str]:
        """Scan for stale missions, recover them. Returns list of recovered mission IDs."""
        from .recovery import get_recovery_engine
        orphaned  = await get_recovery_engine().find_orphaned_missions(db)
        recovered = []
        for mission in orphaned:
            ok = await get_recovery_engine().recover_mission(db, queue, mission["_id"])
            if ok:
                recovered.append(mission["_id"])
        return recovered

    # ── Background loop ───────────────────────────────────────────────────────

    async def _loop(self, db, queue) -> None:
        while self._running:
            try:
                await asyncio.sleep(MONITOR_TICK_S)
                self._tick_count += 1

                # Recover stale missions
                recovered = await self.check_and_recover(db, queue)
                if recovered:
                    logger.info("HeartbeatMonitor recovered %d missions: %s", len(recovered), recovered)

                # Scheduler tick (less frequent)
                if self._tick_count % (SCHEDULER_TICK_S // MONITOR_TICK_S) == 0:
                    from .scheduler import get_scheduler
                    n = await get_scheduler().tick(db, queue)
                    if n:
                        logger.info("Scheduler enqueued %d missions", n)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("HeartbeatMonitor tick error: %s", exc)
                # Never die — just log and continue


# ── Singleton ──────────────────────────────────────────────────────────────────

_monitor: HeartbeatMonitor | None = None


def get_heartbeat_monitor() -> HeartbeatMonitor:
    global _monitor
    if _monitor is None:
        _monitor = HeartbeatMonitor()
    return _monitor
