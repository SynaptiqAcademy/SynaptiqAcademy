"""API Monitoring Middleware.

Tracks per-endpoint daily aggregate statistics using upsert/$inc so storage
stays bounded (one document per endpoint per day, not one per request).
Error requests (4xx/5xx) are also logged individually for incident review.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_SKIP_PREFIXES = (
    "/api/admin/x/api-monitor",  # avoid recursive self-logging
    "/static",
    "/favicon",
    "/openapi",
    "/docs",
    "/redoc",
    "/healthz",
)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _normalize_path(path: str) -> str:
    """Collapse dynamic segments to keep cardinality low.
    /api/users/abc123/details → /api/users/{id}/details
    """
    import re
    path = re.sub(r"/([\w]{24})", "/{id}", path)       # ObjectIds
    path = re.sub(r"/(\d+)", "/{n}", path)              # numeric ids
    path = re.sub(r"/[0-9a-f-]{36}", "/{uuid}", path)  # UUIDs
    return path


class APIMonitorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        t0 = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - t0) * 1000, 2)

        method      = request.method
        status_code = response.status_code
        endpoint    = _normalize_path(path)
        today       = _today()
        now         = datetime.now(timezone.utc).isoformat()

        try:
            from db import get_db, is_db_down  # lazy import — DB not yet ready at module load time
            from repo.shim import make_db_proxy

            # RC1 AUDIT FINDING: this middleware runs on every request. With no
            # circuit-breaker check, a Mongo outage meant every single API call
            # (including ones that don't touch Mongo themselves, e.g. an
            # unauthenticated /api/auth/me returning 401) paid the full
            # connection-timeout cost here, silently swallowed by the except
            # below — reproduced live: /api/health, /api/auth/me, and
            # /api/auth/logout all measured 8.7-13.0s during an outage, purely
            # from this stats write, before this fix.
            if is_db_down():
                return response

            db = make_db_proxy(get_db(), system=True)
            inc = {
                "total_requests": 1,
                "total_duration_ms": duration_ms,
            }
            if 200 <= status_code < 300:
                inc["ok_count"] = 1
            elif 400 <= status_code < 500:
                inc["client_errors"] = 1
            elif status_code >= 500:
                inc["server_errors"] = 1

            await db.api_stats.update_one(
                {"endpoint": endpoint, "method": method, "date": today},
                {
                    "$inc": inc,
                    "$max": {"max_duration_ms": duration_ms},
                    "$min": {"min_duration_ms": duration_ms},
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )

            # Individual log only for server errors
            if status_code >= 500:
                await db.api_error_log.insert_one({
                    "endpoint": endpoint,
                    "method":   method,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "ip":        request.client.host if request.client else None,
                    "created_at": now,
                })
        except Exception:
            pass  # Never let monitoring crash the request

        return response
