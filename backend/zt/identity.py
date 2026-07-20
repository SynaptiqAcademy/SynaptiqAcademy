"""
Enterprise Identity Platform — Phase XXXV.8

Every subject that can make a request gets an IdentityContext.
This is the single source of truth for WHO is making a request.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class IdentityType(str, Enum):
    RESEARCHER          = "researcher"
    STUDENT             = "student"
    FACULTY             = "faculty"
    INSTITUTION_ADMIN   = "institution_admin"
    MARKETPLACE_PROVIDER= "marketplace_provider"
    EDITOR              = "editor"
    REVIEWER            = "reviewer"
    SUPER_ADMIN         = "super_admin"
    SERVICE_ACCOUNT     = "service_account"
    API_CLIENT          = "api_client"
    AI_AGENT            = "ai_agent"
    WORKER              = "worker"
    ANONYMOUS           = "anonymous"


class AuthMethod(str, Enum):
    PASSWORD    = "password"
    PASSKEY     = "passkey"
    TOTP        = "totp"
    HARDWARE_KEY= "hardware_key"
    SSO         = "sso"
    OAUTH2      = "oauth2"
    OIDC        = "oidc"
    SAML        = "saml"
    GOOGLE      = "google"
    MICROSOFT   = "microsoft"
    ORCID       = "orcid"
    API_KEY     = "api_key"
    SERVICE     = "service"
    ANONYMOUS   = "anonymous"


@dataclass
class IdentityContext:
    """Complete security context for a request subject."""
    subject_id:       str
    identity_type:    IdentityType
    auth_method:      AuthMethod          = AuthMethod.ANONYMOUS
    email:            str | None          = None
    institution:      str | None          = None
    roles:            list[str]           = field(default_factory=list)
    scopes:           list[str]           = field(default_factory=list)
    permissions:      set[str]            = field(default_factory=set)
    mfa_verified:     bool                = False
    device_trusted:   bool                = False
    session_id:       str | None          = None
    api_key_id:       str | None          = None
    subscription_tier: str                = "free"
    is_demo:          bool                = False
    is_verified:      bool                = False
    workspace_ids:    list[str]           = field(default_factory=list)
    attributes:       dict[str, Any]      = field(default_factory=dict)

    @property
    def is_authenticated(self) -> bool:
        return self.identity_type != IdentityType.ANONYMOUS

    @property
    def is_super_admin(self) -> bool:
        return self.identity_type == IdentityType.SUPER_ADMIN or "super_admin" in self.roles

    @property
    def is_machine(self) -> bool:
        return self.identity_type in (
            IdentityType.SERVICE_ACCOUNT,
            IdentityType.API_CLIENT,
            IdentityType.AI_AGENT,
            IdentityType.WORKER,
        )

    def has_permission(self, permission: str) -> bool:
        if self.is_super_admin:
            return True
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def to_dict(self) -> dict:
        return {
            "subject_id":      self.subject_id,
            "identity_type":   self.identity_type,
            "auth_method":     self.auth_method,
            "email":           self.email,
            "institution":     self.institution,
            "roles":           self.roles,
            "scopes":          self.scopes,
            "mfa_verified":    self.mfa_verified,
            "device_trusted":  self.device_trusted,
            "subscription_tier": self.subscription_tier,
            "is_demo":         self.is_demo,
            "is_verified":     self.is_verified,
            "is_machine":      self.is_machine,
        }


# ── Identity type mapping from user record fields ─────────────────────────────

def identity_type_from_user(user: dict) -> IdentityType:
    role = user.get("role", "researcher")
    user_type = user.get("user_type", "researcher")
    mapping = {
        "super_admin":     IdentityType.SUPER_ADMIN,
        "admin":           IdentityType.INSTITUTION_ADMIN,
        "faculty":         IdentityType.FACULTY,
        "student":         IdentityType.STUDENT,
        "reviewer":        IdentityType.REVIEWER,
        "editor":          IdentityType.EDITOR,
        "provider":        IdentityType.MARKETPLACE_PROVIDER,
        "researcher":      IdentityType.RESEARCHER,
    }
    return mapping.get(role, mapping.get(user_type, IdentityType.RESEARCHER))


def build_identity_context(
    user: dict | None,
    *,
    auth_method:   AuthMethod  = AuthMethod.PASSWORD,
    api_key_id:    str | None  = None,
    session_id:    str | None  = None,
    device_trusted: bool       = False,
    mfa_verified:  bool        = False,
) -> IdentityContext:
    """Build an IdentityContext from a decoded JWT user dict."""
    if user is None:
        return IdentityContext(
            subject_id    = "anonymous",
            identity_type = IdentityType.ANONYMOUS,
            auth_method   = AuthMethod.ANONYMOUS,
        )
    user_id = str(user.get("_id", user.get("id", "unknown")))
    id_type = identity_type_from_user(user)
    roles   = [id_type.value]
    if user.get("role"):
        roles.append(user["role"])

    return IdentityContext(
        subject_id       = user_id,
        identity_type    = id_type,
        auth_method      = auth_method if api_key_id is None else AuthMethod.API_KEY,
        email            = user.get("email"),
        institution      = user.get("institution"),
        roles            = list(set(roles)),
        mfa_verified     = mfa_verified,
        device_trusted   = device_trusted,
        session_id       = session_id,
        api_key_id       = api_key_id,
        subscription_tier= user.get("subscription_tier", "free"),
        is_demo          = bool(user.get("is_demo")),
        is_verified      = bool(user.get("email_verified")),
        attributes       = {
            "h_index":            user.get("h_index", 0),
            "publications_count": user.get("publications_count", 0),
            "account_age_days":   0,
        },
    )


ANONYMOUS_IDENTITY = IdentityContext(
    subject_id    = "anonymous",
    identity_type = IdentityType.ANONYMOUS,
    auth_method   = AuthMethod.ANONYMOUS,
)
