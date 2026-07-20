"""
Repository Cache Layer.

Two-tier cache:
  1. In-process TTLCache (fast, per-worker)
  2. Redis (optional, shared across workers)

Repositories call `cache.get()` / `cache.set()` / `cache.invalidate()`.
Keys are always prefixed with the collection name to prevent collisions.
Cache is bypass-able per-call (e.g. after writes that must be consistent).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Default TTLs (seconds)
DEFAULT_TTL = 30          # most repo reads
SHORT_TTL   = 10          # frequently mutated (missions, notifications)
LONG_TTL    = 120         # rarely mutated (user profiles, institutions)


class TTLEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: int) -> None:
        self.value      = value
        self.expires_at = time.monotonic() + ttl


class InProcessCache:
    """Per-process LRU-like TTL cache. Thread-safe via asyncio (single-threaded)."""

    def __init__(self, max_size: int = 2000) -> None:
        self._store: dict[str, TTLEntry] = {}
        self._max   = max_size

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        if len(self._store) >= self._max:
            # Evict oldest 10%
            now = time.monotonic()
            expired = [k for k, e in self._store.items() if e.expires_at <= now]
            for k in expired[:max(1, self._max // 10)]:
                self._store.pop(k, None)
            if len(self._store) >= self._max:
                # Still full — evict arbitrary keys
                victims = list(self._store.keys())[: self._max // 10]
                for k in victims:
                    self._store.pop(k, None)
        self._store[key] = TTLEntry(value, ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def delete_prefix(self, prefix: str) -> int:
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        return len(keys)

    def clear(self) -> None:
        self._store.clear()


# Module-level singleton (shared within a worker process)
_local_cache = InProcessCache()


class RepositoryCache:
    """
    Unified cache interface for repositories.

    Redis is used when available; falls back silently to in-process cache.
    """

    def __init__(self, collection: str, redis=None) -> None:
        self._col   = collection
        self._redis = redis   # optional aioredis client

    # ── Core API ──────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Any | None:
        full_key = self._full(key)

        # L1: in-process
        hit = _local_cache.get(full_key)
        if hit is not None:
            return hit

        # L2: Redis
        if self._redis:
            try:
                raw = await self._redis.get(full_key)
                if raw:
                    val = json.loads(raw)
                    _local_cache.set(full_key, val, SHORT_TTL)
                    return val
            except Exception as exc:
                logger.debug("Redis cache get error: %s", exc)

        return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        full_key = self._full(key)
        _local_cache.set(full_key, value, ttl)

        if self._redis:
            try:
                await self._redis.set(full_key, json.dumps(value, default=str), ex=ttl)
            except Exception as exc:
                logger.debug("Redis cache set error: %s", exc)

    async def invalidate(self, key: str) -> None:
        full_key = self._full(key)
        _local_cache.delete(full_key)
        if self._redis:
            try:
                await self._redis.delete(full_key)
            except Exception as exc:
                logger.debug("Redis cache delete error: %s", exc)

    async def invalidate_collection(self) -> int:
        prefix = f"repo:{self._col}:"
        count = _local_cache.delete_prefix(prefix)
        if self._redis:
            try:
                # Use SCAN instead of KEYS to avoid blocking the Redis server on large keyspaces
                keys_to_delete: list[str] = []
                async for key in self._redis.scan_iter(f"{prefix}*", count=100):
                    keys_to_delete.append(key)
                if keys_to_delete:
                    await self._redis.delete(*keys_to_delete)
                    count += len(keys_to_delete)
            except Exception as exc:
                logger.debug("Redis prefix delete error: %s", exc)
        return count

    async def invalidate_user(self, user_id: str) -> int:
        prefix = f"repo:{self._col}:u:{user_id}:"
        count = _local_cache.delete_prefix(prefix)
        if self._redis:
            try:
                keys_to_delete: list[str] = []
                async for key in self._redis.scan_iter(f"{prefix}*", count=100):
                    keys_to_delete.append(key)
                if keys_to_delete:
                    await self._redis.delete(*keys_to_delete)
                    count += len(keys_to_delete)
            except Exception as exc:
                logger.debug("Redis user prefix delete: %s", exc)
        return count

    # ── Key builders ──────────────────────────────────────────────────────────

    def key_doc(self, doc_id: str) -> str:
        return f"doc:{doc_id}"

    def key_query(self, filters: dict, sort: list, limit: int, skip: int) -> str:
        raw = json.dumps({"f": filters, "s": sort, "l": limit, "k": skip}, sort_keys=True, default=str)
        h   = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"q:{h}"

    def key_user_query(self, user_id: str, filters: dict, limit: int) -> str:
        raw = json.dumps({"f": filters, "l": limit}, sort_keys=True, default=str)
        h   = hashlib.sha256(raw.encode()).hexdigest()[:12]
        return f"u:{user_id}:{h}"

    def _full(self, key: str) -> str:
        return f"repo:{self._col}:{key}"


# ── Module-level helpers ───────────────────────────────────────────────────────

def get_cache(collection: str) -> RepositoryCache:
    """Get a cache instance for a collection (no Redis, in-process only)."""
    return RepositoryCache(collection)


def get_cache_with_redis(collection: str, redis) -> RepositoryCache:
    """Get a cache instance with Redis backing."""
    return RepositoryCache(collection, redis)


def clear_all_caches() -> None:
    """Clear all in-process caches. Used in tests."""
    _local_cache.clear()
