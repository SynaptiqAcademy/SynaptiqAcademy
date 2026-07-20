"""Admin audit service — the ONLY module that writes to audit_log and security_events.

AUTH-011: All documents now include an `expires_at` datetime field so that MongoDB
TTL indexes can auto-expire old records.

  audit_log      → 90-day retention
  security_events → 180-day retention
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.admin.audit")

_AUDIT_LOG_TTL_DAYS = 90
_SECURITY_EVENT_TTL_DAYS = 180


async def log_event(
    action: str,
    *,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    target_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_email: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Write one event to audit_log. Swallows exceptions — never blocks the caller."""
    try:
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        now = datetime.now(timezone.utc)
        await db.audit_log.insert_one({
            "action": action,
            "actor_id": actor_id,
            "actor_email": actor_email,
            "target_id": target_id,
            "target_type": target_type,
            "target_email": target_email,
            "ip": ip,
            "user_agent": user_agent,
            "extra": extra or {},
            "created_at": now.isoformat(),
            "expires_at": now + timedelta(days=_AUDIT_LOG_TTL_DAYS),  # TTL index field
        })
    except Exception as e:
        logger.warning("Audit log write failed: %s", e)


async def write_security_event(
    event_type: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Write to security_events collection (failed logins, suspicious activity)."""
    try:
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        now = datetime.now(timezone.utc)
        await db.security_events.insert_one({
            "event_type": event_type,
            "ip": ip,
            "user_agent": user_agent,
            "extra": extra or {},
            "created_at": now.isoformat(),
            "expires_at": now + timedelta(days=_SECURITY_EVENT_TTL_DAYS),  # TTL index field
        })
    except Exception as e:
        logger.warning("Security event write failed: %s", e)


def request_meta(request) -> dict:
    xff = request.headers.get("x-forwarded-for", "")
    ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else None)
    ua = request.headers.get("user-agent", "")
    return {"ip": ip, "user_agent": ua}
