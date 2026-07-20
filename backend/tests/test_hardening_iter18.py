"""Hardening Phase tests — CORS, rate-limit, password policy, consent, email verification, cookie security."""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")[0].strip()
DEMO_EMAIL = "elena.varga@synaptiq.io"
DEMO_PASS = "demo123"


def _u(email_prefix="hardening_iter18"):
    return f"test_{email_prefix}_{uuid.uuid4().hex[:8]}@example.com"


# ------------------ CORS ------------------
class TestCORS:
    def test_cors_allowed_origin_echoed_not_wildcard(self):
        r = requests.options(
            f"{BASE_URL}/api/auth/login",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=15,
        )
        # Some setups respond 200 or 204
        assert r.status_code in (200, 204), f"Unexpected preflight status: {r.status_code}"
        acao = r.headers.get("access-control-allow-origin", "")
        assert acao == ALLOWED_ORIGIN, f"ACAO should echo allowlisted origin, got {acao!r}"
        assert acao != "*", "Wildcard CORS must NOT be combined with credentials"
        assert r.headers.get("access-control-allow-credentials", "").lower() == "true"


# ------------------ Password policy + registration ------------------
class TestRegistrationPolicy:
    def test_weak_password_short_returns_400(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": _u("short"), "password": "abc", "full_name": "Short Pass",
        }, timeout=15)
        assert r.status_code == 400
        assert "at least 8" in r.json().get("detail", "")

    def test_password_missing_complexity_returns_400(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": _u("nocplx"), "password": "12345678", "full_name": "No Complex",
        }, timeout=15)
        assert r.status_code == 400
        assert "letter and one digit" in r.json().get("detail", "")

    def test_strong_password_registers_and_unverified(self):
        email = _u("strong")
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "password": "StrongPass123", "full_name": "Strong User",
        }, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("email_verified") is False
        assert body.get("verification_email_sent") is True
        # Should NOT expose debug token in prod-style mode (EXPOSE_RESET_TOKEN=0)
        assert "debug_verification_token" not in body, "debug_verification_token leaked"
        assert "password_hash" not in body


# ------------------ Login + cookies ------------------
class TestLoginCookies:
    def test_login_success_sets_httponly_cookies(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS}, timeout=15)
        assert r.status_code == 200, r.text
        # Inspect raw Set-Cookie headers
        set_cookie = r.headers.get("set-cookie", "") + " " + "; ".join(r.raw.headers.get_all("Set-Cookie") if hasattr(r.raw.headers, "get_all") else [])
        # Use response.cookies and the raw headers via requests
        # Validate via direct header parse
        raw_headers = r.raw.headers.getlist("Set-Cookie") if hasattr(r.raw.headers, "getlist") else []
        joined = "\n".join(raw_headers) if raw_headers else set_cookie
        assert "access_token=" in joined
        assert "refresh_token=" in joined
        assert "HttpOnly" in joined, f"access cookie must be HttpOnly: {joined}"
        # SameSite=lax (per .env)
        assert "samesite=lax" in joined.lower() or "samesite=Lax" in joined, f"missing SameSite: {joined}"
        # access cookie max-age = ACCESS_MIN*60 = 86400
        assert "Max-Age=86400" in joined or "max-age=86400" in joined.lower()

    def test_login_invalid_credentials_401(self):
        # Use a fresh fake user to avoid rate-limiting demo email
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": f"badlogin_{uuid.uuid4().hex[:8]}@example.com", "password": "WrongPass123",
        }, timeout=15)
        assert r.status_code in (401, 429)

    def test_me_no_sensitive_fields(self):
        s = requests.Session()
        lr = s.post(f"{BASE_URL}/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS}, timeout=15)
        if lr.status_code == 429:
            pytest.skip("Rate-limited; skip /me leak test this run")
        assert lr.status_code == 200, lr.text
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "password_hash" not in body
        orcid = body.get("orcid")
        if isinstance(orcid, dict):
            assert "access_token" not in orcid
            assert "refresh_token" not in orcid


# ------------------ Forgot password — no token leakage ------------------
class TestForgotPasswordNoLeak:
    def test_forgot_password_does_not_expose_debug_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                          json={"email": DEMO_EMAIL}, timeout=15)
        if r.status_code == 429:
            pytest.skip("rate-limited")
        assert r.status_code == 200
        body = r.json()
        assert "debug_reset_token" not in body, f"debug_reset_token leaked: {body}"
        assert set(body.keys()).issubset({"ok", "message"})


# ------------------ Email verification ------------------
class TestEmailVerification:
    def test_verify_email_missing_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/verify-email", json={}, timeout=15)
        assert r.status_code == 400
        assert r.json().get("detail") == "Token required"

    def test_verify_email_junk_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/verify-email", json={"token": "junk"}, timeout=15)
        assert r.status_code == 400
        assert r.json().get("detail") == "Invalid verification token"

    def test_resend_verification_existing_unverified(self):
        # Create fresh unverified user
        email = _u("resend")
        rr = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "password": "StrongPass123", "full_name": "Resend User",
        }, timeout=15)
        if rr.status_code == 429:
            pytest.skip("rate-limited")
        assert rr.status_code == 200, rr.text
        r = requests.post(f"{BASE_URL}/api/auth/resend-verification",
                          json={"email": email}, timeout=15)
        if r.status_code == 429:
            pytest.skip("rate-limited")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_resend_verification_unknown_email_no_enumeration(self):
        r = requests.post(f"{BASE_URL}/api/auth/resend-verification",
                          json={"email": f"nobody_{uuid.uuid4().hex}@example.com"}, timeout=15)
        if r.status_code == 429:
            pytest.skip("rate-limited")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


# ------------------ Consent ------------------
class TestConsent:
    def test_submit_and_get_latest(self):
        cid = uuid.uuid4().hex
        payload = {
            "consent_id": cid,
            "status": "accepted_all",
            "prefs": {"essential": True, "analytics": True, "marketing": True, "preferences": True},
            "source": "banner",
        }
        r = requests.post(f"{BASE_URL}/api/consent", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        rec = body.get("record", {})
        assert rec.get("status") == "accepted_all"
        assert rec.get("consent_id") == cid
        assert "ip_hash" not in rec, "ip_hash should not leak in response"

        # GET latest
        g = requests.get(f"{BASE_URL}/api/consent/latest", params={"consent_id": cid}, timeout=15)
        assert g.status_code == 200
        gb = g.json()
        assert gb.get("record") is not None
        assert gb["record"]["consent_id"] == cid
        assert "ip_hash" not in gb["record"], "ip_hash should not leak in latest"


# ------------------ Rate limiting (RUN LAST) ------------------
class TestRateLimit:
    def test_login_rate_limit_kicks_in(self):
        """Hit /api/auth/login 7 times rapidly; expect at least one 429."""
        statuses = []
        for i in range(7):
            r = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": f"ratelimit_{i}_{uuid.uuid4().hex[:6]}@example.com", "password": "WrongWrong123",
            }, timeout=15)
            statuses.append(r.status_code)
        assert 429 in statuses, f"Expected at least one 429 in {statuses}"
        # Most early ones should be 401 (auth fail), late ones 429
        assert statuses.count(401) >= 1
