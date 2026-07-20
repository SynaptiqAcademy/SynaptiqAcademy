"""
Redis resilience integration tests.

Verifies that:
  1. Rate limiter uses MemoryStorage when REDIS_URL is empty
  2. Rate limiter survives Redis connection failures (never returns HTTP 500)
  3. All /api/auth/* endpoints work with Redis completely disabled
  4. Docker hostname detection falls back to localhost automatically
  5. redis_client._resolve_url handles Docker vs local hostnames
  6. Backend starts successfully with REDIS_URL pointing to a dead host

Run:
    cd backend && python -m pytest tests/test_redis_resilience.py -v
"""
from __future__ import annotations

import os
import socket
import importlib
import types
import uuid
from unittest.mock import patch, MagicMock

import pytest

# ── Env setup (must run before any server.py import) ──────────────────────────

os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("EMAIL_VERIFICATION_REQUIRED", "0")
os.environ.setdefault("EXPOSE_RESET_TOKEN", "1")
os.environ.setdefault("MONGODB_URI", os.environ.get("MONGO_URL", "mongodb://localhost:27017/"))
os.environ.setdefault("MONGODB_DB_NAME", os.environ.get("DB_NAME", "synaptiq_test"))
os.environ.setdefault("MONGO_URL", os.environ["MONGODB_URI"])
os.environ.setdefault("DB_NAME", os.environ["MONGODB_DB_NAME"])
os.environ.setdefault("JWT_SECRET", "TestSecret-xK9mP2nQ7vR4tL8wB5hZ3cA0u1Y6sJ")
os.environ.setdefault("ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("EMAIL_DRY_RUN", "1")


# ── Unit tests: URL resolution ────────────────────────────────────────────────

class TestRedisUrlResolution:
    """Tests for rate_limit._resolve_redis_url and redis_client._resolve_url."""

    def test_empty_url_returns_none_ratelimit(self):
        from rate_limit import _resolve_redis_url
        assert _resolve_redis_url("") is None

    def test_empty_url_returns_empty_redis_client(self):
        from services.redis_client import _resolve_url
        assert _resolve_url("") == ""

    def test_resolvable_hostname_returned_unchanged(self):
        """localhost is always resolvable — URL must be returned as-is."""
        from rate_limit import _resolve_redis_url
        url = "redis://localhost:6379/0"
        # localhost always resolves
        result = _resolve_redis_url(url)
        # Either the original URL or None (if port 6379 refuses connection)
        # but it must NOT raise and must not return a different URL
        assert result is None or result == url

    def test_docker_hostname_falls_back_to_localhost(self):
        """When Docker hostname is unresolvable, substitute localhost."""
        from rate_limit import _resolve_redis_url

        # Mock socket.getaddrinfo: fail for Docker hostname, succeed for localhost
        original = socket.getaddrinfo

        def fake_getaddrinfo(host, port, *a, **kw):
            if host == "synaptiq_redis":
                raise socket.gaierror("Name or service not known")
            return original(host, port, *a, **kw)

        with patch("rate_limit.socket.getaddrinfo", side_effect=fake_getaddrinfo):
            url = "redis://:secret@synaptiq_redis:6379/0"
            result = _resolve_redis_url(url)
            # Should substitute localhost (may still return None if localhost:6379 doesn't answer)
            # Key assertion: must not raise, must not return the Docker URL unchanged
            if result is not None:
                assert "localhost" in result
                assert "synaptiq_redis" not in result

    def test_both_hosts_unresolvable_returns_none(self):
        """When neither Docker host nor localhost resolves, return None."""
        from rate_limit import _resolve_redis_url

        with patch("rate_limit.socket.getaddrinfo", side_effect=socket.gaierror("fail")):
            result = _resolve_redis_url("redis://:pw@synaptiq_redis:6379/0")
            assert result is None

    def test_redis_client_docker_hostname_falls_back(self):
        from services.redis_client import _resolve_url

        original = socket.getaddrinfo

        def fake(host, port, *a, **kw):
            if host == "synaptiq_redis":
                raise socket.gaierror("Name or service not known")
            return original(host, port, *a, **kw)

        with patch("services.redis_client.socket.getaddrinfo", side_effect=fake):
            url = "redis://:pw@synaptiq_redis:6379/0"
            result = _resolve_url(url)
            if result:
                assert "localhost" in result

    def test_redis_client_both_unresolvable_returns_empty(self):
        from services.redis_client import _resolve_url

        with patch("services.redis_client.socket.getaddrinfo", side_effect=socket.gaierror("fail")):
            result = _resolve_url("redis://:pw@synaptiq_redis:6379/0")
            assert result == ""


# ── Unit tests: Limiter construction ─────────────────────────────────────────

class TestLimiterConstruction:
    """Verify the Limiter has resilience flags enabled."""

    def test_limiter_has_swallow_errors(self):
        from rate_limit import limiter
        assert limiter._swallow_errors is True

    def test_limiter_has_in_memory_fallback_enabled(self):
        from rate_limit import limiter
        assert limiter._in_memory_fallback_enabled is True

    def test_limiter_has_fallback_storage(self):
        """SlowAPI creates _fallback_limiter when in_memory_fallback_enabled=True."""
        from rate_limit import limiter
        assert limiter._fallback_limiter is not None

    def test_limiter_disabled_in_test_mode(self):
        """In APP_ENV=test the limiter must be disabled to avoid test interference."""
        from rate_limit import limiter
        assert limiter.enabled is False


# ── Unit tests: Redis client degradation ─────────────────────────────────────

class TestRedisClientDegradation:
    """redis_client functions must never raise when Redis is unavailable."""

    @pytest.mark.anyio
    async def test_get_redis_returns_none_when_not_initialised(self):
        """Before init_redis(), get_redis() must return None gracefully."""
        # Import fresh to avoid cross-test state
        import services.redis_client as rc
        original_client = rc._client
        rc._client = None
        try:
            result = await rc.get_redis()
            assert result is None
        finally:
            rc._client = original_client

    @pytest.mark.anyio
    async def test_init_redis_with_unresolvable_host(self):
        """init_redis() must not raise even with a completely invalid URL."""
        import services.redis_client as rc
        original_url = os.environ.get("REDIS_URL", "")
        os.environ["REDIS_URL"] = "redis://this-host-does-not-exist-xyz:6379/0"
        original_client = rc._client
        try:
            # Should complete without raising
            await rc.init_redis()
            # _client should be None — couldn't connect
            assert rc._client is None
        finally:
            os.environ["REDIS_URL"] = original_url
            rc._client = original_client

    @pytest.mark.anyio
    async def test_health_check_returns_unavailable_without_redis(self):
        import services.redis_client as rc
        original_client = rc._client
        rc._client = None
        try:
            result = await rc.health_check()
            assert result["status"] == "unavailable"
        finally:
            rc._client = original_client


# ── Integration tests: Auth endpoints with Redis disabled ─────────────────────

class TestAuthEndpointsWithoutRedis:
    """All /api/auth/* endpoints must work when Redis is completely disabled."""

    @pytest.fixture(scope="class")
    def client(self):
        from starlette.testclient import TestClient
        from server import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    @pytest.fixture(scope="class")
    def unique_email(self):
        return f"redis-test-{uuid.uuid4().hex[:8]}@example.com"

    def _csrf(self, client):
        r = client.get("/api/auth/csrf-token")
        token = r.json().get("csrf_token", "") if r.status_code == 200 else ""
        if not token:
            return {}
        cookies = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
        return {"X-CSRF-Token": token, "Cookie": cookies}

    def test_register_works_without_redis(self, client, unique_email):
        """POST /api/auth/register must not 500 when Redis is disabled."""
        h = self._csrf(client)
        r = client.post(
            "/api/auth/register",
            json={"full_name": "Redis Test", "email": unique_email, "password": "TestPass1!"},
            headers=h,
        )
        assert r.status_code not in (500, 502, 503), (
            f"Register returned {r.status_code} — Redis may be causing 500. Body: {r.text[:300]}"
        )

    def test_login_works_without_redis(self, client, unique_email):
        """POST /api/auth/login must not 500 when Redis is disabled."""
        h = self._csrf(client)
        r = client.post(
            "/api/auth/login",
            json={"email": unique_email, "password": "TestPass1!"},
            headers=h,
        )
        # 200 (success) or 401 (wrong creds) or 422 (validation) are all fine.
        # 500 means Redis error propagated — that's the bug we're fixing.
        assert r.status_code != 500, (
            f"Login returned 500 — Redis error propagated. Body: {r.text[:300]}"
        )

    def test_forgot_password_works_without_redis(self, client, unique_email):
        """POST /api/auth/forgot-password must not 500."""
        h = self._csrf(client)
        r = client.post(
            "/api/auth/forgot-password",
            json={"email": unique_email},
            headers=h,
        )
        assert r.status_code != 500, (
            f"Forgot password returned 500. Body: {r.text[:300]}"
        )

    def test_csrf_token_works_without_redis(self, client):
        """GET /api/auth/csrf-token must always work."""
        r = client.get("/api/auth/csrf-token")
        assert r.status_code == 200


# ── Integration tests: Rate limit fallback ────────────────────────────────────

class TestRateLimitFallback:
    """Verify rate limiter degrades gracefully when storage errors occur."""

    def test_storage_error_swallowed_by_limiter(self):
        """Simulate a Redis error during _check_request_limit — must not raise."""
        from rate_limit import limiter
        from starlette.datastructures import Headers
        from starlette.requests import Request as StarletteRequest

        # Build a minimal ASGI Request
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/login",
            "query_string": b"",
            "headers": [(b"x-forwarded-for", b"1.2.3.4")],
        }
        request = StarletteRequest(scope)

        # Patch the underlying storage to raise ConnectionError
        from redis.exceptions import ConnectionError as RedisConnError
        # limits library uses .storage (public), not ._storage
        storage_attr = "storage" if hasattr(limiter._limiter, "storage") else "_storage"
        original_storage = getattr(limiter._limiter, storage_attr)

        class BrokenStorage:
            def incr(self, *a, **kw):
                raise RedisConnError("synaptiq_redis:6379 — connection refused")
            def get(self, *a, **kw):
                raise RedisConnError("synaptiq_redis:6379 — connection refused")
            def get_expiry(self, *a, **kw):
                raise RedisConnError()
            def check(self):
                return False
            def reset(self):
                return 0
            def clear(self, *a, **kw):
                pass

        setattr(limiter._limiter, storage_attr, BrokenStorage())
        limiter._storage_dead = False
        limiter.enabled = True  # temporarily enable for this test

        try:
            # _check_request_limit must not raise (swallow_errors=True saves us)
            limiter._check_request_limit(request, None, in_middleware=True)
        except Exception as exc:
            pytest.fail(
                f"_check_request_limit raised {type(exc).__name__}: {exc} — "
                "Redis errors must be swallowed, not propagated"
            )
        finally:
            setattr(limiter._limiter, storage_attr, original_storage)
            limiter._storage_dead = False
            limiter.enabled = False  # restore test mode

    def test_rate_limiter_auth_rate_constant_exists(self):
        from rate_limit import AUTH_RATE
        assert "/" in AUTH_RATE, f"AUTH_RATE format invalid: {AUTH_RATE}"


