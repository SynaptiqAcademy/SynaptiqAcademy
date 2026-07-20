"""Admin Control Center — user management endpoints."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta as _td
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth_utils import serialize_user
from db import get_db
from services.admin_audit import log_event, request_meta
from services.permissions import (
    require_super_admin, require_moderator_or_super_admin,
    is_protected_account, role_level, _API_BLOCKED_ROLES,
    PROTECTED_SUPER_ADMIN_EMAIL,
)
from services.token_service import revoke_all_user_tokens
from repo.shim import DBProxy
from repo.security_context import SecurityContext


def _guard_protected(user: dict, action: str) -> None:
    """Raise 403 if the target is the permanent protected super-admin account."""
    if (user.get("email") or "").strip().lower() == PROTECTED_SUPER_ADMIN_EMAIL:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot {action} the protected platform super-administrator account "
                   f"({PROTECTED_SUPER_ADMIN_EMAIL}). This account is permanently protected. "
                   "Only direct database intervention can modify it.",
        )


def _guard_hierarchy(actor: dict, target: dict, action: str) -> None:
    """Raise 403 if actor's role level is not strictly above target's."""
    if role_level(actor.get("role")) <= role_level(target.get("role")):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot {action} a user with equal or higher authority level.",
        )

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - _td(days=days)).isoformat()


def _today_iso_start() -> str:
    t = datetime.now(timezone.utc)
    return datetime(t.year, t.month, t.day, tzinfo=timezone.utc).isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_oid(uid: str) -> ObjectId:
    try:
        return ObjectId(uid)
    except (InvalidId, Exception):
        raise HTTPException(status_code=400, detail="Invalid user ID")


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class SuspendRequest(BaseModel):
    reason: str = ""


class SetPlanRequest(BaseModel):
    plan_code: str


class AdjustCreditsRequest(BaseModel):
    amount: int
    reason: str = ""


class SetRoleRequest(BaseModel):
    role: str


# ---------------------------------------------------------------------------
# GET /api/admin/users
# ---------------------------------------------------------------------------

@router.get("/users", dependencies=[Depends(require_moderator_or_super_admin)])
async def list_users(
    q: Optional[str] = None,
    plan: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    user_type: Optional[str] = None,
    primary_domain: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    filt: dict = {}
    if q:
        import re
        pattern = re.compile(re.escape(q), re.IGNORECASE)
        filt["$or"] = [{"email": pattern}, {"full_name": pattern}]
    if plan:
        filt["plan_code"] = plan
    if status:
        filt["status"] = status
    if role:
        filt["role"] = role
    if user_type:
        filt["user_type"] = user_type
    if primary_domain:
        filt["primary_domain"] = primary_domain

    projection = {
        "_id": 1, "email": 1, "full_name": 1, "plan_code": 1, "role": 1,
        "status": 1, "created_at": 1, "email_verified": 1, "onboarded": 1,
        "credits_balance": 1, "credits_pack_balance": 1,
        "user_type": 1, "primary_domain": 1,
    }
    skip = (max(page, 1) - 1) * limit
    total = await db.users.count_documents(filt)
    cursor = db.users.find(filt, projection).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    items = []
    for doc in docs:
        item = dict(doc)
        item["id"] = str(item.pop("_id"))
        items.append(item)
    return {"total": total, "items": items}


# ---------------------------------------------------------------------------
# GET /api/admin/users/stats — Context Panel data source for the Users list page
# ---------------------------------------------------------------------------

@router.get("/users/stats", dependencies=[Depends(require_moderator_or_super_admin)])
async def get_users_stats():
    import asyncio

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    today = _today_iso_start()
    day_ago = _ago_iso(1)

    (
        new_today, active_today, pending_verification, paid_users,
        suspended_users, banned_users,
    ) = await asyncio.gather(
        db.users.count_documents({"created_at": {"$gte": today}}),
        db.users.count_documents({"last_successful_login": {"$gte": day_ago}}),
        db.users.count_documents({"email_verified": {"$ne": True}}),
        db.users.count_documents({"plan_code": {"$nin": [None, "free"]}}),
        db.users.count_documents({"status": "suspended"}),
        db.users.count_documents({"status": "banned"}),
    )

    # 14-day daily new-user growth trend (same per-day-loop pattern as
    # admin_aos.py's /timeseries endpoint — no $dateToString pipeline exists
    # for users.created_at elsewhere in the codebase, so this mirrors it).
    now = datetime.now(timezone.utc)
    growth_trend = []
    day_counts = await asyncio.gather(*[
        db.users.count_documents({
            "created_at": {
                "$gte": (now - _td(days=d)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
                "$lte": (now - _td(days=d)).replace(hour=23, minute=59, second=59, microsecond=999999).isoformat(),
            }
        })
        for d in range(13, -1, -1)
    ])
    for d, count in zip(range(13, -1, -1), day_counts):
        growth_trend.append({
            "date": (now - _td(days=d)).strftime("%Y-%m-%d"),
            "count": count,
        })

    return {
        "new_today": new_today,
        "active_today": active_today,
        "pending_verification": pending_verification,
        "paid_users": paid_users,
        "suspended_or_banned": suspended_users + banned_users,
        "growth_trend": growth_trend,
    }


# ---------------------------------------------------------------------------
# GET /api/admin/users/{uid}
# ---------------------------------------------------------------------------

@router.get("/users/{uid}", dependencies=[Depends(require_moderator_or_super_admin)])
async def get_user(uid: str):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    out = serialize_user(user)

    projects_count, workspaces_count, collabs_count, manuscripts_count, publications_count = await __import__("asyncio").gather(
        db.projects.count_documents({"owner_id": uid}),
        db.workspaces.count_documents({"owner_id": uid}),
        db.collaborations.count_documents({"$or": [{"owner_id": uid}, {"member_ids": uid}]}),
        db.manuscripts.count_documents({"owner_id": uid}),
        db.publications.count_documents({"owner_id": uid}),
    )
    out["activity_summary"] = {
        "projects_count": projects_count,
        "workspaces_count": workspaces_count,
        "collabs_count": collabs_count,
        "manuscripts_count": manuscripts_count,
        "publications_count": publications_count,
    }
    return out


# ---------------------------------------------------------------------------
# GET /api/admin/users/{uid}/activity
# ---------------------------------------------------------------------------

@router.get("/users/{uid}/activity", dependencies=[Depends(require_moderator_or_super_admin)])
async def get_user_activity(uid: str):
    _parse_oid(uid)
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.audit_log.find(
        {"$or": [{"actor_id": uid}, {"target_id": uid}]}
    ).sort("created_at", -1).limit(50)
    events = await cursor.to_list(50)
    for ev in events:
        ev["id"] = str(ev.pop("_id"))
    return {"items": events}


# ---------------------------------------------------------------------------
# POST /api/admin/users/{uid}/suspend
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/suspend")
async def suspend_user(
    uid: str,
    body: SuspendRequest,
    request: Request,
    admin: dict = Depends(require_moderator_or_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _guard_protected(user, "suspend")
    _guard_hierarchy(admin, user, "suspend")
    await db.users.update_one(
        {"_id": oid},
        {"$set": {"status": "suspended", "suspended_at": _now_iso(), "suspend_reason": body.reason}},
    )
    await revoke_all_user_tokens(uid)
    meta = request_meta(request)
    await log_event(
        "admin.user.suspend",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"reason": body.reason},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/users/{uid}/unsuspend
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/unsuspend")
async def unsuspend_user(
    uid: str,
    request: Request,
    admin: dict = Depends(require_moderator_or_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one(
        {"_id": oid},
        {"$unset": {"status": "", "suspended_at": "", "suspend_reason": ""}},
    )
    meta = request_meta(request)
    await log_event(
        "admin.user.unsuspend",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/users/{uid}/ban
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/ban")
async def ban_user(
    uid: str,
    body: SuspendRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _guard_protected(user, "ban")
    _guard_hierarchy(admin, user, "ban")
    await db.users.update_one(
        {"_id": oid},
        {"$set": {"status": "banned", "banned_at": _now_iso(), "ban_reason": body.reason}},
    )
    await revoke_all_user_tokens(uid)
    meta = request_meta(request)
    await log_event(
        "admin.user.ban",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"reason": body.reason},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/users/{uid}/unban
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/unban")
async def unban_user(
    uid: str,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one(
        {"_id": oid},
        {"$unset": {"status": "", "banned_at": "", "ban_reason": ""}},
    )
    meta = request_meta(request)
    await log_event(
        "admin.user.unban",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/users/{uid}/force-logout
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/force-logout")
async def force_logout_user(
    uid: str,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await revoke_all_user_tokens(uid)
    await db.users.update_one(
        {"_id": oid},
        {"$set": {"force_logout_at": _now_iso()}},
    )
    meta = request_meta(request)
    await log_event(
        "admin.user.force_logout",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/users/{uid}/set-plan
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/set-plan")
async def set_plan(
    uid: str,
    body: SetPlanRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "plan_code": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from plans_catalogue import get_plan, PLANS
    valid_codes = {p["code"] for p in PLANS}
    if body.plan_code not in valid_codes:
        raise HTTPException(status_code=400, detail=f"Unknown plan code: {body.plan_code}")

    # H6: read current credits so we can create a ledger entry for the change
    user_full = await db.users.find_one({"_id": oid}, {"email": 1, "plan_code": 1, "credits_balance": 1})
    plan = get_plan(body.plan_code)
    new_credits = plan.get("credits_per_month", 0)
    old_credits = (user_full or {}).get("credits_balance", 0)
    from_plan = (user_full or {}).get("plan_code") or user.get("plan_code")
    now = _now_iso()

    await db.users.update_one(
        {"_id": oid},
        {"$set": {
            "plan_code": body.plan_code,
            "credits_balance": new_credits,
            "credits_monthly_allowance": new_credits,
        }},
    )
    # H6: record credit change in the ledger so balance history is auditable
    delta = new_credits - old_credits
    await db.credit_transactions.insert_one({
        "user_id": uid,
        "kind": "admin_grant" if delta >= 0 else "admin_deduct",
        "bucket": "monthly",
        "amount": abs(delta),
        "action": "plan_change",
        "reason": f"Plan changed from {from_plan} to {body.plan_code}",
        "metadata": {"from_plan": from_plan, "to_plan": body.plan_code, "by_admin": admin.get("email")},
        "created_at": now,
    })
    await db.subscription_history.insert_one({
        "user_id": uid,
        "from_plan": from_plan,
        "to_plan": body.plan_code,
        "changed_at": now,
        "changed_by_admin": True,
        "changed_by": admin.get("email"),
    })
    meta = request_meta(request)
    await log_event(
        "admin.user.set_plan",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"from_plan": from_plan, "to_plan": body.plan_code},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/users/{uid}/adjust-credits
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/adjust-credits")
async def adjust_credits(
    uid: str,
    body: AdjustCreditsRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "credits_pack_balance": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # H6: enforce floor — pack balance must not go below 0
    current_pack = user.get("credits_pack_balance", 0)
    if current_pack + body.amount < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reduce pack balance below 0. Current: {current_pack}, adjustment: {body.amount}",
        )

    await db.users.update_one(
        {"_id": oid},
        {"$inc": {"credits_pack_balance": body.amount}},
    )
    kind = "admin_grant" if body.amount >= 0 else "admin_deduct"
    await db.credit_transactions.insert_one({
        "user_id": uid,
        "kind": kind,
        "bucket": "pack",
        "amount": abs(body.amount),
        "action": "admin_adjust",
        "reason": body.reason,
        "metadata": {"by_admin": admin.get("email")},
        "created_at": _now_iso(),
    })
    meta = request_meta(request)
    await log_event(
        "admin.user.adjust_credits",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"amount": body.amount, "reason": body.reason},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/admin/users/{uid}/set-role
# ---------------------------------------------------------------------------

@router.post("/users/{uid}/set-role")
async def set_role(
    uid: str,
    body: SetRoleRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    allowed_roles = {"user", "moderator", "admin", "institution_admin",
                     "verified_researcher", "verified_professor"}
    if body.role not in allowed_roles:
        # super_admin cannot be granted via API — DB/seed only
        if body.role in _API_BLOCKED_ROLES:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{body.role}' cannot be granted via the API. "
                       "Super-admin privileges are managed via database seed only.",
            )
        raise HTTPException(status_code=400, detail=f"Unknown role: {body.role}")

    # Protect the permanent super-admin account: cannot be demoted via API
    _guard_protected(user, "change the role of")

    # Hierarchy: cannot modify users at same or higher level
    _guard_hierarchy(admin, user, "set-role on")

    old_role = user.get("role")
    await db.users.update_one({"_id": oid}, {"$set": {"role": body.role}})
    meta = request_meta(request)
    await log_event(
        "admin.user.set_role",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"from_role": old_role, "to_role": body.role},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# DELETE /api/admin/users/{uid}
# ---------------------------------------------------------------------------

@router.delete("/users/{uid}")
async def delete_user(
    uid: str,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hard block: the protected super-admin can never be deleted via API
    _guard_protected(user, "delete")
    # Hierarchy: cannot delete users at same or higher level
    _guard_hierarchy(admin, user, "delete")

    await revoke_all_user_tokens(uid)
    await db.users.update_one(
        {"_id": oid},
        {"$set": {
            "deleted": True,
            "deleted_at": _now_iso(),
            "deleted_by": admin.get("email"),
            "status": "banned",
        }},
    )
    meta = request_meta(request)
    await log_event(
        "admin.user.delete",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_type="user", target_email=user.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
    )
    return {"ok": True}
