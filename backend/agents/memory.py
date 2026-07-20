"""Shared session memory for the multi-agent copilot.

Each session (keyed by session_id) stores:
  - user profile context
  - the original user request
  - all agent outputs (keyed by agent name)
  - working data (manuscripts, interests, etc.) loaded from MongoDB

Sessions expire after SESSION_TTL (default 1 hour).

Storage: in-process L1 cache + Redis L2 for horizontal scaling.
When Redis is available, sessions survive worker restarts and are shared
across multiple process replicas (no repeated MongoDB context loads).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

SESSION_TTL   = timedelta(hours=1)
_SESSION_TTL_S = int(SESSION_TTL.total_seconds())

# L1: in-process store (fast, per-worker)
_store: dict[str, "_Session"] = {}
_lock  = asyncio.Lock()


def _rkey(sid: str) -> str:
    return f"copilot:session:{sid}"


async def _get_redis():
    """Return async Redis client if available, None otherwise."""
    try:
        from services.redis_client import get_redis
        return await get_redis()
    except Exception:
        return None


class _Session:
    def __init__(self, session_id: str, user: dict, user_input: str):
        self.session_id  = session_id
        self.user        = user
        self.user_input  = user_input
        self.created_at  = datetime.now(timezone.utc)
        self._context: dict[str, Any]  = {}
        self._outputs:  dict[str, Any]  = {}   # agent_name → AgentOutput

    def expired(self) -> bool:
        return (datetime.now(timezone.utc) - self.created_at) > SESSION_TTL

    def _to_redis_dict(self) -> dict:
        """Serialize session metadata and context (agent outputs are ephemeral)."""
        return {
            "session_id": self.session_id,
            "user":        self.user,
            "user_input":  self.user_input,
            "created_at":  self.created_at.isoformat(),
            "context":     self._context,
        }

    @classmethod
    def _from_redis_dict(cls, d: dict) -> "_Session":
        s = cls.__new__(cls)
        s.session_id = d["session_id"]
        s.user       = d.get("user", {})
        s.user_input = d.get("user_input", "")
        s.created_at = datetime.fromisoformat(d["created_at"])
        s._context   = d.get("context", {})
        s._outputs   = {}   # not persisted — ephemeral per orchestration run
        return s


async def _save_to_redis(session: "_Session") -> None:
    redis = await _get_redis()
    if redis is None:
        return
    try:
        data = json.dumps(session._to_redis_dict(), default=str)
        await redis.set(_rkey(session.session_id), data, ex=_SESSION_TTL_S)
    except Exception as exc:
        logger.debug("Session Redis save error: %s", exc)


async def _load_from_redis(session_id: str) -> "_Session | None":
    redis = await _get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(_rkey(session_id))
        if raw:
            d = json.loads(raw)
            s = _Session._from_redis_dict(d)
            if not s.expired():
                return s
    except Exception as exc:
        logger.debug("Session Redis load error: %s", exc)
    return None


class SharedMemory:
    """View over a _Session for a single request cycle."""

    def __init__(self, session_id: str, user: dict, user_input: str):
        self._session = _Session(session_id, user, user_input)
        _store[session_id] = self._session

    # ── Context (loaded from DB) ──────────────────────────────────────────

    async def load_context(self, db, uid: str) -> None:
        """Pre-load common user context into memory for all agents to reuse."""
        try:
            user = self._session.user
            ctx: dict[str, Any] = {
                "uid":          uid,
                "interests":    user.get("research_interests") or user.get("research_areas") or [],
                "domain":       user.get("primary_domain", ""),
                "institution":  user.get("institution", ""),
                "role":         user.get("user_type", ""),
                "orcid":        (user.get("orcid") or {}).get("orcid_id"),
                "manuscripts":  [],
                "projects":     [],
                "collaborations": [],
                "grants":       [],
            }
            try:
                ctx["manuscripts"] = await db.manuscripts.find(
                    {"user_id": uid, "status": {"$nin": ["rejected"]}}
                ).to_list(20)
            except Exception:
                pass
            try:
                ctx["projects"] = await db.projects.find(
                    {"creator_id": uid, "status": "active"}
                ).to_list(10)
            except Exception:
                pass
            try:
                ctx["collaborations"] = await db.collaborations.find(
                    {"status": "open"}
                ).limit(10).to_list(10)
            except Exception:
                pass
            try:
                from datetime import timezone as _tz
                now = datetime.now(_tz.utc)
                ctx["grants"] = await db.grants.find(
                    {"deadline": {"$gte": now}}
                ).sort("deadline", 1).limit(15).to_list(15)
            except Exception:
                pass

            self._session._context = ctx
            await _save_to_redis(self._session)
        except Exception:
            pass

    def get(self, key: str, default=None):
        return self._session._context.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._session._context[key] = value

    # ── Agent outputs ─────────────────────────────────────────────────────

    def set_agent_output(self, agent_name: str, output: Any) -> None:
        self._session._outputs[agent_name] = output

    def get_agent_output(self, agent_name: str) -> Optional[Any]:
        return self._session._outputs.get(agent_name)

    def all_outputs(self) -> dict[str, Any]:
        return dict(self._session._outputs)

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def user_input(self) -> str:
        return self._session.user_input

    @property
    def user(self) -> dict:
        return self._session.user

    @property
    def session_id(self) -> str:
        return self._session.session_id


async def get_or_create(session_id: str, user: dict, user_input: str) -> SharedMemory:
    """Return a SharedMemory for an existing session or create a new one.

    Lookup order:
      1. In-process L1 cache (fastest — same worker, same session)
      2. Redis L2 cache (cross-worker session recovery)
      3. Create new session
    """
    async with _lock:
        # Prune expired sessions from L1
        expired = [k for k, v in _store.items() if v.expired()]
        for k in expired:
            del _store[k]

        if session_id in _store and not _store[session_id].expired():
            _store[session_id].user_input = user_input
            mem = SharedMemory.__new__(SharedMemory)
            mem._session = _store[session_id]
            return mem

    # L1 miss — check Redis for cross-worker session recovery
    restored = await _load_from_redis(session_id)
    if restored:
        restored.user_input = user_input
        async with _lock:
            _store[session_id] = restored
        mem = SharedMemory.__new__(SharedMemory)
        mem._session = restored
        return mem

    # New session
    mem = SharedMemory(session_id, user, user_input)
    await _save_to_redis(mem._session)
    return mem
