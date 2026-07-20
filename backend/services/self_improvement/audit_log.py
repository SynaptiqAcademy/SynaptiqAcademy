"""Audit Log — immutable, bounded trail for all self-improvement actions."""
from __future__ import annotations

import threading
import time
import uuid

_MAX_ENTRIES = 5_000

_singleton:  "AuditLog | None" = None
_lock        = threading.Lock()


class AuditLog:
    def __init__(self):
        self._data_lock = threading.Lock()
        self._entries:  list[dict] = []

    def log(
        self,
        action:      str,
        engine_type: str        = "",
        details:     dict | None = None,
        actor:       str        = "system",
    ) -> dict:
        entry = {
            "entry_id":    str(uuid.uuid4()),
            "timestamp":   time.time(),
            "action":      action,
            "engine_type": engine_type,
            "actor":       actor,
            "details":     details or {},
        }
        with self._data_lock:
            self._entries.append(entry)
            if len(self._entries) > _MAX_ENTRIES:
                self._entries.pop(0)
        return entry

    def get_log(self, engine_type: str | None = None, limit: int = 100) -> list[dict]:
        with self._data_lock:
            src = [e for e in self._entries if e["engine_type"] == engine_type] if engine_type else self._entries
            return list(src[-limit:])

    def get_full_log(self, limit: int = 200) -> list[dict]:
        with self._data_lock:
            return list(self._entries[-limit:])

    def entry_count(self) -> int:
        with self._data_lock:
            return len(self._entries)


def get_audit_log() -> AuditLog:
    global _singleton
    with _lock:
        if _singleton is None:
            _singleton = AuditLog()
    return _singleton


def reset_audit_log() -> None:
    global _singleton
    with _lock:
        _singleton = None
