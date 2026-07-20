"""
Enterprise Mission Execution Engine.

Entry point for server startup:

    from ara.engine import start_engine, stop_engine
    asyncio.create_task(start_engine(db))

Singletons accessible from anywhere:

    from ara.engine import get_queue, get_worker, get_checkpoint, get_lock
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("ara.engine")


async def start_engine(db) -> None:
    """
    Start the complete ARA execution engine:
      1. Startup recovery (recover missions interrupted by previous restart)
      2. Worker loop (pull from queue, execute, checkpoint)
      3. Heartbeat monitor (detect stale workers, drive scheduler)
    """
    from .queue    import get_queue
    from .recovery import get_recovery_engine
    from .worker   import get_worker
    from .heartbeat import get_heartbeat_monitor

    queue   = get_queue()
    worker  = get_worker()
    monitor = get_heartbeat_monitor()

    logger.info("ARA Engine starting...")

    # Phase 1: startup recovery
    try:
        recovered = await get_recovery_engine().startup_recovery(db, queue)
        logger.info("Startup recovery complete: %d missions requeued", recovered)
    except Exception as exc:
        logger.error("Startup recovery error (non-fatal): %s", exc)

    # Phase 2: start worker
    try:
        await worker.start(db)
    except Exception as exc:
        logger.error("Worker start error (non-fatal): %s", exc)

    # Phase 3: start heartbeat monitor
    try:
        await monitor.start(db, queue)
    except Exception as exc:
        logger.error("HeartbeatMonitor start error (non-fatal): %s", exc)

    logger.info("ARA Engine running (worker=%s)", worker.worker_id)


async def stop_engine() -> None:
    """Graceful shutdown: stop worker and monitor."""
    from .worker    import get_worker
    from .heartbeat import get_heartbeat_monitor

    logger.info("ARA Engine stopping...")
    try:
        await get_worker().stop()
    except Exception as exc:
        logger.debug("Worker stop error: %s", exc)
    try:
        await get_heartbeat_monitor().stop()
    except Exception as exc:
        logger.debug("HeartbeatMonitor stop error: %s", exc)
    logger.info("ARA Engine stopped")


# ── Public surface ────────────────────────────────────────────────────────────

from .queue       import get_queue, ExecutionQueue, Priority
from .worker      import get_worker, MissionWorker
from .checkpoint  import get_checkpoint, CheckpointEngine, CheckpointState
from .locking     import get_lock, DistributedLock
from .events      import get_event_bus, MissionEvent, MissionEventBus
from .retry       import get_retry_engine, RetryEngine, RetryPolicy
from .observability import get_observability, MissionObservability
from .heartbeat   import get_heartbeat_monitor, HeartbeatMonitor
from .recovery    import get_recovery_engine, RecoveryEngine
from .scheduler   import get_scheduler, MissionScheduler

__all__ = [
    "start_engine",
    "stop_engine",
    "get_queue",
    "get_worker",
    "get_checkpoint",
    "get_lock",
    "get_event_bus",
    "get_retry_engine",
    "get_observability",
    "get_heartbeat_monitor",
    "get_recovery_engine",
    "get_scheduler",
    "ExecutionQueue",
    "Priority",
    "MissionWorker",
    "CheckpointEngine",
    "CheckpointState",
    "DistributedLock",
    "MissionEvent",
    "MissionEventBus",
    "RetryEngine",
    "RetryPolicy",
    "MissionObservability",
    "HeartbeatMonitor",
    "RecoveryEngine",
    "MissionScheduler",
]
