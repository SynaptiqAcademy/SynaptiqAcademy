"""
Distributed Mission Lock — prevents duplicate execution across workers.

Only one worker may own a mission at any time.

Primary:  Redis SET key value NX EX ttl  (atomic, cluster-safe)
Fallback: MongoDB ara_locks with TTL index on expires_at

Lock key format:  ara:lock:{mission_id}
Lock value:       {worker_id}  (for ownership verification on release)
Default TTL:      60 seconds   (refreshed every 30s by the worker)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("ara.engine.locking")

_LOCK_PREFIX = "ara:lock:"
_LOCK_COLL   = "ara_locks"


class DistributedLock:

    async def acquire(self, mission_id: str, worker_id: str, ttl_s: int = 60) -> bool:
        """
        Try to acquire the lock. Returns True on success, False if already held.
        Never raises.
        """
        try:
            r = await _get_redis()
            if r:
                key = f"{_LOCK_PREFIX}{mission_id}"
                result = await r.set(key, worker_id, nx=True, ex=ttl_s)
                if result:
                    logger.debug("lock acquired (redis): mission=%s worker=%s", mission_id, worker_id)
                    return True
                existing = await r.get(key)
                if existing == worker_id:
                    # Re-entrant: we already own it
                    await r.expire(key, ttl_s)
                    return True
                return False
        except Exception as exc:
            logger.debug("Redis lock acquire failed, trying MongoDB: %s", exc)

        return await self._mongo_acquire(mission_id, worker_id, ttl_s)

    async def release(self, mission_id: str, worker_id: str) -> bool:
        """Release lock. Only succeeds if the caller owns it."""
        try:
            r = await _get_redis()
            if r:
                key = f"{_LOCK_PREFIX}{mission_id}"
                existing = await r.get(key)
                if existing == worker_id:
                    await r.delete(key)
                    logger.debug("lock released (redis): mission=%s", mission_id)
                    return True
                return False
        except Exception as exc:
            logger.debug("Redis lock release failed, trying MongoDB: %s", exc)

        return await self._mongo_release(mission_id, worker_id)

    async def refresh(self, mission_id: str, worker_id: str, ttl_s: int = 60) -> bool:
        """Extend lock TTL. Returns False if we lost the lock."""
        try:
            r = await _get_redis()
            if r:
                key = f"{_LOCK_PREFIX}{mission_id}"
                existing = await r.get(key)
                if existing == worker_id:
                    await r.expire(key, ttl_s)
                    return True
                return False
        except Exception as exc:
            logger.debug("Redis lock refresh failed: %s", exc)

        return await self._mongo_refresh(mission_id, worker_id, ttl_s)

    async def force_release(self, mission_id: str) -> None:
        """Remove lock regardless of owner (used by recovery engine)."""
        try:
            r = await _get_redis()
            if r:
                await r.delete(f"{_LOCK_PREFIX}{mission_id}")
                return
        except Exception:
            pass
        try:
            from db import get_db
            from repo.shim import make_db_proxy
            db = make_db_proxy(get_db(), system=True)
            await db[_LOCK_COLL].delete_one({"mission_id": mission_id})
        except Exception as exc:
            logger.debug("force_release MongoDB failed: %s", exc)

    async def get_holder(self, mission_id: str) -> str | None:
        """Return the worker_id holding this lock, or None."""
        try:
            r = await _get_redis()
            if r:
                return await r.get(f"{_LOCK_PREFIX}{mission_id}")
        except Exception:
            pass
        return None

    # ── MongoDB fallback ──────────────────────────────────────────────────────

    async def _mongo_acquire(self, mission_id: str, worker_id: str, ttl_s: int) -> bool:
        try:
            from db import get_db
            from repo.shim import make_db_proxy
            db = make_db_proxy(get_db(), system=True)
            now = datetime.now(timezone.utc)
            exp = now + timedelta(seconds=ttl_s)
            result = await db[_LOCK_COLL].find_one_and_update(
                {"mission_id": mission_id, "expires_at": {"$lt": now}},
                {"$set": {"worker_id": worker_id, "expires_at": exp, "acquired_at": now}},
                upsert=True,
                return_document=True,
            )
            return result is not None and result.get("worker_id") == worker_id
        except Exception as exc:
            logger.warning("MongoDB lock acquire failed: %s", exc)
            return False

    async def _mongo_release(self, mission_id: str, worker_id: str) -> bool:
        try:
            from db import get_db
            from repo.shim import make_db_proxy
            db = make_db_proxy(get_db(), system=True)
            result = await db[_LOCK_COLL].delete_one(
                {"mission_id": mission_id, "worker_id": worker_id}
            )
            return result.deleted_count > 0
        except Exception as exc:
            logger.debug("MongoDB lock release failed: %s", exc)
            return False

    async def _mongo_refresh(self, mission_id: str, worker_id: str, ttl_s: int) -> bool:
        try:
            from db import get_db
            from repo.shim import make_db_proxy
            db = make_db_proxy(get_db(), system=True)
            exp = datetime.now(timezone.utc) + timedelta(seconds=ttl_s)
            result = await db[_LOCK_COLL].update_one(
                {"mission_id": mission_id, "worker_id": worker_id},
                {"$set": {"expires_at": exp}},
            )
            return result.modified_count > 0
        except Exception as exc:
            logger.debug("MongoDB lock refresh failed: %s", exc)
            return False


# ── Redis accessor ─────────────────────────────────────────────────────────────

async def _get_redis():
    try:
        from services.redis_client import get_redis
        return await get_redis()
    except Exception:
        return None


# ── Singleton ──────────────────────────────────────────────────────────────────

_lock: DistributedLock | None = None


def get_lock() -> DistributedLock:
    global _lock
    if _lock is None:
        _lock = DistributedLock()
    return _lock
