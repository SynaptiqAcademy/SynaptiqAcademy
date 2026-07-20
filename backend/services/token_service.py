"""Refresh token registry — server-side revocation support (AUTH-005).

Every issued refresh token has a UUID jti stored here. Revocation is checked
before any new token pair is issued. Rotation immediately revokes the consumed
jti — but carries the same `session_id` forward, so a "session" (a device
login, in the Active Sessions UI sense) survives silent token rotation while
still being individually revocable.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.token_service")

_REFRESH_DAYS = 14


async def store_refresh_jti(
    jti: str,
    user_id: str,
    session_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Persist a new refresh token. Returns the session_id (generated if not passed)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    session_id = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.refresh_tokens.insert_one({
        "jti": jti,
        "user_id": user_id,
        "session_id": session_id,
        "ip": ip,
        "user_agent": user_agent or "",
        "issued_at": now,
        "last_seen_at": now,
        "expires_at": now + timedelta(days=_REFRESH_DAYS),
        "revoked": False,
        "revoked_at": None,
    })
    return session_id


async def get_refresh_record(jti: str) -> dict | None:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    return await db.refresh_tokens.find_one({"jti": jti})


async def is_jti_revoked(jti: str) -> bool:
    """True if jti is unknown or has been revoked."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    record = await db.refresh_tokens.find_one({"jti": jti})
    if not record:
        return True
    return bool(record.get("revoked"))


async def revoke_jti(jti: str) -> None:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.refresh_tokens.update_one(
        {"jti": jti},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}},
    )


async def revoke_all_user_tokens(user_id: str) -> int:
    """Revoke every active refresh token for a user. Returns the count revoked."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.refresh_tokens.update_many(
        {"user_id": user_id, "revoked": False},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count


async def list_active_sessions(user_id: str) -> list[dict]:
    """One row per active (non-revoked, non-expired) session — the current
    jti's record for each still-live session_id, thanks to rotation carrying
    session_id forward and revoking the previous jti."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = datetime.now(timezone.utc)
    cursor = db.refresh_tokens.find({
        "user_id": user_id,
        "revoked": False,
        "expires_at": {"$gt": now},
    }).sort("last_seen_at", -1)
    return await cursor.to_list(200)


async def revoke_session(user_id: str, session_id: str) -> int:
    """Revoke a session. Falls back to matching by jti for legacy refresh_token
    rows issued before session_id existed on this collection."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.refresh_tokens.update_many(
        {
            "user_id": user_id,
            "revoked": False,
            "$or": [{"session_id": session_id}, {"jti": session_id}],
        },
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count
