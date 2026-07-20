"""Admin Operations — advanced founder tooling.

Endpoints:
  POST /api/admin/users/{uid}/reset-password    — admin-initiated password reset
  POST /api/admin/users/{uid}/verify-email      — admin override email verification
  POST /api/admin/users/{uid}/impersonate       — issue short-lived token for debugging
  POST /api/admin/credits/batch-grant           — bulk credit grant to a user segment
  POST /api/admin/announcements                 — platform-wide in-app announcement
  GET  /api/admin/feature-flags                 — list feature flags
  POST /api/admin/feature-flags                 — create/update a feature flag
  DELETE /api/admin/feature-flags/{name}        — delete a feature flag
  GET  /api/admin/maintenance                   — get maintenance mode status
  POST /api/admin/maintenance                   — enable / disable maintenance mode
"""
from __future__ import annotations
import hashlib
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth_utils import get_current_user, create_access_token
from db import get_db
from services.admin_audit import log_event, request_meta
from services.permissions import require_super_admin
from services.token_service import revoke_all_user_tokens
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/admin", tags=["admin-operations"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_prod() -> bool:
    return os.environ.get("APP_ENV", "development").lower() in ("prod", "production")


def _parse_oid(uid: str) -> ObjectId:
    try:
        return ObjectId(uid)
    except (InvalidId, Exception):
        raise HTTPException(status_code=400, detail="Invalid user ID")


# ---------------------------------------------------------------------------
# Admin-initiated password reset
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/reset-password")
async def admin_reset_password(uid: str, request: Request, admin: dict = Depends(require_super_admin)):
    """Generate a password reset token for a user and send the reset email.
    In development mode, the raw token is also returned in the response for testing.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "full_name": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.get("email"):
        raise HTTPException(status_code=400, detail="User has no email address")

    raw_token = str(uuid.uuid4())
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()

    await db.password_resets.insert_one({
        "user_id": uid,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "used": False,
        "created_at": _now_iso(),
        "created_by_admin": admin.get("email"),
    })

    email_sent = False
    try:
        from services.email_service import send_password_reset
        result = await send_password_reset(user_id=uid, token=raw_token, expires_in_minutes=30)
        email_sent = result.get("ok", False)
    except Exception:
        pass

    await log_event(
        "admin.user.admin_reset_password",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_email=user.get("email"),
        ip=request_meta(request)["ip"],
    )

    response: dict = {"ok": True, "email_sent": email_sent, "expires_at": expires_at}
    if not _is_prod():
        response["reset_token"] = raw_token  # exposed in dev/staging only
    return response


# ---------------------------------------------------------------------------
# Admin email verification override
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/verify-email")
async def admin_verify_email(uid: str, request: Request, admin: dict = Depends(require_super_admin)):
    """Directly mark a user's email as verified (bypass the email flow)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "email_verified": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one(
        {"_id": oid},
        {"$set": {
            "email_verified": True,
            "email_verified_at": _now_iso(),
            "email_verified_by_admin": admin.get("email"),
        }},
    )
    await log_event(
        "admin.user.verify_email",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_email=user.get("email"),
        ip=request_meta(request)["ip"],
    )
    return {"ok": True, "email_verified": True}


