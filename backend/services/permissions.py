"""Centralized SaaS permission engine.

Single source of truth for plan-tier gating, credit gating, and SUPER_ADMIN
escalation. Used as FastAPI dependencies on every premium route:

    from services.permissions import require_feature, require_credits, require_super_admin

    @router.post("/ai/assistant", dependencies=[Depends(require_feature("ai_assistant"))])
    async def assistant_endpoint(...): ...

The functions return FastAPI dependency callables so they can be composed cleanly.
Server-side enforcement only — clients never participate in the decision.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import os
from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status

from auth_utils import get_current_user
from db import get_db
from plans_catalogue import (
    FEATURE_MIN_PLAN, PLAN_RANK, PLAN_QUOTAS, STORAGE_LIMITS_BYTES, CREDIT_COSTS, get_plan,
)
from services.credits_service import ensure_user_credits
from repo.shim import DBProxy
from repo.security_context import SecurityContext


# The one permanent Super Administrator account. Hard-coded so it can never
# be removed by misconfiguring the environment variable.
PROTECTED_SUPER_ADMIN_EMAIL: str = "admin@synaptiq.academy"

SUPER_ADMIN_EMAILS = {
    PROTECTED_SUPER_ADMIN_EMAIL,
    *(
        e.strip().lower()
        for e in os.environ.get("SUPER_ADMIN_EMAILS", "admin@synaptiq.academy").split(",")
        if e.strip()
    ),
}

# Immutable role hierarchy — higher number = higher authority.
ROLE_HIERARCHY: dict[str, int] = {
    "super_admin":        100,
    "admin":              90,
    "institution_admin":  70,
    "moderator":          50,
    "verified_professor": 40,
    "verified_researcher":30,
    "user":               10,
}

# Roles that may NOT be granted via the API at all (DB-only privilege escalation).
_API_BLOCKED_ROLES: frozenset[str] = frozenset({"super_admin"})

# Internal/staff roles — never real paying customers, regardless of what
# plan_code they carry (the protected super-admin is always seeded on
# plan_code="institution" so it has full internal access; moderators are
# admin-granted, not self-service). Revenue/paid-subscriber metrics must
# exclude these or an internal account with zero real payments behind it
# permanently inflates MRR/ARR and "paying user" counts.
INTERNAL_STAFF_ROLES: frozenset[str] = frozenset({"super_admin", "moderator"})
REAL_CUSTOMER_FILTER: dict = {"role": {"$nin": list(INTERNAL_STAFF_ROLES)}}


def is_protected_account(user: dict) -> bool:
    """True if this is the permanent protected super-admin account."""
    return (user.get("email") or "").strip().lower() == PROTECTED_SUPER_ADMIN_EMAIL


def is_super_admin(user: dict) -> bool:
    if user.get("role") == "super_admin":
        return True
    return (user.get("email") or "").lower() in SUPER_ADMIN_EMAILS


def role_level(role: str | None) -> int:
    """Numeric authority level for a role string."""
    return ROLE_HIERARCHY.get(role or "user", 10)


def can_modify_target(actor: dict, target: dict) -> bool:
    """Actor may only modify users below their own authority level."""
    return role_level(actor.get("role")) > role_level(target.get("role"))


# ---------------------------- predicates (sync, pure) ----------------------------

def has_feature_override(user: dict, feature: str | None) -> bool:
    """True if an admin has individually granted this user access to `feature`
    outside their plan tier (see admin_users_mgmt.py's grant/revoke-feature
    endpoints). Overrides are stored as a list on the user doc — see
    services/feature_overrides.py for the exact record shape."""
    if not feature:
        return False
    overrides = user.get("feature_overrides") or []
    return any(o.get("feature") == feature for o in overrides if isinstance(o, dict))


def has_plan_at_least(user: dict, required: str, *, feature: str | None = None) -> bool:
    if is_super_admin(user):
        return True
    if has_feature_override(user, feature):
        return True
    from services.entitlements import effective_plan_code
    user_plan = effective_plan_code(user)
    return PLAN_RANK.get(user_plan, 0) >= PLAN_RANK.get(required, 0)


def has_active_subscription(user: dict) -> bool:
    """Free plan is considered 'active' (always usable). Paid plans must be
    live; past_due is a grace state while Stripe retries the payment."""
    from services.entitlements import ENTITLED_STATUSES
    plan = user.get("plan_code") or "free"
    if plan == "free":
        return True
    return (user.get("subscription_status") or None) in ENTITLED_STATUSES


def can_access_feature(user: dict, feature: str) -> tuple[bool, str | None]:
    """Returns (allowed, required_plan). Used by GET endpoints that should not
    raise but return a soft gate-state to the UI."""
    required = FEATURE_MIN_PLAN.get(feature, "free")
    if has_plan_at_least(user, required, feature=feature):
        return True, required
    return False, required


def can_consume_credits(user: dict, action: str, *, monthly_balance: int = 0,
                        pack_balance: int = 0) -> tuple[bool, int]:
    """Returns (allowed, needed)."""
    cost = CREDIT_COSTS.get(action, 0)
    if cost == 0:
        return True, 0
    if is_super_admin(user):
        return True, 0
    return (monthly_balance + pack_balance) >= cost, cost


# ---------------------------- FastAPI dependencies ----------------------------

def require_plan(min_plan: str, *, feature: str | None = None) -> Callable:
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if not has_plan_at_least(user, min_plan, feature=feature):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "upgrade_required",
                    "message": f"This action requires the {get_plan(min_plan).get('name', 'Pro')} plan or higher.",
                    "required_plan": min_plan,
                    "current_plan": user.get("plan_code") or "free",
                    "upgrade_url": "/pricing",
                },
            )
        if not has_active_subscription(user):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "subscription_inactive",
                    "message": "Your subscription is no longer active. Please update billing.",
                    "current_status": user.get("subscription_status"),
                    "upgrade_url": "/settings/billing",
                },
            )
        return user
    return _dep


def require_feature(feature: str) -> Callable:
    """Convenience wrapper for the feature catalogue."""
    return require_plan(FEATURE_MIN_PLAN.get(feature, "free"), feature=feature)


def require_credits(action: str) -> Callable:
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        cost = CREDIT_COSTS.get(action, 0)
        if cost == 0 or is_super_admin(user):
            return user
        state = await ensure_user_credits(user["id"])
        if state["balance"] < cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "credits_exhausted",
                    "message": "You have exhausted your monthly credits. Buy more credits or upgrade your plan.",
                    "action": action,
                    "needed": cost,
                    "balance": state["balance"],
                    "monthly_balance": state["monthly_balance"],
                    "pack_balance": state["pack_balance"],
                    "buy_credits_url": "/pricing#credit-packs",
                    "upgrade_url": "/pricing",
                },
            )
        return user
    return _dep


async def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    from zt.deps import zt_check
    zt_check(user, "admin", "security")
    return user


def is_moderator(user: dict) -> bool:
    return user.get("role") in ("moderator", "super_admin") or is_super_admin(user)


async def require_moderator_or_super_admin(user: dict = Depends(get_current_user)) -> dict:
    """Allows moderators limited admin access (suspend/view) without full admin rights."""
    from zt.deps import zt_check
    if not is_moderator(user):
        zt_check(user, "admin", "admin")  # will raise 403 with audit trail
    return user


# ---------------------------- quotas (workspaces/projects) ----------------------------

async def assert_quota(user: dict, resource: str) -> None:
    """Raises 402 with upgrade hint when a resource quota would be exceeded."""
    if is_super_admin(user):
        return
    from services.entitlements import effective_plan_code, capability_denied
    plan = effective_plan_code(user)
    quotas = PLAN_QUOTAS.get(plan, {})
    limit = quotas.get(resource, -1)
    if limit == -1:
        return
    if limit == 0:
        # Not part of this plan at all (Free has no projects/workspaces).
        cap = {"projects": "can_create_project", "workspaces": "can_create_workspace",
               "manuscripts": "can_create_project"}.get(resource)
        if cap:
            raise capability_denied(cap, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if resource == "projects":
        count = await db.projects.count_documents({"owner_id": user["id"]})
    elif resource == "workspaces":
        count = await db.workspaces.count_documents({"owner_id": user["id"]})
    elif resource == "manuscripts":
        count = await db.manuscripts.count_documents({"lead_author_id": user["id"]})
    else:
        return
    if count >= limit:
        # count > limit means user already exceeds quota (downgrade scenario)
        code = "quota_exceeded_after_downgrade" if count > limit else "quota_exceeded"
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": code,
                "message": f"You've reached the {resource} limit on your current plan.",
                "resource": resource,
                "limit": limit,
                "current": count,
                "upgrade_url": "/pricing",
            },
        )


# ---------------------------- storage quota ----------------------------

async def get_user_storage_bytes(user_id: str) -> int:
    """Real stored bytes owned by the user, across every place user uploads
    are kept: repository files (latest versions), message attachments, and
    knowledge-base documents. Never taken from the client."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    async def _sum(coll: str, match: dict, field: str) -> int:
        r = await db[coll].aggregate([
            {"$match": match},
            {"$group": {"_id": None, "total": {"$sum": f"${field}"}}},
        ]).to_list(1)
        return int((r[0]["total"] if r else 0) or 0)

    return (await _sum("files", {"owner_id": user_id, "is_latest": True}, "size_bytes")
            + await _sum("message_attachments", {"owner_id": user_id, "is_deleted": {"$ne": True}}, "size")
            + await _sum("knowledge_documents", {"user_id": user_id}, "file_size_bytes"))


