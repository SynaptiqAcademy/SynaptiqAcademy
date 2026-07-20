"""
Security Context — carries the authenticated identity through every repository call.

Every repository receives a SecurityContext, never a raw user dict.
All data-access scoping (user_id, tenant_id, institution_id) is derived from here.

Created once per request from the authenticated user, then passed down the call chain.
Nothing inside the repository layer ever reads from the HTTP request directly.

Usage:
    ctx = SecurityContext.from_user(user, request_id=request.headers.get("x-request-id"))
    repo = MissionRepository(db, ctx)
    missions = await repo.list_missions()
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SecurityContext:
    """Immutable security identity for a single request."""

    user_id:          str
    email:            str             = ""
    role:             str             = "researcher"
    institution:      str             = ""
    institution_id:   Optional[str]   = None
    workspace_id:     Optional[str]   = None
    tenant_id:        Optional[str]   = None   # enterprise: org-level isolation
    subscription_tier: str            = "free"
    permissions:      frozenset       = field(default_factory=frozenset)
    is_super_admin:   bool            = False
    is_admin:         bool            = False
    request_id:       str             = field(default_factory=lambda: str(uuid.uuid4()))
    # Raw user for convenience (not used for security decisions — use explicit fields)
    _user_snapshot:   dict            = field(default_factory=dict, compare=False, hash=False)

    # ── Constructors ──────────────────────────────────────────────────────────

    @classmethod
    def from_user(
        cls,
        user: dict,
        request_id: str | None = None,
        workspace_id: str | None = None,
    ) -> "SecurityContext":
        """Create from authenticated user document (from get_current_user())."""
        if not user:
            raise ValueError("Cannot create SecurityContext from empty user")

        uid = str(user.get("_id") or user.get("id") or "")
        role = user.get("role", "researcher")
        email = user.get("email", "")

        import os
        sa_emails = {
            e.strip().lower()
            for e in os.environ.get("SUPER_ADMIN_EMAILS", "admin@synaptiq.academy").split(",")
            if e.strip()
        }
        is_super  = role == "super_admin" or email.lower() in sa_emails
        is_admin_ = is_super or role in ("admin", "institution_admin")

        # Derive permissions from role
        perms = _role_permissions(role, is_super)

        # Derive tenant_id from institution (enterprise isolation)
        inst = user.get("institution", "")
        tenant_id = _institution_to_tenant(inst) if inst else None

        return cls(
            user_id=uid,
            email=email,
            role=role,
            institution=inst,
            institution_id=str(user.get("institution_id", "")) or None,
            workspace_id=workspace_id or str(user.get("active_workspace_id", "")) or None,
            tenant_id=tenant_id,
            subscription_tier=_subscription_tier(user),
            permissions=frozenset(perms),
            is_super_admin=is_super,
            is_admin=is_admin_,
            request_id=request_id or str(uuid.uuid4()),
            _user_snapshot=dict(user),
        )

    @classmethod
    def system(cls, request_id: str | None = None) -> "SecurityContext":
        """
        System-level context for internal operations (workers, recovery, scheduler).
        Bypasses user-scoped RLS. Use ONLY for system-level code, never for user requests.
        """
        return cls(
            user_id="system",
            email="system@synaptiq.internal",
            role="system",
            is_super_admin=True,
            is_admin=True,
            permissions=frozenset({"*"}),
            request_id=request_id or str(uuid.uuid4()),
        )

    # ── Permission checks ─────────────────────────────────────────────────────

    def has_permission(self, permission: str) -> bool:
        return "*" in self.permissions or permission in self.permissions

    def can_read(self, resource: str) -> bool:
        return self.has_permission(f"read:{resource}") or self.has_permission(f"*:{resource}")

    def can_write(self, resource: str) -> bool:
        return self.has_permission(f"write:{resource}") or self.has_permission(f"*:{resource}")

    def can_delete(self, resource: str) -> bool:
        return (
            self.has_permission(f"delete:{resource}")
            or self.has_permission(f"*:{resource}")
            or self.is_admin
        )

    def can_access_institution(self, institution_id: str) -> bool:
        """True if this context can access resources belonging to the institution."""
        if self.is_super_admin:
            return True
        if self.institution_id and str(institution_id) == str(self.institution_id):
            return True
        return False

    def owns(self, doc: dict) -> bool:
        """True if this user is the owner of a document."""
        return (
            str(doc.get("user_id", "")) == self.user_id
            or str(doc.get("owner_id", "")) == self.user_id
        )

    def to_audit_dict(self) -> dict:
        """Minimal representation for audit log entries."""
        return {
            "user_id":    self.user_id,
            "email":      self.email,
            "role":       self.role,
            "request_id": self.request_id,
            "tenant_id":  self.tenant_id,
        }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _role_permissions(role: str, is_super: bool) -> list[str]:
    if is_super or role == "super_admin":
        return ["*"]
    if role == "admin":
        return [
            "read:*", "write:*", "delete:*",
            "admin:users", "admin:institutions",
        ]
    if role == "institution_admin":
        return [
            "read:*", "write:institution:*",
            "read:users", "admin:institution",
        ]
    # Default: researcher
    return [
        "read:own", "write:own",
        "read:missions", "write:missions",
        "read:publications", "write:publications",
        "read:workspaces", "write:workspaces",
    ]


def _subscription_tier(user: dict) -> str:
    sub = user.get("subscription") or {}
    if isinstance(sub, dict):
        return sub.get("tier", "free")
    return str(sub) if sub else "free"


def _institution_to_tenant(institution: str) -> str | None:
    """Derive a stable tenant_id from the institution name."""
    if not institution:
        return None
    import hashlib
    return hashlib.sha256(institution.strip().lower().encode()).hexdigest()[:16]
