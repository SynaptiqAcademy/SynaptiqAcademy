"""
Regression protection suite.

Guards against known production bugs and critical behaviour that must
never regress.  Each test documents the original bug, the fix, and the
invariant it enforces.

Run:
    cd backend && python -m pytest tests/test_regression.py -v -m regression
"""
import os
import uuid
import pytest

pytestmark = pytest.mark.regression


def unique_email(pfx: str = "reg") -> str:
    return f"{pfx}-{uuid.uuid4().hex[:10]}@regression-test.io"


def _cookie_header(client) -> str:
    return "; ".join(f"{k}={v}" for k, v in client.cookies.items())


def _csrf(client) -> dict:
    r = client.get("/api/auth/csrf-token")
    token = r.json().get("csrf_token", "") if r.status_code == 200 else ""
    if not token:
        return {}
    return {"X-CSRF-Token": token, "Cookie": _cookie_header(client)}


# Use the session-scoped client from conftest.py — do NOT create a second
# TestClient in the middle of a session (causes motor "Event loop is closed" errors).


# ═══════════════════════════════════════════════════════════════════════════════
# REG-001: Auth / security regressions
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthRegressions:
    def test_reg001_rate_limiter_does_not_contaminate_test_env(self, client):
        """
        Bug: REDIS_URL from .env bleeds into tests → rate limiter attempts
        a sync Redis connection → 500 on every endpoint.

        Fix: conftest.py forces REDIS_URL="" + APP_ENV=test disables the limiter.
        Invariant: 10 consecutive registrations never return 429 or 500.
        """
        for i in range(10):
            r = client.post("/api/auth/register", json={
                "full_name": f"Rate {i}",
                "email": unique_email(f"rate{i}"),
                "password": "RatePass1!",
            })
            assert r.status_code not in (429, 500), \
                f"Request {i} returned {r.status_code} — rate limiter or Redis leak"

    def test_reg002_account_lockout_fires_on_wrong_password(self, client):
        """
        Bug: _check_lockout() was placed AFTER the password check, making it
        unreachable for wrong-password attempts (only reached on correct password).
        Brute-force protection did not actually protect.

        Fix: moved _check_lockout() BEFORE the password verification in login().
        Invariant: 6 consecutive wrong-password attempts return 429 after lockout.
        """
        email = unique_email("lockout")
        client.post("/api/auth/register", json={
            "full_name": "Lockout", "email": email, "password": "LockPass1!",
        })
        got_429 = False
        for i in range(7):
            r = client.post("/api/auth/login", json={
                "email": email, "password": "WrongPassword99",
            })
            if r.status_code == 429:
                got_429 = True
                break
        assert got_429, (
            "Account lockout never triggered 429 after 7 failed attempts — "
            "_check_lockout() may be unreachable again"
        )

    def test_reg003_logout_clears_session(self, client):
        """
        Bug: /api/auth/logout was in the CSRF-protected paths and the TestClient
        couldn't send the CSRF cookie, making logout return 403.

        Fix: /api/auth/logout added to _CSRF_EXEMPT_PATHS (CSRF-forced logout
        is an annoyance, not a security breach).
        Invariant: logout must return 200 without a CSRF token.
        """
        email = unique_email("logout")
        client.post("/api/auth/register", json={
            "full_name": "Logout", "email": email, "password": "LogoutPass1!",
        })
        client.post("/api/auth/login", json={"email": email, "password": "LogoutPass1!"})
        r = client.post("/api/auth/logout")  # NO CSRF header — must still work
        assert r.status_code == 200, f"Logout returned {r.status_code}: {r.text[:100]}"

    def test_reg004_password_reset_revokes_refresh_token(self, client):
        """
        Invariant: after /auth/reset-password, the old refresh token is rejected.
        """
        email = unique_email("pwreset")
        client.post("/api/auth/register", json={
            "full_name": "PW Reset", "email": email, "password": "OldPwd1!",
        })
        client.post("/api/auth/login", json={"email": email, "password": "OldPwd1!"})

        forgot_r = client.post("/api/auth/forgot-password", json={"email": email})
        if forgot_r.status_code in (503, 502):
            pytest.skip("Email service unavailable (quota/network) — reset flow not testable")
        assert forgot_r.status_code == 200
        debug_token = forgot_r.json().get("debug_reset_token")
        if not debug_token:
            pytest.skip("EXPOSE_RESET_TOKEN=0")

        reset_r = client.post("/api/auth/reset-password", json={
            "token": debug_token, "new_password": "NewPwd1!",
        })
        assert reset_r.status_code == 200

        refresh_r = client.post("/api/auth/refresh")
        assert refresh_r.status_code == 401, \
            "Old refresh token must be revoked after password reset"

    def test_reg005_duplicate_email_rejected(self, client):
        """Invariant: registering the same email twice returns 400, not 500."""
        email = unique_email("dup")
        payload = {"full_name": "Dup", "email": email, "password": "DupPass1!"}
        r1 = client.post("/api/auth/register", json=payload)
        assert r1.status_code == 200
        r2 = client.post("/api/auth/register", json=payload)
        assert r2.status_code == 400
        assert "password" not in r2.text.lower() or "hash" not in r2.text.lower(), \
            "Password hash must not appear in error responses"

    def test_reg006_no_password_hash_in_responses(self, client):
        """
        Invariant: password_hash must never appear in any auth response body.
        """
        email = unique_email("nohash")
        r = client.post("/api/auth/register", json={
            "full_name": "No Hash", "email": email, "password": "NoHashPass1!",
        })
        assert r.status_code == 200
        assert "password_hash" not in r.text, "password_hash leaked in register response"

        lr = client.post("/api/auth/login", json={
            "email": email, "password": "NoHashPass1!",
        })
        assert lr.status_code == 200
        assert "password_hash" not in lr.text, "password_hash leaked in login response"

        me_r = client.get("/api/auth/me",
                          headers={"Cookie": _cookie_header(client)})
        if me_r.status_code == 200:
            assert "password_hash" not in me_r.text, "password_hash leaked in /me response"


