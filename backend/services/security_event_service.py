"""Enhanced security event service with severity, actor context, and resolution workflow.

Supersedes write_security_event() in admin_audit.py for structured security events.
The existing write_security_event() is kept for backwards-compatibility.

Collection: security_events (already exists, TTL-indexed)
  Enhanced fields added to new events:
    severity: "low"|"medium"|"high"|"critical"
    event_type: str  (categorized)
    actor_id: str | None
    actor_email: str | None
    resolved: bool
    resolved_at: str | None
    resolved_by: str | None
    resolution_note: str | None
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.security_events")

_TTL_DAYS = 365  # keep security events 1 year

_SEVERITY_MAP: dict[str, str] = {
    # auth events
    "login_failed":                 "medium",
    "login_blocked_risk":           "critical",
    "login_new_device":             "low",
    "login_country_change":         "medium",
    "login_impossible_travel":      "critical",
    "login_tor_proxy":              "critical",
    # MFA events
    "mfa_failed":                   "high",
    "mfa_enabled":                  "low",
    "mfa_disabled":                 "high",
    "mfa_recovery_used":            "high",
    "mfa_codes_regenerated":        "medium",
    # privilege events
    "privilege_escalation_attempt": "critical",
    "role_change":                  "medium",
    "unauthorized_admin_access":    "critical",
    "admin_route_violation":        "high",
    # session events
    "session_terminated":           "low",
    "all_sessions_terminated":      "medium",
    "emergency_logout":             "high",
    # device events
    "device_trusted":               "low",
    "device_revoked":               "low",
    "all_devices_revoked":          "medium",
    # account events
    "brute_force_detected":         "high",
    "account_locked":               "medium",
    "account_suspended":            "high",
    "account_banned":               "critical",
    # IP events
    "ip_blocked":                   "high",
    "ip_outside_allowlist":         "high",
    # break-glass
    "break_glass_initiated":        "critical",
    "break_glass_completed":        "critical",
    # generic
    "suspicious_activity":          "high",
}


async def emit_security_event(
    event_type: str,
    *,
    severity: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra: Optional[dict] = None,
) -> Optional[str]:
    """Write a structured security event. Returns the inserted document id."""
    try:
        db  = get_db()
        db = DBProxy(db, SecurityContext.system())

        now = datetime.now(timezone.utc)
        sev = severity or _SEVERITY_MAP.get(event_type, "medium")

        result = await db.security_events.insert_one({
            "event_type":      event_type,
            "severity":        sev,
            "actor_id":        actor_id,
            "actor_email":     actor_email,
            "ip":              ip,
            "user_agent":      user_agent,
            "extra":           extra or {},
            "resolved":        False,
            "resolved_at":     None,
            "resolved_by":     None,
            "resolution_note": None,
            "created_at":      now.isoformat(),
            "expires_at":      now + timedelta(days=_TTL_DAYS),
        })
        try:
            from services.realtime import manager
            await manager.broadcast_admin({
                "type": "security_event", "event_type": event_type,
                "severity": sev, "actor_email": actor_email,
            })
        except Exception:
            pass
        return str(result.inserted_id)
    except Exception as e:
        logger.warning("Security event write failed (%s): %s", event_type, e)
        return None


async def resolve_event(event_id: str, resolved_by: str, note: str = "") -> bool:
    from bson import ObjectId
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.security_events.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": {
            "resolved":        True,
            "resolved_at":     datetime.now(timezone.utc).isoformat(),
            "resolved_by":     resolved_by,
            "resolution_note": note,
        }},
    )
    return result.modified_count > 0


async def get_events(
    *,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    actor_email: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
) -> list[dict]:
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    flt: dict = {}
    if severity:    flt["severity"]    = severity
    if event_type:  flt["event_type"]  = event_type
    if resolved is not None: flt["resolved"] = resolved
    if actor_email: flt["actor_email"] = actor_email

    docs = await db.security_events.find(flt, {"expires_at": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


async def event_stats() -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    pipeline = [
        {"$group": {
            "_id": "$severity",
            "total": {"$sum": 1},
            "unresolved": {"$sum": {"$cond": [{"$eq": ["$resolved", False]}, 1, 0]}},
        }},
    ]
    agg = await db.security_events.aggregate(pipeline).to_list(10)
    by_sev = {d["_id"]: {"total": d["total"], "unresolved": d["unresolved"]} for d in agg}

    critical = by_sev.get("critical", {})
    high     = by_sev.get("high", {})

    return {
        "by_severity": by_sev,
        "total_unresolved": sum(d["unresolved"] for d in by_sev.values()),
        "critical_unresolved": critical.get("unresolved", 0),
        "high_unresolved": high.get("unresolved", 0),
    }
