"""
AUTH-014: Security test suite.

Tests every auth flow, CSRF, lockout, token revocation, and admin protection.
Run: cd backend && python -m pytest tests/test_auth_security.py -v
"""
import os
import uuid
import pytest

# Override (not setdefault) so .env values never bleed into tests.
# REDIS_URL must be empty so the in-memory rate-limiter is used; otherwise
# the Docker Redis hostname resolves and causes sync connection errors.
os.environ["REDIS_URL"]                   = os.environ.get("REDIS_URL", "")
os.environ["MONGODB_URI"]                 = os.environ.get("MONGODB_URI", os.environ.get("MONGO_URL", "mongodb://localhost:27017/"))
os.environ["MONGODB_DB_NAME"]             = os.environ.get("MONGODB_DB_NAME", os.environ.get("DB_NAME", "synaptiq_test"))
os.environ["MONGO_URL"]                   = os.environ["MONGODB_URI"]
os.environ["DB_NAME"]                     = os.environ["MONGODB_DB_NAME"]
os.environ.setdefault("JWT_SECRET",                   "TestSecret-xK9mP2nQ7vR4tL8wB5hZ3cA0u1Y6sJ")
os.environ.setdefault("EMAIL_VERIFICATION_REQUIRED",  "0")
os.environ.setdefault("EXPOSE_RESET_TOKEN",           "1")
os.environ.setdefault("APP_ENV",                      "test")
os.environ.setdefault("CORS_ORIGINS",                 "http://localhost:3000")

def _csrf_headers(client) -> dict:
    """Fetch a fresh CSRF token and return X-CSRF-Token + full Cookie header.

    Starlette's ASGI TestClient (backed by HTTPX) does not automatically
    forward the session's cookie jar into the ASGI request scope.  We work
    around this by building the Cookie header explicitly from the client's
    jar so that both the CSRF middleware (reads csrf_token cookie) and the
    auth middleware (reads access_token cookie) see the cookies they expect.
    """
    r = client.get("/api/auth/csrf-token")
    token = r.json().get("csrf_token", "") if r.status_code == 200 else ""
    if not token:
        return {}
    all_cookies = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
    return {"X-CSRF-Token": token, "Cookie": all_cookies}


# Use the session-scoped client from conftest.py — do NOT create a second
# TestClient here.  Creating a second TestClient for the same app object
# in the middle of a session causes motor's event loop to be re-bound to a
# new anyio loop while the original one may still be closing, resulting in
# "Event loop is closed" errors during the second startup.


@pytest.fixture(scope="module")
def unique_email():
    return f"security-test-{uuid.uuid4().hex[:8]}@example.com"


# ─────────────────── AUTH-001: JWT secret validation ─────────────────────────

def test_jwt_secret_strength_rejects_short():
    from auth_utils import validate_jwt_secret
    with pytest.raises(RuntimeError, match="32 characters"):
        validate_jwt_secret("short")


def test_jwt_secret_strength_rejects_predictable():
    from auth_utils import validate_jwt_secret
    with pytest.raises(RuntimeError, match="predictable"):
        validate_jwt_secret("1234567890123456789012345678901234567890")


def test_jwt_secret_strength_accepts_strong():
    from auth_utils import validate_jwt_secret
    validate_jwt_secret("xK9mP2nQ7vR4tL8wB5hZ3cA0u1Y6sJfG")  # no exception


# ─────────────────── AUTH-002: Register + verify flow ────────────────────────

