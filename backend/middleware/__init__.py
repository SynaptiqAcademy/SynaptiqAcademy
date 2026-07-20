"""Security middleware stack.

SecurityHeadersMiddleware  — CSP, HSTS, X-Frame, etc.
CSRFMiddleware             — double-submit cookie validation on mutating requests (AUTH-007)
IPBlockMiddleware          — reject requests from IPs in the blocked_ips collection (H4 fix)

CSP changes (AUTH-004 / AUTH-008):
  BEFORE: script-src 'self' 'unsafe-inline' https://js.stripe.com
          connect-src 'self' https: wss:
  AFTER:  script-src 'self' https://js.stripe.com          (no unsafe-inline)
          connect-src 'self' https://api.stripe.com https://js.stripe.com
                      https://sandbox.orcid.org https://orcid.org
                      https://api.openalex.org https://pub.sandbox.orcid.org
                      https://pub.orcid.org wss:
"""
import os
import secrets
import time as _time_module
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


def _is_prod() -> bool:
    return os.environ.get("APP_ENV", "development").lower() in ("prod", "production")


def _csp() -> str:
    """
    AUTH-004: script-src has NO 'unsafe-inline'.
    AUTH-008: connect-src uses an explicit allowlist instead of 'https:'.
    """
    allowed_connect = " ".join([
        "'self'",
        # Stripe
        "https://api.stripe.com",
        "https://js.stripe.com",
        "https://hooks.stripe.com",
        # ORCID (sandbox + production)
        "https://sandbox.orcid.org",
        "https://orcid.org",
        "https://pub.sandbox.orcid.org",
        "https://pub.orcid.org",
        # OpenAlex (citation enrichment)
        "https://api.openalex.org",
        # WebSocket support for dev hot-reload and production websockets
        "wss:",
    ])
    base = [
        "default-src 'self'",
        "img-src 'self' data: blob: https:",
        "style-src 'self' 'unsafe-inline'",      # Tailwind/Shadcn need inline styles
        "font-src 'self' data: https://fonts.gstatic.com",
        # AUTH-004: no 'unsafe-inline' — use INLINE_RUNTIME_CHUNK=false in React build
        f"script-src 'self' https://js.stripe.com",
        f"connect-src {allowed_connect}",
        "frame-src 'self' https://js.stripe.com https://hooks.stripe.com",
        "frame-ancestors 'self'",
        "form-action 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "upgrade-insecure-requests",
    ]
    report = os.environ.get("CSP_REPORT_URI", "").strip()
    if report:
        base.append(f"report-uri {report}")
    return "; ".join(base)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "SAMEORIGIN"
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        h["X-XSS-Protection"] = "0"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        h["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(self), usb=()"
        )
        if os.environ.get("COOKIE_SECURE", "0") == "1":
            h["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        h["Content-Security-Policy"] = _csp()
        return response


# AUTH-007: CSRF double-submit cookie validation
# ─────────────────────────────────────────────
# Strategy: the server sets a non-HttpOnly cookie `csrf_token` on login/register/OAuth.
# The frontend reads it via JS and sends it back as the `X-CSRF-Token` header.
# The middleware compares them with a timing-safe compare_digest.
#
# Exempt: safe methods (GET/HEAD/OPTIONS) + pre-auth endpoints where the cookie
# does not yet exist.

_CSRF_EXEMPT_PATHS = frozenset({
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/logout",       # CSRF-forced logout is an annoyance, not a security breach
    "/api/auth/refresh",
    "/api/auth/forgot-password",
    "/api/auth/verify-email",
    "/api/auth/resend-verification",
    "/api/auth/reset-password",
    "/api/auth/csrf-token",
    "/api/orcid/callback",
    "/api/google/callback",
    "/api/billing/webhook",   # Stripe server-to-server — no browser session
    "/api/unsubscribe",       # Email unsubscribe link — may be clicked without session
    "/api/",
})

_CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in _CSRF_SAFE_METHODS:
            return await call_next(request)
        if request.url.path in _CSRF_EXEMPT_PATHS:
            return await call_next(request)
        cookie_token = request.cookies.get("csrf_token", "")
        header_token = request.headers.get("X-CSRF-Token", "")
        if not cookie_token or not header_token:
            return JSONResponse(
                {"detail": "CSRF token missing. Ensure you are authenticated and retry."},
                status_code=403,
            )
        if not secrets.compare_digest(cookie_token, header_token):
            return JSONResponse(
                {"detail": "CSRF token mismatch. Refresh the page and retry."},
                status_code=403,
            )
        return await call_next(request)


# H4: IP block enforcement
# ─────────────────────────────────────────────────────────────────────────────
# Cache the blocked IP set in memory and refresh every 60 seconds so we avoid
# a DB round-trip on every single request.

_blocked_ip_cache: set = set()
_blocked_ip_cache_ts: float = 0.0
_IP_CACHE_TTL: float = 60.0


def _extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return ""


async def _get_blocked_ips() -> set:
    global _blocked_ip_cache, _blocked_ip_cache_ts
    now = _time_module.monotonic()
    if now - _blocked_ip_cache_ts < _IP_CACHE_TTL:
        return _blocked_ip_cache

    # RC1 AUDIT FINDING: this runs on EVERY request (IPBlockMiddleware has no
    # skip-list). The cache timestamp was only advanced on a *successful*
    # refresh, so a Mongo outage meant every single request re-attempted the
    # query and paid the full connection timeout (~4s), forever — the 60s TTL
    # cache gave zero protection once the first attempt failed. Reproduced
    # live: /openapi.json (which no other middleware even touches Mongo for)
    # still measured ~4-4.7s during the outage until this fix.
    from db import is_db_down
    if is_db_down():
        return _blocked_ip_cache
    try:
        from db import get_db
        from repo.shim import make_db_proxy
        docs = await make_db_proxy(get_db(), system=True).blocked_ips.find({}, {"ip": 1, "_id": 0}).to_list(10000)
        _blocked_ip_cache = {d["ip"] for d in docs}
    except Exception:
        pass
    finally:
        # Advance the timestamp regardless of outcome so a failed attempt
        # also respects the TTL — otherwise a Mongo error that ISN'T yet
        # recognized by the circuit breaker (a fresh, not-yet-classified
        # failure) would still retry on every request instead of waiting a
        # full cache window.
        _blocked_ip_cache_ts = now
    return _blocked_ip_cache


class IPBlockMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = _extract_client_ip(request)
        if ip:
            blocked = await _get_blocked_ips()
            if ip in blocked:
                return JSONResponse({"detail": "Access denied."}, status_code=403)
        return await call_next(request)
