"""Google OAuth 2.0 service (AUTH-013).

Implements the authorization code flow with HMAC-signed state for CSRF protection.

Required env vars:
  GOOGLE_CLIENT_ID      — from Google Cloud Console > Credentials
  GOOGLE_CLIENT_SECRET  — from Google Cloud Console > Credentials
  GOOGLE_REDIRECT_URI   — must match exactly what is registered in the console
                          e.g. https://yourdomain.com/api/google/callback

Optional (same conventions as services/orcid/oauth.py):
  FRONTEND_BASE_URL     — frontend origin for post-login redirects (falls back to the
                          deprecated APP_BASE_URL, then a hardcoded default, for
                          backward compatibility)
  BACKEND_BASE_URL      — backend origin, used only to derive GOOGLE_REDIRECT_URI when
                          that variable itself isn't set
  GOOGLE_STATE_SECRET   — dedicated OAuth-state signing secret (falls back to JWT_SECRET)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

logger = logging.getLogger("synaptiq.google_oauth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_SCOPES = "openid email profile"

# FRONTEND_BASE_URL is canonical; APP_BASE_URL is a deprecated backward-compatible
# alias (historically the only variable read here, and still required by
# services/prod_validator.py as a fallback — see ENVIRONMENT_VARIABLES.md).
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL") or os.environ.get("APP_BASE_URL", "https://synaptiq.academy")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
# Dedicated state-signing secret, same convention as ORCID_STATE_SECRET.
GOOGLE_STATE_SECRET = os.environ.get("GOOGLE_STATE_SECRET", os.environ.get("JWT_SECRET", ""))
STATE_WINDOW_SECS = 600  # 10-minute state validity


def is_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def _require_configured():
    if not is_configured():
        raise HTTPException(503, detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")


def _state_secret() -> str:
    if not GOOGLE_STATE_SECRET:
        raise RuntimeError("JWT_SECRET or GOOGLE_STATE_SECRET required for Google OAuth state signing")
    return GOOGLE_STATE_SECRET


def encode_state(mode: str, requesting_user_id: Optional[str] = None) -> str:
    """Create HMAC-signed state blob to prevent CSRF in the OAuth callback."""
    payload = json.dumps({"mode": mode, "uid": requesting_user_id, "ts": int(time.time())},
                         separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(_state_secret().encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + sig).decode().rstrip("=")


def decode_state(state: str) -> dict:
    """Verify and decode state. Raises ValueError on bad/expired state."""
    try:
        padded = state + "=" * (-len(state) % 4)
        raw = base64.urlsafe_b64decode(padded)
        payload, sig = raw.rsplit(b".", 1)
    except Exception:
        raise ValueError("Malformed state parameter")
    expected = hmac.new(_state_secret().encode(), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("State signature invalid")
    data = json.loads(payload.decode())
    if time.time() - data.get("ts", 0) > STATE_WINDOW_SECS:
        raise ValueError("State expired")
    return data


def authorization_url(mode: str, requesting_user_id: Optional[str] = None) -> str:
    _require_configured()
    redirect = GOOGLE_REDIRECT_URI or f"{os.environ.get('BACKEND_BASE_URL', '')}/api/google/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": encode_state(mode, requesting_user_id),
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    redirect = GOOGLE_REDIRECT_URI or f"{os.environ.get('BACKEND_BASE_URL', '')}/api/google/callback"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        })
        if r.status_code != 200:
            logger.error("Google token exchange failed: %s %s", r.status_code, r.text)
            raise HTTPException(502, "Google token exchange failed")
        return r.json()


async def get_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if r.status_code != 200:
            raise HTTPException(502, "Failed to fetch Google user info")
        return r.json()


def config_info() -> dict:
    return {
        "configured": is_configured(),
        "client_id_hint": GOOGLE_CLIENT_ID[:8] + "..." if GOOGLE_CLIENT_ID else None,
        "redirect_uri": GOOGLE_REDIRECT_URI or None,
    }