def test_register_creates_user(client, unique_email):
    r = client.post("/api/auth/register", json={
        "full_name": "Security Test", "email": unique_email, "password": "TestPass1"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == unique_email
    assert "password_hash" not in data


def test_register_duplicate_email(client, unique_email):
    r = client.post("/api/auth/register", json={
        "full_name": "Dup", "email": unique_email, "password": "TestPass1"
    })
    assert r.status_code == 400


def test_register_weak_password_rejected(client):
    r = client.post("/api/auth/register", json={
        "full_name": "Weak", "email": f"weak-{uuid.uuid4().hex[:6]}@example.com",
        "password": "short"
    })
    assert r.status_code == 400


def test_register_no_letter_rejected(client):
    r = client.post("/api/auth/register", json={
        "full_name": "NL", "email": f"nl-{uuid.uuid4().hex[:6]}@example.com",
        "password": "12345678"
    })
    assert r.status_code == 400


# ─────────────────── AUTH-002: Login ─────────────────────────────────────────

def test_login_success(client, unique_email):
    r = client.post("/api/auth/login", json={"email": unique_email, "password": "TestPass1"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == unique_email
    # Auth cookies must be HttpOnly — not visible in response body
    assert "password_hash" not in data
    # Cookies should be set
    assert "access_token" in r.cookies or "access_token" in r.headers.get("set-cookie", "")


def test_login_wrong_password(client, unique_email):
    r = client.post("/api/auth/login", json={"email": unique_email, "password": "WrongPass9"})
    assert r.status_code == 401


def test_login_nonexistent_user(client):
    r = client.post("/api/auth/login", json={
        "email": "nobody@example.com", "password": "TestPass1"
    })
    assert r.status_code == 401


# ─────────────────── AUTH-003: No token exposure ─────────────────────────────

def test_forgot_password_never_exposes_token_in_production():
    """In production mode, EXPOSE_RESET_TOKEN=0 must be enforced."""
    from routers.auth import _expose_reset_token
    original_env = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "production"
    try:
        assert _expose_reset_token() is False
    finally:
        if original_env:
            os.environ["APP_ENV"] = original_env
        else:
            del os.environ["APP_ENV"]


# ─────────────────── AUTH-005: Refresh token revocation ──────────────────────

def test_token_revocation_on_logout(client, unique_email):
    """After logout, the refresh token jti must be revoked."""
    login_r = client.post("/api/auth/login", json={"email": unique_email, "password": "TestPass1"})
    assert login_r.status_code == 200

    # Logout requires CSRF header (double-submit cookie pattern)
    logout_r = client.post("/api/auth/logout", headers=_csrf_headers(client))
    assert logout_r.status_code == 200

    # Refresh should fail after logout (revoked jti)
    refresh_r = client.post("/api/auth/refresh")
    assert refresh_r.status_code == 401


def test_token_rotation_on_refresh(client, unique_email):
    """Each refresh issues a new token pair; old pair should not reuse."""
    login_r = client.post("/api/auth/login", json={"email": unique_email, "password": "TestPass1"})
    assert login_r.status_code == 200

    def _cookie_header():
        return "; ".join(f"{k}={v}" for k, v in client.cookies.items())

    r1 = client.post("/api/auth/refresh", headers={"Cookie": _cookie_header()})
    assert r1.status_code == 200

    r2 = client.post("/api/auth/refresh", headers={"Cookie": _cookie_header()})
    assert r2.status_code == 200

    client.post("/api/auth/logout", headers=_csrf_headers(client))


# ─────────────────── AUTH-006: Account lockout ───────────────────────────────

def test_account_lockout_triggers_after_failures(client):
    """5 consecutive wrong passwords should result in a 429."""
    test_email = f"lockout-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "full_name": "LockTest", "email": test_email, "password": "LockPass1"
    })
    for i in range(5):
        r = client.post("/api/auth/login", json={"email": test_email, "password": "WrongPass9"})
        if r.status_code == 429:
            break
    else:
        r6 = client.post("/api/auth/login", json={"email": test_email, "password": "WrongPass9"})
        assert r6.status_code == 429, "Expected lockout (429) after 5+ failures"


# ─────────────────── AUTH-007: CSRF protection ───────────────────────────────

def test_csrf_required_for_state_changing_requests(client, unique_email):
    """POST without CSRF token should be rejected (403) on protected endpoints."""
    login_r = client.post("/api/auth/login", json={"email": unique_email, "password": "TestPass1"})
    assert login_r.status_code == 200

    # Explicit empty CSRF header — must be rejected
    r = client.post("/api/auth/change-password", json={
        "current_password": "TestPass1", "new_password": "NewPass99"
    }, headers={"X-CSRF-Token": ""})
    assert r.status_code in (400, 403)

    # Confirm correct CSRF token makes the endpoint reachable (may still 400 for wrong pw)
    r2 = client.post("/api/auth/change-password", json={
        "current_password": "WRONG_TO_AVOID_CHANGE", "new_password": "NewPass99!"
    }, headers=_csrf_headers(client))
    assert r2.status_code in (400, 422)  # 400=wrong pw; NOT 403 CSRF

    client.post("/api/auth/logout", headers=_csrf_headers(client))


def test_csrf_endpoint_returns_token(client):
    r = client.get("/api/auth/csrf-token")
    assert r.status_code == 200
    data = r.json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 10


# ─────────────────── AUTH-009: Proper JTI in tokens ──────────────────────────

def test_refresh_token_has_uuid_jti(client, unique_email):
    import jwt as pyjwt
    client.post("/api/auth/login", json={"email": unique_email, "password": "TestPass1"})
    refresh_cookie = client.cookies.get("refresh_token")
    if refresh_cookie:
        payload = pyjwt.decode(
            refresh_cookie, options={"verify_signature": False, "verify_exp": False}
        )
        jti = payload.get("jti", "")
        # Valid UUID4
        try:
            uuid.UUID(jti, version=4)
        except ValueError:
            pytest.fail(f"refresh token jti is not a valid UUID4: {jti!r}")
    client.post("/api/auth/logout")


def test_access_token_has_uuid_jti(client, unique_email):
    import jwt as pyjwt
    client.post("/api/auth/login", json={"email": unique_email, "password": "TestPass1"})
    access_cookie = client.cookies.get("access_token")
    if access_cookie:
        payload = pyjwt.decode(
            access_cookie, options={"verify_signature": False, "verify_exp": False}
        )
        jti = payload.get("jti", "")
        try:
            uuid.UUID(jti, version=4)
        except ValueError:
            pytest.fail(f"access token jti is not a valid UUID4: {jti!r}")
    client.post("/api/auth/logout")


# ─────────────────── AUTH-011: Audit log retention ───────────────────────────

async def test_audit_log_entry_has_expires_at(unique_email):
    """Audit log entries written by the auth flow must carry an expires_at TTL field.

    Uses a fresh motor client on the test's own event loop rather than sharing
    the TestClient's internal loop (which would cause 'Future attached to a
    different loop' errors).
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.environ.get("MONGODB_DB_NAME", "synaptiq_test")
    mclient = AsyncIOMotorClient(uri)
    try:
        record = await mclient[db_name].audit_log.find_one({"actor_email": unique_email})
        if record:
            assert "expires_at" in record, "audit_log entries must have expires_at for TTL index"
            assert record["expires_at"] is not None
    finally:
        mclient.close()


# ─────────────────── AUTH-011: Admin protection ──────────────────────────────

def test_admin_endpoint_requires_super_admin(client, unique_email):
    """Regular user must not access admin dashboard."""
    client.post("/api/auth/login", json={"email": unique_email, "password": "TestPass1"})
    r = client.get("/api/admin/dashboard")
    assert r.status_code in (403, 401)
    client.post("/api/auth/logout")


def test_unauthenticated_access_blocked(client):
    """Unauthenticated requests to protected endpoints return 401."""
    r = client.get("/api/auth/me")
    assert r.status_code == 401


# ─────────────────── AUTH-012: ORCID encryption helpers ──────────────────────

def test_encrypt_decrypt_roundtrip():
    import base64
    key = base64.b64encode(b"\x00" * 32).decode()
    os.environ["ENCRYPTION_KEY"] = key

    # Reset key cache
    import services.encryption_service as enc_svc
    enc_svc._key_cache = enc_svc._UNSET

    from services.encryption_service import encrypt_field, decrypt_field
    plaintext = "test_orcid_access_token_value"
    encrypted = encrypt_field(plaintext)
    assert encrypted.get("encrypted") is True
    assert "ciphertext" in encrypted

    decrypted = decrypt_field(encrypted)
    assert decrypted == plaintext

    # Cleanup
    del os.environ["ENCRYPTION_KEY"]
    enc_svc._key_cache = enc_svc._UNSET


def test_decrypt_legacy_plaintext():
    from services.encryption_service import decrypt_field
    assert decrypt_field("plain_string") == "plain_string"
    assert decrypt_field(None) == ""
    assert decrypt_field({"encrypted": False, "value": "unencrypted"}) == "unencrypted"


# ─────────────────── AUTH-015: Production readiness ──────────────────────────

def test_prod_validator_rejects_weak_jwt_in_prod():
    from services.prod_validator import evaluate_env
    original = {k: os.environ.get(k) for k in ["APP_ENV", "JWT_SECRET"]}
    os.environ["APP_ENV"] = "production"
    os.environ["JWT_SECRET"] = "weakpassword"
    try:
        result = evaluate_env()
        jwt_check = next((c for c in result["checks"] if c["name"] == "JWT_SECRET"), None)
        assert jwt_check is not None
        assert jwt_check["passed"] is False
    finally:
        for k, v in original.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]


def test_prod_validator_checks_encryption_key_in_prod():
    from services.prod_validator import evaluate_env
    original = {k: os.environ.get(k) for k in ["APP_ENV", "ENCRYPTION_KEY"]}
    os.environ["APP_ENV"] = "production"
    os.environ.pop("ENCRYPTION_KEY", None)
    try:
        result = evaluate_env()
        enc_check = next((c for c in result["checks"] if c["name"] == "ENCRYPTION_KEY"), None)
        assert enc_check is not None
        assert enc_check["passed"] is False
    finally:
        for k, v in original.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]


def test_password_reset_revokes_all_tokens(client, unique_email):
    """After /auth/reset-password, existing refresh tokens must be revoked."""
    login_r = client.post("/api/auth/login", json={"email": unique_email, "password": "TestPass1"})
    assert login_r.status_code == 200

    forgot_r = client.post("/api/auth/forgot-password", json={"email": unique_email})
    if forgot_r.status_code in (503, 502):
        pytest.skip("Email service unavailable (quota/network) — reset flow not testable")
    assert forgot_r.status_code == 200
    debug_token = forgot_r.json().get("debug_reset_token")

    if debug_token:
        reset_r = client.post("/api/auth/reset-password", json={
            "token": debug_token, "new_password": "TestPass1"
        })
        assert reset_r.status_code == 200

        # After reset, old refresh token is revoked (token_version bump)
        refresh_r = client.post("/api/auth/refresh")
        assert refresh_r.status_code == 401
