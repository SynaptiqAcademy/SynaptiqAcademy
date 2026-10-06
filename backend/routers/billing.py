import json as _json
import logging
import os
from datetime import datetime, timezone, timedelta
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger(__name__)
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from auth_utils import get_current_user
from db import get_db
from plans_catalogue import (
    PLANS, PLAN_RANK, get_plan, get_plan_by_price_id, CREDIT_PACKS, get_credit_pack,
    CREDIT_USAGE_DISPLAY, FEATURE_MATRIX, FEATURE_MATRIX_GROUPS, AI_OPERATIONS,
)
from services import stripe_service
from services.credits_service import (
    ensure_user_credits, grant_pack_credits, allocate_subscription_credits,
    apply_plan_change_credits,
)
from services.billing_history_service import (
    record_billing_event, record_subscription_transition,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _safe_plan(p: dict) -> dict:
    """Public-safe plan dict (strips internal stripe price ids, and the
    internal reference price of non-self-serve plans — Institutional/
    Enterprise are Custom / Contact Sales, so no public price is published;
    the values stay in plans_catalogue.py for internal/sales reference)."""
    custom = p["code"] in NOT_SELF_SERVE_PLANS
    return {
        "code": p["code"],
        "name": p["name"],
        "tagline": p.get("tagline", ""),
        "price_eur_monthly": None if custom else p["price_eur_monthly"],
        "price_eur_annual": None if custom else p["price_eur_annual"],
        "future_price_eur_monthly": p.get("future_price_eur_monthly"),
        "badge": p.get("badge"),
        "recommended": bool(p.get("recommended")),
        "key": p.get("key"),
        "price_label": p.get("price_label"),
        "credits_per_month": None if custom else p["credits_per_month"],
        "limits": {} if custom else p["limits"],
        # Server-authoritative: a paid plan can be bought only when Stripe can
        # both take the payment and deliver the plan (price + webhook secret).
        "checkout_available": (not custom and p["code"] != "free"
                               and bool(p.get("stripe_price_id_monthly"))
                               and stripe_service.checkout_ready()),
        "features": p["features"],
        "excluded": p.get("excluded", []),
        "cta": p.get("cta", f"Choose {p['name']}"),
    }


# ----------------------------- PUBLIC LISTING -----------------------------

@router.get("/plans")
async def list_plans():
    """Public list of plans for the pricing page."""
    return [_safe_plan(p) for p in PLANS]


@router.get("/credit-packs")
async def list_credit_packs():
    """Public list of credit packs (one-time purchases for Pro / Pro Advanced;
    purchased credits never expire)."""
    return [{"code": p["code"], "key": p["key"], "name": p["name"], "credits": p["credits"],
             "price_eur": p["price_eur"],
             "label": p["label"], "available": bool(p.get("stripe_price_id"))
             and stripe_service.checkout_ready()} for p in CREDIT_PACKS]


@router.get("/credit-usage-catalogue")
async def credit_usage_catalogue():
    """AI credit price list (server-side catalogue — the frontend never
    hardcodes costs). `operations` maps operation code -> credits."""
    from plans_catalogue import CREDIT_COSTS
    return {
        "display": CREDIT_USAGE_DISPLAY,
        "operations": {op: m["credits"] for op, m in AI_OPERATIONS.items()},
        # Per-action prices (action keys used by individual endpoints).
        "actions": dict(CREDIT_COSTS),
    }


@router.get("/feature-matrix")
async def feature_matrix():
    """Feature comparison for the pricing page: the three individual plans
    (Institutional is arranged per organisation and not compared row by
    row). Rows are grouped by intent; the extra-credits row is shown only
    while credit packs can actually be bought."""
    packs_on = any(p.get("stripe_price_id") for p in CREDIT_PACKS) and stripe_service.checkout_ready()
    return {
        "columns": ["free", "researcher", "pro_researcher"],
        "rows": [
            {"label": r[0], "group": FEATURE_MATRIX_GROUPS.get(r[0], "Other"), "values": list(r[1:4])}
            for r in FEATURE_MATRIX
            if packs_on or r[0] != "Buy extra AI credits"
        ],
    }


# ----------------------------- USER STATE -----------------------------

@router.get("/subscription")
async def get_subscription(user: dict = Depends(get_current_user)):
    """Current user's subscription + plan + credits."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    sub = await db.subscriptions.find_one({
        "user_id": user["id"],
        "status": {"$in": ["active", "trialing", "past_due"]},
    })
    plan = get_plan(user.get("plan_code") or "free")
    credits = await ensure_user_credits(user["id"])
    out = {
        "plan": _safe_plan(plan),
        "subscription": None,
        "credits": credits,
        "stripe_configured": stripe_service.is_configured(),
    }
    if sub:
        out["subscription"] = {
            "id": str(sub["_id"]),
            "status": sub.get("status"),
            "billing_period": sub.get("billing_period", "monthly"),
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            "stripe_subscription_id": sub.get("stripe_subscription_id", ""),
        }
    return out


@router.get("/me")
async def billing_me(user: dict = Depends(get_current_user)):
    """Authoritative billing state for the UI (no Stripe internals)."""
    from services.entitlements import get_entitlements
    db = DBProxy(get_db(), SecurityContext.system())
    credits = await ensure_user_credits(user["id"])
    fresh = await db.users.find_one({"_id": ObjectId(user["id"])}) or user
    fresh = dict(fresh, id=user["id"])
    ent = get_entitlements(fresh)
    sub = await db.subscriptions.find_one(
        {"user_id": user["id"], "status": {"$in": ["active", "trialing", "past_due", "unpaid"]}},
        sort=[("updated_at", -1)])
    period_end = (sub or {}).get("current_period_end")
    return {
        "plan": ent["effective_plan_code"],
        "plan_name": ent["plan_name"],
        "tier": ent["tier"],
        "subscription_status": (sub or {}).get("status") or fresh.get("subscription_status") or None,
        "cancel_at_period_end": bool((sub or {}).get("cancel_at_period_end")),
        "current_period_end": _ts_iso(period_end) if isinstance(period_end, (int, float)) else period_end,
        "subscription_credits": credits["subscription_credits"],
        "monthly_credit_allowance": ent["monthly_ai_credits"],
        "purchased_credits": credits["purchased_credits"],
        "total_available_credits": credits["total_credits"] if credits["credits_usable"] else 0,
        "credits_usable": credits["credits_usable"],
        "credits_renew_at": credits["reset_at"] if ent["tier"] != "FREE" else None,
        "workspace_limit": ent["workspace_limit"],
        "project_limit": ent["project_limit"],
        "storage_limit_bytes": ent["storage_limit_bytes"],
        "can_purchase_ai_credits": ent["capabilities"]["can_purchase_ai_credits"],
        "billing_mode": stripe_service.stripe_mode(),
        "checkout_available": stripe_service.is_configured(),
    }


@router.get("/history")
async def billing_history(limit: int = 50, user: dict = Depends(get_current_user)):
    """User-visible billing history (invoices, pack purchases, refunds)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.billing_history.find({"user_id": user["id"]}) \
        .sort("created_at", -1).limit(limit).to_list(limit)
    return [{
        "id": str(d["_id"]),
        "kind": d.get("kind"),
        "amount_eur": d.get("amount_eur"),
        "currency": d.get("currency", "eur"),
        "status": d.get("status"),
        "description": d.get("description", ""),
        "created_at": d["created_at"],
    } for d in docs]


@router.get("/subscription-history")
async def subscription_history(limit: int = 50, user: dict = Depends(get_current_user)):
    """State-transition log for plan changes / cancellations."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.subscription_history.find({"user_id": user["id"]}) \
        .sort("created_at", -1).limit(limit).to_list(limit)
    return [{
        "id": str(d["_id"]),
        "from_plan": d.get("from_plan"),
        "to_plan": d.get("to_plan"),
        "reason": d.get("reason", ""),
        "created_at": d["created_at"],
    } for d in docs]


# ----------------------------- CHECKOUT -----------------------------

# "institution" is deliberately NOT self-serve here (Phase 9A Part 2, §13):
# it's an individual-account plan_code with no real organization binding —
# real institution access is granted only via institution_memberships
# (services/permissions.py::require_institution_member), never plan_code.
# Letting an individual self-checkout "institution" would silently sell
# something that doesn't provide what its name implies. "enterprise" is
# intentionally excluded too — contact-sales/custom-invoiced only, per
# plans_catalogue.py's own "contact_sales": True flag.
VALID_PAID_PLANS = {"researcher", "pro_researcher"}
NOT_SELF_SERVE_PLANS = {"institution", "enterprise"}


def _frontend_url(path: str) -> str:
    """Redirect targets are built server-side from FRONTEND_BASE_URL — the
    browser never supplies them (no open redirects via Stripe)."""
    base = (os.environ.get("FRONTEND_BASE_URL") or os.environ.get("APP_BASE_URL") or "").rstrip("/")
    if not base:
        raise HTTPException(status_code=503, detail={"code": "billing_not_configured",
                                                     "message": "Online checkout isn't available yet."})
    return f"{base}{path}"


async def _stripe_customer_id(db, user_id: str) -> str:
    """The user's existing Stripe customer, if any (reused for new checkouts)."""
    u = await db.users.find_one({"_id": ObjectId(user_id)}, {"stripe_customer_id": 1})
    if (u or {}).get("stripe_customer_id"):
        return u["stripe_customer_id"]
    sub = await db.subscriptions.find_one(
        {"user_id": user_id, "stripe_customer_id": {"$nin": [None, ""]}}, sort=[("updated_at", -1)])
    return (sub or {}).get("stripe_customer_id", "")


_LIVE_SUB_STATUSES = ["active", "trialing", "past_due"]


@router.post("/checkout-session")
async def create_checkout(body: dict, user: dict = Depends(get_current_user)):
    """Start a subscription (Free -> paid) or change plan (paid -> other paid).

    Nothing here grants access or credits: the plan and credits change only
    when Stripe's verified webhook confirms the subscription.
    """
    from plans_catalogue import PLAN_KEY_TO_CODE
    requested = body.get("plan") or body.get("plan_code")
    plan_code = PLAN_KEY_TO_CODE.get(requested, requested) if isinstance(requested, str) else None
    billing_period = body.get("billing_period", "monthly")
    if plan_code in NOT_SELF_SERVE_PLANS:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This plan isn't available for self-service purchase — please contact us.",
                "code": "not_self_serve",
            },
        )
    if plan_code not in VALID_PAID_PLANS:
        raise HTTPException(status_code=400, detail={
            "code": "invalid_plan", "message": "Choose 'pro' or 'pro_advanced'."})
    if billing_period != "monthly":
        raise HTTPException(status_code=400, detail={
            "code": "billing_period_unavailable",
            "message": "Only monthly billing is available.",
        })

    plan = get_plan(plan_code)
    price_id = plan.get("stripe_price_id_monthly") or ""

    if not stripe_service.checkout_ready() or not price_id:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Online checkout isn't available yet.",
                "code": "billing_not_configured",
                "plan_code": plan_code,
            },
        )

    db = DBProxy(get_db(), SecurityContext.system())
    live = await db.subscriptions.find_one(
        {"user_id": user["id"], "status": {"$in": _LIVE_SUB_STATUSES},
         "stripe_subscription_id": {"$nin": [None, ""]}},
        sort=[("updated_at", -1)],
    )
    if live:
        current = live.get("plan_code") or user.get("plan_code")
        if current == plan_code:
            raise HTTPException(status_code=400, detail={
                "code": "already_subscribed", "message": f"You're already on {plan['name']}."})
        # Plan change on the existing subscription — never a second subscription.
        upgrade = PLAN_RANK.get(plan_code, 0) > PLAN_RANK.get(current or "free", 0)
        try:
            result = stripe_service.change_subscription_plan(
                live["stripe_subscription_id"], new_price_id=price_id,
                plan_code=plan_code, upgrade=upgrade)
        except Exception as e:
            logger.error("[billing] plan change failed for user %s: %s", user["id"], e)
            raise HTTPException(status_code=502, detail={
                "code": "plan_change_failed",
                "message": "We couldn't change your plan right now. You have not been charged.",
            })
        if result is None:
            raise HTTPException(status_code=503, detail="Stripe SDK unavailable.")
        return {"changed": True, "upgrade": upgrade, "plan_code": plan_code,
                "message": "Your plan change is being confirmed by our payment provider."}

    result = stripe_service.create_checkout_session(
        user_email=user["email"],
        user_id=user["id"],
        plan_code=plan_code,
        billing_period="monthly",
        success_url=_frontend_url("/payment/success?type=plan"),
        cancel_url=_frontend_url("/payment/cancelled"),
        stripe_price_id=price_id,
        customer_id=await _stripe_customer_id(db, user["id"]),
    )
    if result is None:
        raise HTTPException(status_code=503, detail="Stripe SDK unavailable.")
    return result


