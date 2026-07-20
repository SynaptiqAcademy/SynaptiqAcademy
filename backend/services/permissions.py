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

def has_plan_at_least(user: dict, required: str) -> bool:
    if is_super_admin(user):
        return True
    user_plan = user.get("plan_code") or "free"
    return PLAN_RANK.get(user_plan, 0) >= PLAN_RANK.get(required, 0)


def has_active_subscription(user: dict) -> bool:
    """Free plan is considered 'active' (always usable). Paid plans must be live."""
    plan = user.get("plan_code") or "free"
    if plan == "free":
        return True
    status_val = user.get("subscription_status") or "active"
    return status_val in ("active", "trialing")


def can_access_feature(user: dict, feature: str) -> tuple[bool, str | None]:
    """Returns (allowed, required_plan). Used by GET endpoints that should not
    raise but return a soft gate-state to the UI."""
    required = FEATURE_MIN_PLAN.get(feature, "free")
    if has_plan_at_least(user, required):
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

def require_plan(min_plan: str) -> Callable:
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if not has_plan_at_least(user, min_plan):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "upgrade_required",
                    "message": f"This action requires the {min_plan.replace('_',' ').title()} plan or higher.",
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
    return require_plan(FEATURE_MIN_PLAN.get(feature, "free"))


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
    plan = user.get("plan_code") or "free"
    quotas = PLAN_QUOTAS.get(plan, {})
    limit = quotas.get(resource, -1)
    if limit == -1:
        return
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
    """Sum size_bytes of all latest-version files owned by the user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.files.aggregate([
        {"$match": {"owner_id": user_id, "is_latest": True}},
        {"$group": {"_id": None, "total": {"$sum": "$size_bytes"}}},
    ]).to_list(1)
    return result[0]["total"] if result else 0


async def assert_storage_quota(user: dict, upload_size_bytes: int) -> None:
    """Raises 402 when a file upload would exceed the plan's storage limit."""
    if is_super_admin(user):
        return
    plan = user.get("plan_code") or "free"
    limit = STORAGE_LIMITS_BYTES.get(plan, STORAGE_LIMITS_BYTES["free"])
    current = await get_user_storage_bytes(user["id"])
    if current + upload_size_bytes > limit:
        code = "storage_exceeded_after_downgrade" if current >= limit else "storage_limit_exceeded"
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": code,
                "message": "You've reached your repository storage limit.",
                "current_bytes": current,
                "upload_bytes": upload_size_bytes,
                "limit_bytes": limit,
                "upgrade_url": "/pricing",
            },
        )


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
                    "Upgrade to Researcher for unlimited access."
                ),
                "resource": limit_key,
                "limit": limit,
                "month": month,
                "upgrade_url": "/pricing",
            },
        )


# ---------------------------- introspection endpoint helper ----------------------------

async def access_summary(user: dict) -> dict:
    """Used by GET /api/permissions/me to populate the frontend gating cache."""
    plan_code = user.get("plan_code") or "free"
    state = await ensure_user_credits(user["id"])
    features = {f: has_plan_at_least(user, m) for f, m in FEATURE_MIN_PLAN.items()}
    return {
        "is_super_admin": is_super_admin(user),
        "plan": plan_code,
        "subscription_status": user.get("subscription_status") or ("active" if plan_code == "free" else None),
        "features": features,
        "quotas": PLAN_QUOTAS.get(plan_code, {}),
        "credits": state,
    }
