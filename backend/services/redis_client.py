"""Async Redis client with connection pooling and graceful degradation.

All public functions degrade gracefully when Redis is unavailable —
the platform continues in single-instance mode without distributed
cache, pub/sub, or locking. No exception ever propagates to callers.

Environment detection:
  If REDIS_URL contains a Docker-only hostname (e.g. synaptiq_redis) that cannot
  be resolved outside Docker, the client automatically substitutes localhost so
  local development works without Docker.

Required env var:
  REDIS_URL             — connection URI (no default; must be explicitly set in production)

Optional:
  REDIS_MAX_CONNECTIONS — pool size (default 20)
  REDIS_SOCKET_TIMEOUT  — socket / connect timeout in seconds (default 3)
"""
from __future__ import annotations

import logging
import os
import socket
import time
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("synaptiq.redis")

_client: Optional["redis.asyncio.Redis"] = None  # type: ignore[name-defined]

# Retry-from-cold-start cooldown (RC production blocker fix): `get_redis()`'s
# reconnect branch below only fired when a previously-live `_client` went bad
# mid-request — if Redis was simply unreachable at `init_redis()` time (the
# common case: Redis not up yet when this process boots), `_client` stayed
# `None` forever and no caller ever re-attempted a connection for the rest of
# the process's life. This cooldown lets `get_redis()` retry periodically
# from a cold `None` state too, without hammering a down Redis on every call.
_RETRY_COOLDOWN_SECONDS = float(os.environ.get("REDIS_RETRY_COOLDOWN_SECONDS", "15"))
_last_cold_retry: float = 0.0


def _resolve_url(raw: str) -> str:
    """Return a usable Redis URL from *raw*, substituting localhost when the
    original hostname (e.g. a Docker service name) cannot be resolved.
    Returns empty string if Redis is definitively unavailable."""
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        hostname = parsed.hostname or ""
        port = parsed.port or 6379
        if not hostname:
            return raw

        old = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(1)
            socket.getaddrinfo(hostname, port)
            return raw  # hostname resolves — use as-is (Docker / local Redis)
        except (socket.gaierror, OSError):
            pass
        finally:
            socket.setdefaulttimeout(old)

        # Hostname unresolvable — try localhost with same port/credentials
        localhost_url = raw.replace(hostname, "localhost", 1)
        try:
            socket.setdefaulttimeout(old)
            socket.setdefaulttimeout(1)
            socket.getaddrinfo("localhost", port)
            logger.info(
                "Redis hostname %r unresolvable — switched to localhost (%s)",
                hostname, localhost_url,
            )
            return localhost_url
        except (socket.gaierror, OSError):
            pass
        finally:
            socket.setdefaulttimeout(old)

        logger.warning(
            "Redis unreachable at %r (and localhost) — running without Redis",
            hostname,
        )
        return ""
    except Exception as exc:
        logger.warning("Error resolving REDIS_URL — running without Redis: %s", exc)
        return ""


def _url() -> str:
    raw = os.environ.get("REDIS_URL", "").strip()
    if not raw:
        logger.debug("REDIS_URL not set — Redis features disabled")
        return ""
    return _resolve_url(raw)


def _pool_size() -> int:
    return int(os.environ.get("REDIS_MAX_CONNECTIONS", "20"))


def _timeout() -> float:
    return float(os.environ.get("REDIS_SOCKET_TIMEOUT", "3"))


async def init_redis() -> None:
    """Open the connection pool and verify connectivity. Call at server startup."""
    global _client
    url = _url()
    if not url:
        logger.warning(
            "REDIS_URL not set — running in degraded mode "
            "(no distributed cache, pub/sub, or rate-limit persistence)"
        )
        return
    try:
        import redis.asyncio as aioredis  # type: ignore[import]
        from redis.asyncio.retry import Retry
        from redis.backoff import ExponentialBackoff
        from redis.exceptions import BusyLoadingError, ConnectionError, TimeoutError

        retry = Retry(ExponentialBackoff(cap=8, base=0.5), retries=3)
        _client = aioredis.from_url(
            url,
            max_connections=_pool_size(),
            socket_connect_timeout=_timeout(),
            socket_timeout=_timeout(),
            socket_keepalive=True,
            decode_responses=True,
            retry_on_timeout=True,
            retry=retry,
            retry_on_error=[BusyLoadingError, ConnectionError, TimeoutError],
            health_check_interval=30,
        )
        await _client.ping()
        logger.info("Redis connected (pool=%d, timeout=%.1fs)", _pool_size(), _timeout())
    except Exception as exc:
        logger.warning(
            "Redis unavailable at startup — degraded mode "
            "(no distributed cache, pub/sub, or rate-limit persistence): %s", exc
        )
        _client = None


async def get_redis() -> Optional["redis.asyncio.Redis"]:  # type: ignore[name-defined]
    """Return the async Redis client, or None if unavailable.

    Attempts a reconnect if the connection was lost since startup, and — if
    Redis was never reachable at startup at all — retries from cold every
    `_RETRY_COOLDOWN_SECONDS` so a Redis instance that comes up after this
    process started is picked up automatically, no restart required.
    Callers must treat None as "Redis unavailable" and degrade gracefully.
    """
    global _client, _last_cold_retry
    if _client is None:
        now = time.monotonic()
        # Check the cooldown BEFORE calling _url() — _url() does a blocking
        # socket.getaddrinfo() DNS resolution, and with many concurrent cold
        # callers (lock polling, queue polling) this branch is hit far more
        # than once per cooldown window. Gate the expensive call itself, not
        # just init_redis(), or every caller re-triggers the DNS lookup.
        if (now - _last_cold_retry) < _RETRY_COOLDOWN_SECONDS:
            return None
        _last_cold_retry = now
        if not _url():
            return None
        try:
            await init_redis()
        except Exception:
            pass
        return _client
    try:
        await _client.ping()
        return _client
    except Exception:
        # Connection dropped — attempt one reconnect
        try:
            await _client.aclose()
        except Exception:
            pass
        _client = None
        try:
            await init_redis()
        except Exception:
            pass
        return _client


async def close_redis() -> None:
    """Gracefully close the connection pool. Call at server shutdown."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
            logger.info("Redis connection closed")
        except Exception:
            pass
        _client = None


async def health_check() -> dict:
    """Redis health summary for the /admin/health endpoint."""
    r = await get_redis()
    if r is None:
        return {"status": "unavailable", "url": _url()}
    try:
        info = await r.info("server")
        return {
            "status": "ok",
            "url": _url(),
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
