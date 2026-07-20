"""
Policy Engine — Phase XXXV.8

Runtime-configurable policies that layer on top of RBAC/ABAC.
Policies are stored in MongoDB and evaluated per-request.
"""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_COL = "zt_policies"


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY  = "deny"
    DEFER = "defer"    # pass to next policy


class PolicyScope(str, Enum):
    GLOBAL      = "global"
    INSTITUTION = "institution"
    WORKSPACE   = "workspace"
    USER        = "user"
    ROLE        = "role"


@dataclass
class Policy:
    policy_id:   str
    name:        str
    effect:      PolicyEffect
    scope:       PolicyScope        = PolicyScope.GLOBAL
    scope_value: str | None         = None   # institution_id / workspace_id / user_id
    actions:     list[str]          = field(default_factory=list)  # ["read", "*"]
    resources:   list[str]          = field(default_factory=list)  # ["papers", "*"]
    conditions:  dict[str, Any]     = field(default_factory=dict)
    priority:    int                = 100    # lower = higher priority
    enabled:     bool               = True
    created_at:  str                = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by:  str                = "system"
    description: str                = ""

    def matches(self, action: str, resource: str, context: dict) -> bool:
        if not self.enabled:
            return False
        action_match   = "*" in self.actions or action in self.actions
        resource_match = "*" in self.resources or resource in self.resources
        if not (action_match and resource_match):
            return False
        return self._eval_conditions(context)

    def _eval_conditions(self, context: dict) -> bool:
        for key, expected in self.conditions.items():
            actual = context.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    def to_dict(self) -> dict:
        return {
            "policy_id":   self.policy_id,
            "name":        self.name,
            "effect":      self.effect,
            "scope":       self.scope,
            "scope_value": self.scope_value,
            "actions":     self.actions,
            "resources":   self.resources,
            "conditions":  self.conditions,
            "priority":    self.priority,
            "enabled":     self.enabled,
            "created_at":  self.created_at,
            "created_by":  self.created_by,
            "description": self.description,
        }


class PolicyEngine:

    def __init__(self, db: Any) -> None:
        self._db    = db
        self._col   = db[_COL]
        self._cache: list[Policy] = []

    async def ensure_indexes(self) -> None:
        try:
            await self._col.create_index("policy_id", unique=True)
            await self._col.create_index([("scope", 1), ("priority", 1)])
            await self._col.create_index("enabled")
        except Exception as exc:
            logger.debug("Policy index: %s", exc)

    async def load_policies(self) -> None:
        self._cache = []
        async for doc in self._col.find({"enabled": True}).sort("priority", 1):
            doc.pop("_id", None)
            p = Policy(
                policy_id   = doc["policy_id"],
                name        = doc["name"],
                effect      = PolicyEffect(doc["effect"]),
                scope       = PolicyScope(doc.get("scope", "global")),
                scope_value = doc.get("scope_value"),
                actions     = doc.get("actions", ["*"]),
                resources   = doc.get("resources", ["*"]),
                conditions  = doc.get("conditions", {}),
                priority    = doc.get("priority", 100),
                enabled     = True,
                created_at  = doc.get("created_at", ""),
                created_by  = doc.get("created_by", "system"),
                description = doc.get("description", ""),
            )
            self._cache.append(p)

    def evaluate(
        self,
        action:   str,
        resource: str,
        context:  dict,
    ) -> PolicyEffect:
        """
        Evaluate all cached policies in priority order.
        First matching ALLOW or DENY wins; DEFER continues.
        Returns DEFER (neutral) if no policy matches.
        """
        for policy in sorted(self._cache, key=lambda p: p.priority):
            if policy.matches(action, resource, context):
                if policy.effect != PolicyEffect.DEFER:
                    return policy.effect
        return PolicyEffect.DEFER

    async def create_policy(
        self,
        name:        str,
        effect:      PolicyEffect,
        actions:     list[str],
        resources:   list[str],
        scope:       PolicyScope     = PolicyScope.GLOBAL,
        scope_value: str | None      = None,
        conditions:  dict | None     = None,
        priority:    int             = 100,
        description: str             = "",
        created_by:  str             = "system",
    ) -> Policy:
        p = Policy(
            policy_id   = "pol_" + secrets.token_hex(8),
            name        = name,
            effect      = effect,
            scope       = scope,
            scope_value = scope_value,
            actions     = actions,
            resources   = resources,
            conditions  = conditions or {},
            priority    = priority,
            description = description,
            created_by  = created_by,
        )
        doc = p.to_dict()
        await self._col.insert_one(doc)
        self._cache.append(p)
        self._cache.sort(key=lambda x: x.priority)
        return p

    async def delete_policy(self, policy_id: str) -> bool:
        result = await self._col.delete_one({"policy_id": policy_id})
        self._cache = [p for p in self._cache if p.policy_id != policy_id]
        return result.deleted_count > 0

    async def toggle_policy(self, policy_id: str, enabled: bool) -> bool:
        result = await self._col.update_one(
            {"policy_id": policy_id}, {"$set": {"enabled": enabled}}
        )
        for p in self._cache:
            if p.policy_id == policy_id:
                p.enabled = enabled
        return result.modified_count > 0

    def list_cached(self) -> list[dict]:
        return [p.to_dict() for p in self._cache]


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: PolicyEngine | None = None


def init_policy_engine(db: Any) -> PolicyEngine:
    global _engine
    _engine = PolicyEngine(db)
    return _engine


def get_policy_engine() -> PolicyEngine:
    if _engine is None:
        raise RuntimeError("PolicyEngine not initialised")
    return _engine
