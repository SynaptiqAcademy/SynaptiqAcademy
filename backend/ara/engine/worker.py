"""
Mission Worker — stateless executor that owns no mission state.

The worker:
  1. Polls the ExecutionQueue for the next mission
  2. Acquires a distributed lock (prevents duplicate execution)
  3. Restores checkpoint (skips already-completed steps)
  4. Executes each pending step via _execute_step from orchestrator
  5. Checkpoints after each successful step
  6. Updates heartbeat every HEARTBEAT_INTERVAL_S
  7. Creates approval gates for irreversible actions
  8. Releases lock and persists final status on completion

If the worker crashes mid-step:
  - Heartbeat expires
  - HeartbeatMonitor detects stale mission
  - RecoveryEngine requeues mission
  - Next worker picks it up, restores checkpoint, skips completed steps

Workers are completely stateless — they write all state to MongoDB.
Multiple workers can run concurrently (one per mission, enforced by locking).
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import socket
import time
import uuid
from datetime import datetime, timezone

from .checkpoint import get_checkpoint
from .heartbeat import HEARTBEAT_INTERVAL_S
from events import (
    get_bus,
    MissionStarted, MissionCompleted, MissionFailed, MissionApprovalNeeded,
    StepStarted, StepCompleted, StepFailed,
)
from .locking import get_lock
from .observability import get_observability
from .queue import get_queue, Priority
from .retry import get_retry_engine

logger = logging.getLogger("ara.engine.worker")

WORKER_POLL_INTERVAL_S  = 1     # how often to poll queue when idle
LOCK_TTL_S              = 90    # lock expires after 90s (refreshed every 30s)
LOCK_REFRESH_S          = 30    # refresh lock this often during execution


def _make_worker_id() -> str:
    """Unique worker ID: hostname + pid + random suffix."""
    host = socket.gethostname()[:12]
    pid  = os.getpid()
    rnd  = random.randint(1000, 9999)
    return f"{host}-{pid}-{rnd}"


class MissionWorker:
    """
    Stateless mission worker. Can run multiple instances in parallel
    (each handles a different mission; locking prevents overlap).
    """

    def __init__(self):
        self.worker_id        = _make_worker_id()
        self._running         = False
        self._loop_task: asyncio.Task | None   = None
        self._hb_task:   asyncio.Task | None   = None
        self._active_mission: str | None        = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, db) -> None:
        """Start the worker event loop as a background task."""
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._loop(db))
        logger.info("MissionWorker %s started", self.worker_id)

    async def stop(self) -> None:
        self._running = False
        for task in (self._loop_task, self._hb_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("MissionWorker %s stopped", self.worker_id)

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _loop(self, db) -> None:
        """Poll queue and execute missions until stopped."""
        while self._running:
            try:
                did_work = await self._process_one(db)
                if not did_work:
                    await asyncio.sleep(WORKER_POLL_INTERVAL_S)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Worker loop error: %s", exc)
                await asyncio.sleep(5)

    async def _process_one(self, db) -> bool:
        """Dequeue and execute one mission. Returns True if work was done."""
        queue      = get_queue()
        mission_id = await queue.dequeue()
        if not mission_id:
            return False

        # Acquire distributed lock
        acquired = await get_lock().acquire(mission_id, self.worker_id, ttl_s=LOCK_TTL_S)
        if not acquired:
            # Another worker already has it — requeue and try again later
            logger.debug("Lock contention: mission=%s already owned by another worker", mission_id)
            await queue.requeue(mission_id, delay_seconds=5)
            return True  # we did check the queue (not idle)

        logger.info("Worker %s acquired mission %s", self.worker_id, mission_id)
        try:
            await self._execute_mission(db, mission_id)
        finally:
            await get_lock().release(mission_id, self.worker_id)
            self._active_mission = None
        return True

    # ── Mission execution ─────────────────────────────────────────────────────

    async def _execute_mission(self, db, mission_id: str) -> None:
        from ara import mission_store
        from ara.safe_autonomy import can_auto_execute
        from ara.models import StepStatus

        self._active_mission = mission_id
        exec_token = str(uuid.uuid4())

        mission = await mission_store.get_mission(db, mission_id)
        if not mission:
            logger.error("Mission %s not found; skipping", mission_id)
            return

        # Guard: only execute missions in queued/retrying state
        if mission.get("status") not in ("queued", "retrying", "running"):
            logger.warning("Mission %s is in state '%s'; skipping", mission_id, mission.get("status"))
            return

        # Mark running
        await mission_store.mark_running(db, mission_id, self.worker_id, exec_token)
        await get_bus().publish(MissionStarted(
            aggregate_id=mission_id,
            user_id=mission.get("user_id", ""),
            payload={"worker_id": self.worker_id},
        ))
        await get_observability().record_execution_start(db, mission_id, self.worker_id)
        await mission_store.append_log(db, mission_id, "worker", "started",
                                       f"Worker {self.worker_id} started execution (token={exec_token})")

        # Start lock-refresh loop and heartbeat loop
        refresh_task = asyncio.create_task(
            self._refresh_loop(mission_id, db)
        )
        mission_start = time.monotonic()

        try:
            # Restore checkpoint (skip already-completed steps)
            checkpoint = await get_checkpoint().restore(db, mission_id)
            if checkpoint.completed_step_ids:
                logger.info("Resuming mission %s from checkpoint (%s)",
                            mission_id, checkpoint.resume_from())
                await mission_store.append_log(db, mission_id, "worker", "checkpoint_restored",
                                               f"Resuming from checkpoint: {len(checkpoint.completed_step_ids)} steps already done")

            # Rebuild mission memory from checkpoint outputs
            from ara import mission_memory as mem_store
            memory = await mem_store.get_or_create(
                mission_id, mission["user_id"], mission.get("params") or {}
            )
            for step_id, outputs in checkpoint.step_outputs.items():
                memory.set_step_output(step_id, outputs)

            # Load steps
            steps = await mission_store.get_steps(db, mission_id)
            autonomy_level = mission.get("autonomy_level", 1)
            user = {"_id": mission["user_id"], "name": "", "institution": ""}

            # Execute each pending step
            await self._execute_steps(
                db, mission, steps, memory, checkpoint,
                autonomy_level, user, exec_token,
            )

        except asyncio.CancelledError:
            # Worker is stopping — leave mission in running state so recovery picks it up
            logger.warning("Worker %s cancelled during mission %s", self.worker_id, mission_id)
            raise

        except Exception as exc:
            # Unexpected error — apply retry policy
            logger.error("Mission %s execution error: %s", mission_id, exc)
            retry_count = mission.get("retry_count", 0)
            retry_ok = await get_retry_engine().schedule_retry(
                db, get_queue(), mission_id, str(exc), retry_count,
            )
            if not retry_ok:
                await get_bus().publish(MissionFailed(
                    aggregate_id=mission_id,
                    user_id=mission.get("user_id", ""),
                    payload={"error": str(exc), "worker_id": self.worker_id},
                ))

        finally:
            refresh_task.cancel()
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass
            total_ms = int((time.monotonic() - mission_start) * 1000)
            final = await mission_store.get_mission(db, mission_id)
            final_status = (final or {}).get("status", "unknown")
            await get_observability().record_mission_end(db, mission_id, final_status, total_ms)

    async def _execute_steps(
        self, db, mission: dict, steps: list[dict],
        memory, checkpoint, autonomy_level: int,
        user: dict, exec_token: str,
    ) -> None:
        from ara import mission_store
        from ara.models import StepStatus
        from ara.safe_autonomy import can_auto_execute
        from ara.orchestrator import _execute_step, _create_approval_gate

        mission_id     = mission["_id"]
        completed_ids  = set(checkpoint.completed_step_ids)
        step_map       = {s["step_id"]: s for s in steps}
        total_cost     = 0.0

        for step in steps:
            step_id = step["step_id"]

            # Skip already-completed steps (checkpoint restore)
            if step_id in completed_ids:
                continue

            # Skip if dependency failed
            skip = False
            for dep_id in step.get("depends_on") or []:
                dep = step_map.get(dep_id)
                if dep and dep.get("status") == "failed":
                    await mission_store.update_step(db, mission_id, step_id,
                                                    {"status": StepStatus.SKIPPED.value,
                                                     "error": f"Dependency {dep_id} failed"})
                    skip = True
                    break
            if skip:
                continue

            # Check approval requirement
            action = step.get("action", "")
            if not can_auto_execute(action, autonomy_level):
                approval_id = await _create_approval_gate(db, step, mission["user_id"])
                await mission_store.update_mission(db, mission_id, {"status": "awaiting_human"})
                await get_bus().publish(MissionApprovalNeeded(
                    aggregate_id=mission_id,
                    user_id=mission.get("user_id", ""),
                    payload={"step_id": step_id, "action": action, "approval_id": approval_id},
                ))
                await mission_store.append_log(db, mission_id, "worker", "approval_gate",
                                               f"Approval required for step {step_id} action={action}",
                                               {"approval_id": approval_id})
                # Pause execution — will be requeued by resume_after_approval
                return

            # Mark step running
            await mission_store.update_step(db, mission_id, step_id, {
                "status":     StepStatus.RUNNING.value,
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
            await get_bus().publish(StepStarted(
                aggregate_id=mission_id,
                user_id=mission.get("user_id", ""),
                payload={"step_id": step_id, "worker_id": self.worker_id},
            ))
            await get_observability().record_step_start(db, mission_id, step_id, step.get("agent_name", ""))
            step_start = time.monotonic()

            try:
                updated = await _execute_step(db, step, memory, user)
                await mission_store.upsert_step(db, updated)

                step_ms  = int((time.monotonic() - step_start) * 1000)
                success  = updated["status"] == "completed"
                confidence = updated.get("confidence", "low")

                # Checkpoint the step
                await get_checkpoint().save(
                    db, mission_id, step_id,
                    outputs=updated.get("outputs", {}),
                    evidence=updated.get("evidence", []),
                    confidence=confidence,
                    agent_name=step.get("agent_name", ""),
                )
                completed_ids.add(step_id)

                _step_cls = StepCompleted if success else StepFailed
                await get_bus().publish(_step_cls(
                    aggregate_id=mission_id,
                    user_id=mission.get("user_id", ""),
                    payload={"step_id": step_id, "confidence": confidence, "duration_ms": step_ms},
                ))
                await get_observability().record_step_end(
                    db, mission_id, step_id, step_ms,
                    success=success, confidence=confidence,
                    agent=step.get("agent_name", ""),
                )

                # Increment mission completed_steps counter
                current = await mission_store.get_mission(db, mission_id)
                done = (current or {}).get("completed_steps", 0) + 1
                await mission_store.update_mission(db, mission_id, {"completed_steps": done})

                await mission_store.append_log(db, mission_id, step.get("agent_name", "worker"),
                                               "step_completed" if success else "step_failed",
                                               f"Step {step_id} {updated['status']} ({step_ms}ms)",
                                               {"confidence": confidence})

            except Exception as exc:
                step_ms = int((time.monotonic() - step_start) * 1000)
                logger.error("Step %s failed in mission %s: %s", step_id, mission_id, exc)
                await mission_store.update_step(db, mission_id, step_id, {
                    "status": StepStatus.FAILED.value,
                    "error":  str(exc)[:500],
                })
                await get_bus().publish(StepFailed(
                    aggregate_id=mission_id,
                    user_id=mission.get("user_id", ""),
                    payload={"step_id": step_id, "error": str(exc)[:200]},
                ))
                await get_observability().record_step_end(
                    db, mission_id, step_id, step_ms, success=False, error=str(exc)[:200]
                )
                await mission_store.update_mission(db, mission_id, {
                    "status": "failed", "error": str(exc)[:500],
                })
                await get_bus().publish(MissionFailed(
                    aggregate_id=mission_id,
                    user_id=mission.get("user_id", ""),
                    payload={"error": str(exc)[:200], "step_id": step_id},
                ))
                return

        # All steps completed — run validation and finalise
        await self._finalise_mission(db, mission, steps, memory)

    async def _finalise_mission(self, db, mission: dict, steps: list, memory) -> None:
        from ara import mission_store
        from ara import validation_agent

        mission_id = mission["_id"]

        # Run validation agent
        all_steps  = await mission_store.get_steps(db, mission_id)
        val_report = validation_agent.run(all_steps, mission)

        # Build result summary
        outputs_by_step = memory.all_step_outputs()
        lines = []
        for step in all_steps:
            out = outputs_by_step.get(step["step_id"])
            if out and out.get("summary"):
                lines.append(f"{step['name']}: {out['summary'][:200]}")
        result_summary = "\n\n".join(lines) or "Mission completed. Review step outputs for details."

        await mission_store.update_mission(db, mission_id, {
            "status":         "completed",
            "completed_at":   datetime.now(timezone.utc),
            "result_summary": result_summary,
            "validation":     val_report,
        })
        await mission_store.append_log(db, mission_id, "worker", "completed",
                                       "Mission completed successfully",
                                       {"validation_passed": val_report.get("passed", False),
                                        "worker_id": self.worker_id})
        await get_bus().publish(MissionCompleted(
            aggregate_id=mission_id,
            user_id=mission.get("user_id", ""),
            payload={"worker_id": self.worker_id, "validation_passed": val_report.get("passed", False)},
        ))
        # Free mission memory
        from ara import mission_memory as mem_store
        mem_store.release(mission_id)
        logger.info("Mission %s completed by worker %s", mission_id, self.worker_id)

    # ── Lock refresh loop ─────────────────────────────────────────────────────

    async def _refresh_loop(self, mission_id: str, db) -> None:
        """
        Background task: refresh distributed lock AND update heartbeat
        every LOCK_REFRESH_S seconds during mission execution.
        """
        while True:
            await asyncio.sleep(LOCK_REFRESH_S)
            try:
                refreshed = await get_lock().refresh(mission_id, self.worker_id, ttl_s=LOCK_TTL_S)
                if not refreshed:
                    logger.warning("Lost lock for mission %s — stopping execution", mission_id)
                    break
                from ara import mission_store
                await mission_store.update_heartbeat(db, mission_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Lock refresh error: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────────

_worker: MissionWorker | None = None


def get_worker() -> MissionWorker:
    global _worker
    if _worker is None:
        _worker = MissionWorker()
    return _worker
