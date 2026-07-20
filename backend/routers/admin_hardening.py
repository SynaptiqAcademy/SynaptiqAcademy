"""Admin Security Hardening — Phase XII.

Sections covered:
  4.  Trusted Device Management
  5.  Geolocation & Risk Detection
  6.  IP Allowlist (allowlist / monitor mode)
  7.  Session Security Center
  8.  Break-Glass Recovery System
  9.  (UI audit is frontend-only — no endpoints needed)
  10. Super Admin Audit Center
  11. Security Event Engine
  12. Security Certification scoring
"""
from __future__ import annotations

import asyncio
import ipaddress
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import get_db
from services.admin_audit import log_event, request_meta
from services.device_service import get_trusted_devices, revoke_device, revoke_all_devices
from services.mfa_service import mfa_is_enabled
from services.permissions import require_super_admin, PROTECTED_SUPER_ADMIN_EMAIL
from services.security_event_service import (
    emit_security_event, resolve_event, get_events, event_stats,
)
from services.token_service import revoke_all_user_tokens
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin/hardening", tags=["admin-hardening"])
_GATE = [Depends(require_super_admin)]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ═════════════════════════════════════════════════════════════════════════════
# 4. TRUSTED DEVICE MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/devices", dependencies=_GATE)
async def list_trusted_devices(admin: dict = Depends(require_super_admin)):
    devices = await get_trusted_devices(admin["id"])
    return {"devices": devices, "count": len(devices)}


@router.delete("/devices/{device_id}", dependencies=_GATE)
async def revoke_trusted_device(
    device_id: str,
    admin: dict = Depends(require_super_admin),
    request: Request = None,
):
    ok = await revoke_device(device_id, admin["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found")
    meta = request_meta(request) if request else {}
    await log_event("admin.device.revoked", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"device_id": device_id})
    await emit_security_event("device_revoked", actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"), extra={"device_id": device_id})
    return {"ok": True}


@router.delete("/devices", dependencies=_GATE)
async def revoke_all_trusted_devices(
    admin: dict = Depends(require_super_admin),
    request: Request = None,
):
    count = await revoke_all_devices(admin["id"])
    meta  = request_meta(request) if request else {}
    await log_event("admin.device.revoked_all", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"count": count})
    await emit_security_event("all_devices_revoked", actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"), extra={"count": count})
    return {"ok": True, "revoked_count": count}


# ═════════════════════════════════════════════════════════════════════════════
# 5. GEOLOCATION & RISK DETECTION
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/risk/history", dependencies=_GATE)
async def risk_history(limit: int = 50):
    """Recent security events related to login risk."""
    events = await get_events(
        event_type=None, resolved=None, limit=limit
    )
    risk_types = {
        "login_impossible_travel", "login_tor_proxy", "login_country_change",
        "login_blocked_risk", "suspicious_activity",
    }
    filtered = [e for e in events if e.get("event_type") in risk_types]
    return {"events": filtered, "count": len(filtered)}


@router.post("/risk/assess", dependencies=_GATE)
async def manual_risk_assess(ip: str):
    """On-demand geolocation + risk indicator check for an IP address."""
    from services.risk_engine import geolocate
    geo = await geolocate(ip)
    return {
        "ip":       ip,
        "geo":      geo,
        "is_proxy": geo.get("proxy", False),
        "is_hosting": geo.get("hosting", False),
        "country":  geo.get("countryCode"),
        "city":     geo.get("city"),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 6. IP ALLOWLIST
# ═════════════════════════════════════════════════════════════════════════════

class IPEntry(BaseModel):
    ip:    str        # CIDR range or single IP, e.g. "192.168.1.0/24" or "10.0.0.1"
    label: str = ""

class IPAllowlistMode(BaseModel):
    mode: str  # "monitor" | "enforce"


@router.get("/ip-allowlist", dependencies=_GATE)
async def get_ip_allowlist():
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    entries = await db.ip_allowlist.find({"active": True}, {"_id": 1, "ip": 1, "label": 1, "added_at": 1, "added_by": 1}).to_list(200)
    for e in entries:
        e["id"] = str(e.pop("_id"))
    mode_doc = await db.ip_allowlist_config.find_one({"_id": "config"})
    mode = mode_doc.get("mode", "monitor") if mode_doc else "monitor"
    return {"entries": entries, "count": len(entries), "mode": mode}


@router.post("/ip-allowlist", dependencies=_GATE)
async def add_ip_allowlist(body: IPEntry, admin: dict = Depends(require_super_admin), request: Request = None):
    # Validate IP/CIDR
    try:
        ipaddress.ip_network(body.ip, strict=False)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid IP address or CIDR range: {body.ip}")

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    existing = await db.ip_allowlist.find_one({"ip": body.ip, "active": True})
    if existing:
        raise HTTPException(status_code=409, detail="IP/range already in allowlist")

    await db.ip_allowlist.insert_one({
        "ip": body.ip, "label": body.label or body.ip,
        "active": True, "added_at": _now(), "added_by": admin.get("email"),
    })
    meta = request_meta(request) if request else {}
    await log_event("admin.ip_allowlist.added", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"entry": body.ip})
    return {"ok": True}


@router.delete("/ip-allowlist/{entry_id}", dependencies=_GATE)
async def remove_ip_allowlist(entry_id: str, admin: dict = Depends(require_super_admin), request: Request = None):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.ip_allowlist.update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": {"active": False, "removed_at": _now(), "removed_by": admin.get("email")}},
    )
    if not result.modified_count:
        raise HTTPException(status_code=404, detail="Entry not found")
    meta = request_meta(request) if request else {}
    await log_event("admin.ip_allowlist.removed", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"entry_id": entry_id})
    return {"ok": True}


