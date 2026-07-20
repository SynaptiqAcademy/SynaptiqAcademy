"""
Field-Level Security Engine — Phase XXXV.8

Controls field visibility per identity context.
Modes: visible, hidden, masked, encrypted, role-dependent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .identity import IdentityContext, IdentityType

logger = logging.getLogger(__name__)


class FieldVisibility(str, Enum):
    VISIBLE   = "visible"   # Full value shown
    MASKED    = "masked"    # Partial redaction (e.g. email@***.com)
    HIDDEN    = "hidden"    # Field removed from response
    ENCRYPTED = "encrypted" # Value is encrypted at rest, decrypted on read


@dataclass
class FieldRule:
    field_name:     str
    visibility:     FieldVisibility = FieldVisibility.VISIBLE
    allowed_roles:  list[str]       = field(default_factory=list)   # empty = all
    mask_pattern:   str             = "***"
    encrypt_key_id: str             = "default"

    def effective_visibility(self, identity: IdentityContext) -> FieldVisibility:
        if identity.is_super_admin:
            return FieldVisibility.VISIBLE
        if not self.allowed_roles:
            return self.visibility
        has_role = any(r in identity.roles for r in self.allowed_roles)
        if has_role:
            return self.visibility
        # Role not matched → hidden
        return FieldVisibility.HIDDEN


def _mask_email(value: str) -> str:
    if "@" in value:
        local, domain = value.split("@", 1)
        parts  = domain.split(".")
        masked = local[:2] + "***@" + "***." + (parts[-1] if parts else "com")
        return masked
    return value[:2] + "***"


def _mask_value(value: str, pattern: str) -> str:
    if "@" in value:
        return _mask_email(value)
    if len(value) <= 4:
        return pattern
    return value[:2] + pattern + value[-2:]


# ── Pre-defined field rule sets ───────────────────────────────────────────────

# Fields on user objects that need protection
USER_FIELD_RULES: list[FieldRule] = [
    FieldRule("password_hash",   FieldVisibility.HIDDEN),
    FieldRule("email",           FieldVisibility.MASKED,    allowed_roles=["super_admin", "institution_admin"]),
    FieldRule("phone",           FieldVisibility.MASKED,    allowed_roles=["super_admin"]),
    FieldRule("ip_address",      FieldVisibility.HIDDEN,    allowed_roles=["super_admin"]),
    FieldRule("failed_login_count", FieldVisibility.HIDDEN, allowed_roles=["super_admin", "institution_admin"]),
    FieldRule("locked_until",    FieldVisibility.HIDDEN,    allowed_roles=["super_admin", "institution_admin"]),
    FieldRule("mfa_secret",      FieldVisibility.HIDDEN),
    FieldRule("totp_secret",     FieldVisibility.HIDDEN),
    FieldRule("api_key_hash",    FieldVisibility.HIDDEN),
]

# Fields on AI request logs
AI_REQUEST_FIELD_RULES: list[FieldRule] = [
    FieldRule("prompt",          FieldVisibility.HIDDEN,    allowed_roles=["super_admin"]),
    FieldRule("raw_response",    FieldVisibility.HIDDEN,    allowed_roles=["super_admin"]),
    FieldRule("api_key",         FieldVisibility.HIDDEN),
]


class FieldSecurityEngine:

    def __init__(self) -> None:
        self._rule_sets: dict[str, list[FieldRule]] = {
            "user":       USER_FIELD_RULES,
            "ai_request": AI_REQUEST_FIELD_RULES,
        }

    def register_rules(self, context_name: str, rules: list[FieldRule]) -> None:
        self._rule_sets[context_name] = rules

    def apply(
        self,
        data:         dict,
        context_name: str,
        identity:     IdentityContext,
    ) -> dict:
        """Apply field security rules to a data dict. Returns filtered/masked copy."""
        rules = self._rule_sets.get(context_name, [])
        if not rules:
            return data

        result = dict(data)
        rule_map = {r.field_name: r for r in rules}

        for field_name, rule in rule_map.items():
            if field_name not in result:
                continue
            vis = rule.effective_visibility(identity)
            if vis == FieldVisibility.HIDDEN:
                result.pop(field_name, None)
            elif vis == FieldVisibility.MASKED:
                val = result[field_name]
                if isinstance(val, str):
                    result[field_name] = _mask_value(val, rule.mask_pattern)
                else:
                    result[field_name] = rule.mask_pattern
        return result

    def apply_list(
        self,
        items:        list[dict],
        context_name: str,
        identity:     IdentityContext,
    ) -> list[dict]:
        return [self.apply(item, context_name, identity) for item in items]

    def list_rules(self, context_name: str | None = None) -> dict[str, list[dict]]:
        target = {context_name: self._rule_sets[context_name]} if context_name else self._rule_sets
        return {
            ctx: [{"field": r.field_name, "visibility": r.visibility, "allowed_roles": r.allowed_roles}
                  for r in rules]
            for ctx, rules in target.items()
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: FieldSecurityEngine | None = None


def get_field_security() -> FieldSecurityEngine:
    global _engine
    if _engine is None:
        _engine = FieldSecurityEngine()
    return _engine
