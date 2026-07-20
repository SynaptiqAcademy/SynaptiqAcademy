"""Autonomous Research Agents — Shared memory bus (Phase XIII).

Thread-safe, session-scoped key-value store shared between all agents in a
workflow execution. Each execution gets an isolated namespace.
"""
from __future__ import annotations

import threading
from typing import Any


class MemoryBus:
    """Thread-safe shared memory for inter-agent communication within a session."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._store: dict[str, Any] = {}
        self._lock = threading.Lock()

    def write(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = value

    def read(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._store.get(key, default)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._store)

    def merge(self, data: dict) -> None:
        """Merge a dict into the bus without overwriting existing keys."""
        with self._lock:
            for k, v in data.items():
                if k not in self._store:
                    self._store[k] = v

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


class MemoryBusRegistry:
    """Global registry of active MemoryBus instances, one per session."""

    _sessions: dict[str, MemoryBus] = {}
    _lock = threading.Lock()

    @classmethod
    def get_or_create(cls, session_id: str) -> MemoryBus:
        with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = MemoryBus(session_id)
            return cls._sessions[session_id]

    @classmethod
    def release(cls, session_id: str) -> None:
        with cls._lock:
            cls._sessions.pop(session_id, None)

    @classmethod
    def active_sessions(cls) -> list[str]:
        with cls._lock:
            return list(cls._sessions.keys())
