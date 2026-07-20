"""Admin Control Center — security monitoring and IP management."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import get_db
from services.admin_audit import log_event, request_meta
from services.permissions import require_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _ago_hours_iso(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class BlockIPRequest(BaseModel):
    ip: str
    reason: str = ""


class UnblockIPRequest(BaseModel):
    ip: str


class ForceLogoutAllRequest(BaseModel):
    reason: str = ""


# ---------------------------------------------------------------------------
# GET /api/admin/security/events
# ---------------------------------------------------------------------------

@router.get("/security/events", dependencies=[Depends(require_super_admin)])
async def security_events(
    limit: int = 100,
    event_type: Optional[str] = None,
    ip: Optional[str] = None,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    filt: dict = {}
    if event_type:
        filt["event_type"] = event_type
    if ip:
        filt["ip"] = ip
    cursor = db.security_events.find(filt).sort("created_at", -1).limit(limit)
    events = await cursor.to_list(limit)
    for ev in events:
        ev["id"] = str(ev.pop("_id"))
    return {"items": events}


# ---------------------------------------------------------------------------
# GET /api/admin/security/failed-logins
# ---------------------------------------------------------------------------

@router.get("/security/failed-logins", dependencies=[Depends(require_super_admin)])
async def failed_logins(hours: int = 24):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    since = _ago_hours_iso(hours)
    pipe = [
        {"$match": {"event_type": "login_failed", "created_at": {"$gte": since}}},
        {"$group": {"_id": "$ip", "count": {"$sum": 1}, "last_seen": {"$max": "$created_at"}}},
        {"$sort": {"count": -1}},
        {"$project": {"ip": "$_id", "count": 1, "last_seen": 1, "_id": 0}},
    ]
    results = await db.security_events.aggregate(pipe).to_list(500)
    return {"hours": hours, "items": results}


# ---------------------------------------------------------------------------
# GET /api/admin/security/blocked-ips
# ---------------------------------------------------------------------------

@router.get("/security/blocked-ips", dependencies=[Depends(require_super_admin)])
async def blocked_ips():
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.blocked_ips.find({}).sort("blocked_at", -1)
    docs = await cursor.to_list(1000)
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
    return {"items": docs}


# ---------------------------------------------------------------------------
# POST /api/admin/security/block-ip
# ---------------------------------------------------------------------------

@router.post("/security/block-ip")
async def block_ip(
    body: BlockIPRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    if not body.ip:
        raise HTTPException(status_code=400, detail="IP address required")
    now = _now_iso()
    await db.blocked_ips.update_one(
        {"ip": body.ip},
        {"$set": {
            "ip": body.ip,
            "reason": body.reason,
            "blocked_at": now,
            "blocked_by": admin.get("email"),
        }},
        upsert=True,
    )
    meta = request_meta(request)
    await log_event(
        "admin.security.block_ip",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"blocked_ip": body.ip, "reason": body.reason},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/security/unblock-ip
# ---------------------------------------------------------------------------

@router.post("/security/unblock-ip")
async def unblock_ip(
    body: UnblockIPRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    if not body.ip:
        raise HTTPException(status_code=400, detail="IP address required")
    result = await db.blocked_ips.delete_one({"ip": body.ip})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="IP not found in blocklist")
    meta = request_meta(request)
    await log_event(
        "admin.security.unblock_ip",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"unblocked_ip": body.ip},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/security/force-logout-all
# ---------------------------------------------------------------------------

@router.post("/security/force-logout-all")
async def force_logout_all(
    body: ForceLogoutAllRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    now_dt = datetime.now(timezone.utc)

    # Stamp all users — get_current_user rejects access tokens issued before this.
    await db.users.update_many({}, {"$set": {"force_logout_at": now}})

    # Revoke every active refresh token in one sweep.
    # Without this, users can re-authenticate via /auth/refresh and obtain a new
    # access token whose iat is AFTER force_logout_at, bypassing the check above.
    revoked = await db.refresh_tokens.update_many(
        {"revoked": False},
        {"$set": {"revoked": True, "revoked_at": now_dt}},
    )

    meta = request_meta(request)
    await log_event(
        "admin.security.force_logout_all",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"reason": body.reason, "refresh_tokens_revoked": revoked.modified_count},
    )
    return {"ok": True, "refresh_tokens_revoked": revoked.modified_count}