@router.post("/credit-pack-checkout")
async def create_credit_pack_checkout(body: dict, user: dict = Depends(get_current_user)):
    """One-time Stripe Checkout for a credit pack — Pro / Pro Advanced only.
    Credits are granted only by the verified webhook, never by the redirect."""
    from services.entitlements import assert_capability
    assert_capability(user, "can_purchase_ai_credits")

    requested = body.get("pack") or body.get("pack_code")
    pack = get_credit_pack(requested) if isinstance(requested, str) else None
    if not pack:
        raise HTTPException(status_code=400, detail={
            "code": "invalid_pack", "message": "Choose 'small', 'plus' or 'max'."})
    pack_code = pack["code"]

    if not stripe_service.checkout_ready() or not pack.get("stripe_price_id"):
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Credit packs can't be purchased online yet.",
                "code": "billing_not_configured",
                "pack_code": pack_code,
            },
        )

    db = DBProxy(get_db(), SecurityContext.system())
    result = stripe_service.create_credit_pack_checkout_session(
        user_email=user["email"],
        user_id=user["id"],
        pack_code=pack_code,
        credits=pack["credits"],
        success_url=_frontend_url(f"/payment/success?kind=credits&pack={pack_code}"),
        cancel_url=_frontend_url("/payment/cancelled?kind=credits"),
        stripe_price_id=pack["stripe_price_id"],
        customer_id=await _stripe_customer_id(db, user["id"]),
    )
    if result is None:
        raise HTTPException(status_code=503, detail="Stripe SDK unavailable.")
    return result


