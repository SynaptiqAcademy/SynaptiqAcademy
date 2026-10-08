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
    """Rate-limit key: the client address from trusted proxy headers only
    (services/client_ip.py). Never the leftmost X-Forwarded-For entry, which
    the client controls."""
    from services.client_ip import client_ip
    return client_ip(request) or get_remote_address(request)


def _is_test() -> bool:
    return os.environ.get("APP_ENV", "").lower() == "test"


def _is_production() -> bool:
    return os.environ.get("APP_ENV", "development").lower() in ("prod", "production")


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

    Handles Docker-only hostnames gracefully outside production: if the
    hostname in the URL cannot be resolved (e.g. ``synaptiq_redis`` outside
    Docker), we substitute ``localhost`` with the same port and credentials
    and try again. In production, an unresolvable hostname means REDIS_URL
    is misconfigured for this deployment — substituting localhost there
    would never work and would only mask the real problem, so we log it
    plainly and degrade to MemoryStorage instead of guessing.
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

        if _is_production():
            logger.error(
                "Rate limiter: REDIS_URL hostname %r does not resolve in this "
                "environment — using in-memory storage. This almost always means "
                "REDIS_URL is set to the wrong value for this deployment. "
                "Check the REDIS_URL environment variable.",
                hostname,
            )
            return None

        # 2. Non-production convenience: try substituting localhost
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


def _redact(url: str) -> str:
    """Connection string without credentials, safe for logs."""
    try:
        p = urlparse(url)
        host = p.hostname or ""
        port = f":{p.port}" if p.port else ""
        return f"{p.scheme}://{host}{port}"
    except Exception:
        return "<unparseable>"


def _storage_uri() -> str | None:
    """The resolved Redis URL, or None when Redis is not usable."""
    raw = os.environ.get("REDIS_URL", "").strip()
    return _resolve_redis_url(raw) if raw else None


def _mongo_uri() -> str:
    return (os.environ.get("MONGODB_URI", "").strip()
            or os.environ.get("MONGO_URL", "").strip())


def _storage_config() -> tuple[str | None, dict]:
    """(storage_uri, storage_options) for SlowAPI.

    Limits must be shared by every worker process and replica, otherwise each
    process enforces its own copy (2 workers = twice the allowance) and a
    restart resets them. Order:
      1. Redis, when REDIS_URL is set and resolvable.
      2. MongoDB (the application database, in dedicated rate_limit_*
         collections with TTL indexes), when no Redis is configured.
      3. Per-process memory — tests, or RATE_LIMIT_STORAGE=memory.
    """
    choice = os.environ.get("RATE_LIMIT_STORAGE", "auto").strip().lower()
    if choice == "memory" or _is_test():
        logger.info("Rate limiter: in-memory storage (per process)")
        return None, {}

    raw = os.environ.get("REDIS_URL", "").strip()
    if raw and choice in ("auto", "redis"):
        resolved = _storage_uri()
        if resolved:
            logger.info("Rate limiter: Redis backend (%s)", _redact(resolved))
            return resolved, {}

    mongo = _mongo_uri()
    if mongo and choice in ("auto", "mongodb"):
        db_name = (os.environ.get("MONGODB_DB_NAME", "").strip()
                   or os.environ.get("DB_NAME", "").strip() or "synaptiq")
        logger.info("Rate limiter: shared MongoDB backend (%s, db=%s)", _redact(mongo), db_name)
        return mongo, {
            "database_name": db_name,
            "counter_collection_name": "rate_limit_counters",
            "window_collection_name": "rate_limit_windows",
            "serverSelectionTimeoutMS": 3000,
            "connectTimeoutMS": 3000,
            "socketTimeoutMS": 3000,
        }

    logger.warning("Rate limiter: no shared storage configured — limits are per process")
    return None, {}


_STORAGE_URI, _STORAGE_OPTIONS = _storage_config()


# ── Limiter ────────────────────────────────────────────────────────────────────

