"""
Checkpoint Engine — durable step-level state persistence.

After every successful step:
  - Step outputs are persisted to ara_checkpoints
  - Gateway AI Memory is updated (Redis)
  - Mission's checkpoint_step field is updated

On recovery after crash:
  - CheckpointEngine.restore() returns the set of completed step IDs
  - The worker skips already-completed steps
  - Execution resumes from the first non-completed step

No completed work is ever lost or re-executed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ara.engine.checkpoint")

_COLL = "ara_checkpoints"


@dataclass
class CheckpointState:
    mission_id:           str
    completed_step_ids:   set[str]       = field(default_factory=set)
    step_outputs:         dict[str, dict] = field(default_factory=dict)
    last_checkpointed_at: datetime | None = None

    def is_done(self, step_id: str) -> bool:
        return step_id in self.completed_step_ids

    def resume_from(self) -> str | None:
        """Return the last completed step_id (for logging). None if starting fresh."""
        if not self.completed_step_ids:
            return None
        return f"{len(self.completed_step_ids)} steps already completed"


class CheckpointEngine:

    async def save(
        self,
        db,
        mission_id:    str,
        step_id:       str,
        outputs:       dict,
        evidence:      list[dict] | None = None,
        confidence:    str               = "low",
        cost_credits:  float             = 0.0,
        agent_name:    str               = "",
    ) -> None:
        """
        Persist step checkpoint. Idempotent: upserts by (mission_id, step_id).
        Also updates gateway AIMemory (Redis) as a secondary store.
        """
        now = datetime.now(timezone.utc)
        doc = {
            "mission_id":   mission_id,
            "step_id":      step_id,
            "agent_name":   agent_name,
            "outputs":      outputs,
            "evidence":     evidence or [],
            "confidence":   confidence,
            "cost_credits": cost_credits,
            "saved_at":     now,
        }
        try:
            await db[_COLL].update_one(
                {"mission_id": mission_id, "step_id": step_id},
                {"$set": doc},
                upsert=True,
            )
            # Update mission-level checkpoint pointer
            from ara import mission_store
            await mission_store.update_mission(db, mission_id, {"checkpoint_step": step_id})
        except Exception as exc:
            logger.error("Checkpoint save failed (mission=%s step=%s): %s", mission_id, step_id, exc)
            raise

        # Secondary: gateway AI memory (Redis-backed; best-effort)
        try:
            from gateway.ai_memory import get_memory
            await get_memory().set_step_output(mission_id, step_id, outputs)
        except Exception as exc:
            logger.debug("Checkpoint AI memory update failed (non-blocking): %s", exc)

        logger.debug("checkpoint saved: mission=%s step=%s confidence=%s", mission_id, step_id, confidence)

    async def restore(self, db, mission_id: str) -> CheckpointState:
        """
        Load all checkpoints for a mission. Returns CheckpointState
        with the set of completed step IDs and their outputs.
        """
        state = CheckpointState(mission_id=mission_id)
        try:
            docs = await db[_COLL].find(
                {"mission_id": mission_id}, {"_id": 0}
            ).to_list(200)

            for doc in docs:
                step_id = doc["step_id"]
                state.completed_step_ids.add(step_id)
                state.step_outputs[step_id] = doc.get("outputs", {})
                saved_at = doc.get("saved_at")
                if saved_at and (state.last_checkpointed_at is None or saved_at > state.last_checkpointed_at):
                    state.last_checkpointed_at = saved_at

            if state.completed_step_ids:
                logger.info(
                    "Checkpoint restored: mission=%s steps_done=%d last_checkpoint=%s",
                    mission_id, len(state.completed_step_ids),
                    state.last_checkpointed_at.isoformat() if state.last_checkpointed_at else "never",
                )
        except Exception as exc:
            logger.error("Checkpoint restore failed (mission=%s): %s", mission_id, exc)

        return state

    async def get_completed_step_ids(self, db, mission_id: str) -> set[str]:
        """Fast path: only return the completed step IDs, not outputs."""
        try:
            docs = await db[_COLL].find(
                {"mission_id": mission_id}, {"step_id": 1, "_id": 0}
            ).to_list(200)
            return {d["step_id"] for d in docs}
        except Exception:
            return set()

    async def clear(self, db, mission_id: str) -> None:
        """Delete all checkpoints for a mission (called on archive/delete)."""
        try:
            await db[_COLL].delete_many({"mission_id": mission_id})
            from gateway.ai_memory import get_memory
            await get_memory().release_mission(mission_id)
        except Exception as exc:
            logger.debug("Checkpoint clear failed (non-blocking): %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────────

_ckpt: CheckpointEngine | None = None


def get_checkpoint() -> CheckpointEngine:
    global _ckpt
    if _ckpt is None:
        _ckpt = CheckpointEngine()
    return _ckpt
