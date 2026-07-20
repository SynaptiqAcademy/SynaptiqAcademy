"""
Central test configuration for Synaptiq backend.

Sets all required environment variables BEFORE any test file imports server.py,
so that load_dotenv() never overrides test-safe values with production settings.

Key guarantees:
  - REDIS_URL is always cleared → in-memory rate-limiter (no Docker Redis needed)
  - APP_ENV=test → disables production startup guards
  - EMAIL_VERIFICATION_REQUIRED=0 → immediate login after register
  - EXPOSE_RESET_TOKEN=1 → password-reset flow testable
  - MONGODB_DB_NAME defaults to synaptiq_test (isolated from production)
"""
from __future__ import annotations

import os
import uuid

# ── Environment setup ─────────────────────────────────────────────────────────
# These assignments run at conftest import time — BEFORE any test file imports
# server.py, so load_dotenv() sees these values already set and skips them.

os.environ["REDIS_URL"]                   = ""   # in-memory rate-limiter; no Docker needed
os.environ["APP_ENV"]                     = "test"
os.environ["EMAIL_VERIFICATION_REQUIRED"] = "0"
os.environ["EXPOSE_RESET_TOKEN"]          = "1"
os.environ["CORS_ORIGINS"]               = "http://localhost:3000"
os.environ["EMAIL_DRY_RUN"]              = "1"   # never send real emails during tests

os.environ.setdefault("MONGODB_URI",      "mongodb://localhost:27017/")
os.environ.setdefault("MONGODB_DB_NAME",  "synaptiq_test")
os.environ.setdefault("MONGO_URL",        os.environ["MONGODB_URI"])
os.environ.setdefault("DB_NAME",          os.environ["MONGODB_DB_NAME"])
os.environ.setdefault("JWT_SECRET",       "TestSecret-xK9mP2nQ7vR4tL8wB5hZ3cA0u1Y6sJ")
os.environ.setdefault("ENCRYPTION_KEY",   "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")  # 32-byte b64


# ── Helpers ───────────────────────────────────────────────────────────────────

def unique_email(prefix: str = "test") -> str:
    """Generate a collision-free test email address."""
    return f"{prefix}-{uuid.uuid4().hex[:10]}@synaptiq-test.io"


def csrf_headers(client) -> dict[str, str]:
    """Return X-CSRF-Token + full Cookie header for state-changing requests.

    Starlette's ASGI TestClient (backed by HTTPX) does not forward the session
    cookie jar into the ASGI request scope automatically.  We explicitly build
    the Cookie header from the jar so that CSRF and auth middleware both see
    the cookies they need.  The csrf_token is fetched fresh from the endpoint
    so the double-submit pattern is satisfied.
    """
    r = client.get("/api/auth/csrf-token")
    token = r.json().get("csrf_token", "") if r.status_code == 200 else ""
    if not token:
        return {}
    all_cookies = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
    return {"X-CSRF-Token": token, "Cookie": all_cookies}


# ── Shared pytest fixtures ─────────────────────────────────────────────────────

import pytest


@pytest.fixture(scope="session")
def app():
    """FastAPI application — imported once per session."""
    from server import app as _app
    return _app


@pytest.fixture(scope="session")
def client(app):
    """
    Session-scoped TestClient.  Cookies persist across tests in the same session
    (by design — auth flows need to carry cookies between steps).

    For tests that need a clean cookie jar, use `fresh_client` instead.
    """
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def fresh_client(app):
    """
    Function-scoped TestClient with a clean cookie jar — use for tests that
    must start with no existing session (e.g. unauthenticated flow checks).
    """
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def registered_user(client):
    """Register a session-long user and return its credentials."""
    email = unique_email("session")
    password = "SessionPass1!"
    r = client.post("/api/auth/register", json={
        "full_name": "Session User",
        "email": email,
        "password": password,
    })
    assert r.status_code == 200, f"Session user registration failed: {r.status_code} {r.text[:200]}"
    return {"email": email, "password": password, "data": r.json()}


@pytest.fixture(scope="session")
def auth_client(client, registered_user):
    """Session-scoped TestClient that is already logged in."""
    r = client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert r.status_code == 200, f"Session user login failed: {r.status_code} {r.text[:200]}"
    return client


@pytest.fixture
def auth_headers(auth_client) -> dict[str, str]:
    """Return the X-CSRF-Token header for state-changing requests."""
    return csrf_headers(auth_client)


# ── Live-server test skip guard ────────────────────────────────────────────────
# These test files make real HTTP requests to a running backend process.
# When no server is reachable they are auto-skipped instead of failing with
# ConnectionRefusedError.  test_auth_suite.py has its own guard; it is listed
# here too so the set is the single source of truth.

_LIVE_SERVER_REACHABLE: bool = False
try:
    import httpx as _httpx_probe
    for _probe_url in ("http://localhost:8000/api/health", "http://localhost:8001/api/health"):
        try:
            _httpx_probe.get(_probe_url, timeout=0.5)
            _LIVE_SERVER_REACHABLE = True
            break
        except Exception:
            pass
    del _httpx_probe, _probe_url
except ImportError:
    pass

_LIVE_SERVER_FILES = frozenset({
    "test_auth_suite.py",
    "test_ai_chat.py",
    "test_attachments_phase.py",
    "test_files_phase.py",
    "test_institutions_phase.py",
    "test_files_smoke_iter15.py",
    "test_institutions_smoke_iter13.py",
    "test_hardening_iter18.py",
    "test_orcid_phase.py",
    "test_marketplace_extras.py",
    "test_marketplace_phase.py",
})


def pytest_collection_modifyitems(config, items):
    if _LIVE_SERVER_REACHABLE:
        return
    skip_mark = pytest.mark.skip(
        reason="Live server not reachable — start backend to run this suite"
    )
    for item in items:
        if item.fspath.basename in _LIVE_SERVER_FILES:
            item.add_marker(skip_mark)