async def assert_storage_quota(user: dict, upload_size_bytes: int) -> None:
    """Raises 402 when a file upload would exceed the plan's storage limit."""
    if is_super_admin(user):
        return
    from services.entitlements import effective_plan_code
    plan = effective_plan_code(user)
    limit = STORAGE_LIMITS_BYTES.get(plan, STORAGE_LIMITS_BYTES["free"])
    if limit == -1:
        return  # contract-defined / unlimited
    current = await get_user_storage_bytes(user["id"])
    if current + upload_size_bytes > limit:
        code = "storage_exceeded_after_downgrade" if current >= limit else "storage_limit_exceeded"
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": code,
                "message": ("File storage is part of Pro." if limit == 0
                            else "You've reached your storage limit."),
                "current_bytes": current,
                "upload_bytes": upload_size_bytes,
                "limit_bytes": limit,
                "upgrade_url": "/pricing",
            },
        )


@asynccontextmanager
async def storage_upload_slot(user: dict, upload_size_bytes: int, *, wait_seconds: float = 120.0):
    """Quota check that holds under concurrent uploads.

    The plan limit is checked against stored bytes, then the file is stored and
    recorded. Without serialisation, several uploads started together all see
    the same usage and all pass. Each user's uploads therefore run one at a
    time inside a short MongoDB lease (services/coordination.py): the check,
    the storage write and the database record happen together, and the next
    upload checks against the updated total. A crashed holder's lease expires
    after LEASE_TTL, so nothing stays blocked.

        async with storage_upload_slot(user, len(data)):
            put_object(...); insert the file record
    """
    import asyncio
    import time
    import uuid as _uuid
    from services.coordination import LeaseLock

    if is_super_admin(user):
        yield
        return
    uid = str(user.get("id") or user.get("_id") or "")
    lock = LeaseLock(f"storage-quota:{uid}", ttl_seconds=180, holder=f"upload:{_uuid.uuid4().hex}")
    deadline = time.monotonic() + wait_seconds
    while not await lock.acquire():
        if time.monotonic() > deadline:
            raise HTTPException(status_code=429, detail={
                "code": "upload_in_progress",
                "message": "Another upload is still finishing. Please try again in a moment."})
        await asyncio.sleep(0.25)
    try:
        await assert_storage_quota(dict(user, id=uid), upload_size_bytes)
        yield
    finally:
        try:
            await lock.release()
        except Exception:
            pass


