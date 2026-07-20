"""
Data Classification Engine — Phase XXXV.8

Every data object has a classification level.
Classification determines encryption, retention, access, and export policies.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ClassificationLevel(str, Enum):
    PUBLIC                  = "public"
    INTERNAL                = "internal"
    CONFIDENTIAL            = "confidential"
    RESTRICTED              = "restricted"
    SENSITIVE               = "sensitive"
    RESEARCH_CONFIDENTIAL   = "research_confidential"
    INSTITUTION_CONFIDENTIAL= "institution_confidential"
    PERSONAL                = "personal"
    AI_GENERATED            = "ai_generated"
    VERIFIED                = "verified"


# Numeric severity — higher = more protected
_LEVEL_SEVERITY: dict[ClassificationLevel, int] = {
    ClassificationLevel.PUBLIC:                   0,
    ClassificationLevel.AI_GENERATED:             1,
    ClassificationLevel.INTERNAL:                 2,
    ClassificationLevel.VERIFIED:                 2,
    ClassificationLevel.CONFIDENTIAL:             3,
    ClassificationLevel.RESEARCH_CONFIDENTIAL:    4,
    ClassificationLevel.INSTITUTION_CONFIDENTIAL: 4,
    ClassificationLevel.PERSONAL:                 5,
    ClassificationLevel.RESTRICTED:               6,
    ClassificationLevel.SENSITIVE:                7,
}


@dataclass
class ClassificationPolicy:
    level:                ClassificationLevel
    requires_auth:        bool       = True
    requires_mfa:         bool       = False
    encrypt_at_rest:      bool       = False
    encrypt_in_transit:   bool       = True
    max_retention_days:   int | None = None
    export_allowed:       bool       = True
    ai_access_allowed:    bool       = True
    audit_on_read:        bool       = False
    audit_on_write:       bool       = True
    allowed_roles:        list[str]  = field(default_factory=list)
    description:          str        = ""


_POLICIES: dict[ClassificationLevel, ClassificationPolicy] = {
    ClassificationLevel.PUBLIC: ClassificationPolicy(
        level             = ClassificationLevel.PUBLIC,
        requires_auth     = False,
        encrypt_at_rest   = False,
        export_allowed    = True,
        ai_access_allowed = True,
        audit_on_read     = False,
        description       = "Publicly accessible data",
    ),
    ClassificationLevel.INTERNAL: ClassificationPolicy(
        level             = ClassificationLevel.INTERNAL,
        requires_auth     = True,
        encrypt_at_rest   = False,
        export_allowed    = True,
        ai_access_allowed = True,
        description       = "Internal platform data",
    ),
    ClassificationLevel.CONFIDENTIAL: ClassificationPolicy(
        level             = ClassificationLevel.CONFIDENTIAL,
        requires_auth     = True,
        encrypt_at_rest   = True,
        export_allowed    = True,
        ai_access_allowed = True,
        audit_on_read     = True,
        description       = "Confidential research data",
    ),
    ClassificationLevel.RESTRICTED: ClassificationPolicy(
        level             = ClassificationLevel.RESTRICTED,
        requires_auth     = True,
        requires_mfa      = True,
        encrypt_at_rest   = True,
        export_allowed    = False,
        ai_access_allowed = False,
        audit_on_read     = True,
        description       = "Restricted data — MFA required",
    ),
    ClassificationLevel.SENSITIVE: ClassificationPolicy(
        level             = ClassificationLevel.SENSITIVE,
        requires_auth     = True,
        requires_mfa      = True,
        encrypt_at_rest   = True,
        export_allowed    = False,
        ai_access_allowed = False,
        audit_on_read     = True,
        max_retention_days= 365,
        description       = "Highly sensitive — encrypt + MFA",
    ),
    ClassificationLevel.RESEARCH_CONFIDENTIAL: ClassificationPolicy(
        level             = ClassificationLevel.RESEARCH_CONFIDENTIAL,
        requires_auth     = True,
        encrypt_at_rest   = True,
        export_allowed    = True,
        ai_access_allowed = True,
        audit_on_read     = True,
        description       = "Confidential research data",
    ),
    ClassificationLevel.INSTITUTION_CONFIDENTIAL: ClassificationPolicy(
        level             = ClassificationLevel.INSTITUTION_CONFIDENTIAL,
        requires_auth     = True,
        encrypt_at_rest   = True,
        export_allowed    = False,
        ai_access_allowed = False,
        audit_on_read     = True,
        description       = "Institution-only — no external AI",
    ),
    ClassificationLevel.PERSONAL: ClassificationPolicy(
        level             = ClassificationLevel.PERSONAL,
        requires_auth     = True,
        requires_mfa      = False,
        encrypt_at_rest   = True,
        export_allowed    = True,   # GDPR right to portability
        ai_access_allowed = False,
        audit_on_read     = True,
        max_retention_days= 2555,   # 7 years
        description       = "Personal data (GDPR-scoped)",
    ),
    ClassificationLevel.AI_GENERATED: ClassificationPolicy(
        level             = ClassificationLevel.AI_GENERATED,
        requires_auth     = True,
        encrypt_at_rest   = False,
        export_allowed    = True,
        ai_access_allowed = True,
        description       = "AI-generated content — evidence required",
    ),
    ClassificationLevel.VERIFIED: ClassificationPolicy(
        level             = ClassificationLevel.VERIFIED,
        requires_auth     = True,
        encrypt_at_rest   = False,
        export_allowed    = True,
        ai_access_allowed = True,
        audit_on_write    = True,
        description       = "Human-verified data",
    ),
}


class DataClassifier:

    def get_policy(self, level: ClassificationLevel) -> ClassificationPolicy:
        return _POLICIES[level]

    def severity(self, level: ClassificationLevel) -> int:
        return _LEVEL_SEVERITY.get(level, 0)

    def classify_collection(self, collection_name: str) -> ClassificationLevel:
        """Infer classification from MongoDB collection name."""
        mapping = {
            # Personal / sensitive
            "users":           ClassificationLevel.PERSONAL,
            "mfa_configs":     ClassificationLevel.RESTRICTED,
            "trusted_devices": ClassificationLevel.RESTRICTED,
            "refresh_tokens":  ClassificationLevel.RESTRICTED,
            "password_resets": ClassificationLevel.RESTRICTED,
            # Research confidential
            "manuscripts":     ClassificationLevel.RESEARCH_CONFIDENTIAL,
            "manuscript_versions": ClassificationLevel.RESEARCH_CONFIDENTIAL,
            "grant_applications":  ClassificationLevel.RESEARCH_CONFIDENTIAL,
            # Internal
            "publications":    ClassificationLevel.INTERNAL,
            "collaborations":  ClassificationLevel.INTERNAL,
            "workspaces":      ClassificationLevel.INTERNAL,
            # Confidential AI
            "obs_audit":       ClassificationLevel.CONFIDENTIAL,
            "obs_security":    ClassificationLevel.CONFIDENTIAL,
            "zt_audit":        ClassificationLevel.CONFIDENTIAL,
        }
        return mapping.get(collection_name, ClassificationLevel.INTERNAL)

    def all_levels(self) -> list[dict]:
        return [
            {
                "level":       level.value,
                "severity":    self.severity(level),
                "policy":      {
                    "requires_auth":      p.requires_auth,
                    "requires_mfa":       p.requires_mfa,
                    "encrypt_at_rest":    p.encrypt_at_rest,
                    "export_allowed":     p.export_allowed,
                    "ai_access_allowed":  p.ai_access_allowed,
                    "max_retention_days": p.max_retention_days,
                    "description":        p.description,
                },
            }
            for level, p in _POLICIES.items()
        ]

    def check_access(
        self,
        level:        ClassificationLevel,
        is_authenticated: bool,
        mfa_verified: bool,
        action:       str = "read",
    ) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        policy = self.get_policy(level)
        if policy.requires_auth and not is_authenticated:
            return False, "Authentication required"
        if policy.requires_mfa and not mfa_verified:
            return False, "MFA required for this classification"
        if action == "export" and not policy.export_allowed:
            return False, "Export not allowed for this classification"
        if action == "ai_access" and not policy.ai_access_allowed:
            return False, "AI access not allowed for this classification"
        return True, "Access granted"


# ── Singleton ─────────────────────────────────────────────────────────────────

_classifier: DataClassifier | None = None


def get_classifier() -> DataClassifier:
    global _classifier
    if _classifier is None:
        _classifier = DataClassifier()
    return _classifier
