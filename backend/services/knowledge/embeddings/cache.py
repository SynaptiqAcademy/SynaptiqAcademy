"""LRU+TTL embedding cache — keyed by (provider, text_hash)."""
from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from threading import Lock

_MAX_SIZE = 50_000


def _text_key(provider_name: str, text: str) -> str:
    h = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
    return f"{provider_name}:{h}"


class EmbeddingCache:
    def __init__(self, max_size: int = _MAX_SIZE, ttl: float = 3600.0) -> None:
        self._max = max_size
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[list[float], float]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> list[float] | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            emb, expires_at = entry
            if time.monotonic() > expires_at:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return emb

    def set(self, key: str, embedding: list[float]) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = (embedding, time.monotonic() + self._ttl)
            if len(self._data) > self._max:
                self._data.popitem(last=False)

    def size(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def make_key(self, provider_name: str, text: str) -> str:
        return _text_key(provider_name, text)
