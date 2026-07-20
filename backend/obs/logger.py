"""
Structured Logging — Phase XXXV.6

Provides a structured logging layer that:
  1. Enriches every log record with the active trace context
  2. Keeps a thread-safe in-memory ring buffer (last 5,000 records)
  3. Persists WARNING+ records to MongoDB `obs_logs` for searchability

Existing code needs no changes. Any logger retrieved via
`logging.getLogger(name)` automatically gets trace context injected
because the StructuredHandler is installed on the root logger.

get_logger(name) returns a pre-configured logger with the handler already
attached — preferred for new code in Phase XXXV.6+.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any

from .tracer import get_context_dict

_LOGS_COL = "obs_logs"
_BUFFER_SIZE = 5_000


# ── In-memory ring buffer ─────────────────────────────────────────────────────

class _LogBuffer:
    def __init__(self, maxlen: int = _BUFFER_SIZE) -> None:
        self._buf:  deque[dict] = deque(maxlen=maxlen)
        self._lock: threading.Lock = threading.Lock()

    def append(self, record: dict) -> None:
        with self._lock:
            self._buf.append(record)

    def query(
        self,
        level:     str | None = None,
        component: str | None = None,
        operation: str | None = None,
        trace_id:  str | None = None,
        user_id:   str | None = None,
        limit:     int = 100,
    ) -> list[dict]:
        with self._lock:
            docs = list(self._buf)
        # Newest first
        docs.reverse()
        results: list[dict] = []
        for d in docs:
            if level and d.get("level") != level.upper():
                continue
            if component and d.get("component") != component:
                continue
            if operation and d.get("operation") != operation:
                continue
            if trace_id and d.get("trace_id") != trace_id:
                continue
            if user_id and d.get("user_id") != user_id:
                continue
            results.append(d)
            if len(results) >= limit:
                break
        return results

    def recent(self, n: int = 100) -> list[dict]:
        with self._lock:
            docs = list(self._buf)
        docs.reverse()
        return docs[:n]

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()


_buffer = _LogBuffer()


def get_log_buffer() -> _LogBuffer:
    return _buffer


# ── Custom logging handler ────────────────────────────────────────────────────

class StructuredHandler(logging.Handler):
    """
    Logging handler that:
    - Injects active trace context into every LogRecord
    - Writes structured dict to the in-memory ring buffer
    - Async-writes WARNING+ to MongoDB (best-effort via scheduled task)
    """

    def __init__(self, db: Any = None) -> None:
        super().__init__()
        self._db = db
        self._pending: list[dict] = []
        self._lock = threading.Lock()

    def set_db(self, db: Any) -> None:
        self._db = db

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ctx = get_context_dict()
            doc: dict = {
                "timestamp":  datetime.utcfromtimestamp(record.created).isoformat(),
                "level":      record.levelname,
                "logger":     record.name,
                "component":  record.name.split(".")[0],
                "message":    self.format(record),
                "module":     record.module,
                "function":   record.funcName,
                "line":       record.lineno,
                # trace context
                "trace_id":      ctx.get("trace_id"),
                "request_id":    ctx.get("request_id"),
                "user_id":       ctx.get("user_id"),
                "mission_id":    ctx.get("mission_id"),
                "workspace_id":  ctx.get("workspace_id"),
                "institution":   ctx.get("institution"),
                "correlation_id": ctx.get("correlation_id"),
                "operation":     ctx.get("operation"),
            }
            # Remove None values to keep docs lean
            doc = {k: v for k, v in doc.items() if v is not None}

            _buffer.append(doc)

            if record.levelno >= logging.WARNING and self._db is not None:
                with self._lock:
                    self._pending.append(doc)
        except Exception:
            self.handleError(record)

    async def flush_to_db(self) -> int:
        """Persist pending WARNING+ records to MongoDB. Call periodically."""
        if not self._db:
            return 0
        with self._lock:
            batch, self._pending = self._pending[:], []
        if not batch:
            return 0
        try:
            await self._db[_LOGS_COL].insert_many(batch, ordered=False)
            return len(batch)
        except Exception as exc:
            logging.getLogger(__name__).debug("flush_to_db error: %s", exc)
            return 0


# ── Module-level handler (installed once) ─────────────────────────────────────

_handler: StructuredHandler | None = None


def install_structured_handler(db: Any | None = None) -> StructuredHandler:
    """
    Install the StructuredHandler on the root logger once.
    Safe to call multiple times — idempotent.
    """
    global _handler
    if _handler is not None:
        if db is not None:
            _handler.set_db(db)
        return _handler

    _handler = StructuredHandler(db=db)
    _handler.setLevel(logging.DEBUG)
    _handler.setFormatter(logging.Formatter("%(message)s"))

    root = logging.getLogger()
    # Avoid installing twice (e.g. during test reloads)
    for h in root.handlers:
        if isinstance(h, StructuredHandler):
            _handler = h
            if db is not None:
                h.set_db(db)
            return h
    root.addHandler(_handler)
    return _handler


def get_structured_handler() -> StructuredHandler | None:
    return _handler


def get_logger(name: str) -> logging.Logger:
    """Return a standard Python logger. The StructuredHandler is on root."""
    return logging.getLogger(name)


async def flush_logs(db: Any | None = None) -> int:
    """Persist pending WARNING+ logs to MongoDB. Call from periodic task."""
    if _handler is None:
        return 0
    if db is not None:
        _handler.set_db(db)
    return await _handler.flush_to_db()


async def search_logs_in_db(
    db:        Any,
    level:     str | None = None,
    component: str | None = None,
    trace_id:  str | None = None,
    user_id:   str | None = None,
    from_ts:   str | None = None,
    to_ts:     str | None = None,
    limit:     int = 100,
) -> list[dict]:
    """Search persisted (WARNING+) logs in MongoDB."""
    try:
        filt: dict = {}
        if level:
            filt["level"] = level.upper()
        if component:
            filt["component"] = component
        if trace_id:
            filt["trace_id"] = trace_id
        if user_id:
            filt["user_id"] = user_id
        if from_ts or to_ts:
            ts_filt: dict = {}
            if from_ts:
                ts_filt["$gte"] = from_ts
            if to_ts:
                ts_filt["$lte"] = to_ts
            filt["timestamp"] = ts_filt
        return await db[_LOGS_COL].find(
            filt, {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
    except Exception:
        return []
