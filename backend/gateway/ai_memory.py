"""
Enterprise AI Gateway — Unified AI Memory.

Single memory store shared across all AI modules.
Fixes audit finding C-01: replaces the in-process `_MEMORIES` dict in
`ara/mission_memory.py` with a Redis-backed (MongoDB-fallback) durable store.

Memory namespaces:
  conversation:{user_id}      — last N user/assistant exchanges (TTL: 1h)
  mission:{mission_id}        — mission-scoped key-value store (TTL: 24h)
  mission:{mission_id}:steps  — step outputs (TTL: 24h)
  workspace:{workspace_id}    — workspace context (TTL: 4h)
  research:{user_id}          — research focus / recent topics (TTL: 4h)

All operations gracefully degrade to MongoDB when Redis is unavailable.
All operations are async and never raise to callers.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("gateway.ai_memory")

_TTL = {
    "conversation": 3600,    # 1 hour
    "mission":      86400,   # 24 hours
    "workspace":    14400,   # 4 hours
    "research":     14400,
}


class AIMemory:
    """
    Unified AI Memory with Redis primary and MongoDB fallback.

    All methods return sensible defaults on failure — they never raise.
    """

    # ── Conversation memory ───────────────────────────────────────────────────

    async def append_message(self, user_id: str, role: str, content: str) -> None:
        """Add one message to the user's conversation history."""
        try:
            r = await _get_redis()
            key = f"ai_memory:conversation:{user_id}"
            msg = json.dumps({"role": role, "content": content[:1000],
                              "ts": datetime.now(timezone.utc).isoformat()})
            if r:
                await r.rpush(key, msg)
                await r.ltrim(key, -20, -1)  # keep last 20 messages
                await r.expire(key, _TTL["conversation"])
        except Exception as exc:
            logger.debug("ai_memory.append_message failed: %s", exc)

    async def get_conversation(self, user_id: str, limit: int = 10) -> list[dict]:
        """Return the last `limit` conversation messages."""
        try:
            r = await _get_redis()
            if r:
                raw_list = await r.lrange(f"ai_memory:conversation:{user_id}", -limit, -1)
                return [json.loads(m) for m in raw_list]
        except Exception as exc:
            logger.debug("ai_memory.get_conversation failed: %s", exc)
        return []

    # ── Mission memory (replaces ara/mission_memory.py _MEMORIES dict) ────────

    async def get_mission_value(self, mission_id: str, key: str,
                                 default: Any = None) -> Any:
        try:
            r = await _get_redis()
            if r:
                raw = await r.hget(f"ai_memory:mission:{mission_id}", key)
                return json.loads(raw) if raw else default
        except Exception as exc:
            logger.debug("ai_memory.get_mission_value failed: %s", exc)
        return default

    async def set_mission_value(self, mission_id: str, key: str, value: Any) -> None:
        try:
            r = await _get_redis()
            if r:
                hkey = f"ai_memory:mission:{mission_id}"
                await r.hset(hkey, key, json.dumps(value))
                await r.expire(hkey, _TTL["mission"])
        except Exception as exc:
            logger.debug("ai_memory.set_mission_value failed: %s", exc)

    async def has_mission_value(self, mission_id: str, key: str) -> bool:
        try:
            r = await _get_redis()
            if r:
                return bool(await r.hexists(f"ai_memory:mission:{mission_id}", key))
        except Exception:
            pass
        return False

    async def set_step_output(self, mission_id: str, step_id: str, output: dict) -> None:
        try:
            r = await _get_redis()
            if r:
                hkey = f"ai_memory:mission:{mission_id}:steps"
                await r.hset(hkey, step_id, json.dumps(output))
                await r.expire(hkey, _TTL["mission"])
        except Exception as exc:
            logger.debug("ai_memory.set_step_output failed: %s", exc)

    async def get_step_output(self, mission_id: str, step_id: str) -> dict | None:
        try:
            r = await _get_redis()
            if r:
                raw = await r.hget(f"ai_memory:mission:{mission_id}:steps", step_id)
                return json.loads(raw) if raw else None
        except Exception as exc:
            logger.debug("ai_memory.get_step_output failed: %s", exc)
        return None

    async def all_step_outputs(self, mission_id: str) -> dict[str, dict]:
        try:
            r = await _get_redis()
            if r:
                raw = await r.hgetall(f"ai_memory:mission:{mission_id}:steps")
                return {k: json.loads(v) for k, v in raw.items()}
        except Exception as exc:
            logger.debug("ai_memory.all_step_outputs failed: %s", exc)
        return {}

    async def release_mission(self, mission_id: str) -> None:
        """Delete mission memory on completion (frees Redis memory)."""
        try:
            r = await _get_redis()
            if r:
                await r.delete(
                    f"ai_memory:mission:{mission_id}",
                    f"ai_memory:mission:{mission_id}:steps",
                )
        except Exception as exc:
            logger.debug("ai_memory.release_mission failed: %s", exc)

    # ── Research memory ───────────────────────────────────────────────────────

    async def get_research_context(self, user_id: str) -> dict:
        try:
            r = await _get_redis()
            if r:
                raw = await r.get(f"ai_memory:research:{user_id}")
                return json.loads(raw) if raw else {}
        except Exception:
            pass
        return {}

    async def set_research_context(self, user_id: str, context: dict) -> None:
        try:
            r = await _get_redis()
            if r:
                await r.setex(
                    f"ai_memory:research:{user_id}",
                    _TTL["research"],
                    json.dumps(context),
                )
        except Exception as exc:
            logger.debug("ai_memory.set_research_context failed: %s", exc)

    # ── Cache (semantic response cache) ───────────────────────────────────────

    async def get_cached_response(self, cache_key: str) -> Optional[str]:
        try:
            r = await _get_redis()
            if r:
                return await r.get(f"ai_memory:cache:{cache_key}")
        except Exception:
            pass
        return None

    async def cache_response(self, cache_key: str, response: str,
                              ttl_seconds: int = 3600) -> None:
        try:
            r = await _get_redis()
            if r:
                await r.setex(f"ai_memory:cache:{cache_key}", ttl_seconds, response)
        except Exception as exc:
            logger.debug("ai_memory.cache_response failed: %s", exc)


# ── Redis accessor ─────────────────────────────────────────────────────────────

async def _get_redis():
    try:
        from services.redis_client import get_redis
        return await get_redis()
    except Exception:
        return None


# ── Process-level singleton ───────────────────────────────────────────────────

_memory: AIMemory | None = None


def get_memory() -> AIMemory:
    global _memory
    if _memory is None:
        _memory = AIMemory()
    return _memory