# ---------------------------------------------------------------------------
# User impersonation
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/impersonate")
async def impersonate_user(uid: str, request: Request, admin: dict = Depends(require_super_admin)):
    """Issue a short-lived (15 min) access token for the target user.

    The admin can use this token to make requests as the user — useful for
    reproducing bugs or providing support. No refresh token is issued.
    All impersonation events are audit logged.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "status": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("status") in ("banned",):
        raise HTTPException(status_code=400, detail="Cannot impersonate a banned user")
    if zt_is_super_admin(user) and uid != admin["id"]:
        raise HTTPException(status_code=403, detail="Cannot impersonate another super admin")

    access_token = create_access_token(uid, user.get("email", ""))

    await log_event(
        "admin.user.impersonate",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_email=user.get("email"),
        ip=request_meta(request)["ip"],
        extra={"impersonator": admin.get("email")},
    )
    return {
        "ok": True,
        "access_token": access_token,
        "user_id": uid,
        "email": user.get("email"),
        "expires_in": "15 minutes",
        "note": "Use as Bearer token. No refresh token issued. Expires in 15 minutes.",
    }


# ---------------------------------------------------------------------------
# Batch credit grants
# ---------------------------------------------------------------------------

class BatchGrantRequest(BaseModel):
    segment: str = "all"   # "all" | "free" | "paid" | "specific"
    user_ids: Optional[list] = None   # if segment == "specific"
    amount: int
    reason: str = ""


@router.post("/credits/batch-grant")
async def batch_grant_credits(
    body: BatchGrantRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    """Grant credits to a segment of users or a specific list of user IDs."""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")

    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    if body.segment == "specific":
        if not body.user_ids:
            raise HTTPException(status_code=400, detail="user_ids required when segment=specific")
        user_oids = []
        for uid_str in body.user_ids:
            try:
                user_oids.append(ObjectId(uid_str))
            except Exception:
                pass
        query = {"_id": {"$in": user_oids}}
    elif body.segment == "free":
        query = {"plan_code": "free"}
    elif body.segment == "paid":
        query = {"plan_code": {"$in": ["researcher", "pro_researcher", "institution"]}}
    else:
        query = {}

    granted_count = 0
    now = _now_iso()
    cursor = db.users.find(query, {"_id": 1})
    async for user in cursor:
        uid_str = str(user["_id"])
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$inc": {"credits_pack_balance": body.amount}},
        )
        await db.credit_transactions.insert_one({
            "user_id": uid_str,
            "kind": "admin_grant",
            "bucket": "pack",
            "amount": body.amount,
            "action": "batch_grant",
            "reason": body.reason,
            "metadata": {"by_admin": admin.get("email"), "segment": body.segment},
            "created_at": now,
        })
        granted_count += 1

    await log_event(
        "admin.credits.batch_grant",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"segment": body.segment, "amount": body.amount, "granted_to": granted_count, "reason": body.reason},
    )
    return {"ok": True, "granted_to": granted_count, "amount": body.amount}


# ---------------------------------------------------------------------------
# Platform-wide announcements
# ---------------------------------------------------------------------------

class AnnouncementRequest(BaseModel):
    title: str
    body: str
    link: str = ""
    kind: str = "announcement"
    segment: str = "all"


@router.post("/announcements")
async def send_announcement(body: AnnouncementRequest, request: Request, admin: dict = Depends(require_super_admin)):
    """Create an in-app notification for all users (or a segment)."""
    if not body.title:
        raise HTTPException(status_code=400, detail="title required")

    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    if body.segment == "free":
        query: dict = {"plan_code": "free"}
    elif body.segment == "paid":
        query = {"plan_code": {"$in": ["researcher", "pro_researcher", "institution"]}}
    else:
        query = {}

    now = _now_iso()
    sent_count = 0
    notifications = []
    cursor = db.users.find(query, {"_id": 1})
    async for user in cursor:
        uid_str = str(user["_id"])
        notifications.append({
            "user_id": uid_str,
            "type": body.kind,
            "title": body.title,
            "body": body.body,
            "link": body.link,
            "actor_id": admin["id"],
            "payload": {"sent_by_admin": admin.get("email")},
            "read": False,
            "created_at": now,
        })
        sent_count += 1
        if len(notifications) >= 500:
            await db.notifications.insert_many(notifications)
            notifications = []
    if notifications:
        await db.notifications.insert_many(notifications)

    result = await db.announcements.insert_one({
        "title": body.title,
        "body": body.body,
        "link": body.link,
        "kind": body.kind,
        "segment": body.segment,
        "sent_to": sent_count,
        "sent_by": admin.get("email"),
        "created_at": now,
    })

    await log_event(
        "admin.announcement.send",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"title": body.title, "segment": body.segment, "sent_to": sent_count},
    )
    return {"ok": True, "announcement_id": str(result.inserted_id), "sent_to": sent_count}


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

@router.get("/feature-flags", dependencies=[Depends(require_super_admin)])
async def list_feature_flags():
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.feature_flags.find({}).sort("name", 1).to_list(500)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return {"items": docs}


class FeatureFlagBody(BaseModel):
    name: str
    enabled: bool
    description: str = ""
    rollout_pct: int = 100  # 0-100 percentage rollout
    allowed_plans: Optional[list] = None


@router.post("/feature-flags")
async def upsert_feature_flag(body: FeatureFlagBody, request: Request, admin: dict = Depends(require_super_admin)):
    """Create or update a feature flag."""
    if not body.name:
        raise HTTPException(status_code=400, detail="name required")
    if not body.name.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="name must be alphanumeric with _ or - only")

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    await db.feature_flags.update_one(
        {"name": body.name},
        {"$set": {
            "name": body.name,
            "enabled": body.enabled,
            "description": body.description,
            "rollout_pct": max(0, min(100, body.rollout_pct)),
            "allowed_plans": body.allowed_plans,
            "updated_at": now,
            "updated_by": admin.get("email"),
        }, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await log_event(
        "admin.feature_flag.upsert",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"flag": body.name, "enabled": body.enabled},
    )
    return {"ok": True, "name": body.name, "enabled": body.enabled}


@router.delete("/feature-flags/{name}")
async def delete_feature_flag(name: str, request: Request, admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.feature_flags.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    await log_event(
        "admin.feature_flag.delete",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"flag": name},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Maintenance mode
# ---------------------------------------------------------------------------

@router.get("/maintenance", dependencies=[Depends(require_super_admin)])
async def get_maintenance():
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    doc = await db.platform_settings.find_one({"key": "maintenance_mode"})
    return {
        "maintenance_mode": (doc or {}).get("enabled", False),
        "message": (doc or {}).get("message", ""),
        "updated_at": (doc or {}).get("updated_at"),
        "updated_by": (doc or {}).get("updated_by"),
    }


class MaintenanceRequest(BaseModel):
    enabled: bool
    message: str = "The platform is currently undergoing scheduled maintenance. We'll be back shortly."


@router.post("/maintenance")
async def set_maintenance_mode(body: MaintenanceRequest, request: Request, admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    await db.platform_settings.update_one(
        {"key": "maintenance_mode"},
        {"$set": {
            "key": "maintenance_mode",
            "enabled": body.enabled,
            "message": body.message,
            "updated_at": now,
            "updated_by": admin.get("email"),
        }},
        upsert=True,
    )
    await log_event(
        "admin.maintenance.set",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"enabled": body.enabled, "message": body.message},
    )
    return {"ok": True, "maintenance_mode": body.enabled, "message": body.message}
