"""ORCID OAuth service — sandbox-by-default, dry-run safe.

Graceful behavior:
- If ORCID_CLIENT_ID / ORCID_CLIENT_SECRET are not set, every flow raises a
  503 with a helpful message. Frontend can detect via `/api/orcid/config` and
  render a "ORCID not configured" CTA.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

logger = logging.getLogger("synaptiq.orcid")

# Sandbox defaults — overridable via env.
ORCID_BASE_URL     = os.environ.get("ORCID_BASE_URL",     "https://sandbox.orcid.org")
ORCID_API_BASE_URL = os.environ.get("ORCID_API_BASE_URL", "https://pub.sandbox.orcid.org/v3.0")
ORCID_CLIENT_ID    = os.environ.get("ORCID_CLIENT_ID",    "")
ORCID_CLIENT_SECRET = os.environ.get("ORCID_CLIENT_SECRET", "")
ORCID_REDIRECT_URI = os.environ.get(
    "ORCID_REDIRECT_URI",
    (os.environ.get("BACKEND_BASE_URL") or "").rstrip("/") + "/api/orcid/callback"
    if os.environ.get("BACKEND_BASE_URL")
    else ""
)
ORCID_STATE_SECRET = os.environ.get("ORCID_STATE_SECRET", os.environ.get("JWT_SECRET", "synaptiq-orcid-state"))

# Frontend base for post-callback redirect.
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "")


def is_configured() -> bool:
    return bool(ORCID_CLIENT_ID and ORCID_CLIENT_SECRET)


def config_info() -> dict:
    """Public-safe configuration snapshot for the frontend."""
    return {
        "configured": is_configured(),
        "environment": "sandbox" if "sandbox" in ORCID_BASE_URL else "production",
        "base_url": ORCID_BASE_URL,
        "redirect_uri": ORCID_REDIRECT_URI,
    }


def _require_configured():
    if not is_configured():
        raise HTTPException(503, "ORCID is not configured. Ask an admin to set ORCID_CLIENT_ID and ORCID_CLIENT_SECRET.")


# ============================= STATE TOKEN ==================================
def encode_state(payload: dict) -> str:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(ORCID_STATE_SECRET.encode(), data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(data + b"." + sig).decode()


def decode_state(state: str) -> dict:
    raw = base64.urlsafe_b64decode(state.encode())
    data, sig = raw.rsplit(b".", 1)
    expected = hmac.new(ORCID_STATE_SECRET.encode(), data, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("Invalid state signature")
    return json.loads(data.decode())


# ============================= OAUTH ========================================
def authorization_url(mode: Literal["login", "signup", "link"],
                      requesting_user_id: Optional[str] = None) -> str:
    _require_configured()
    state = encode_state({"mode": mode, "uid": requesting_user_id, "ts": int(time.time())})
    qs = urlencode({
        "client_id":    ORCID_CLIENT_ID,
        "response_type": "code",
        "scope":        "/authenticate",  # implicitly includes /read-public
        "redirect_uri": ORCID_REDIRECT_URI,
        "state":        state,
    })
    return f"{ORCID_BASE_URL}/oauth/authorize?{qs}"


async def exchange_code(code: str) -> dict:
    _require_configured()
    async with httpx.AsyncClient(timeout=12.0) as cli:
        r = await cli.post(
            f"{ORCID_BASE_URL}/oauth/token",
            data={
                "client_id": ORCID_CLIENT_ID,
                "client_secret": ORCID_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": ORCID_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
    if r.status_code >= 400:
        logger.warning("ORCID token exchange failed: %s %s", r.status_code, r.text[:200])
        raise HTTPException(502, "ORCID token exchange failed")
    return r.json()


def normalize_token(token: dict) -> dict:
    now = datetime.now(timezone.utc)
    expires_in = token.get("expires_in")
    expires_at = (now + timedelta(seconds=int(expires_in))).isoformat() \
        if expires_in else (now + timedelta(days=365 * 20)).isoformat()
    return {
        "access_token":  token.get("access_token"),
        "refresh_token": token.get("refresh_token"),
        "scope":         token.get("scope"),
        "orcid_id":      token.get("orcid"),
        "expires_at":    expires_at,
        "verified_at":   now.isoformat(),
        "connected_at":  now.isoformat(),
        "name":          token.get("name"),
    }


# ============================= PUBLIC API ===================================
async def fetch_record(orcid_id: str, access_token: Optional[str] = None) -> dict:
    headers = {"Accept": "application/json"}
    if access_token: headers["Authorization"] = f"Bearer {access_token}"
    async with httpx.AsyncClient(timeout=15.0) as cli:
        r = await cli.get(f"{ORCID_API_BASE_URL}/{orcid_id}/record", headers=headers)
    if r.status_code >= 400:
        logger.warning("ORCID record fetch failed: %s %s", r.status_code, r.text[:200])
        raise HTTPException(502, f"ORCID record fetch failed ({r.status_code})")
    return r.json()


# ============================= TOKEN REFRESH =================================

async def refresh_access_token(refresh_token_value: str) -> dict:
    """Exchange a refresh token for a new access + refresh token pair.

    Calls the ORCID token endpoint with grant_type=refresh_token.
    Returns a normalized token dict (same shape as normalize_token).
    Raises HTTPException(502) on failure.
    """
    _require_configured()
    async with httpx.AsyncClient(timeout=12.0) as cli:
        r = await cli.post(
            f"{ORCID_BASE_URL}/oauth/token",
            data={
                "client_id":     ORCID_CLIENT_ID,
                "client_secret": ORCID_CLIENT_SECRET,
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token_value,
            },
            headers={"Accept": "application/json"},
        )
    if r.status_code >= 400:
        logger.warning("ORCID token refresh failed: %s %s", r.status_code, r.text[:200])
        raise HTTPException(502, "ORCID token refresh failed")
    return normalize_token(r.json())


async def get_valid_access_token(db, user_id: str) -> Optional[str]:
    """Return a non-expired ORCID access token for a user, refreshing if needed.

    Returns None if the user has no ORCID connection or credentials are not
    configured.  Updates the user document in-place when a refresh occurs.
    """
    if not is_configured():
        return None

    from bson import ObjectId
    u = await db.users.find_one(
        {"_id": ObjectId(user_id)},
        {"orcid.access_token": 1, "orcid.refresh_token": 1, "orcid.expires_at": 1},
    )
    orcid_data = (u or {}).get("orcid") or {}
    access     = orcid_data.get("access_token")
    refresh    = orcid_data.get("refresh_token")
    expires_at = orcid_data.get("expires_at")

    if not access:
        return None

    # check expiry — refresh if within 7 days of expiry or already expired
    if expires_at and refresh:
        try:
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            remaining = (exp - datetime.now(timezone.utc)).total_seconds()
            if remaining < 7 * 86_400:  # less than 7 days
                new_tok = await refresh_access_token(refresh)
                await db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {
                        "orcid.access_token":  new_tok["access_token"],
                        "orcid.refresh_token": new_tok.get("refresh_token", refresh),
                        "orcid.expires_at":    new_tok["expires_at"],
                    }},
                )
                logger.info("ORCID token refreshed for user %s", user_id)
                return new_tok["access_token"]
        except Exception as exc:
            logger.warning("ORCID token refresh skipped for user %s: %s", user_id, exc)

    return access


async def fetch_work_detail(orcid_id: str, put_code: str | int,
                              access_token: Optional[str] = None) -> Optional[dict]:
    """Pull full work detail (for abstract, DOI, citation, etc.)."""
    headers = {"Accept": "application/json"}
    if access_token: headers["Authorization"] = f"Bearer {access_token}"
    async with httpx.AsyncClient(timeout=15.0) as cli:
        r = await cli.get(f"{ORCID_API_BASE_URL}/{orcid_id}/work/{put_code}", headers=headers)
    if r.status_code >= 400: return None
    return r.json()