@router.post("/portal-session")
async def create_portal(body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    customer_id = await _stripe_customer_id(DBProxy(get_db(), SecurityContext.system()), user["id"])
    if not stripe_service.is_configured() or not customer_id:
        raise HTTPException(
            status_code=503,
            detail={"code": "portal_unavailable",
                    "message": "Billing management is available once you have a paid plan."},
        )
    url = stripe_service.create_billing_portal_session(customer_id, _frontend_url("/settings/billing"))
    if not url:
        raise HTTPException(status_code=503, detail="Could not create portal session.")
    return {"url": url}


@router.post("/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    """Cancel at period end. If Stripe is configured we tell Stripe; otherwise
    we just flip the local flag so the UI reflects the intent."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    sub = await db.subscriptions.find_one({"user_id": user["id"],
                                            "status": {"$in": ["active", "trialing", "past_due"]}})
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found.")
    stripe_sub_id = sub.get("stripe_subscription_id", "")
    if stripe_service.is_configured() and stripe_sub_id:
        try:
            stripe = stripe_service._stripe()
            stripe.Subscription.modify(stripe_sub_id, cancel_at_period_end=True)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Stripe cancellation failed: {e}")
    await db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {"$set": {"cancel_at_period_end": True,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    await record_subscription_transition(
        user_id=user["id"], from_plan=user.get("plan_code"), to_plan=user.get("plan_code"),
        reason="user_requested_cancel_at_period_end",
        stripe_subscription_id=stripe_sub_id,
    )
    from services.audit import write_audit
    await write_audit(actor=user, action="subscription_cancel",
                      entity_kind="subscription", entity_id=stripe_sub_id or str(sub["_id"]),
                      target_user_id=user["id"],
                      metadata={"cancel_at_period_end": True})
    return {"ok": True, "cancel_at_period_end": True}


# ----------------------------- WEBHOOK -----------------------------
#
# Stripe is the billing source of truth. Every handler is idempotent on its
# own (not only via the event-id dedupe), because Stripe may deliver related
# events (subscription.created / invoice.paid) in any order:
#   - subscription credits are allocated per billing cycle key
#     "<subscription_id>:<period_start>" — a cycle is allocated at most once;
#   - pack credits are granted per Checkout Session (unique index);
#   - plan changes apply the same deterministic credit rule however often they
#     are replayed (services/credits_service.apply_plan_change_credits).
# If processing fails, the event marker is removed and 500 is returned so
# Stripe retries — a failed delivery is never silently swallowed as a duplicate.

_ENDED_STATUSES = ("canceled", "incomplete_expired")
_STALE_PROCESSING = timedelta(minutes=10)


_EVENT_INDEX_READY = False


async def _event_index_ready(db) -> bool:
    """True once the unique stripe_event_id index is confirmed (cached per
    process). Creates it if missing; False if it can't be guaranteed."""
    global _EVENT_INDEX_READY
    if _EVENT_INDEX_READY:
        return True
    try:
        await db.billing_events.create_index(
            [("stripe_event_id", 1)], unique=True, sparse=True, name="billing_events_idempotency")
        _EVENT_INDEX_READY = True
    except Exception as exc:
        logger.error("[billing/webhook] cannot ensure billing_events unique index: %s", exc)
    return _EVENT_INDEX_READY


def _ts_iso(ts) -> str | None:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat() if ts else None
    except (TypeError, ValueError):
        return None


def _sub_period(sub: dict) -> tuple[int | None, int | None]:
    """(period_start, period_end) — top-level on older API versions, on the
    subscription item on newer ones."""
    start, end = sub.get("current_period_start"), sub.get("current_period_end")
    if not start:
        item = ((sub.get("items") or {}).get("data") or [{}])[0]
        start, end = item.get("current_period_start"), item.get("current_period_end")
    return start, end


def _sub_price_id(sub: dict) -> str:
    return (((sub.get("items") or {}).get("data") or [{}])[0].get("price") or {}).get("id", "")


def _invoice_subscription_line(inv: dict) -> dict:
    lines = (inv.get("lines") or {}).get("data") or []
    for ln in lines:
        if ln.get("type") == "subscription" or (ln.get("parent") or {}).get("type") == "subscription_item_details":
            return ln
    return lines[0] if lines else {}


def _invoice_subscription_id(inv: dict) -> str:
    sub = inv.get("subscription")
    if isinstance(sub, dict):
        sub = sub.get("id")
    if not sub:
        sub = (((inv.get("parent") or {}).get("subscription_details") or {}).get("subscription")) or ""
    return sub or ""


def _line_price_id(line: dict) -> str:
    price = line.get("price") or {}
    if isinstance(price, dict) and price.get("id"):
        return price["id"]
    pricing = (line.get("pricing") or {}).get("price_details") or {}
    return pricing.get("price", "") if isinstance(pricing.get("price"), str) else ""


def _resolve_plan(price_id: str, metadata: dict) -> tuple[str | None, str]:
    """Price id first (it follows plan changes); metadata only as fallback."""
    match = get_plan_by_price_id(price_id)
    if match:
        return match
    code = (metadata or {}).get("plan_code")
    return (code if code in VALID_PAID_PLANS else None), (metadata or {}).get("billing_period", "monthly")


async def _resolve_user_id(db, obj: dict, *, subscription_id: str = "") -> str:
    md = obj.get("metadata") or {}
    uid = md.get("user_id") or obj.get("client_reference_id") or ""
    if not uid:
        details = (obj.get("subscription_details") or
                   ((obj.get("parent") or {}).get("subscription_details")) or {})
        uid = (details.get("metadata") or {}).get("user_id", "")
    if not uid and subscription_id:
        local = await db.subscriptions.find_one({"stripe_subscription_id": subscription_id})
        uid = (local or {}).get("user_id", "")
    if not uid and obj.get("customer"):
        local = await db.subscriptions.find_one({"stripe_customer_id": obj["customer"],
                                                 "user_id": {"$nin": [None, ""]}})
        uid = (local or {}).get("user_id", "")
    return uid or ""


async def _track(user_id: str, event: str, props: dict) -> None:
    from services.product_analytics import track_server_event
    await track_server_event(user_id, event, props)


def _invalidate(user_id: str) -> None:
    """Drop the auth layer's 60s user cache so entitlement checks see the
    webhook's plan/status change on the very next request."""
    try:
        from auth_utils import invalidate_user_cache
        invalidate_user_cache(user_id)
    except Exception:
        pass


async def _fulfil_credit_pack(db, obj: dict, user_id: str, stripe_event_id: str) -> None:
    if obj.get("payment_status") not in ("paid", "no_payment_required"):
        # Async payment methods: wait for checkout.session.async_payment_succeeded.
        logger.info("[billing/webhook] pack session %s not paid yet (%s)", obj.get("id"), obj.get("payment_status"))
        return
    md = obj.get("metadata") or {}
    pack = get_credit_pack(md.get("pack_code", ""))
    if not pack:
        logger.error("[billing/webhook] paid session %s has unknown pack_code %r — not granted",
                     obj.get("id"), md.get("pack_code"))
        return
    # Credits come from the server catalogue for the paid pack, never from
    # client-influenced metadata.
    granted = await grant_pack_credits(
        user_id, pack_code=pack["code"], credits=pack["credits"],
        stripe_checkout_session_id=obj.get("id", ""),
        stripe_payment_intent_id=obj.get("payment_intent", "") or "",
    )
    if granted is None:
        return  # already fulfilled
    await record_billing_event(
        user_id=user_id, kind="pack_purchase",
        amount_eur=(obj.get("amount_total", 0) or 0) / 100.0,
        currency=obj.get("currency", "eur"), status="paid",
        stripe_event_id=stripe_event_id,
        description=f"AI credit pack: {pack['credits']} credits",
        metadata={"pack_code": pack["code"], "credits": pack["credits"]},
    )
    await _track(user_id, "credit_pack_purchased", {"pack_code": pack["code"], "credits": pack["credits"]})


async def _handle_subscription_change(db, obj: dict, event_type: str, stripe_event_id: str) -> None:
    sub_id = obj.get("id", "")
    status = obj.get("status")
    user_id = await _resolve_user_id(db, obj, subscription_id=sub_id)
    plan_code, billing_period = _resolve_plan(_sub_price_id(obj), obj.get("metadata") or {})
    period_start, period_end = _sub_period(obj)
    period_end_iso = _ts_iso(period_end)
    cycle_key = f"{sub_id}:{period_start}" if sub_id and period_start else None

    prior_local = await db.subscriptions.find_one({"stripe_subscription_id": sub_id}) if sub_id else None
    if sub_id:
        await db.subscriptions.update_one(
            {"stripe_subscription_id": sub_id},
            {"$set": {
                "stripe_subscription_id": sub_id,
                "stripe_customer_id": obj.get("customer", ""),
                "user_id": user_id or (prior_local or {}).get("user_id", ""),
                "plan_code": plan_code,
                "billing_period": billing_period,
                "status": status,
                "current_period_start": period_start,
                "current_period_end": period_end,
                "cancel_at_period_end": obj.get("cancel_at_period_end", False),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
    if not user_id or not plan_code:
        logger.warning("[billing/webhook] %s for sub %s: user=%r plan=%r unresolved",
                       event_type, sub_id, user_id, plan_code)
        return

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    prior_plan = (user or {}).get("plan_code") or "free"

    if obj.get("customer"):
        await db.users.update_one({"_id": ObjectId(user_id)},
                                  {"$set": {"stripe_customer_id": obj["customer"]}})

    if status in ("active", "trialing", "past_due"):
        # Duplicate-subscription guard: a second live subscription for the same
        # user (e.g. two checkouts completed in parallel tabs) is flagged for
        # admin action — never silently double-billed or auto-cancelled.
        other = await db.subscriptions.find_one({
            "user_id": user_id, "stripe_subscription_id": {"$ne": sub_id},
            "status": {"$in": ["active", "trialing", "past_due"]}})
        if other:
            await db.billing_alerts.update_one(
                {"kind": "duplicate_subscription", "user_id": user_id,
                 "subscriptions": sorted([sub_id, other["stripe_subscription_id"]])},
                {"$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat(),
                                  "resolved": False}},
                upsert=True)
            logger.error("[billing/webhook] user %s has two live subscriptions (%s, %s)",
                         user_id, sub_id, other["stripe_subscription_id"])
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {
            "plan_code": plan_code, "subscription_status": status}})
        if prior_plan != plan_code:
            await apply_plan_change_credits(user_id, from_plan=prior_plan, to_plan=plan_code,
                                            cycle_key=cycle_key, period_end_iso=period_end_iso)
            await record_subscription_transition(
                user_id=user_id, from_plan=prior_plan, to_plan=plan_code,
                reason=event_type, stripe_subscription_id=sub_id, metadata={"status": status})
            direction = ("subscription_started" if prior_plan == "free" else
                         "subscription_upgraded" if PLAN_RANK.get(plan_code, 0) > PLAN_RANK.get(prior_plan, 0)
                         else "subscription_downgraded")
            await _track(user_id, direction, {"from_plan": prior_plan, "to_plan": plan_code})
        elif cycle_key and (user or {}).get("credits_cycle_key") is None:
            # Same plan but credits never allocated by Stripe (e.g. plan was
            # set by an earlier event before this handler existed).
            await allocate_subscription_credits(user_id, plan_code=plan_code, cycle_key=cycle_key,
                                                period_end_iso=period_end_iso,
                                                reason="Subscription credit allocation")
        if obj.get("cancel_at_period_end") and not (prior_local or {}).get("cancel_at_period_end"):
            await _track(user_id, "subscription_cancelled", {"plan_code": plan_code, "at_period_end": True})
    elif status in _ENDED_STATUSES:
        await _end_subscription(db, user_id, plan_code, sub_id, status, event_type)
    elif status == "unpaid":
        # Stripe exhausted payment retries but kept the subscription. Paid
        # access is suspended (entitlements treat 'unpaid' as Free) while the
        # plan, data and credits stay — paying the open invoice restores it.
        await db.users.update_one({"_id": ObjectId(user_id), "plan_code": plan_code},
                                  {"$set": {"subscription_status": "unpaid"}})
    # 'incomplete': first payment pending — no access change until it succeeds.

    await record_billing_event(
        user_id=user_id, kind="subscription_event", amount_eur=None, status=status,
        stripe_event_id=stripe_event_id, description=f"Subscription {status}",
        metadata={"stripe_subscription_id": sub_id, "plan_code": plan_code},
    )


async def _end_subscription(db, user_id: str, plan_code: str | None, sub_id: str,
                            status: str, reason: str) -> None:
    """Paid access ends: plan -> free. Data is never deleted — workspaces above
    the Free limit become read-only; purchased credits are preserved (usable
    again on re-subscribing); subscription credits expire."""
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    current = (user or {}).get("plan_code") or "free"
    if current == "free" or (plan_code and current != plan_code):
        return  # already ended, or the user has since moved to another plan
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {
        "plan_code": "free",
        "subscription_status": "expired" if status != "unpaid" else "unpaid",
    }})
    await apply_plan_change_credits(user_id, from_plan=current, to_plan="free")
    await record_subscription_transition(user_id=user_id, from_plan=current, to_plan="free",
                                         reason=reason, stripe_subscription_id=sub_id)
    await _track(user_id, "subscription_cancelled", {"plan_code": current, "ended": True, "status": status})


