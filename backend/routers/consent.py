"""Cookie consent storage — GDPR compliance.

Stores user consent preferences either tied to an authenticated user OR by an
anonymous consent_id stored client-side. Required so we can prove consent was
captured per the EU ePrivacy Directive ("Cookie Law").

Schema (collection `consent_records`):
  - user_id: optional
  - consent_id: client-side UUID (always)
  - status: 'accepted_all' | 'rejected_non_essential' | 'custom'
  - prefs: {essential: True, analytics: bool, marketing: bool, preferences: bool}
  - source: 'banner' | 'preferences_modal'
  - user_agent, ip_hash (truncated for GDPR-friendly storage)
  - created_at
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from db import get_db
from auth_utils import get_optional_user
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/consent", tags=["consent"])


class ConsentPrefs(BaseModel):
    essential: bool = True  # immutable — required for app function
    analytics: bool = False
    marketing: bool = False
    preferences: bool = False


class ConsentIn(BaseModel):
    consent_id: str = Field(..., min_length=8, max_length=64)
    status: str  # accepted_all | rejected_non_essential | custom
    prefs: ConsentPrefs
    source: str = "banner"


def _hash_ip(ip: str) -> str:
    if not ip: return ""
    # Use a dedicated IP_HASH_SALT separate from JWT_SECRET to avoid salt reuse.
    # Falls back to a truncated JWT_SECRET for backward-compat if not configured.
    salt = os.environ.get("IP_HASH_SALT", "") or os.environ.get("JWT_SECRET", "salt")[:16]
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


def _client_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for", "")
    if xff: return xff.split(",")[0].strip()
    return req.client.host if req.client else ""


@router.post("")
async def submit_consent(payload: ConsentIn, request: Request):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user = await get_optional_user(request)
    doc = {
        "consent_id": payload.consent_id,
        "user_id": user["id"] if user else None,
        "status": payload.status if payload.status in ("accepted_all",
                                                       "rejected_non_essential",
                                                       "custom") else "custom",
        "prefs": payload.prefs.model_dump(),
        "source": payload.source if payload.source in ("banner", "preferences_modal") else "banner",
        "user_agent": (request.headers.get("user-agent") or "")[:200],
        "ip_hash": _hash_ip(_client_ip(request)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.consent_records.insert_one(doc)
    doc["id"] = str(doc.pop("_id")) if "_id" in doc else None
    return {"ok": True, "record": {k: v for k, v in doc.items() if k != "ip_hash"}}


@router.get("/latest")
async def get_latest_consent(consent_id: Optional[str] = None, request: Request = None):
    """Return the most recent consent for the current user OR consent_id."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user = await get_optional_user(request) if request else None
    q = {}
    if user:
        q["user_id"] = user["id"]
    elif consent_id:
        q["consent_id"] = consent_id
    else:
        return {"record": None}
    doc = await db.consent_records.find_one(q, sort=[("created_at", -1)])
    if not doc:
        return {"record": None}
    doc["id"] = str(doc.pop("_id"))
    doc.pop("ip_hash", None)
    return {"record": doc}
