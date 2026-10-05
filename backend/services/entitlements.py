"""Capability-based entitlements — the single authority for "may this user do X".

Derived entirely from plans_catalogue (TIER_BY_PLAN, TIER_CAPABILITIES,
PLAN_QUOTAS, STORAGE_LIMITS_BYTES, PLANS[].credits_per_month), so there is
one source of truth for tiers. services/permissions.py, the route policy
middleware (services/plan_access_policy.py) and the credit chokepoint
(services/credits_service.py) all ask this module.

Never trust a plan or entitlement value supplied by the client: every
function here takes the server-side user document.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from plans_catalogue import (
    CAPABILITIES,
    CAPABILITY_FEATURE,
    PLAN_QUOTAS,
    STORAGE_LIMITS_BYTES,
    TIER_BY_PLAN,
    TIER_CAPABILITIES,
    TIER_FREE,
    TIER_PRO_ADVANCED,
    capability_min_plan,
    get_plan,
)

# Subscription states that keep paid entitlements. past_due is a grace state
# while Stripe retries the card; data is never deleted in any state.
ENTITLED_STATUSES = frozenset({"active", "trialing", "past_due", None, ""})

# What the user is told when a capability is missing (paywall copy).
CAPABILITY_MESSAGES = {
    "can_use_research_network": "Upgrade to Pro to connect with researchers.",
    "can_discover_researchers": "Upgrade to Pro to discover and connect with researchers.",
    "can_message_researchers": "Upgrade to Pro to message researchers.",
    "can_send_collaboration_request": "Sending collaboration requests is part of Pro.",
    "can_accept_collaboration": "Upgrade to Pro to respond to collaboration invitations.",
    "can_join_collaboration_workflows": "Collaboration workflows are part of Pro.",
    "can_create_project": "Projects are part of Pro.",
    "can_create_workspace": "Workspaces are part of Pro.",
    "can_use_journal_discovery": "Upgrade to Pro to discover journals for your research.",
    "can_use_conference_discovery": "Upgrade to Pro to discover conferences for your research.",
    "can_use_grant_discovery": "Upgrade to Pro to discover grants for your research.",
    "can_use_research_assistant": "Upgrade to Pro to use the AI Research Assistant.",
    "can_use_manuscript_copilot": "Upgrade to Pro to use Manuscript Copilot.",
    "can_use_teaching_hub": "The Teaching Hub is part of Pro.",
    "can_use_teaching_ai": "Teaching AI is part of Pro.",
    "can_use_publication_tracking": "Publication tracking is part of Pro.",
    "can_view_research_analytics": "Research analytics are part of Pro.",
    "can_purchase_ai_credits": "Extra AI credits are available on Pro and Pro Advanced.",
    "can_use_collaboration_intelligence": "Collaboration Intelligence is part of Pro Advanced.",
    "can_use_citation_monitoring": "Citation Monitoring is part of Pro Advanced.",
    "can_view_impact_dashboard": "The Impact Dashboard is part of Pro Advanced.",
    "can_view_advanced_analytics": "Advanced Analytics is part of Pro Advanced.",
    "can_use_advanced_ai": "The Advanced AI Research Assistant is part of Pro Advanced.",
    "can_use_advanced_manuscript_intelligence": "Advanced Manuscript Intelligence is part of Pro Advanced.",
    "can_use_advanced_teaching_ai": "Advanced AI Teaching is part of Pro Advanced.",
}


def _is_super_admin(user: dict) -> bool:
    # Local import: permissions imports this module.
    from services.permissions import is_super_admin
    return is_super_admin(user)


def effective_plan_code(user: dict) -> str:
    """The plan whose entitlements apply right now. A paid plan_code whose
    subscription has lapsed (unpaid / canceled / expired / incomplete) is
    treated as Free — data stays, access to paid capabilities does not."""
    plan = user.get("plan_code") or "free"
    if plan == "free":
        return "free"
    if (user.get("subscription_status") or None) not in ENTITLED_STATUSES:
        return "free"
    return plan if plan in TIER_BY_PLAN else "free"


def tier_for(user: dict) -> str:
    if _is_super_admin(user):
        return TIER_PRO_ADVANCED
    return TIER_BY_PLAN.get(effective_plan_code(user), TIER_FREE)


def _override_features(user: dict) -> set[str]:
    return {o.get("feature") for o in (user.get("feature_overrides") or []) if isinstance(o, dict)}


def has_capability(user: dict, capability: str) -> bool:
    if capability not in CAPABILITIES:
        raise KeyError(f"Unknown capability: {capability}")
    if TIER_CAPABILITIES[tier_for(user)].get(capability):
        return True
    feature = CAPABILITY_FEATURE.get(capability)
    return bool(feature and feature in _override_features(user))


def _limit(n: int | None) -> int | None:
    """-1 (catalogue 'unlimited') -> None; everything else unchanged."""
    return None if n is None or n == -1 else n


def get_entitlements(user: dict) -> dict:
    """Full entitlement snapshot. Null numeric limit = unlimited."""
    tier = tier_for(user)
    plan_code = effective_plan_code(user)
    if _is_super_admin(user):
        quotas = {"projects": -1, "workspaces": -1}
        storage = -1
    else:
        quotas = PLAN_QUOTAS.get(plan_code, PLAN_QUOTAS["free"])
        storage = STORAGE_LIMITS_BYTES.get(plan_code, 0)
    caps = {c: has_capability(user, c) for c in CAPABILITIES}
    return {
        "tier": tier,
        "plan_code": user.get("plan_code") or "free",
        "effective_plan_code": plan_code,
        "plan_name": get_plan(plan_code).get("name", "Free"),
        "subscription_status": user.get("subscription_status") or None,
        "capabilities": caps,
        "monthly_ai_credits": get_plan(plan_code).get("credits_per_month", 0) if tier != TIER_FREE else 0,
        "project_limit": _limit(quotas.get("projects", 0)),
        "workspace_limit": _limit(quotas.get("workspaces", 0)),
        "storage_limit_bytes": _limit(storage),
    }


def capability_denied(capability: str, user: dict | None = None) -> HTTPException:
    required = capability_min_plan(capability)
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": "upgrade_required",
            "capability": capability,
            "message": CAPABILITY_MESSAGES.get(capability, "This feature requires an upgrade."),
            "required_plan": required,
            "required_plan_name": get_plan(required).get("name"),
            "current_plan": (user or {}).get("plan_code") or "free",
            "upgrade_url": "/pricing",
        },
    )


def assert_capability(user: dict, capability: str) -> None:
    if not has_capability(user, capability):
        raise capability_denied(capability, user)


def require_capability(capability: str):
    """FastAPI dependency: 402 upgrade_required unless the user has it."""
    if capability not in CAPABILITIES:
        raise KeyError(f"Unknown capability: {capability}")
    from auth_utils import get_current_user

    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        assert_capability(user, capability)
        return user
    return _dep


async def locked_workspace_ids(user: dict, db) -> set[str]:
    """Owned workspaces above the plan's workspace limit (oldest stay
    unlocked). Locked workspaces are read-only — never deleted — so a
    downgrade preserves all data and an upgrade unlocks it again."""
    limit = get_entitlements(user)["workspace_limit"]
    if limit is None:
        return set()
    docs = await db.workspaces.find(
        {"owner_id": user.get("id")}, {"_id": 1, "created_at": 1},
    ).sort([("created_at", 1), ("_id", 1)]).to_list(None)
    return {str(d["_id"]) for d in docs[limit:]}