async def _handle_invoice_paid(db, inv: dict, stripe_event_id: str) -> None:
    sub_id = _invoice_subscription_id(inv)
    user_id = await _resolve_user_id(db, inv, subscription_id=sub_id)
    if not user_id:
        logger.warning("[billing/webhook] invoice %s: user unresolved", inv.get("id"))
        return
    await record_billing_event(
        user_id=user_id, kind="invoice", status="paid",
        amount_eur=(inv.get("amount_paid", 0) or 0) / 100.0,
        currency=inv.get("currency", "eur"), stripe_event_id=stripe_event_id,
        description=inv.get("description") or "Invoice paid",
        metadata={"invoice_id": inv.get("id", ""), "billing_reason": inv.get("billing_reason")},
    )
    if not sub_id:
        return
    reason = inv.get("billing_reason")
    line = _invoice_subscription_line(inv)
    period = line.get("period") or {}
    if reason in ("subscription_cycle", "subscription_create") and period.get("start"):
        local = await db.subscriptions.find_one({"stripe_subscription_id": sub_id})
        plan_code = (get_plan_by_price_id(_line_price_id(line)) or (None,))[0] or (local or {}).get("plan_code")
        if plan_code in VALID_PAID_PLANS:
            allocated = await allocate_subscription_credits(
                user_id, plan_code=plan_code, cycle_key=f"{sub_id}:{period['start']}",
                period_end_iso=_ts_iso(period.get("end")),
                reason="Subscription renewal" if reason == "subscription_cycle" else "Subscription start")
            if allocated and reason == "subscription_cycle":
                await _track(user_id, "subscription_renewed", {"plan_code": plan_code})
    # A successful payment clears a past_due grace state.
    await db.subscriptions.update_many({"stripe_subscription_id": sub_id, "status": "past_due"},
                                       {"$set": {"status": "active",
                                                 "updated_at": datetime.now(timezone.utc).isoformat()}})
    await db.users.update_one({"_id": ObjectId(user_id), "subscription_status": {"$in": ["past_due", "unpaid"]}},
                              {"$set": {"subscription_status": "active"}})


