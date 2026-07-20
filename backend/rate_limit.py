"""Centralised slowapi rate-limiter with automatic Redis → memory fallback.

Behaviour matrix:
  ┌──────────────────────────────┬──────────────────────────────────────────┐
  │ REDIS_URL                    │ Result                                   │
  ├──────────────────────────────┼──────────────────────────────────────────┤
  │ not set / empty              │ MemoryStorage (single-instance)          │
  │ Docker hostname resolvable   │ RedisStorage (distributed)               │
  │ Docker hostname unresolvable │ try localhost:same-port/credentials      │
  │ localhost also unreachable   │ MemoryStorage (graceful degradation)     │
  │ Redis dies at runtime        │ auto-fallback to MemoryStorage via       │
  │                              │ SlowAPI's in_memory_fallback_enabled     │
  │ Any other storage error      │ swallow_errors=True — log + continue     │
  └──────────────────────────────┴──────────────────────────────────────────┘

Redis is NEVER required.  No Redis error can ever propagate to an API endpoint
or return HTTP 500.
"""
from __future__ import annotations

import logging
import os
import socket
from urllib.parse import urlparse, urlunparse

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger("synaptiq.rate_limit")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    """Honour proxy chain (Kubernetes ingress sets X-Forwarded-For)."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


def _is_test() -> bool:
    return os.environ.get("APP_ENV", "").lower() == "test"


def _hostname_reachable(hostname: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if hostname:port resolves (DNS only, no TCP connect)."""
    old = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo(hostname, port)
        return True
    except (socket.gaierror, OSError):
        return False
    finally:
        socket.setdefaulttimeout(old)


def _resolve_redis_url(raw: str) -> str | None:
    """Resolve *raw* REDIS_URL to a usable URL, or None for in-memory fallback.

    Handles Docker-only hostnames gracefully: if the hostname in the URL cannot
    be resolved (e.g. ``synaptiq_redis`` outside Docker), we substitute
    ``localhost`` with the same port and credentials and try again.  If neither
    works, we return None so the rate limiter uses MemoryStorage.
    """
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
        hostname = parsed.hostname or ""
        port = parsed.port or 6379

        if not hostname:
            return raw  # no hostname to validate

        # 1. Try the URL as-is (works inside Docker / when Redis is local)
        if _hostname_reachable(hostname, port):
            return raw

        # 2. Try substituting localhost (works for local dev with Redis running)
        # Replace only the first occurrence so we don't corrupt URL-encoded passwords
        localhost_url = raw.replace(hostname, "localhost", 1)
        if _hostname_reachable("localhost", port):
            logger.info(
                "Rate limiter: hostname %r unresolvable — switched to localhost (%s)",
                hostname, localhost_url,
            )
            return localhost_url

        # 3. Neither works — degrade to memory
        logger.warning(
            "Rate limiter: Redis unreachable at %r (and localhost) — "
            "using in-memory storage; rate limits are per-process only",
            hostname,
        )
        return None
    except Exception as exc:
        logger.warning("Rate limiter: error resolving REDIS_URL — using in-memory: %s", exc)
        return None


def _storage_uri() -> str | None:
    """Return the resolved Redis URL for SlowAPI, or None for MemoryStorage."""
    raw = os.environ.get("REDIS_URL", "").strip()
    if not raw:
        logger.info("Rate limiter: REDIS_URL not set — using in-memory storage")
        return None
    resolved = _resolve_redis_url(raw)
    if resolved:
        logger.info("Rate limiter: Redis backend ready (%s)", resolved)
    else:
        logger.info("Rate limiter: using in-memory storage (Redis unavailable)")
    return resolved


# ── Limiter ────────────────────────────────────────────────────────────────────

limiter = Limiter(
    key_func=_client_ip,
    default_limits=[],
    storage_uri=_storage_uri(),
    enabled=not _is_test(),
    # When Redis becomes unreachable at runtime, SlowAPI automatically switches
    # to _fallback_storage (MemoryStorage) and sets _storage_dead=True.
    # It retries the real storage periodically and resets the flag on recovery.
    in_memory_fallback_enabled=True,
    # Last-resort safety net: if any storage error reaches the except clause
    # that the fallback path didn't handle, log it and allow the request through
    # rather than returning HTTP 500.
    swallow_errors=True,
)

# Default rate-limit policy (env-overridable).
# In APP_ENV=test the limiter is disabled so this value is never evaluated.
AUTH_RATE = os.environ.get("RATE_LIMIT_AUTH", "5/minute")
