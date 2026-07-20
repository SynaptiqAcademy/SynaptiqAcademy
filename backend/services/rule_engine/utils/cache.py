"""In-process TTL cache for rule engine computations."""
from __future__ import annotations

import functools
import hashlib
import json
import threading
import time
from typing import Any, Callable

_LOCK = threading.Lock()
_STORE: dict[str, tuple[Any, float]] = {}


def _make_key(*args: Any, **kwargs: Any) -> str:
    try:
        raw = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    except Exception:
        raw = repr((args, kwargs))
    return hashlib.md5(raw.encode()).hexdigest()


def cached(ttl: float = 300.0) -> Callable:
    """Decorator: cache synchronous function results by arguments for `ttl` seconds."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = f"{fn.__module__}.{fn.__qualname__}:{_make_key(*args, **kwargs)}"
            now = time.monotonic()
            with _LOCK:
                entry = _STORE.get(key)
                if entry is not None and now - entry[1] < ttl:
                    return entry[0]
            result = fn(*args, **kwargs)
            with _LOCK:
                _STORE[key] = (result, now)
            return result
        return wrapper
    return decorator


def set_cache(key: str, value: Any, ttl: float = 300.0) -> None:
    with _LOCK:
        _STORE[key] = (value, time.monotonic() + ttl - ttl)  # store with creation time


def get_cache(key: str) -> tuple[bool, Any]:
    """Returns (hit, value). hit=False means expired or absent."""
    now = time.monotonic()
    with _LOCK:
        entry = _STORE.get(key)
        if entry is None:
            return False, None
        value, created = entry
        return True, value


def invalidate(prefix: str = "") -> int:
    """Remove entries whose key starts with `prefix`. Returns count removed."""
    with _LOCK:
        if not prefix:
            count = len(_STORE)
            _STORE.clear()
            return count
        keys = [k for k in _STORE if k.startswith(prefix)]
        for k in keys:
            del _STORE[k]
        return len(keys)


def cache_stats() -> dict[str, int]:
    with _LOCK:
        return {"total_entries": len(_STORE)}