# ---------------------------- discovery quota ----------------------------

_DISCOVERY_LIMIT_KEYS: dict[str, str] = {
    "journal": "journal_recs_per_month",
    "conference": "conference_recs_per_month",
    "grant": "grant_recs_per_month",
}


async def check_discovery_quota(user: dict, kind: str) -> None:
    """Enforce monthly discovery recommendations quota for free-plan users.

    Researcher+ plans always pass through (limit == -1). Free users are capped
    at their plan limit. Usage is tracked per-user/kind/month in discovery_usage.
    Raises 402 with code "quota_exceeded" when the limit is reached.
    """
    if is_super_admin(user):
        return
    plan_code = user.get("plan_code") or "free"
    plan = get_plan(plan_code)
    limit_key = _DISCOVERY_LIMIT_KEYS.get(kind)
    if not limit_key:
        return
    limit: int = (plan.get("limits") or {}).get(limit_key, -1)
    if limit == -1:
        return  # unlimited — paid plan
    if limit == 0:
        from services.entitlements import capability_denied
        raise capability_denied(f"can_use_{kind}_discovery", user)

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.discovery_usage.find_one_and_update(
        {"user_id": user["id"], "kind": kind, "month": month},
        {"$inc": {"count": 1}},
        upsert=True,
        return_document=True,
    )
    if doc["count"] > limit:
        await db.discovery_usage.update_one(
            {"user_id": user["id"], "kind": kind, "month": month},
            {"$inc": {"count": -1}},
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "quota_exceeded",
                "message": (
                    f"You've used your {limit} {kind} recommendations for this month. "
                    f"Upgrade to {get_plan('researcher').get('name', 'Pro')} for unlimited access."
                ),
                "resource": limit_key,
                "limit": limit,
                "month": month,
                "upgrade_url": "/pricing",
            },
        )


