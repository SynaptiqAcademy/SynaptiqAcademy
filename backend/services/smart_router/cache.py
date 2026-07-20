"""RouterCache — three-level cache for routing decisions, prompt outputs, and templates."""
from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from threading import Lock


def _hash(data: str) -> str:
    return hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()


class _LRUCache:
    def __init__(self, max_size: int, ttl: float) -> None:
        self._max = max_size
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[object, float]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> object | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            val, expires = entry
            if time.monotonic() > expires:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return val

    def set(self, key: str, value: object) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = (value, time.monotonic() + self._ttl)
            if len(self._data) > self._max:
                self._data.popitem(last=False)

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._data)

    def stats(self) -> dict:
        with self._lock:
            return {"size": len(self._data), "max_size": self._max, "ttl_s": self._ttl}


class RouterCache:
    """Three-level cache: routing decisions, output responses, prompt templates."""

    def __init__(
        self,
        decision_ttl: float = 300.0,
        output_ttl: float = 3600.0,
        template_ttl: float = 86400.0,
    ) -> None:
        self._decisions = _LRUCache(max_size=5000, ttl=decision_ttl)
        self._outputs = _LRUCache(max_size=2000, ttl=output_ttl)
        self._templates = _LRUCache(max_size=500, ttl=template_ttl)
        self._hits = {"decisions": 0, "outputs": 0, "templates": 0}
        self._misses = {"decisions": 0, "outputs": 0, "templates": 0}
        self._lock = Lock()

    # ── Decision cache ────────────────────────────────────────────────────────

    def make_decision_key(self, feature: str, user_id: str) -> str:
        return _hash(f"decision:{feature}:{user_id}")

    def get_decision(self, key: str) -> dict | None:
        result = self._decisions.get(key)
        with self._lock:
            if result is not None:
                self._hits["decisions"] += 1
            else:
                self._misses["decisions"] += 1
        return result  # type: ignore

    def set_decision(self, key: str, decision: dict) -> None:
        self._decisions.set(key, decision)

    # ── Output cache (deterministic responses) ────────────────────────────────

    def make_output_key(
        self,
        feature: str,
        system_prompt: str,
        messages: list[dict],
    ) -> str:
        payload = json.dumps(
            {"f": feature, "s": system_prompt[:1000], "m": messages[-3:]},
            sort_keys=True,
        )
        return _hash(payload)

    def get_output(self, key: str) -> str | None:
        result = self._outputs.get(key)
        with self._lock:
            if result is not None:
                self._hits["outputs"] += 1
            else:
                self._misses["outputs"] += 1
        return result  # type: ignore

    def set_output(self, key: str, response_text: str) -> None:
        self._outputs.set(key, response_text)

    # ── Template cache ────────────────────────────────────────────────────────

    def get_template(self, key: str) -> str | None:
        return self._templates.get(key)  # type: ignore

    def set_template(self, key: str, template: str) -> None:
        self._templates.set(key, template)

    # ── Admin ─────────────────────────────────────────────────────────────────

    def clear(self, level: str = "all") -> None:
        if level in ("all", "decisions"):
            self._decisions.clear()
        if level in ("all", "outputs"):
            self._outputs.clear()
        if level in ("all", "templates"):
            self._templates.clear()

    def stats(self) -> dict:
        with self._lock:
            hits = dict(self._hits)
            misses = dict(self._misses)
        total_hits = sum(hits.values())
        total_miss = sum(misses.values())
        total = total_hits + total_miss
        return {
            "decision_cache": self._decisions.stats(),
            "output_cache": self._outputs.stats(),
            "template_cache": self._templates.stats(),
            "hit_counts": hits,
            "miss_counts": misses,
            "overall_hit_rate_pct": round(total_hits / total * 100, 1) if total > 0 else 0.0,
        }