# ── Docker environment detection ──────────────────────────────────────────────

class TestDockerDetection:
    """Verify environment detection logic."""

    def test_storage_uri_empty_when_no_redis_url(self):
        from rate_limit import _storage_uri
        with patch.dict(os.environ, {"REDIS_URL": ""}):
            assert _storage_uri() is None

    def test_storage_uri_resolves_docker_hostname(self):
        """When Docker hostname is unresolvable, must substitute localhost or None."""
        from rate_limit import _storage_uri

        with patch.dict(os.environ, {"REDIS_URL": "redis://:pw@synaptiq_redis:6379/0"}):
            with patch("rate_limit.socket.getaddrinfo", side_effect=socket.gaierror("fail")):
                result = _storage_uri()
                # Must be None (no Redis) — never the original Docker URL
                assert result is None or "synaptiq_redis" not in result

    def test_storage_uri_uses_docker_url_when_resolvable(self):
        """When Docker hostname resolves (inside Docker), original URL is kept."""
        from rate_limit import _storage_uri

        docker_url = "redis://:pw@synaptiq_redis:6379/0"
        with patch.dict(os.environ, {"REDIS_URL": docker_url}):
            with patch("rate_limit.socket.getaddrinfo", return_value=[("", 0, 0, "", ("127.0.0.1", 6379))]):
                result = _storage_uri()
                assert result == docker_url