# ---------------------------- institution membership ----------------------------
# Canonical institution-access check. Institution access is granted ONLY by a
# real, approved row in institution_memberships — never by plan_code (an
# individual can self-purchase the "institution" plan tier without joining any
# real organization), institution_verified, ORCID affiliation, or
# professional_role. Every institution-scoped route should call one of these
# instead of hand-rolling its own membership query.

async def get_institution_membership(institution_id: str, user: dict) -> dict | None:
    """The caller's own approved institution_memberships row, or None."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    return await db.institution_memberships.find_one({
        "institution_id": institution_id,
        "user_id": user.get("id"),
        "status": "approved",
    })


async def require_institution_member(institution_id: str, user: dict) -> dict:
    """Raise 403 unless the user has real, approved membership in this
    institution (platform admin/super_admin bypass). Returns the membership
    row (or a synthetic platform-admin marker)."""
    from zt.deps import zt_is_admin
    if zt_is_admin(user):
        return {"role": "platform_admin", "status": "approved"}
    m = await get_institution_membership(institution_id, user)
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this institution")
    return m


async def require_institution_admin(institution_id: str, user: dict) -> dict:
    """Raise 403 unless the user is an owner/admin of this institution (or a
    platform admin)."""
    m = await require_institution_member(institution_id, user)
    if m.get("role") == "platform_admin":
        return m
    if m.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Institution admin access required")
    return m


async def get_my_institution_context(user: dict) -> dict:
    """The single source of truth the frontend uses to decide whether to show
    the Institution navigation section at all — real approved membership only,
    never plan/verification/affiliation/role heuristics."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    m = await db.institution_memberships.find_one(
        {"user_id": user.get("id"), "status": "approved"},
        sort=[("joined_at", 1)],
    )
    if not m:
        return {"is_member": False}
    inst = await db.institutions.find_one({"_id": _to_object_id(m["institution_id"])}, {"name": 1})
    return {
        "is_member": True,
        "institution_id": m["institution_id"],
        "institution_name": (inst or {}).get("name", ""),
        "role": m.get("role"),
        "is_admin": m.get("role") in ("owner", "admin"),
    }


def _to_object_id(value: str):
    from bson import ObjectId
    try:
        return ObjectId(value)
    except Exception:
        return value


# ---------------------------- introspection endpoint helper ----------------------------

async def access_summary(user: dict) -> dict:
    """Used by GET /api/permissions/me to populate the frontend gating cache."""
    plan_code = user.get("plan_code") or "free"
    state = await ensure_user_credits(user["id"])
    features = {f: has_plan_at_least(user, m, feature=f) for f, m in FEATURE_MIN_PLAN.items()}
    institution = await get_my_institution_context(user)
    from services.entitlements import get_entitlements, CAPABILITY_MESSAGES
    from plans_catalogue import capability_min_plan
    return {
        "is_super_admin": is_super_admin(user),
        "plan": plan_code,
        "plan_name": get_plan(plan_code).get("name", plan_code),
        "subscription_status": user.get("subscription_status") or ("active" if plan_code == "free" else None),
        "features": features,
        "quotas": PLAN_QUOTAS.get(plan_code, {}),
        "credits": state,
        "institution": institution,
        "entitlements": get_entitlements(user),
        # Paywall copy per capability, so the UI explains locked features with
        # the same words the API uses when it refuses them.
        "paywall": {cap: {"message": msg,
                          "required_plan": capability_min_plan(cap),
                          "required_plan_name": get_plan(capability_min_plan(cap)).get("name")}
                    for cap, msg in CAPABILITY_MESSAGES.items()},
    }