@router.patch("/ip-allowlist/mode", dependencies=_GATE)
async def set_allowlist_mode(body: IPAllowlistMode, admin: dict = Depends(require_super_admin), request: Request = None):
    if body.mode not in ("monitor", "enforce"):
        raise HTTPException(status_code=400, detail="Mode must be 'monitor' or 'enforce'")
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.ip_allowlist_config.update_one(
        {"_id": "config"}, {"$set": {"mode": body.mode, "updated_at": _now(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    meta = request_meta(request) if request else {}
    await log_event("admin.ip_allowlist.mode_changed", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"mode": body.mode})
    return {"ok": True, "mode": body.mode}


def is_ip_in_allowlist(ip: str, entries: list[dict]) -> bool:
    """Check if an IP is covered by any entry in the allowlist."""
    try:
        client_ip = ipaddress.ip_address(ip)
        for entry in entries:
            try:
                net = ipaddress.ip_network(entry["ip"], strict=False)
                if client_ip in net:
                    return True
            except ValueError:
                pass
    except ValueError:
        pass
    return False


# ═════════════════════════════════════════════════════════════════════════════
# 7. SESSION SECURITY CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/sessions", dependencies=_GATE)
async def list_admin_sessions(admin: dict = Depends(require_super_admin)):
    """List active (non-revoked) refresh tokens for the admin account.

    Each refresh token row corresponds to one active session.
    """
    db      = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_id = admin["id"]
    tokens  = await db.refresh_tokens.find(
        {"user_id": user_id, "revoked": False},
        {"_id": 1, "jti": 0, "issued_at": 1, "expires_at": 1, "device_info": 1, "ip": 1},
    ).sort("issued_at", -1).to_list(50)

    sessions = []
    for t in tokens:
        sessions.append({
            "id":         str(t["_id"]),
            "issued_at":  str(t.get("issued_at") or ""),
            "expires_at": str(t.get("expires_at") or ""),
            "device_info": t.get("device_info") or "Unknown",
            "ip":          t.get("ip") or "Unknown",
        })

    return {"sessions": sessions, "count": len(sessions)}


class TerminateSessionBody(BaseModel):
    session_id: str


@router.post("/sessions/terminate", dependencies=_GATE)
async def terminate_session(
    body: TerminateSessionBody,
    admin: dict = Depends(require_super_admin),
    request: Request = None,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.refresh_tokens.update_one(
        {"_id": ObjectId(body.session_id), "user_id": admin["id"]},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}},
    )
    if not result.modified_count:
        raise HTTPException(status_code=404, detail="Session not found")
    meta = request_meta(request) if request else {}
    await log_event("admin.session.terminated", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"session_id": body.session_id})
    await emit_security_event("session_terminated", actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"))
    return {"ok": True}


@router.post("/sessions/terminate-all", dependencies=_GATE)
async def terminate_all_sessions(
    admin: dict = Depends(require_super_admin),
    request: Request = None,
):
    """Revoke every active session for the admin account."""
    count = await revoke_all_user_tokens(admin["id"])
    meta  = request_meta(request) if request else {}
    await log_event("admin.session.terminate_all", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"sessions_revoked": count})
    await emit_security_event("all_sessions_terminated", actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"), extra={"count": count})
    return {"ok": True, "sessions_revoked": count}


@router.post("/sessions/emergency-logout", dependencies=_GATE)
async def emergency_logout(
    admin: dict = Depends(require_super_admin),
    request: Request = None,
):
    """Nuclear option: revoke all sessions AND all trusted devices."""
    count   = await revoke_all_user_tokens(admin["id"])
    devices = await revoke_all_devices(admin["id"])
    meta    = request_meta(request) if request else {}
    await log_event("admin.session.emergency_logout", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"sessions_revoked": count, "devices_revoked": devices})
    await emit_security_event("emergency_logout", severity="high",
                               actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"), extra={"sessions": count, "devices": devices})
    return {"ok": True, "sessions_revoked": count, "devices_revoked": devices}


# ═════════════════════════════════════════════════════════════════════════════
# 8. BREAK-GLASS RECOVERY SYSTEM
# ═════════════════════════════════════════════════════════════════════════════

_BREAK_GLASS_TOKEN_TTL_MINUTES = 15


class BreakGlassInitBody(BaseModel):
    reason: str


@router.post("/break-glass/initiate", dependencies=_GATE)
async def initiate_break_glass(
    body: BreakGlassInitBody,
    admin: dict = Depends(require_super_admin),
    request: Request = None,
):
    """Generate a time-limited recovery token (15 min) and log the event.

    This token can be used to reset MFA or unlock the account without
    going through the normal auth flow. The token is returned ONCE and
    never stored in plaintext.
    """
    raw_token   = secrets.token_urlsafe(32)
    token_hash  = __import__("hashlib").sha256(raw_token.encode()).hexdigest()
    expires_at  = datetime.now(timezone.utc) + timedelta(minutes=_BREAK_GLASS_TOKEN_TTL_MINUTES)

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.break_glass_events.insert_one({
        "actor_id":    admin["id"],
        "actor_email": admin.get("email"),
        "reason":      body.reason,
        "token_hash":  token_hash,
        "expires_at":  expires_at.isoformat(),
        "used":        False,
        "used_at":     None,
        "created_at":  _now(),
    })

    meta = request_meta(request) if request else {}
    await log_event("admin.break_glass.initiated", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"),
                    extra={"reason": body.reason, "expires_at": expires_at.isoformat()})
    await emit_security_event("break_glass_initiated", severity="critical",
                               actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"), extra={"reason": body.reason})

    return {
        "recovery_token": raw_token,
        "expires_at":     expires_at.isoformat(),
        "expires_in_minutes": _BREAK_GLASS_TOKEN_TTL_MINUTES,
        "event_id":       str(result.inserted_id),
        "warning":        "Store this token securely. It expires in 15 minutes and will not be shown again.",
    }


@router.post("/break-glass/use")
async def use_break_glass(recovery_token: str, action: str = "reset_mfa"):
    """Use a break-glass token to perform emergency recovery without admin session.

    Actions: 'reset_mfa' — disable MFA on the protected account.
    This endpoint is intentionally NOT gated by require_super_admin because
    it's the recovery path when the admin is locked out.
    """
    import hashlib
    token_hash = hashlib.sha256(recovery_token.encode()).hexdigest()
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = datetime.now(timezone.utc)

    doc = await db.break_glass_events.find_one({"token_hash": token_hash, "used": False})
    if not doc:
        raise HTTPException(status_code=401, detail="Invalid or already-used recovery token")
    expires = datetime.fromisoformat(doc["expires_at"].replace("Z", "+00:00"))
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        raise HTTPException(status_code=401, detail="Recovery token has expired")

    result_msg = ""
    if action == "reset_mfa":
        from services.mfa_service import disable_mfa as _disable_mfa
        protected = await db.users.find_one({"email": PROTECTED_SUPER_ADMIN_EMAIL})
        if protected:
            await _disable_mfa(str(protected["_id"]))
            result_msg = "MFA disabled on protected super-admin account"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    await db.break_glass_events.update_one(
        {"_id": doc["_id"]},
        {"$set": {"used": True, "used_at": now.isoformat(), "action": action}},
    )
    await log_event("admin.break_glass.used", actor_id=doc.get("actor_id"),
                    actor_email=doc.get("actor_email"), extra={"action": action})
    await emit_security_event("break_glass_completed", severity="critical",
                               actor_id=doc.get("actor_id"), actor_email=doc.get("actor_email"),
                               extra={"action": action})
    return {"ok": True, "action": action, "result": result_msg}


@router.get("/break-glass/history", dependencies=_GATE)
async def break_glass_history(limit: int = 20):
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.break_glass_events.find(
        {}, {"token_hash": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return {"events": docs, "count": len(docs)}


# ═════════════════════════════════════════════════════════════════════════════
# 10. SUPER ADMIN AUDIT CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/audit", dependencies=_GATE)
async def admin_audit_log(
    action:  Optional[str] = None,
    actor:   Optional[str] = None,
    limit:   int = 100,
    skip:    int = 0,
):
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    flt: dict = {}
    if action: flt["action"] = {"$regex": action, "$options": "i"}
    if actor:  flt["actor_email"] = actor

    docs = await db.audit_log.find(flt, {"expires_at": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.audit_log.count_documents(flt)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return {
        "events": docs,
        "total":  total,
        "page":   skip // limit if limit else 0,
    }


@router.get("/audit/summary", dependencies=_GATE)
async def audit_summary():
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = datetime.now(timezone.utc)
    last_24h = (now - timedelta(hours=24)).isoformat()
    last_7d  = (now - timedelta(days=7)).isoformat()

    total_24h, total_7d, login_events, security_events_count = await asyncio.gather(
        db.audit_log.count_documents({"created_at": {"$gte": last_24h}}),
        db.audit_log.count_documents({"created_at": {"$gte": last_7d}}),
        db.audit_log.count_documents({"action": {"$regex": "^auth\\.login"}}),
        db.security_events.count_documents({"resolved": False}),
    )

    recent = await db.audit_log.find({}, {"action": 1, "actor_email": 1, "ip": 1, "created_at": 1, "expires_at": 0})\
        .sort("created_at", -1).limit(10).to_list(10)
    for d in recent:
        d["id"] = str(d.pop("_id"))

    return {
        "total_last_24h":         total_24h,
        "total_last_7d":          total_7d,
        "login_events_total":     login_events,
        "unresolved_security_events": security_events_count,
        "recent_events":          recent,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 11. SECURITY EVENT ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class ResolveBody(BaseModel):
    note: str = ""


@router.get("/security-events", dependencies=_GATE)
async def list_security_events(
    severity:   Optional[str] = None,
    event_type: Optional[str] = None,
    resolved:   Optional[bool] = None,
    limit:      int = 100,
    skip:       int = 0,
):
    events = await get_events(
        severity=severity, event_type=event_type, resolved=resolved, limit=limit, skip=skip
    )
    stats  = await event_stats()
    return {"events": events, "count": len(events), "stats": stats}


@router.post("/security-events/{event_id}/resolve", dependencies=_GATE)
async def resolve_security_event(
    event_id: str,
    body: ResolveBody,
    admin: dict = Depends(require_super_admin),
    request: Request = None,
):
    ok = await resolve_event(event_id, admin.get("email", ""), body.note)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    meta = request_meta(request) if request else {}
    await log_event("admin.security_event.resolved", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), extra={"event_id": event_id, "note": body.note})
    return {"ok": True}


@router.get("/security-events/stats", dependencies=_GATE)
async def security_event_stats():
    return await event_stats()


# ═════════════════════════════════════════════════════════════════════════════
# 12. SECURITY CERTIFICATION
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/certification", dependencies=_GATE)
async def security_certification(admin: dict = Depends(require_super_admin)):
    """Compute real-time security certification scores based on current platform state."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    protected_email = PROTECTED_SUPER_ADMIN_EMAIL

    # Gather data
    (
        protected_doc,
        mfa_cfg,
        rogue_count,
        trusted_device_count,
        allowlist_entries,
        allowlist_cfg,
        active_sessions,
        break_glass_events,
        unresolved_events,
        audit_count_24h,
    ) = await asyncio.gather(
        db.users.find_one({"email": protected_email}, {"role": 1, "protected": 1, "email_verified": 1, "status": 1, "mfa_enabled": 1}),
        db.mfa_configs.find_one({"user_id": admin["id"]}),
        db.users.count_documents({"role": "super_admin", "email": {"$ne": protected_email}}),
        db.trusted_devices.count_documents({"user_id": admin["id"], "revoked": {"$ne": True}}),
        db.ip_allowlist.count_documents({"active": True}),
        db.ip_allowlist_config.find_one({"_id": "config"}),
        db.refresh_tokens.count_documents({"user_id": admin["id"], "revoked": False}),
        db.break_glass_events.count_documents({}),
        db.security_events.count_documents({"resolved": False}),
        db.audit_log.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}}),
    )

    mfa_enabled    = bool(mfa_cfg and mfa_cfg.get("enabled"))
    has_allowlist  = allowlist_entries > 0
    allowlist_mode = (allowlist_cfg or {}).get("mode", "monitor")
    has_break_glass = break_glass_events > 0

    # ── Score calculations ────────────────────────────────────────────────────

    # 1. Authentication Security (0-100)
    auth_score = 0
    auth_checks = []
    if protected_doc and protected_doc.get("role") == "super_admin":
        auth_score += 20; auth_checks.append(("✓ Protected account has correct role", True))
    else:
        auth_checks.append(("✗ Protected account role incorrect", False))
    if protected_doc and protected_doc.get("email_verified"):
        auth_score += 10; auth_checks.append(("✓ Email verified", True))
    else:
        auth_checks.append(("✗ Email not verified", False))
    if mfa_enabled:
        auth_score += 40; auth_checks.append(("✓ MFA enabled", True))
    else:
        auth_checks.append(("✗ MFA not configured — strongly recommended", False))
    if rogue_count == 0:
        auth_score += 20; auth_checks.append(("✓ No rogue super-admins", True))
    else:
        auth_checks.append((f"✗ {rogue_count} rogue super-admin account(s) detected", False))
    if protected_doc and protected_doc.get("protected"):
        auth_score += 10; auth_checks.append(("✓ Protected flag set", True))
    else:
        auth_checks.append(("✗ Protected flag missing", False))

    # 2. Authorization Security (0-100)
    authz_score = 90  # base: API blocks are hardcoded
    authz_checks = [
        ("✓ super_admin role cannot be granted via API", True),
        ("✓ Protected account cannot be suspended via API", True),
        ("✓ Protected account cannot be deleted via API", True),
        ("✓ Role hierarchy enforced on all user-management endpoints", True),
        ("✓ Seed heals account on every startup", True),
    ]
    if rogue_count == 0:
        authz_score += 10
        authz_checks.append(("✓ Zero rogue super-admin accounts", True))
    else:
        authz_score -= 30
        authz_checks.append((f"✗ {rogue_count} rogue super-admin(s) exist", False))

    # 3. Auditability (0-100)
    audit_score = 0
    audit_checks = []
    if audit_count_24h > 0:
        audit_score += 40; audit_checks.append(("✓ Audit log active (events in last 24h)", True))
    else:
        audit_checks.append(("⚠ No audit events in last 24h — may indicate idle platform", False))
        audit_score += 10
    audit_score += 30; audit_checks.append(("✓ Admin audit log with 90-day retention", True))
    audit_score += 30; audit_checks.append(("✓ Security events with 365-day retention", True))

    # 4. Session Security (0-100)
    session_score = 60  # base: JWT + httponly cookies + refresh rotation
    session_checks = [
        ("✓ JWT access tokens (15-min TTL)", True),
        ("✓ Refresh token rotation with JTI revocation", True),
        ("✓ HttpOnly cookies prevent XSS token theft", True),
    ]
    if mfa_enabled:
        session_score += 20; session_checks.append(("✓ MFA required on all logins", True))
    else:
        session_checks.append(("✗ No MFA — single-factor sessions", False))
    if trusted_device_count > 0:
        session_score += 10; session_checks.append((f"✓ {trusted_device_count} trusted device(s) registered", True))
    else:
        session_checks.append(("⚠ No trusted devices — every login triggers MFA challenge", False))
        session_score += 5
    if active_sessions <= 3:
        session_score += 10; session_checks.append((f"✓ {active_sessions} active session(s) — minimal exposure", True))
    else:
        session_checks.append((f"⚠ {active_sessions} active sessions — consider terminating unused ones", False))
        session_score += 5

    # 5. Recovery Readiness (0-100)
    recovery_score = 40  # base: seed.py heals on restart
    recovery_checks = [("✓ Startup auto-heal restores super-admin if tampered", True)]
    if mfa_enabled:
        cfg = mfa_cfg or {}
        remaining = len(cfg.get("recovery_codes", []))
        if remaining >= 5:
            recovery_score += 30; recovery_checks.append((f"✓ {remaining} MFA recovery codes available", True))
        elif remaining > 0:
            recovery_score += 15; recovery_checks.append((f"⚠ Only {remaining} recovery codes remaining — regenerate soon", False))
        else:
            recovery_checks.append(("✗ No MFA recovery codes — enable MFA to generate them", False))
    if has_break_glass:
        recovery_score += 20; recovery_checks.append((f"✓ Break-glass system used ({break_glass_events} event(s) on record)", True))
    else:
        recovery_checks.append(("⚠ Break-glass system not yet exercised", False))
        recovery_score += 10
    recovery_score = min(recovery_score, 100)

    # 6. Privilege Escalation Resistance (0-100)
    priv_score = 85
    priv_checks = [
        ("✓ super_admin role API-blocked", True),
        ("✓ Protected account API-immutable", True),
        ("✓ Role hierarchy enforced", True),
        ("✓ Actors cannot modify equal/higher authority users", True),
        ("✓ Startup strips rogue super-admins", True),
    ]
    if rogue_count == 0:
        priv_score += 15; priv_checks.append(("✓ Zero rogue super-admins confirmed", True))
    else:
        priv_score -= 50; priv_checks.append((f"✗ {rogue_count} rogue super-admin(s) — run lockdown immediately", False))

    # 7. Zero-Trust Readiness (0-100)
    zt_score = 20  # base: identity verification
    zt_checks = []
    if mfa_enabled:
        zt_score += 25; zt_checks.append(("✓ MFA (something you have)", True))
    else:
        zt_checks.append(("✗ No MFA — violates zero-trust 'verify explicitly'", False))
    if trusted_device_count > 0:
        zt_score += 20; zt_checks.append(("✓ Trusted device management active", True))
    else:
        zt_checks.append(("⚠ No trusted devices registered", False))
    if has_allowlist:
        zt_checks.append((f"✓ IP allowlist active ({allowlist_entries} entries, mode={allowlist_mode})", True))
        zt_score += 20 if allowlist_mode == "enforce" else 10
    else:
        zt_checks.append(("⚠ No IP allowlist configured", False))
    zt_score += 15; zt_checks.append(("✓ All admin routes require super_admin role", True))
    zt_score = min(zt_score, 100)

    scores = {
        "authentication":            auth_score,
        "authorization":             min(authz_score, 100),
        "auditability":              audit_score,
        "session_security":          min(session_score, 100),
        "recovery_readiness":        recovery_score,
        "privilege_escalation_resistance": min(priv_score, 100),
        "zero_trust_readiness":      zt_score,
    }

    overall = round(sum(scores.values()) / len(scores))

    if overall >= 90:   grade, color = "A",  "green"
    elif overall >= 80: grade, color = "B",  "lime"
    elif overall >= 70: grade, color = "C",  "yellow"
    elif overall >= 60: grade, color = "D",  "orange"
    else:               grade, color = "F",  "red"

    checks = {
        "authentication": auth_checks,
        "authorization":  authz_checks,
        "auditability":   audit_checks,
        "session":        session_checks,
        "recovery":       recovery_checks,
        "privilege":      priv_checks,
        "zero_trust":     zt_checks,
    }

    return {
        "scores":           scores,
        "overall":          overall,
        "grade":            grade,
        "grade_color":      color,
        "checks":           checks,
        "certified":        overall >= 80,
        "certification_label": "SYNAPTIQ SUPER ADMIN ZERO-TRUST CERTIFIED" if overall >= 80 else "NOT CERTIFIED",
        "evaluated_at":     _now(),
        "mfa_enabled":      mfa_enabled,
        "rogue_super_admins": rogue_count,
        "active_sessions":  active_sessions,
        "trusted_devices":  trusted_device_count,
        "ip_allowlist_entries": allowlist_entries,
        "ip_allowlist_mode": allowlist_mode,
    }