# ═══════════════════════════════════════════════════════════════════════════════
# REG-002: JWT / token regressions
# ═══════════════════════════════════════════════════════════════════════════════


class TestJWTRegressions:
    def test_reg007_refresh_token_has_jti(self, client):
        """Invariant: refresh token must contain a valid UUID4 jti for revocation."""
        import jwt as pyjwt
        email = unique_email("jti")
        client.post("/api/auth/register", json={
            "full_name": "JTI", "email": email, "password": "JtiPass1!",
        })
        client.post("/api/auth/login", json={"email": email, "password": "JtiPass1!"})
        token = client.cookies.get("refresh_token")
        if not token:
            pytest.skip("refresh_token cookie not in jar — HTTPX forwarding issue")
        payload = pyjwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        jti = payload.get("jti", "")
        assert jti, "refresh_token jti must not be empty"
        try:
            uuid.UUID(jti, version=4)
        except ValueError:
            pytest.fail(f"refresh_token jti is not a valid UUID4: {jti!r}")

    def test_reg008_access_token_has_jti(self, client):
        """Invariant: access token must contain a valid UUID4 jti."""
        import jwt as pyjwt
        email = unique_email("atjti")
        client.post("/api/auth/register", json={
            "full_name": "AT JTI", "email": email, "password": "AtjtiPass1!",
        })
        client.post("/api/auth/login", json={"email": email, "password": "AtjtiPass1!"})
        token = client.cookies.get("access_token")
        if not token:
            pytest.skip("access_token cookie not in jar — HTTPX forwarding issue")
        payload = pyjwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        jti = payload.get("jti", "")
        assert jti, "access_token jti must not be empty"
        try:
            uuid.UUID(jti, version=4)
        except ValueError:
            pytest.fail(f"access_token jti is not a valid UUID4: {jti!r}")

    def test_reg009_weak_jwt_secret_rejected_in_prod(self):
        """Invariant: a weak JWT secret fails validation in production mode."""
        from auth_utils import validate_jwt_secret
        with pytest.raises(RuntimeError, match="32 characters"):
            validate_jwt_secret("short")
        with pytest.raises(RuntimeError, match="predictable"):
            validate_jwt_secret("1234567890123456789012345678901234567890")


# ═══════════════════════════════════════════════════════════════════════════════
# REG-003: CSRF regressions
# ═══════════════════════════════════════════════════════════════════════════════


class TestCSRFRegressions:
    def test_reg010_csrf_endpoint_returns_token(self, client):
        """Invariant: GET /api/auth/csrf-token always returns a token."""
        r = client.get("/api/auth/csrf-token")
        assert r.status_code == 200
        data = r.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) >= 20

    def test_reg011_state_change_blocked_without_csrf(self, client):
        """Invariant: POST to CSRF-protected endpoint without token returns 403."""
        email = unique_email("csrf")
        client.post("/api/auth/register", json={
            "full_name": "CSRF", "email": email, "password": "CsrfPass1!",
        })
        client.post("/api/auth/login", json={"email": email, "password": "CsrfPass1!"})
        r = client.post("/api/auth/change-password",
                        json={"current_password": "x", "new_password": "y"},
                        headers={"Cookie": _cookie_header(client)})  # auth but no CSRF
        assert r.status_code in (400, 403, 422), \
            f"Expected rejection, got {r.status_code}: {r.text[:100]}"

    def test_reg012_csrf_with_correct_token_reaches_endpoint(self, client):
        """Invariant: correct CSRF token allows the request to reach the endpoint."""
        email = unique_email("csrf2")
        client.post("/api/auth/register", json={
            "full_name": "CSRF2", "email": email, "password": "CsrfPass1!",
        })
        client.post("/api/auth/login", json={"email": email, "password": "CsrfPass1!"})
        headers = _csrf(client)
        r = client.post("/api/auth/change-password",
                        json={"current_password": "WRONG_DONT_CHANGE", "new_password": "NewPass1!"},
                        headers=headers)
        assert r.status_code not in (403,), \
            f"CSRF-protected endpoint returned 403 with valid token: {r.text[:100]}"


