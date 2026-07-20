"""LRU+TTL cache for retrieval results."""
from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from threading import Lock

_MAX_SIZE = 2000


class RetrievalCache:
    def __init__(self, max_size: int = _MAX_SIZE, ttl: float = 120.0) -> None:
        self._max = max_size
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[list, float]] = OrderedDict()
        self._lock = Lock()

    def make_key(self, query: str, user_id: str, top_k: int, workspace_id: str | None) -> str:
        raw = json.dumps(
            {"q": query[:500], "u": user_id, "k": top_k, "w": workspace_id or ""},
            sort_keys=True,
        )
        return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()

    def get(self, key: str) -> list | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            results, expires = entry
            if time.monotonic() > expires:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return results

    def set(self, key: str, results: list) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = (results, time.monotonic() + self._ttl)
            if len(self._data) > self._max:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._data)
