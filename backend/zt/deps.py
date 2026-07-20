"""
Zero Trust FastAPI Dependency Layer — Sprint 1.3

Single entry point for all authorization decisions.
Routers import from here; no router implements permission logic directly.

Usage — inline gate (raises HTTP 403 if denied):
    zt_check(user, "admin", "admin")

Usage — boolean predicate (for conditional branching):
    if zt_is_admin(user): ...

Usage — FastAPI dependency on route:
    @router.get("/items", dependencies=[Depends(require_permission("read", "papers"))])
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status

from auth_utils import get_current_user
from zt.authorization import get_authz_engine, AuthzDecision
from zt.identity import build_identity_context, IdentityContext, IdentityType

log = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_identity(user: dict) -> IdentityContext:
    return build_identity_context(user)


def _audit_fire(
    subject_id: str,
    action: str,
    resource: str,
    decision: AuthzDecision,
    *,
    trace_id: str | None = None,
) -> None:
    """Fire-and-forget audit entry for every ZT authorization decision."""
    async def _write() -> None:
        try:
            from db import get_db
            from repo.shim import make_db_proxy
            db = make_db_proxy(get_db(), system=True)
            await db["zt_audit"].insert_one({
                "actor_id":   subject_id,
                "action":     action,
                "resource":   resource,
                "decision":   "allow" if decision.allowed else "deny",
                "reason":     decision.reason,
                "policy_id":  decision.policy_id,
                "risk_level": decision.risk_level,
                "trace_id":   trace_id,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass  # audit must never fail the request

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_write())
    except RuntimeError:
        pass  # not in async context (tests / startup) — skip


def _raise_forbidden(decision: AuthzDecision) -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code":      "zt_forbidden",
            "reason":    decision.reason,
            "policy_id": decision.policy_id,
        },
    )


# ── Core sync helpers (for use inside function bodies) ────────────────────────

def zt_check(user: dict, action: str, resource: str) -> None:
    """
    Inline ZT authorization gate.

    Evaluates the ZT engine, fires an audit entry, and raises HTTP 403 if
    the decision is deny.  Use this to replace raw role/is_admin checks
    inside router function bodies.

    Replaces patterns like:
        if user.get("role") not in ("admin", "super_admin"):
            raise HTTPException(403, ...)
        if not (user.get("is_super_admin") or user.get("role") in ("admin", ...)):
            raise HTTPException(403, ...)

    Usage:
        zt_check(user, "admin", "admin")     # admin or above
        zt_check(user, "admin", "security")  # super_admin only
    """
    identity = _build_identity(user)
    engine   = get_authz_engine()
    decision = engine.check(identity, action, resource)
    _audit_fire(identity.subject_id, action, resource, decision)
    if not decision.allowed:
        _raise_forbidden(decision)


def zt_is_admin(user: dict) -> bool:
    """
    Predicate: returns True if the ZT engine grants admin-level access.

    Replaces:
        user.get("is_super_admin") or user.get("role") in ("admin", "super_admin")
        user.get("role") in ("admin", "super_admin")
    """
    identity = _build_identity(user)
    engine   = get_authz_engine()
    decision = engine.check(identity, "admin", "admin")
    _audit_fire(identity.subject_id, "admin", "admin", decision)
    return decision.allowed


def zt_is_super_admin(user: dict) -> bool:
    """
    Predicate: returns True only for super_admin.

    Replaces:
        user.get("is_super_admin")
        user.get("role") == "super_admin"
    """
    identity = _build_identity(user)
    return identity.is_super_admin


# ── FastAPI dependency functions ──────────────────────────────────────────────

def require_permission(action: str, resource: str) -> Callable:
    """
    Dependency factory: require ZT permission on a route.

    Usage:
        @router.get("/secure", dependencies=[Depends(require_permission("read", "audit"))])
    """
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        zt_check(user, action, resource)
        return user
    return _dep


async def require_admin_dep(user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency: admin or institution_admin required.

    Replaces:
        dependencies=[Depends(require_admin)]  →  dependencies=[Depends(require_admin_dep)]
    """
    zt_check(user, "admin", "admin")
    return user


async def require_super_admin_dep(user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency: super_admin required.

    Replaces:
        dependencies=[Depends(require_super_admin)]  on ZT-gated routes.
    """
    zt_check(user, "admin", "security")
    return user


# ── Feature & subscription gates ─────────────────────────────────────────────

def require_feature_zt(feature: str) -> Callable:
    """
    ZT-backed feature gate that also enforces plan tier.
    Routes through services.permissions.require_feature for plan checks,
    THEN through the ZT engine for additional policy enforcement.
    """
    from services.permissions import require_feature, FEATURE_MIN_PLAN
    base_dep = require_feature(feature)

    async def _dep(user: dict = Depends(base_dep)) -> dict:
        resource = feature.replace("_", ":")
        identity = _build_identity(user)
        engine   = get_authz_engine()
        decision = engine.check(identity, "read", resource)
        _audit_fire(identity.subject_id, "read", resource, decision)
        # Note: plan gate already enforced by base_dep; ZT adds policy layer.
        # We do not raise here to preserve backward-compat subscription errors.
        return user
    return _dep