# ═══════════════════════════════════════════════════════════════════════════════
# REG-004: DB proxy regressions (Phase 3)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDBProxyRegressions:
    def test_reg013_get_db_returns_proxy(self):
        """
        Invariant (Phase 3): get_db() must return a DBProxy, not a raw motor db.
        All 713 direct db = get_db() call sites must automatically get security
        context injection.
        """
        from db import get_db
        from repo.shim import DBProxy
        db = get_db()
        assert isinstance(db, DBProxy), \
            f"get_db() returned {type(db).__name__!r}, expected DBProxy — Phase 3 regression"

    def test_reg014_dbproxy_does_not_double_wrap(self):
        """Invariant: wrapping a DBProxy in another DBProxy returns the same proxy."""
        from db import get_db
        from repo.shim import DBProxy, make_db_proxy
        db1 = get_db()
        assert isinstance(db1, DBProxy)
        db2 = make_db_proxy(db1, system=True)
        # Both must wrap the same underlying motor database
        inner1 = object.__getattribute__(db1, "_db")
        inner2 = object.__getattribute__(db2, "_db")
        assert inner1 is inner2, "Double-wrapping created two different motor db objects"

    def test_reg015_encryption_roundtrip(self):
        """Invariant: encrypt → decrypt must return the original plaintext."""
        import base64
        key = base64.b64encode(b"\x00" * 32).decode()
        os.environ["ENCRYPTION_KEY"] = key
        import services.encryption_service as enc_svc
        enc_svc._key_cache = enc_svc._UNSET
        try:
            from services.encryption_service import encrypt_field, decrypt_field
            plaintext = "regression-test-secret-value"
            encrypted = encrypt_field(plaintext)
            assert encrypted.get("encrypted") is True
            decrypted = decrypt_field(encrypted)
            assert decrypted == plaintext
        finally:
            del os.environ["ENCRYPTION_KEY"]
            enc_svc._key_cache = enc_svc._UNSET


# ═══════════════════════════════════════════════════════════════════════════════
# REG-005: Security boundary regressions
# ═══════════════════════════════════════════════════════════════════════════════


class TestSecurityRegressions:
    def test_reg016_unauthenticated_me_returns_401(self, client):
        """Invariant: /api/auth/me without auth must return 401."""
        from server import app
        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=False) as fresh:
            r = fresh.get("/api/auth/me")
            assert r.status_code == 401

    def test_reg017_admin_requires_super_admin(self, client):
        """Invariant: /api/admin/* rejects regular users with 401 or 403."""
        email = unique_email("adm")
        client.post("/api/auth/register", json={
            "full_name": "Admin Test", "email": email, "password": "AdminPass1!",
        })
        client.post("/api/auth/login", json={"email": email, "password": "AdminPass1!"})
        r = client.get("/api/admin/dashboard",
                       headers={"Cookie": _cookie_header(client)})
        assert r.status_code in (401, 403), \
            f"Regular user accessed admin dashboard: {r.status_code}"

    def test_reg018_sql_injection_does_not_500(self, client):
        """Invariant: injection payloads must never return 500."""
        payloads = [
            {"email": "' OR '1'='1", "password": "x"},
            {"email": {"$gt": ""}, "password": "x"},
        ]
        for p in payloads:
            r = client.post("/api/auth/login", json=p)
            assert r.status_code != 500, f"Injection payload caused 500: {p}"

    def test_reg019_expose_reset_token_false_in_production(self):
        """Invariant: in production mode, debug_reset_token must never appear."""
        from routers.auth import _expose_reset_token
        orig = os.environ.get("APP_ENV")
        os.environ["APP_ENV"] = "production"
        try:
            assert _expose_reset_token() is False, \
                "debug_reset_token exposed in production mode"
        finally:
            if orig is not None:
                os.environ["APP_ENV"] = orig
            elif "APP_ENV" in os.environ:
                del os.environ["APP_ENV"]

    def test_reg020_rate_limit_disabled_in_test_env(self):
        """Invariant: rate limiter must be disabled when APP_ENV=test."""
        from rate_limit import limiter
        # slowapi exposes enabled state
        enabled = getattr(limiter, "enabled", None)
        if enabled is None:
            # older API — check _storage attribute
            pytest.skip("slowapi version does not expose .enabled")
        assert enabled is False, \
            f"Rate limiter is ENABLED in test env — will cause test pollution"
