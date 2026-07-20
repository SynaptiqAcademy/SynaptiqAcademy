"""
Centralized Authorization Engine — Phase XXXV.8

Implements RBAC + ABAC + Policy-Based access.
This is the single point of truth for all authorization decisions.

Existing services/permissions.py remains unchanged and continues to work.
New subsystems may call AuthorizationEngine.check() directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .identity import IdentityContext, IdentityType

logger = logging.getLogger(__name__)


class Action(str, Enum):
    READ   = "read"
    WRITE  = "write"
    DELETE = "delete"
    ADMIN  = "admin"
    EXECUTE= "execute"
    EXPORT = "export"
    SHARE  = "share"
    APPROVE= "approve"


class Resource(str, Enum):
    USERS        = "users"
    PAPERS       = "papers"
    WORKSPACE    = "workspace"
    MANUSCRIPT   = "manuscript"
    MISSION      = "mission"
    AI_REQUEST   = "ai_request"
    GRAPH        = "graph"
    TWIN         = "twin"
    GRANTS       = "grants"
    BILLING      = "billing"
    ADMIN        = "admin"
    SETTINGS     = "settings"
    AUDIT        = "audit"
    SECURITY     = "security"
    PRIVACY      = "privacy"
    FILES        = "files"
    MESSAGES     = "messages"
    ANALYTICS    = "analytics"
    REPUTATION   = "reputation"
    TEACHING     = "teaching"
    REVIEWS      = "reviews"


@dataclass
class AuthzDecision:
    allowed:    bool
    reason:     str
    policy_id:  str | None = None
    risk_level: str        = "low"

    @classmethod
    def allow(cls, reason: str = "RBAC grant") -> "AuthzDecision":
        return cls(allowed=True, reason=reason)

    @classmethod
    def deny(cls, reason: str = "Insufficient permission") -> "AuthzDecision":
        return cls(allowed=False, reason=reason)


# ── Role permission maps ──────────────────────────────────────────────────────

_ROLE_PERMISSIONS: dict[str, set[str]] = {
    IdentityType.SUPER_ADMIN.value: {"*"},  # Wildcard — everything

    IdentityType.INSTITUTION_ADMIN.value: {
        "read:users", "write:users", "delete:users",
        "read:workspace", "write:workspace", "admin:workspace",
        "read:papers", "write:papers",
        "read:grants", "write:grants",
        "read:analytics", "read:audit",
        "read:reputation", "write:reputation",
        "read:billing", "admin:settings",
        # Platform admin access gate (used by zt_check(user, "admin", "admin"))
        "admin:admin", "admin:users",
    },

    IdentityType.FACULTY.value: {
        "read:papers", "write:papers", "export:papers",
        "read:workspace", "write:workspace",
        "read:grants", "write:grants",
        "read:manuscript", "write:manuscript",
        "read:reviews", "write:reviews", "approve:reviews",
        "read:teaching", "write:teaching",
        "execute:ai_request", "read:analytics",
    },

    IdentityType.RESEARCHER.value: {
        "read:papers", "write:papers", "export:papers",
        "read:workspace", "write:workspace",
        "read:grants", "write:grants",
        "read:manuscript", "write:manuscript",
        "read:reviews",
        "execute:ai_request",
        "read:messages", "write:messages",
        "read:analytics",
    },

    IdentityType.STUDENT.value: {
        "read:papers",
        "read:workspace", "write:workspace",
        "read:manuscript", "write:manuscript",
        "execute:ai_request",
        "read:messages", "write:messages",
    },

    IdentityType.REVIEWER.value: {
        "read:papers", "read:manuscript",
        "read:reviews", "write:reviews",
        "execute:ai_request",
    },

    IdentityType.EDITOR.value: {
        "read:papers", "write:papers",
        "read:manuscript", "write:manuscript",
        "read:reviews", "write:reviews", "approve:reviews",
        "execute:ai_request",
    },

    IdentityType.MARKETPLACE_PROVIDER.value: {
        "read:papers",
        "execute:ai_request",
        "read:messages", "write:messages",
    },

    IdentityType.SERVICE_ACCOUNT.value: {
        "read:papers", "read:users", "read:workspace",
        "execute:ai_request",
        "read:analytics",
    },

    IdentityType.API_CLIENT.value: {
        "read:papers", "execute:ai_request",
    },

    IdentityType.AI_AGENT.value: {
        "read:papers", "read:grants", "read:workspace",
        "execute:ai_request",
    },

    IdentityType.WORKER.value: {
        "read:papers", "write:papers",
        "execute:ai_request",
        "read:workspace", "write:workspace",
    },

    IdentityType.ANONYMOUS.value: set(),
}


class AuthorizationEngine:
    """
    Centralized authorization engine.

    Usage:
        engine = get_authz_engine()
        decision = engine.check(identity, "read", "papers")
    """

    def __init__(self) -> None:
        self._policy_overrides: dict[str, bool] = {}  # "action:resource" → bool

    # ── Core check ────────────────────────────────────────────────────────────

    def check(
        self,
        identity:   IdentityContext,
        action:     str,
        resource:   str,
        context:    dict | None = None,
    ) -> AuthzDecision:
        """
        Evaluate whether identity may perform action on resource.
        Evaluation order: super_admin bypass → RBAC → ABAC → deny.
        """
        ctx = context or {}

        # 1. Super admin bypass
        if identity.is_super_admin:
            return AuthzDecision.allow("super_admin bypass")

        permission = f"{action}:{resource}"

        # 2. Policy overrides (explicit allow/deny)
        if permission in self._policy_overrides:
            allowed = self._policy_overrides[permission]
            return AuthzDecision(
                allowed  = allowed,
                reason   = "policy_override",
                policy_id= "override",
            )

        # 3. RBAC — check role permissions
        role_perms = set()
        for role in identity.roles:
            role_perms |= _ROLE_PERMISSIONS.get(role, set())

        rbac_allowed = "*" in role_perms or permission in role_perms

        if not rbac_allowed:
            return AuthzDecision.deny(f"Role {identity.roles} lacks {permission}")

        # 4. ABAC — attribute-based conditions
        abac_result = self._abac_check(identity, action, resource, ctx)
        if abac_result is not None:
            return abac_result

        return AuthzDecision.allow(f"RBAC grant: {permission}")

    def _abac_check(
        self,
        identity: IdentityContext,
        action:   str,
        resource: str,
        ctx:      dict,
    ) -> AuthzDecision | None:
        """
        Attribute-Based Access Control checks.
        Returns None if no ABAC rule matches (RBAC decision stands).
        """
        # Demo accounts cannot export or delete
        if identity.is_demo and action in ("export", "delete"):
            return AuthzDecision.deny("Demo accounts cannot export or delete")

        # Billing requires non-free tier or admin role
        if resource == "billing" and action in ("write", "admin"):
            if identity.identity_type not in (
                IdentityType.SUPER_ADMIN, IdentityType.INSTITUTION_ADMIN
            ) and "billing_write" not in identity.scopes:
                return AuthzDecision.deny("Billing write requires elevated permission")

        # Admin resource requires admin role
        if resource == "admin" and identity.identity_type not in (
            IdentityType.SUPER_ADMIN, IdentityType.INSTITUTION_ADMIN
        ):
            return AuthzDecision.deny("Admin access requires admin role")

        # Security resource — super admin only (enforced here as belt-and-suspenders)
        if resource == "security" and not identity.is_super_admin:
            return AuthzDecision.deny("Security access requires super_admin")

        # MFA required for highest-privilege resources only
        # "admin" is NOT in this list — platform admin does not enforce MFA
        # at the ZT layer (existing routes have no MFA dependency).
        if resource in ("audit", "security") and not identity.mfa_verified:
            if not identity.is_machine:
                return AuthzDecision.deny("MFA required for this resource")

        return None

    # ── Policy override management ────────────────────────────────────────────

    def set_policy_override(self, permission: str, allow: bool) -> None:
        self._policy_overrides[permission] = allow

    def remove_policy_override(self, permission: str) -> None:
        self._policy_overrides.pop(permission, None)

    def list_role_permissions(self, role: str) -> list[str]:
        return sorted(_ROLE_PERMISSIONS.get(role, set()))

    def all_roles(self) -> list[dict]:
        return [
            {"role": role, "permissions": sorted(perms)}
            for role, perms in _ROLE_PERMISSIONS.items()
        ]


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: AuthorizationEngine | None = None


def init_authz_engine() -> None:
    global _engine
    _engine = AuthorizationEngine()


def get_authz_engine() -> AuthorizationEngine:
    if _engine is None:
        init_authz_engine()
    return _engine
