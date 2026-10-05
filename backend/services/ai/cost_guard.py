"""Per-request AI cost control, run by the gateway before every provider call.

  1. Attribution — the paying user, plan and catalogue operation come from the
     request's credit reservation (services/credits_service.py context), never
     from client input.
  2. Routing     — operations tagged model_tier="simple" go to the cheap model
     (services/ai/pricing.py::model_for_tier) unless the caller pinned a model.
  3. Guards      — max input tokens, max output tokens, max estimated cost per
     request, and per-user daily / monthly provider-cost ceilings.
  4. Accounting  — after the call, usage is attached to the reservation and the
     user's cost counters are incremented.

A guard rejection raises HTTPException; the monetization middleware then
releases the request's reservation, so the user is never charged for it.

Billing classification of every AI call (recorded on ai_requests):
  USER_BILLABLE           a credit reservation is attached (user pays)
  INTERNAL_NON_BILLABLE   feature explicitly listed in INTERNAL_NON_BILLABLE_FEATURES
  BACKGROUND_UNATTRIBUTED no HTTP request and no reservation (scheduled/system
                          jobs) — monitored in admin metrics
Inside a user HTTP request, an AI call that is neither billed nor explicitly
internal is BLOCKED (UnbilledAIBlocked) — no user-triggered path can spend
provider money without consuming credits.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException

from plans_catalogue import AI_OPERATIONS, TIER_BY_PLAN
from services.ai.pricing import (
    estimate_cost_usd, estimate_tokens, guards_for, model_for_tier,
)

logger = logging.getLogger("synaptiq.ai.cost_guard")

_ESTIMATE_MODEL = "claude-sonnet-4-6"   # conservative when no model is pinned

USER_BILLABLE = "USER_BILLABLE"
INTERNAL_NON_BILLABLE = "INTERNAL_NON_BILLABLE"
BACKGROUND_UNATTRIBUTED = "BACKGROUND_UNATTRIBUTED"

# AI features allowed to run inside an HTTP request without a credit
# reservation. Each entry must say why it is not billed to a user.
INTERNAL_NON_BILLABLE_FEATURES: dict[str, str] = {
    "admin_copilot": "Admin OS copilot — admin/super-admin only (routers/admin_expansion.py)",
    "validation": "Evidence check run inside an already-billed request (gateway/response_validator.py)",
}


class UnbilledAIBlocked(HTTPException):
    """A user-request AI call with no credit reservation and no internal
    classification. Optional AI enrichments catch this and degrade
    gracefully; anything else surfaces as 503 and is logged as a defect."""

    def __init__(self, feature: str):
        super().__init__(status_code=503, detail={
            "code": "ai_unavailable",
            "message": "This AI action isn't available right now.",
        })
        self.feature = feature


def classify(billing: dict | None, feature: str | None) -> str:
    if billing and billing.get("id"):
        return USER_BILLABLE
    if (feature or "") in INTERNAL_NON_BILLABLE_FEATURES:
        return INTERNAL_NON_BILLABLE
    return BACKGROUND_UNATTRIBUTED


@dataclass
class GuardContext:
    user_id: str | None
    tier: str
    plan_code: str | None
    operation: str | None
    reservation_id: str | None
    credits: int


def _attribution(request) -> GuardContext:
    from services.credits_service import current_reservation
    r = current_reservation()
    if r:
        return GuardContext(user_id=r["user_id"], tier=TIER_BY_PLAN.get(r["plan_code"], "PRO"),
                            plan_code=r["plan_code"], operation=r.get("operation"),
                            reservation_id=r["id"], credits=r.get("credits", 0))
    return GuardContext(user_id=getattr(request, "user_id", None), tier="SYSTEM", plan_code=None,
                        operation=None, reservation_id=None, credits=0)


def _counter_ids(user_id: str, now: datetime) -> tuple[str, str]:
    return f"{user_id}:d:{now:%Y-%m-%d}", f"{user_id}:m:{now:%Y-%m}"


def _db():
    from db import get_db
    from repo.shim import DBProxy
    from repo.security_context import SecurityContext
    return DBProxy(get_db(), SecurityContext.system())


def _cloud_provider_is_anthropic(request) -> bool:
    if request.provider and request.provider != "anthropic":
        return False
    try:
        from services.ai.engine.core import get_engine
        preferred = get_engine()._config.preferred_cloud_provider
        return preferred in (None, "", "anthropic")
    except Exception:
        return False


async def preflight(request, system: str, user_text: str) -> GuardContext:
    """Route, clamp and enforce guards on a GatewayRequest (mutated in place)."""
    g = _attribution(request)

    # Unbilled-path enforcement (see module docstring).
    from services.credits_service import current_request_context
    feature = getattr(request, "feature", None) or "general"
    if (g.reservation_id is None and current_request_context() is not None
            and feature not in INTERNAL_NON_BILLABLE_FEATURES):
        logger.error("UNBILLED_AI_BLOCKED feature=%s — user-request AI call without a credit "
                     "reservation; add consume_credits() or classify it as internal", feature)
        raise UnbilledAIBlocked(feature)

    limits = guards_for(g.tier)

    # Cost-aware routing by catalogue operation.
    if not request.model and g.operation and _cloud_provider_is_anthropic(request):
        routed = model_for_tier(AI_OPERATIONS.get(g.operation, {}).get("model_tier"))
        if routed:
            request.model = routed

    # Output budget.
    max_out = int(limits["max_output_tokens"])
    if not request.max_tokens or request.max_tokens > max_out:
        request.max_tokens = max_out

    # Input budget.
    if request.messages:
        body = "".join(str(m.get("content", "")) for m in request.messages)
    else:
        body = user_text or ""
    in_tokens = estimate_tokens(system) + estimate_tokens(body)
    if in_tokens > limits["max_input_tokens"]:
        max_words = int(limits["max_input_tokens"] * 0.75)
        raise HTTPException(status_code=413, detail={
            "code": "ai_input_too_large",
            "message": (f"This text is too long for one AI request (about {max_words:,} words max on "
                        "your plan). Select the most relevant section and try again."
                        + ("" if g.tier == "PRO_ADVANCED" else
                           " Pro Advanced includes extended context for longer documents.")),
            "estimated_tokens": in_tokens,
        })

    # Per-request cost ceiling: shrink the output budget to fit, or refuse.
    model = request.model or _ESTIMATE_MODEL
    cap = limits["max_cost_per_request_usd"]
    if estimate_cost_usd(model, in_tokens, request.max_tokens) > cap:
        input_cost = estimate_cost_usd(model, in_tokens, 0)
        out_rate_cost = estimate_cost_usd(model, 0, 1_000_000) / 1_000_000
        affordable = int((cap - input_cost) / out_rate_cost) if out_rate_cost else request.max_tokens
        if affordable < 256:
            raise HTTPException(status_code=413, detail={
                "code": "ai_request_cost_limit",
                "message": "This request is too large to process. Select a shorter section and try again.",
            })
        request.max_tokens = min(request.max_tokens, affordable)

    # Per-user daily / monthly provider-cost ceilings.
    if g.user_id and g.tier != "SYSTEM":
        now = datetime.now(timezone.utc)
        day_id, month_id = _counter_ids(g.user_id, now)
        try:
            docs = await _db().ai_user_cost_counters.find(
                {"_id": {"$in": [day_id, month_id]}}).to_list(2)
        except Exception as exc:
            logger.warning("cost counters unavailable (failing open): %s", exc)
            docs = []
        spent = {d["_id"]: float(d.get("cost_usd", 0)) for d in docs}
        if spent.get(day_id, 0) >= limits["daily_cost_limit_usd"]:
            raise HTTPException(status_code=429, detail={
                "code": "ai_daily_limit",
                "message": "You've reached today's AI usage safety limit. It resets at midnight UTC.",
            })
        if spent.get(month_id, 0) >= limits["monthly_cost_limit_usd"]:
            raise HTTPException(status_code=429, detail={
                "code": "ai_monthly_limit",
                "message": "You've reached this month's AI usage safety limit. Contact support if you need more.",
            })
    return g


async def record_provider_usage(billing: dict | None, *, model: str, input_tokens: int,
                                output_tokens: int, cache_read_tokens: int, cache_write_tokens: int,
                                cost_usd: float) -> None:
    """Called for EVERY provider call (services/ai/request_logger.py): attach
    usage to the request's reservation and bump the paying user's cost
    counters. Never raises."""
    billing = billing or {}
    if billing.get("id"):
        from services.credits_service import attach_telemetry
        await attach_telemetry(billing["id"], input_tokens=input_tokens,
                               output_tokens=output_tokens, cache_read_tokens=cache_read_tokens,
                               cache_write_tokens=cache_write_tokens, cost_usd=cost_usd, model=model)
    uid = billing.get("user_id")
    if uid and cost_usd:
        now = datetime.now(timezone.utc)
        day_id, month_id = _counter_ids(uid, now)
        try:
            db = _db()
            for cid, period in ((day_id, f"{now:%Y-%m-%d}"), (month_id, f"{now:%Y-%m}")):
                await db.ai_user_cost_counters.update_one(
                    {"_id": cid},
                    {"$inc": {"cost_usd": float(cost_usd), "requests": 1},
                     "$setOnInsert": {"user_id": uid, "period": period}},
                    upsert=True,
                )
        except Exception as exc:
            logger.warning("cost counter update failed (non-blocking): %s", exc)
