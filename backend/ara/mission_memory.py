"""
Per-mission shared memory store — backed by gateway AIMemory (Redis/MongoDB).

Audit fix (C-01): The original in-process `_MEMORIES` dict was lost on server
restart and not shared across workers. This module now:

  1. Keeps a local in-process cache (fast reads during a single execution)
  2. Fire-and-forget writes to Redis via gateway.ai_memory (durable, shared)
  3. On `get_or_create`, restores step outputs from Redis if the mission was
     previously started (handles server restarts and worker handoffs)
  4. On `release`, deletes from both the local cache and Redis

The public API (MissionMemory class + module-level functions) is unchanged.
All callers in orchestrator.py work without modification.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ara.mission_memory")


class MissionMemory:
    """
    Shared context for all agents within a single mission execution.

    Sync API preserved for backward compatibility with orchestrator.py.
    Writes are mirrored to Redis asynchronously (fire-and-forget) so the
    state survives server restarts and is visible across workers.
    """

    def __init__(self, mission_id: str, user_id: str, params: dict):
        self.mission_id  = mission_id
        self.user_id     = user_id
        self.params      = params
        self._store: dict[str, Any] = {}
        self._step_outputs: dict[str, dict] = {}
        self._created_at = datetime.now(timezone.utc)

    # ── Key-value store ───────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        _fire(self.mission_id, "set_mission_value", key, value)

    def has(self, key: str) -> bool:
        return key in self._store

    # ── Step outputs ──────────────────────────────────────────────────────────

    def set_step_output(self, step_id: str, output: dict) -> None:
        self._step_outputs[step_id] = output
        _fire(self.mission_id, "set_step_output", step_id, output)

    def get_step_output(self, step_id: str) -> dict | None:
        return self._step_outputs.get(step_id)

    def all_step_outputs(self) -> dict[str, dict]:
        return dict(self._step_outputs)

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "mission_id":  self.mission_id,
            "keys":        list(self._store.keys()),
            "steps_done":  list(self._step_outputs.keys()),
            "age_s":       (datetime.now(timezone.utc) - self._created_at).total_seconds(),
        }


# ── Fire-and-forget helper ─────────────────────────────────────────────────────

def _fire(mission_id: str, method: str, key: str, value: Any) -> None:
    """Schedule a Redis write without blocking the caller."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_redis_write(mission_id, method, key, value))
    except Exception:
        pass  # degraded mode: in-process dict only


async def _redis_write(mission_id: str, method: str, key: str, value: Any) -> None:
    try:
        from gateway.ai_memory import get_memory
        mem = get_memory()
        if method == "set_mission_value":
            await mem.set_mission_value(mission_id, key, value)
        elif method == "set_step_output":
            await mem.set_step_output(mission_id, key, value)
    except Exception as exc:
        logger.debug("mission_memory._redis_write failed: %s", exc)


# ── Process-level cache ────────────────────────────────────────────────────────

_MEMORIES: dict[str, MissionMemory] = {}
_LOCK = asyncio.Lock()


async def get_or_create(mission_id: str, user_id: str, params: dict) -> MissionMemory:
    """Return existing MissionMemory or create a new one, restoring from Redis if available."""
    async with _LOCK:
        if mission_id not in _MEMORIES:
            mem = MissionMemory(mission_id, user_id, params)
            # Restore step outputs from Redis (handles server restarts)
            try:
                from gateway.ai_memory import get_memory
                step_outputs = await get_memory().all_step_outputs(mission_id)
                if step_outputs:
                    mem._step_outputs = {k: v for k, v in step_outputs.items()}
                    logger.info(
                        "Restored %d step outputs from Redis for mission %s",
                        len(step_outputs), mission_id,
                    )
            except Exception as exc:
                logger.debug("Redis restore failed (using empty memory): %s", exc)
            _MEMORIES[mission_id] = mem
        return _MEMORIES[mission_id]


def get(mission_id: str) -> MissionMemory | None:
    return _MEMORIES.get(mission_id)


def release(mission_id: str) -> None:
    """Remove from local cache and schedule Redis cleanup."""
    _MEMORIES.pop(mission_id, None)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_redis_release(mission_id))
    except Exception:
        pass


async def _redis_release(mission_id: str) -> None:
    try:
        from gateway.ai_memory import get_memory
        await get_memory().release_mission(mission_id)
    except Exception as exc:
        logger.debug("mission_memory._redis_release failed: %s", exc)
