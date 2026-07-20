"""
Distributed Tracing Engine — Phase XXXV.6

Generates globally unique Trace IDs and propagates them through every
subsystem via Python contextvars (async-safe, no thread-local issues).

Spans represent units of work within a trace. Both are persisted to
MongoDB for time-travel debugging.

Usage:
    # Middleware sets context for each request
    ctx = TraceContext(trace_id=new_trace_id(), request_id=new_request_id())
    set_trace_context(ctx)

    # Any code anywhere can read it
    trace_id = get_trace_id()

    # Create a span for a unit of work
    span = create_span("kg.update", "knowledge_graph", "update_nodes")
    try:
        ...
    finally:
        span.finish()
        await get_tracer().record_span(span)
"""
from __future__ import annotations

import uuid
import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_TRACES_COL = "obs_traces"
_SPANS_COL  = "obs_spans"


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class TraceContext:
    trace_id:       str
    request_id:     str
    user_id:        str | None = None
    mission_id:     str | None = None
    workspace_id:   str | None = None
    institution:    str | None = None
    correlation_id: str | None = None
    component:      str | None = None
    operation:      str | None = None
    path:           str | None = None
    method:         str | None = None
    metadata:       dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "trace_id":       self.trace_id,
            "request_id":     self.request_id,
            "user_id":        self.user_id,
            "mission_id":     self.mission_id,
            "workspace_id":   self.workspace_id,
            "institution":    self.institution,
            "correlation_id": self.correlation_id,
            "component":      self.component,
            "operation":      self.operation,
            "path":           self.path,
            "method":         self.method,
            "metadata":       self.metadata,
        }.items() if v is not None or k in ("trace_id", "request_id")}

    def enrich(self, **kwargs: Any) -> "TraceContext":
        """Return a new context with additional fields set."""
        d = self.__dict__.copy()
        d.update(kwargs)
        return TraceContext(**d)


@dataclass
class Span:
    span_id:     str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id:    str = "no-trace"
    parent_id:   str | None = None
    name:        str = ""
    component:   str = ""
    operation:   str = ""
    status:      str = "ok"       # ok | error | timeout
    error:       str | None = None
    started_at:  datetime = field(default_factory=datetime.utcnow)
    ended_at:    datetime | None = None
    duration_ms: float | None = None
    tags:        dict = field(default_factory=dict)

    def finish(self, status: str = "ok", error: str | None = None) -> "Span":
        self.ended_at    = datetime.utcnow()
        self.duration_ms = (self.ended_at - self.started_at).total_seconds() * 1000
        self.status      = status
        self.error       = error
        return self

    def to_dict(self) -> dict:
        return {
            "span_id":     self.span_id,
            "trace_id":    self.trace_id,
            "parent_id":   self.parent_id,
            "name":        self.name,
            "component":   self.component,
            "operation":   self.operation,
            "status":      self.status,
            "error":       self.error,
            "started_at":  self.started_at.isoformat(),
            "ended_at":    self.ended_at.isoformat() if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "tags":        self.tags,
        }


# ── Context propagation ───────────────────────────────────────────────────────

_trace_ctx: ContextVar[TraceContext | None] = ContextVar("trace_ctx", default=None)


def new_trace_id() -> str:
    return str(uuid.uuid4())


def new_request_id() -> str:
    return str(uuid.uuid4())[:8]


def set_trace_context(ctx: TraceContext) -> None:
    _trace_ctx.set(ctx)


def get_trace_context() -> TraceContext | None:
    return _trace_ctx.get()


def get_trace_id() -> str | None:
    ctx = _trace_ctx.get()
    return ctx.trace_id if ctx else None


def get_context_dict() -> dict:
    """Return full trace context as a dict (empty if no context active)."""
    ctx = _trace_ctx.get()
    return ctx.to_dict() if ctx else {}


def create_span(name: str, component: str, operation: str) -> Span:
    ctx = _trace_ctx.get()
    return Span(
        trace_id  = ctx.trace_id if ctx else "no-trace",
        name      = name,
        component = component,
        operation = operation,
    )


# ── Tracer (MongoDB persistence) ──────────────────────────────────────────────

class Tracer:
    """Stores traces and spans to MongoDB. All writes are best-effort."""

    def __init__(self, db: Any) -> None:
        self._db = db

    async def start_trace(self, ctx: TraceContext, path: str = "", method: str = "") -> None:
        try:
            doc = {
                **ctx.to_dict(),
                "path":       path,
                "method":     method,
                "started_at": datetime.utcnow().isoformat(),
                "status":     "active",
            }
            await self._db[_TRACES_COL].update_one(
                {"trace_id": ctx.trace_id},
                {"$setOnInsert": doc},
                upsert=True,
            )
        except Exception as exc:
            logger.debug("Tracer.start_trace: %s", exc)

    async def finish_trace(
        self,
        trace_id:    str,
        status:      str = "ok",
        status_code: int = 200,
        duration_ms: float = 0.0,
        error:       str | None = None,
    ) -> None:
        try:
            await self._db[_TRACES_COL].update_one(
                {"trace_id": trace_id},
                {"$set": {
                    "status":      status,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "error":       error,
                    "finished_at": datetime.utcnow().isoformat(),
                }},
            )
        except Exception as exc:
            logger.debug("Tracer.finish_trace: %s", exc)

    async def record_span(self, span: Span) -> None:
        try:
            await self._db[_SPANS_COL].insert_one(span.to_dict())
        except Exception as exc:
            logger.debug("Tracer.record_span: %s", exc)

    async def get_trace(self, trace_id: str) -> dict | None:
        try:
            return await self._db[_TRACES_COL].find_one({"trace_id": trace_id}, {"_id": 0})
        except Exception:
            return None

    async def get_spans(self, trace_id: str) -> list[dict]:
        try:
            return await self._db[_SPANS_COL].find(
                {"trace_id": trace_id}, {"_id": 0}
            ).sort("started_at", 1).to_list(500)
        except Exception:
            return []

    async def list_traces(
        self,
        limit:      int = 50,
        status:     str | None = None,
        user_id:    str | None = None,
        component:  str | None = None,
    ) -> list[dict]:
        try:
            filt: dict = {}
            if status:
                filt["status"] = status
            if user_id:
                filt["user_id"] = user_id
            if component:
                filt["component"] = component
            return await self._db[_TRACES_COL].find(
                filt, {"_id": 0}
            ).sort("started_at", -1).limit(limit).to_list(limit)
        except Exception:
            return []

    async def ensure_indexes(self) -> None:
        try:
            await self._db[_TRACES_COL].create_index("trace_id", unique=True)
            await self._db[_TRACES_COL].create_index("started_at")
            await self._db[_TRACES_COL].create_index("user_id")
            await self._db[_SPANS_COL].create_index("trace_id")
            await self._db[_SPANS_COL].create_index("started_at")
        except Exception as exc:
            logger.debug("Tracer.ensure_indexes: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_tracer: Tracer | None = None


def init_tracer(db: Any) -> Tracer:
    global _tracer
    _tracer = Tracer(db)
    return _tracer


def get_tracer() -> Tracer | None:
    return _tracer
