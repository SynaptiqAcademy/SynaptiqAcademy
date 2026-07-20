"""TTL-based response cache for deterministic local AI responses."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict

logger = logging.getLogger("synaptiq.local_ai.cache")

# Features whose responses are stable enough to cache
_CACHEABLE_FEATURES: frozenset[str] = frozenset({
    "grammar_correction",
    "academic_proofreading",
    "translation",
    "keyword_extraction_local",
    "title_generation",
    "subtitle_generation",
    "bullet_points",
    "plain_language_explanation",
    "outline_generation",
    "summarization",
    "document_summarization",
    "section_summarization",
    "paragraph_summarization",
})


def is_cacheable(feature: str) -> bool:
    return feature in _CACHEABLE_FEATURES


def make_cache_key(feature: str, system: str, messages: list[dict]) -> str:
    payload = json.dumps(
        {"f": feature, "s": system, "m": messages},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: str, ttl: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl


class LocalResponseCache:
    """LRU + TTL in-memory cache. Thread-safe."""

    def __init__(self, ttl_seconds: float = 300.0, max_size: int = 1000) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> str | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                self._misses += 1
                return None
            # LRU: move to end
            self._store.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key: str, value: str) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = _CacheEntry(value, self._ttl)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            self._hits = 0
            self._misses = 0
            return count

    def evict_expired(self) -> int:
        now = time.monotonic()
        with self._lock:
            expired = [k for k, e in self._store.items() if now > e.expires_at]
            for k in expired:
                del self._store[k]
            return len(expired)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._store),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(self._hits / total * 100, 1) if total else 0.0,
                "ttl_seconds": self._ttl,
            }
