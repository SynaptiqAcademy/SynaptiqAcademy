"""Trusted Device Management.

Identifies devices by a fingerprint derived from request headers and IP.
When a super-admin logs in from an unknown device, MFA is required regardless
of whether MFA is globally enabled.

Collection: trusted_devices
  {
    user_id: str,
    fingerprint: str,  (SHA-256 of ip+ua+accept-language)
    browser: str,
    os: str,
    ip: str,
    country: str | None,
    city: str | None,
    trusted_at: str,
    last_seen_at: str,
    revoked: bool,
    revoked_at: str | None,
    user_label: str | None,  (optional user-assigned name)
  }
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import Request

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.device_service")


# ─────────────────────────────────────────────────────────────────────────────
# Fingerprinting
# ─────────────────────────────────────────────────────────────────────────────

def build_fingerprint(request: Request) -> str:
    """Deterministic fingerprint: hash of IP + User-Agent + Accept-Language."""
    xff = request.headers.get("x-forwarded-for", "")
    ip  = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")
    ua  = request.headers.get("user-agent", "")
    al  = request.headers.get("accept-language", "")
    raw = f"{ip}|{ua}|{al}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _parse_browser(ua: str) -> str:
    ua = ua or ""
    if "Edg/" in ua or "Edge/" in ua:  return "Edge"
    if "Firefox/" in ua:               return "Firefox"
    if "Chrome/" in ua:                return "Chrome"
    if "Safari/" in ua:                return "Safari"
    if "Opera/" in ua or "OPR/" in ua: return "Opera"
    if "curl" in ua.lower():           return "curl"
    return "Unknown"


def _parse_os(ua: str) -> str:
    ua = ua or ""
    if "Windows NT" in ua:  return "Windows"
    if "Mac OS X" in ua:    return "macOS"
    if "Linux" in ua:       return "Linux"
    if "Android" in ua:     return "Android"
    if "iPhone" in ua or "iPad" in ua: return "iOS"
    return "Unknown"


def _get_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")


# ─────────────────────────────────────────────────────────────────────────────
# Trust management
# ─────────────────────────────────────────────────────────────────────────────

async def is_trusted_device(user_id: str, fingerprint: str) -> bool:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    doc = await db.trusted_devices.find_one({
        "user_id": user_id, "fingerprint": fingerprint, "revoked": {"$ne": True}
    })
    if doc:
        # Update last_seen
        await db.trusted_devices.update_one(
            {"_id": doc["_id"]},
            {"$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()}},
        )
    return doc is not None


async def trust_device(user_id: str, fingerprint: str, request: Request,
                        country: Optional[str] = None, city: Optional[str] = None) -> str:
    """Register device as trusted. Returns device document id."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    ua  = request.headers.get("user-agent", "")
    ip  = _get_ip(request)
    now = datetime.now(timezone.utc).isoformat()

    # Upsert: if fingerprint already exists (even if revoked), re-activate it
    existing = await db.trusted_devices.find_one({"user_id": user_id, "fingerprint": fingerprint})
    if existing:
        await db.trusted_devices.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "revoked": False, "revoked_at": None,
                "last_seen_at": now, "ip": ip,
                "country": country, "city": city,
            }},
        )
        return str(existing["_id"])

    result = await db.trusted_devices.insert_one({
        "user_id":     user_id,
        "fingerprint": fingerprint,
        "browser":     _parse_browser(ua),
        "os":          _parse_os(ua),
        "ip":          ip,
        "country":     country,
        "city":        city,
        "trusted_at":  now,
        "last_seen_at": now,
        "revoked":     False,
        "revoked_at":  None,
        "user_label":  None,
    })
    return str(result.inserted_id)


async def get_trusted_devices(user_id: str) -> list[dict]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.trusted_devices.find(
        {"user_id": user_id, "revoked": {"$ne": True}},
        {"fingerprint": 0},   # never expose fingerprint to UI
    ).sort("last_seen_at", -1).to_list(50)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


async def revoke_device(device_id: str, user_id: str) -> bool:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.trusted_devices.update_one(
        {"_id": ObjectId(device_id), "user_id": user_id},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc).isoformat()}},
    )
    return result.modified_count > 0


async def revoke_all_devices(user_id: str) -> int:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.trusted_devices.update_many(
        {"user_id": user_id, "revoked": {"$ne": True}},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc).isoformat()}},
    )
    return result.modified_count
