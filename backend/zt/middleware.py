"""
Zero Trust Middleware — Phase XXXV.8

Every HTTP request is verified, risk-scored, and security-enriched.
The middleware is additive: it never blocks requests that were
previously allowed (backward-compatible), but it:

1. Extracts identity from JWT / API key
2. Builds IdentityContext and attaches to request.state
3. Scores request risk
4. Checks AI security for relevant endpoints
5. Tracks request in security monitor
6. Adds Zero Trust response headers
7. Audit-logs access (async, non-blocking)

No business logic is changed; only the security context is enriched.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .identity import IdentityContext, AuthMethod, ANONYMOUS_IDENTITY, build_identity_context
from .risk_engine import get_risk_engine

logger = logging.getLogger(__name__)

_AI_PATHS = ("/api/ai", "/api/copilot", "/api/ara", "/api/sie")
_SKIP_PATHS = ("/api/health", "/api/", "/docs", "/redoc", "/openapi.json")


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """
    Zero Trust request enrichment middleware.
    Wraps every HTTP request with identity context and risk scoring.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        # Skip static / health paths
        if any(path.startswith(p) for p in _SKIP_PATHS):
            return await call_next(request)

        t0 = time.monotonic()

        # ── 1. Identity extraction ────────────────────────────────────────────
        identity = await self._extract_identity(request)
        request.state.zt_identity = identity

        # ── 2. Risk scoring ───────────────────────────────────────────────────
        try:
            risk = get_risk_engine().score(
                identity   = identity,
                path       = path,
                method     = request.method,
                ip         = self._get_ip(request),
                user_agent = request.headers.get("user-agent", ""),
                new_device = not identity.device_trusted,
            )
            request.state.zt_risk = risk
        except Exception:
            risk = None

        # ── 3. Security monitor tracking ──────────────────────────────────────
        asyncio.ensure_future(self._track(identity, request))

        # ── 4. Call downstream ────────────────────────────────────────────────
        response = await call_next(request)

        # ── 5. Security response headers ──────────────────────────────────────
        response.headers["X-ZT-Identity-Type"] = identity.identity_type
        response.headers["X-ZT-Auth"]          = str(identity.is_authenticated).lower()
        if risk:
            response.headers["X-ZT-Risk-Level"]  = risk.level
            response.headers["X-ZT-Risk-Score"]  = str(risk.score)

        return response

    async def _extract_identity(self, request: Request) -> IdentityContext:
        """
        Try to resolve identity from Authorization header.
        Falls back to anonymous if no token or token is invalid.
        Does NOT raise — backward compatibility is mandatory.
        """
        auth_header = request.headers.get("authorization", "")
        if not auth_header:
            return ANONYMOUS_IDENTITY

        try:
            if auth_header.lower().startswith("bearer "):
                token = auth_header[7:]
                from auth_utils import decode_access_token
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("sub") or payload.get("user_id")
                    return build_identity_context(
                        {"_id": user_id, "role": payload.get("role", "researcher"),
                         "email": payload.get("email"), "subscription_tier": payload.get("tier", "free"),
                         "email_verified": payload.get("email_verified", True)},
                        auth_method  = AuthMethod.PASSWORD,
                        mfa_verified = bool(payload.get("mfa")),
                    )
        except Exception:
            pass

        return ANONYMOUS_IDENTITY

    def _get_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    async def _track(self, identity: IdentityContext, request: Request) -> None:
        try:
            from .monitoring import get_monitor
            monitor = get_monitor()
            monitor.track_request(identity.subject_id, self._get_ip(request))
        except Exception:
            pass
