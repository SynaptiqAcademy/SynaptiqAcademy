"""AI provider cost budget — the single source for every AI spending cap.

Caps are derived from an explicit monthly provider budget and a planning cost
per credit, not from subscription prices:

  AI_MONTHLY_BUDGET_USD            total provider spend Synaptiq accepts per month
                                   (all users + background jobs).      default 500
  AI_SYSTEM_BUDGET_SHARE           share of that budget background / system AI may
                                   use (no paying user attached).      default 0.10
  AI_EXPECTED_COST_PER_CREDIT_USD  planning provider cost of one credit, measured
                                   from ai_requests after launch.      default 0.01
  AI_USER_HEADROOM                 how far one user may exceed the expected cost
                                   of their plan's credits (abuse backstop). default 3
  AI_BUDGET_ALERT_THRESHOLDS       comma list of budget fractions that alert.
                                                                       default 0.5,0.8,1.0

Derived caps:
  background monthly  = budget × system share
  background daily    = background monthly × 2 / 30   (allows a busy day, bounded)
  per-user monthly    = plan credits per month × cost per credit × headroom
  per-user daily      = per-user monthly / 4
Per-request cost and token limits stay in services/ai/pricing.py.

Example with the defaults: budget $500 → background $50/month, $3.33/day;
Pro (200 credits) → $6/month, $1.50/day; Pro Advanced (750 credits) →
$22.50/month, $5.63/day.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("synaptiq.ai.budget")

# Plan used to size each tier's per-user cap (TIER_BY_PLAN in plans_catalogue).
_TIER_PLAN = {"PRO": "researcher", "PRO_ADVANCED": "pro_researcher"}


def _f(name: str, default: float) -> float:
    try:
        v = float(os.environ.get(name, "").strip() or default)
        return v if v >= 0 else default
    except ValueError:
        logger.error("%s is not a number — using %s", name, default)
        return default


def monthly_budget_usd() -> float:
    return _f("AI_MONTHLY_BUDGET_USD", 500.0)


def system_share() -> float:
    return min(1.0, _f("AI_SYSTEM_BUDGET_SHARE", 0.10))


def cost_per_credit_usd() -> float:
    return _f("AI_EXPECTED_COST_PER_CREDIT_USD", 0.01)


def user_headroom() -> float:
    return _f("AI_USER_HEADROOM", 3.0)


def system_monthly_cap_usd() -> float:
    return round(monthly_budget_usd() * system_share(), 4)


def system_daily_cap_usd() -> float:
    return round(system_monthly_cap_usd() * 2 / 30, 4)


def user_caps_usd(tier: str) -> tuple[float, float]:
    """(daily, monthly) provider-cost ceiling for one user on this tier."""
    from plans_catalogue import get_plan
    plan = get_plan(_TIER_PLAN.get(tier, "researcher")) or {}
    credits = max(int(plan.get("credits_per_month") or 0), 0)
    monthly = round(credits * cost_per_credit_usd() * user_headroom(), 4)
    return round(monthly / 4, 4), monthly


def alert_thresholds() -> list[float]:
    raw = os.environ.get("AI_BUDGET_ALERT_THRESHOLDS", "0.5,0.8,1.0")
    out = []
    for part in raw.split(","):
        try:
            out.append(float(part))
        except ValueError:
            pass
    return sorted(x for x in out if x > 0) or [0.8, 1.0]


def summary() -> dict:
    d_pro, m_pro = user_caps_usd("PRO")
    d_adv, m_adv = user_caps_usd("PRO_ADVANCED")
    return {
        "monthly_budget_usd": monthly_budget_usd(),
        "system": {"daily": system_daily_cap_usd(), "monthly": system_monthly_cap_usd()},
        "per_user": {"PRO": {"daily": d_pro, "monthly": m_pro},
                     "PRO_ADVANCED": {"daily": d_adv, "monthly": m_adv}},
        "cost_per_credit_usd": cost_per_credit_usd(),
        "user_headroom": user_headroom(),
    }