async def _handle_pack_refund(db, charge: dict, user_id: str) -> None:
    """Credit-pack refund policy (deterministic, idempotent):
      - only a FULL refund (charge.refunded == true) reverses a pack; partial
        refunds are recorded in billing_alerts for manual review;
      - the reversal removes min(pack credits, current purchased balance) —
        balances never go negative; if part of the pack was already spent the
        shortfall is recorded (ledger metadata + billing_alerts) for review;
      - the purchase row flips paid -> refunded exactly once (atomic), so a
        duplicate refund event can't adjust twice.
    """
    pi = charge.get("payment_intent") or ""
    if not pi:
        return
    if not charge.get("refunded"):
        purchase = await db.credit_purchases.find_one({"stripe_payment_intent_id": pi})
        if purchase:
            await db.billing_alerts.update_one(
                {"kind": "partial_pack_refund", "payment_intent": pi},
                {"$set": {"user_id": purchase["user_id"], "amount_refunded": charge.get("amount_refunded"),
                          "updated_at": datetime.now(timezone.utc).isoformat()},
                 "$setOnInsert": {"resolved": False}}, upsert=True)
        return
    purchase = await db.credit_purchases.find_one_and_update(
        {"stripe_payment_intent_id": pi, "status": "paid"},
        {"$set": {"status": "refunded", "refunded_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not purchase:
        return
    uid = purchase["user_id"]
    credits = int(purchase.get("credits", 0))
    removed = 0
    for _ in range(3):   # retry on concurrent spend
        user = await db.users.find_one({"_id": ObjectId(uid)}, {"credits_pack_balance": 1})
        bal = max((user or {}).get("credits_pack_balance", 0) or 0, 0)
        want = min(credits, bal)
        if want <= 0:
            break
        r = await db.users.update_one({"_id": ObjectId(uid), "credits_pack_balance": {"$gte": want}},
                                      {"$inc": {"credits_pack_balance": -want}})
        if r.modified_count:
            removed = want
            break
    shortfall = credits - removed
    await db.credit_transactions.insert_one({
        "user_id": uid, "kind": "admin_deduct", "ledger_type": "ADMIN_ADJUSTMENT",
        "bucket": "pack", "amount": removed, "balance_effect": -removed,
        "action": "pack_refund", "reason": f"Credit pack refunded ({purchase.get('pack_code')})",
        "metadata": {"payment_intent": pi, "pack_credits": credits, "already_spent": shortfall},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    if shortfall:
        await db.billing_alerts.insert_one({
            "kind": "refunded_pack_partly_spent", "user_id": uid, "payment_intent": pi,
            "credits_already_spent": shortfall, "resolved": False,
            "created_at": datetime.now(timezone.utc).isoformat()})


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook receiver with mandatory HMAC signature verification.

    STRIPE_WEBHOOK_SECRET must be set to process any events. Without it the
    endpoint acknowledges receipt but discards the payload — this prevents
    unauthenticated callers from forging plan changes or credit grants when
    Stripe is not yet configured.
    """
    raw_body = await request.body()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    sig_header = request.headers.get("stripe-signature", "")

    if not webhook_secret:
        # Not acknowledged: a 2xx would tell Stripe the event was delivered and
        # it would never be retried, losing a payment's plan/credit grant.
        # 503 makes Stripe retry until the secret is configured.
        logger.error("[billing/webhook] STRIPE_WEBHOOK_SECRET not set — event not processed; Stripe will retry.")
        raise HTTPException(status_code=503, detail="Billing webhook not configured.")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    try:
        _stripe_sdk = stripe_service._stripe()
        if _stripe_sdk is not None:
            _stripe_sdk.Webhook.construct_event(raw_body, sig_header, webhook_secret)
        else:
            raise HTTPException(status_code=503, detail="Stripe SDK unavailable")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Webhook signature verification failed")

    try:
        payload = _json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    db = DBProxy(get_db(), SecurityContext.system())
    event_type = payload.get("type", "unknown")
    stripe_event_id = payload.get("id", "")
    if not stripe_event_id:
        raise HTTPException(status_code=400, detail="Missing event id")

    # Deduplication depends on the unique index — never process without it.
    if not await _event_index_ready(db):
        logger.error("[billing/webhook] billing_events unique index unavailable — refusing to process %s",
                     stripe_event_id)
        raise HTTPException(status_code=503, detail="Billing temporarily unavailable; Stripe will retry.")

    # Event state machine (unique index on billing_events.stripe_event_id):
    #   PROCESSING -> COMPLETED | FAILED
    # Only COMPLETED blocks reprocessing. A FAILED event, or one stuck in
    # PROCESSING longer than _STALE_PROCESSING (worker crashed mid-way), is
    # re-claimed atomically by the next delivery. Handlers are idempotent on
    # their own, so re-running a partially applied event is safe.
    now = datetime.now(timezone.utc)
    try:
        await db.billing_events.insert_one({
            "stripe_event_id": stripe_event_id,
            "type": event_type,
            "payload": payload,
            "received_at": now.isoformat(),
            "status": "PROCESSING",
            "processing_started_at": now.isoformat(),
            "attempts": 1,
            "processed": False,
        })
    except Exception as dup_exc:
        if not ("E11000" in str(dup_exc) or "duplicate key" in str(dup_exc).lower()):
            raise
        stale_before = (now - _STALE_PROCESSING).isoformat()
        claimed = await db.billing_events.find_one_and_update(
            {"stripe_event_id": stripe_event_id,
             "processed": {"$ne": True},
             "$or": [{"status": "FAILED"},
                     {"status": "PROCESSING", "processing_started_at": {"$lt": stale_before}},
                     {"status": {"$exists": False}}]},       # legacy marker never completed
            {"$set": {"status": "PROCESSING", "processing_started_at": now.isoformat()},
             "$inc": {"attempts": 1}},
        )
        if claimed is None:
            logger.info("[billing/webhook] duplicate event %s ignored (completed or in progress)", stripe_event_id)
            return {"received": True, "processed": False, "reason": "duplicate"}
        logger.warning("[billing/webhook] reprocessing event %s (previous status %s)",
                       stripe_event_id, claimed.get("status"))

    obj = (payload.get("data") or {}).get("object") or {}
    try:
        await _dispatch_event(db, event_type, obj, stripe_event_id)
    except Exception as exc:
        logger.exception("[billing/webhook] processing %s (%s) failed: %s", stripe_event_id, event_type, exc)
        try:
            await db.billing_events.update_one(
                {"stripe_event_id": stripe_event_id},
                {"$set": {"status": "FAILED", "last_error": str(exc)[:500],
                          "failed_at": datetime.now(timezone.utc).isoformat()}})
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Webhook processing failed; Stripe will retry.")

    uid_for_cache = (obj.get("metadata") or {}).get("user_id")
    if not uid_for_cache:
        try:
            uid_for_cache = await _resolve_user_id(db, obj, subscription_id=obj.get("id", "") if
                                                   str(obj.get("id", "")).startswith("sub_") else _invoice_subscription_id(obj))
        except Exception:
            uid_for_cache = ""
    if uid_for_cache:
        _invalidate(uid_for_cache)

    await db.billing_events.update_one(
        {"stripe_event_id": stripe_event_id},
        {"$set": {"status": "COMPLETED", "processed": True,
                  "processed_at": datetime.now(timezone.utc).isoformat()}},
    )
    try:
        from services.realtime import manager
        await manager.broadcast_admin({"type": "payment_received", "stripe_event_type": event_type})
    except Exception:
        pass
    return {"received": True}


async def _dispatch_event(db, event_type: str, obj: dict, stripe_event_id: str) -> None:
    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        user_id = await _resolve_user_id(db, obj)
        md = obj.get("metadata") or {}
        if not user_id:
            logger.warning("[billing/webhook] checkout session %s without user", obj.get("id"))
            return
        if md.get("kind") == "credit_pack":
            await _fulfil_credit_pack(db, obj, user_id, stripe_event_id)
        elif md.get("plan_code") and event_type == "checkout.session.completed":
            # Access is granted by customer.subscription.* / invoice.paid, not here.
            await record_subscription_transition(
                user_id=user_id, from_plan=None, to_plan=md["plan_code"],
                reason="checkout.session.completed",
                stripe_subscription_id=obj.get("subscription", "") or "", metadata=md,
            )

    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        await _handle_subscription_change(db, obj, event_type, stripe_event_id)

    elif event_type == "customer.subscription.deleted":
        sub_id = obj.get("id", "")
        user_id = await _resolve_user_id(db, obj, subscription_id=sub_id)
        local = await db.subscriptions.find_one({"stripe_subscription_id": sub_id}) if sub_id else None
        if sub_id:
            await db.subscriptions.update_one(
                {"stripe_subscription_id": sub_id},
                {"$set": {"status": "expired", "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
        if user_id:
            plan_code, _ = _resolve_plan(_sub_price_id(obj), obj.get("metadata") or {})
            await _end_subscription(db, user_id, plan_code or (local or {}).get("plan_code"),
                                    sub_id, "canceled", "customer.subscription.deleted")

    elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
        await _handle_invoice_paid(db, obj, stripe_event_id)

    elif event_type == "invoice.payment_failed":
        sub_id = _invoice_subscription_id(obj)
        user_id = await _resolve_user_id(db, obj, subscription_id=sub_id)
        if not user_id:
            return
        await record_billing_event(
            user_id=user_id, kind="invoice", status="payment_failed",
            amount_eur=(obj.get("amount_due", 0) or 0) / 100.0,
            currency=obj.get("currency", "eur"), stripe_event_id=stripe_event_id,
            description="Invoice payment failed", metadata={"invoice_id": obj.get("id", "")},
        )
        # Grace state: access continues while Stripe retries the payment.
        q = {"stripe_subscription_id": sub_id} if sub_id else {"user_id": user_id}
        await db.subscriptions.update_many({**q, "status": "active"}, {"$set": {
            "status": "past_due", "updated_at": datetime.now(timezone.utc).isoformat()}})
        await db.users.update_one({"_id": ObjectId(user_id), "plan_code": {"$ne": "free"}},
                                  {"$set": {"subscription_status": "past_due"}})
        await db.notifications.insert_one({
            "user_id": user_id, "type": "payment_failed",
            "title": "Payment failed",
            "body": "We couldn't process your subscription payment. Update your payment method to keep access.",
            "action_url": "/billing", "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"invoice_id": obj.get("id", "")},
        })
        await _track(user_id, "subscription_payment_failed", {"invoice_id": obj.get("id", "")})

    elif event_type == "customer.subscription.trial_will_end":
        sub_id = obj.get("id")
        user_id = await _resolve_user_id(db, obj, subscription_id=sub_id or "")
        if user_id:
            await db.notifications.insert_one({
                "user_id": user_id, "type": "trial_ending",
                "title": "Your trial ends soon",
                "body": "Your Synaptiq trial period ends in 3 days. Add a payment method to keep access.",
                "action_url": "/billing", "read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"stripe_subscription_id": sub_id, "trial_end": obj.get("trial_end")},
            })

    elif event_type == "charge.refunded":
        user_id = await _resolve_user_id(db, obj)
        await _handle_pack_refund(db, obj, user_id)
        if user_id:
            await record_billing_event(
                user_id=user_id, kind="refund", status="refunded",
                amount_eur=(obj.get("amount_refunded", 0) or 0) / 100.0,
                currency=obj.get("currency", "eur"), stripe_event_id=stripe_event_id,
                description=f"Refund processed (charge {obj.get('id', '')})",
                metadata={"charge_id": obj.get("id", "")},
            )

    elif event_type == "charge.dispute.created":
        # Logged for admin review — never auto-actioned.
        await db.billing_disputes.insert_one({
            "stripe_dispute_id": obj.get("id", ""), "charge_id": obj.get("charge", ""),
            "user_id": (obj.get("metadata") or {}).get("user_id", ""),
            "status": obj.get("status", "needs_response"), "reason": obj.get("reason", ""),
            "amount": (obj.get("amount", 0) or 0) / 100.0, "currency": obj.get("currency", "eur"),
            "stripe_event_id": stripe_event_id,
            "created_at": datetime.now(timezone.utc).isoformat(), "resolved": False,
        })
        logger.warning("[billing/webhook] dispute opened charge=%s dispute=%s reason=%s",
                       obj.get("charge"), obj.get("id"), obj.get("reason"))

    elif event_type == "invoice.payment_action_required":
        user_id = await _resolve_user_id(db, obj, subscription_id=_invoice_subscription_id(obj))
        if user_id:
            await db.notifications.insert_one({
                "user_id": user_id, "type": "payment_action_required",
                "title": "Payment authentication required",
                "body": "Your payment requires additional authentication. Please complete it to keep your subscription active.",
                "action_url": obj.get("hosted_invoice_url", "") or "/billing", "read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"invoice_id": obj.get("id", "")},
            })
