"""
Observability Middleware — Phase XXXV.6

FastAPI ASGI middleware that transparently injects observability into
every HTTP request without touching any route handler:

  1. Generate Trace ID + Request ID
  2. Set TraceContext in contextvars (propagates to all async code)
  3. Record request span to MongoDB (async, best-effort)
  4. Emit API latency metric
  5. Emit API request counter (tagged by method + path prefix)
  6. Add response headers: X-Trace-ID, X-Request-ID

The middleware is purely additive — it never modifies request/response
bodies or raises exceptions that would break the API.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .tracer import (
    TraceContext,
    new_trace_id,
    new_request_id,
    set_trace_context,
    get_tracer,
    create_span,
)
from .metrics import get_metrics, M_API_REQUESTS, M_API_ERRORS, M_API_LATENCY

logger = logging.getLogger(__name__)

# Paths that are high-frequency and don't need trace storage
_SKIP_TRACE_PATHS = {"/health", "/metrics", "/favicon.ico", "/openapi.json", "/docs", "/redoc"}

# Only store the first 2 path segments as the tag to limit cardinality
def _path_prefix(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    return "/" + "/".join(parts[:2]) if parts else "/"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Transparent observability middleware.
    Added AFTER all security/CORS/rate-limit middleware in server.py.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # ── Generate IDs ──────────────────────────────────────────────────────
        trace_id   = request.headers.get("X-Trace-ID")  or new_trace_id()
        request_id = request.headers.get("X-Request-ID") or new_request_id()

        # ── Extract context from request ──────────────────────────────────────
        user_id    = None
        mission_id = request.headers.get("X-Mission-ID")
        workspace  = request.headers.get("X-Workspace-ID")
        institution = request.headers.get("X-Institution")
        correlation = request.headers.get("X-Correlation-ID")

        # Try to read user from request.state (set by auth middleware)
        try:
            state_user = getattr(request.state, "user", None)
            if state_user and isinstance(state_user, dict):
                user_id = str(state_user.get("_id", ""))
        except Exception:
            pass

        ctx = TraceContext(
            trace_id       = trace_id,
            request_id     = request_id,
            user_id        = user_id,
            mission_id     = mission_id,
            workspace_id   = workspace,
            institution    = institution,
            correlation_id = correlation,
            component      = "api",
            operation      = f"{request.method} {request.url.path}",
            path           = request.url.path,
            method         = request.method,
        )
        set_trace_context(ctx)

        path   = request.url.path
        prefix = _path_prefix(path)
        skip   = path in _SKIP_TRACE_PATHS

        # ── Record trace start ────────────────────────────────────────────────
        tracer = get_tracer()
        if tracer and not skip:
            asyncio.ensure_future(tracer.start_trace(ctx, path=path, method=request.method))

        # ── Execute request ───────────────────────────────────────────────────
        t0 = time.monotonic()
        status_code = 500
        error_msg   = None
        try:
            response    = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            error_msg   = str(exc)
            status_code = 500
            raise
        finally:
            duration_ms = (time.monotonic() - t0) * 1000
            ok          = status_code < 400
            status_str  = "ok" if ok else "error"

            # ── Metrics (always, synchronous) ─────────────────────────────────
            try:
                m = get_metrics()
                m.inc(M_API_REQUESTS, tags={"method": request.method, "path": prefix})
                m.observe(M_API_LATENCY, duration_ms, tags={"path": prefix})
                if not ok:
                    m.inc(M_API_ERRORS, tags={"method": request.method, "path": prefix,
                                               "status": str(status_code)})
            except Exception:
                pass

            # ── Profiler ──────────────────────────────────────────────────────
            try:
                from obs.profiler import get_profiler
                get_profiler().record(
                    f"{request.method} {prefix}", duration_ms, component="api"
                )
            except Exception:
                pass

            # ── Finish trace (async, best-effort) ────────────────────────────
            if tracer and not skip:
                asyncio.ensure_future(tracer.finish_trace(
                    trace_id    = trace_id,
                    status      = status_str,
                    status_code = status_code,
                    duration_ms = duration_ms,
                    error       = error_msg,
                ))

        # ── Add trace headers to response ─────────────────────────────────────
        try:
            response.headers["X-Trace-ID"]   = trace_id
            response.headers["X-Request-ID"]  = request_id
        except Exception:
            pass

        return response