limiter = Limiter(
    key_func=_client_ip,
    default_limits=[],
    storage_uri=_STORAGE_URI,
    storage_options=_STORAGE_OPTIONS,
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

# General authenticated-write policy — comment creation, wiki search, and
# similar endpoints that are cheap individually but abusable at volume
# (notification-spam via comments, repeated full-collection scans via
# search). Looser than AUTH_RATE since these are behind auth + real
# membership checks already, not a credential-stuffing surface.
WRITE_RATE = os.environ.get("RATE_LIMIT_WRITE", "30/minute")

# Public, unauthenticated preview surface (the landing-page "what are you
# researching?" demo, Phase 9A Part 2 §19) — IP-keyed since there's no user
# yet. Looser than AUTH_RATE (this is read-only and deterministic, no AI
# cost) but still real: unauthenticated + no DB write means it's the
# cheapest possible target for a scripted loop.
PUBLIC_DEMO_RATE = os.environ.get("RATE_LIMIT_PUBLIC_DEMO", "10/minute")

_public_demo_rate_item = None


def check_public_demo_rate_limit(ip: str) -> None:
    """Raise HTTPException(429) if `ip` exceeds PUBLIC_DEMO_RATE.

    Same fail-open-on-backend-error pattern as check_ai_rate_limit /
    check_write_rate_limit — an unreachable rate-limit store must never
    block a legitimate anonymous visitor trying the product.
    """
    if not limiter.enabled:
        return
    global _public_demo_rate_item
    try:
        if _public_demo_rate_item is None:
            from limits import parse
            _public_demo_rate_item = parse(PUBLIC_DEMO_RATE)
        if not limiter.limiter.hit(_public_demo_rate_item, "public_demo", ip):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a moment and try again.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Public demo rate limiter check failed (allowing request): %s", exc)


# Per-user AI-action policy — every credit-billed AI feature (research
# assistant, manuscript review, literature review, collaborator matching,
# etc. — ~25 routers) funnels through services.credits_service.consume_credits
# before it calls out to a real LLM provider. Rate limiting there, keyed by
# user id rather than IP, is the single chokepoint that stops one account
# (compromised or scripted) from bursting through the shared smart_router
# daily/monthly $ budget and denying AI service to everyone else, without
# having to duplicate a @limiter.limit decorator across every AI endpoint.
AI_ACTION_RATE = os.environ.get("RATE_LIMIT_AI_ACTION", "20/minute")

_ai_rate_item = None


def check_ai_rate_limit(user_id: str) -> None:
    """Raise HTTPException(429) if `user_id` exceeds AI_ACTION_RATE.

    Reuses the same slowapi Limiter/storage backend as route-level limits
    (Redis when configured, in-memory otherwise) so behaviour under a
    multi-process deployment stays consistent with the rest of the app.
    Fails open on any backend error — an unreachable rate-limit store must
    never block a legitimate paid AI request.
    """
    if not limiter.enabled:
        return
    global _ai_rate_item
    try:
        if _ai_rate_item is None:
            from limits import parse
            _ai_rate_item = parse(AI_ACTION_RATE)
        if not limiter.limiter.hit(_ai_rate_item, "ai_action", user_id):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Too many AI requests. Please slow down and try again shortly.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("AI rate limiter check failed (allowing request): %s", exc)


_write_rate_item = None


def check_write_rate_limit(user_id: str, *, bucket: str = "write") -> None:
    """Raise HTTPException(429) if `user_id` exceeds WRITE_RATE for `bucket`.

    P1 Phase 8E: collaboration-request sending is a new abuse surface (mass
    invitations, automated outreach) — this is the same per-user chokepoint
    pattern as check_ai_rate_limit above, reusing WRITE_RATE (already
    defined for exactly this "cheap individually, abusable at volume"
    class of authenticated write) instead of introducing a new constant or
    limiter. `bucket` namespaces the hit-count key so unrelated write
    endpoints reusing this helper don't share one counter.
    """
    if not limiter.enabled:
        return
    global _write_rate_item
    try:
        if _write_rate_item is None:
            from limits import parse
            _write_rate_item = parse(WRITE_RATE)
        if not limiter.limiter.hit(_write_rate_item, bucket, user_id):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down and try again shortly.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Write rate limiter check failed (allowing request): %s", exc)
