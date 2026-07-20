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
    PLANS, get_plan, get_plan_by_price_id, CREDIT_PACKS, get_credit_pack,
    CREDIT_USAGE_DISPLAY, FEATURE_MATRIX, CREDIT_COSTS,
)
from services import stripe_service
from services.credits_service import ensure_user_credits, grant_pack_credits
from services.billing_history_service import (
    record_billing_event, record_subscription_transition,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _safe_plan(p: dict) -> dict:
    """Public-safe plan dict (strips internal stripe price ids)."""
    return {
        "code": p["code"],
        "name": p["name"],
        "tagline": p.get("tagline", ""),
        "price_eur_monthly": p["price_eur_monthly"],
        "price_eur_annual": p["price_eur_annual"],
        "future_price_eur_monthly": p.get("future_price_eur_monthly"),
        "badge": p.get("badge"),
        "credits_per_month": p["credits_per_month"],
        "limits": p["limits"],
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
    """Public list of credit packs (one-time purchases that never expire)."""
    return [{"code": p["code"], "credits": p["credits"], "price_eur": p["price_eur"],
             "label": p["label"]} for p in CREDIT_PACKS]


@router.get("/credit-usage-catalogue")
async def credit_usage_catalogue():
    """Per-action credit cost display (Research Credit Usage section on pricing)."""
    return {"display": CREDIT_USAGE_DISPLAY, "costs": CREDIT_COSTS}


@router.get("/feature-matrix")
async def feature_matrix():
    """Feature comparison matrix for the pricing page."""
    return {
        "columns": ["free", "researcher", "pro_researcher", "institution", "enterprise"],
        "rows": [
            {"label": r[0], "values": list(r[1:])} for r in FEATURE_MATRIX
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

VALID_PAID_PLANS = {"researcher", "pro_researcher", "institution", "enterprise"}


@router.post("/checkout-session")
async def create_checkout(body: dict, user: dict = Depends(get_current_user)):
    """Subscription Stripe Checkout."""
    plan_code = body.get("plan_code")
    billing_period = body.get("billing_period", "monthly")
    if plan_code not in VALID_PAID_PLANS:
        raise HTTPException(status_code=400,
                            detail=f"Invalid plan_code (use one of {sorted(VALID_PAID_PLANS)}).")
    if billing_period not in {"monthly", "annual"}:
        raise HTTPException(status_code=400, detail="Invalid billing_period.")

    plan = get_plan(plan_code)
    price_key = "stripe_price_id_monthly" if billing_period == "monthly" else "stripe_price_id_annual"
    price_id = plan.get(price_key) or ""

    if not stripe_service.is_configured() or not price_id:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Stripe is not yet configured for this environment.",
                "next_step": "Set STRIPE_SECRET_KEY plus the plan's stripe_price_id_monthly/annual to activate.",
                "plan_code": plan_code,
                "billing_period": billing_period,
            },
        )

    result = stripe_service.create_checkout_session(
        user_email=user["email"],
        user_id=user["id"],
        plan_code=plan_code,
        billing_period=billing_period,
        success_url=body.get("success_url") or "",
        cancel_url=body.get("cancel_url") or "",
        stripe_price_id=price_id,
    )
    if result is None:
        raise HTTPException(status_code=503, detail="Stripe SDK unavailable.")
    return result


@router.post("/credit-pack-checkout")
async def create_credit_pack_checkout(body: dict, user: dict = Depends(get_current_user)):
    """One-time Stripe Checkout for a credit pack. Auth required (anyone, even Free users)."""
    pack_code = body.get("pack_code")
    pack = get_credit_pack(pack_code)
    if not pack:
        raise HTTPException(status_code=400, detail=f"Unknown pack_code: {pack_code}")

    if not stripe_service.is_configured() or not pack.get("stripe_price_id"):
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Stripe is not yet configured for credit-pack purchases.",
                "next_step": "Set STRIPE_SECRET_KEY plus stripe_price_id on the pack to activate.",
                "pack_code": pack_code,
            },
        )

    result = stripe_service.create_credit_pack_checkout_session(
        user_email=user["email"],
        user_id=user["id"],
        pack_code=pack_code,
        credits=pack["credits"],
        success_url=body.get("success_url") or "",
        cancel_url=body.get("cancel_url") or "",
        stripe_price_id=pack["stripe_price_id"],
    )
    if result is None:
        raise HTTPException(status_code=503, detail="Stripe SDK unavailable.")
    return result


@router.post("/portal-session")
async def create_portal(body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    sub = await db.subscriptions.find_one({"user_id": user["id"]})
    customer_id = (sub or {}).get("stripe_customer_id", "")
    if not stripe_service.is_configured() or not customer_id:
        raise HTTPException(
            status_code=503,
            detail={"message": "Billing portal unavailable until Stripe is configured and a subscription exists."},
        )
    url = stripe_service.create_billing_portal_session(customer_id, body.get("return_url") or "")
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
        # Stripe not configured — acknowledge so Stripe doesn't retry, but do not process.
        logger.warning("[billing/webhook] STRIPE_WEBHOOK_SECRET not set — event discarded (not processed).")
        return {"received": True, "processed": False}

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

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    event_type = payload.get("type", "unknown")
    stripe_event_id = payload.get("id", "")

    # ── Idempotency guard ──────────────────────────────────────────────────────
    # Stripe retries failed webhook deliveries for up to 72 hours.
    # A unique index on billing_events.stripe_event_id (created at startup) makes
    # the insert fail on duplicates; we catch the E11000 and return early so
    # credit grants / plan changes are never applied twice.
    if stripe_event_id:
        try:
            await db.billing_events.insert_one({
                "stripe_event_id": stripe_event_id,
                "type": event_type,
                "payload": payload,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "processed": False,
            })
        except Exception as dup_exc:
            if "E11000" in str(dup_exc) or "duplicate key" in str(dup_exc).lower():
                logger.info("[billing/webhook] duplicate event %s ignored (idempotency)", stripe_event_id)
                return {"received": True, "processed": False, "reason": "duplicate"}
            raise
    else:
        await db.billing_events.insert_one({
            "type": event_type,
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
        })

    try:
        from services.realtime import manager
        await manager.broadcast_admin({"type": "payment_received", "stripe_event_type": event_type})
    except Exception:
        pass

    # Best-effort idempotent handlers (run only when the relevant fields are present).
    obj = (payload.get("data") or {}).get("object") or {}
    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id")

    if event_type == "checkout.session.completed" and user_id:
        kind = metadata.get("kind")
        if kind == "credit_pack":
            pack_code = metadata.get("pack_code", "")
            try:
                credits = int(metadata.get("credits", "0"))
            except ValueError:
                credits = 0
            if credits > 0:
                await grant_pack_credits(
                    user_id, pack_code=pack_code, credits=credits,
                    stripe_checkout_session_id=obj.get("id", ""),
                    stripe_payment_intent_id=obj.get("payment_intent", "") or "",
                )
                await record_billing_event(
                    user_id=user_id, kind="pack_purchase",
                    amount_eur=(obj.get("amount_total", 0) or 0) / 100.0,
                    currency=obj.get("currency", "eur"),
                    status="paid",
                    stripe_event_id=payload.get("id", ""),
                    description=f"Credit pack purchase: {pack_code}",
                    metadata={"pack_code": pack_code, "credits": credits},
                )
        elif metadata.get("plan_code"):
            # Subscription checkout — Stripe will follow up with subscription.created
            await record_subscription_transition(
                user_id=user_id, from_plan=None, to_plan=metadata["plan_code"],
                reason="checkout.session.completed",
                stripe_subscription_id=obj.get("subscription", "") or "",
                metadata=metadata,
            )

    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        # Persist/update local subscription record
        sub_id = obj.get("id")
        status = obj.get("status")
        customer = obj.get("customer", "")
        # Try to recover user_id from metadata or from items->plan->metadata
        if not user_id:
            user_id = (obj.get("metadata") or {}).get("user_id", "")
        billing_period = (obj.get("metadata") or {}).get("billing_period", "monthly")

        # Resolve which plan this subscription is for — prefer metadata (set via
        # subscription_data.metadata at checkout), fall back to matching the
        # subscription's Stripe price id against the plan catalogue. Without this,
        # a confirmed Stripe payment would never actually upgrade the user's
        # plan_code/credits (the subscriptions collection and users collection
        # would silently disagree about what plan the user is on).
        resolved_plan_code = (obj.get("metadata") or {}).get("plan_code")
        price_id = ((obj.get("items") or {}).get("data") or [{}])[0].get("price", {}).get("id", "")
        if not resolved_plan_code:
            match = get_plan_by_price_id(price_id)
            if match:
                resolved_plan_code, billing_period = match

        if sub_id:
            await db.subscriptions.update_one(
                {"stripe_subscription_id": sub_id},
                {"$set": {
                    "stripe_subscription_id": sub_id,
                    "stripe_customer_id": customer,
                    "user_id": user_id or "",
                    "plan_code": resolved_plan_code,
                    "billing_period": billing_period,
                    "status": status,
                    "current_period_end": obj.get("current_period_end"),
                    "cancel_at_period_end": obj.get("cancel_at_period_end", False),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )

        if user_id and resolved_plan_code and status in ("active", "trialing"):
            current_user = await db.users.find_one({"_id": ObjectId(user_id)})
            prior_plan_code = (current_user or {}).get("plan_code") or "free"
            if prior_plan_code != resolved_plan_code:
                new_plan = get_plan(resolved_plan_code)
                await db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {
                        "plan_code": resolved_plan_code,
                        "credits_balance": new_plan["credits_per_month"],
                        "credits_monthly_allowance": new_plan["credits_per_month"],
                        "credits_reset_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                        "subscription_status": "active",
                    }},
                )
                await record_subscription_transition(
                    user_id=user_id, from_plan=prior_plan_code, to_plan=resolved_plan_code,
                    reason=event_type, stripe_subscription_id=sub_id or "",
                    metadata={"status": status},
                )
            else:
                # Same plan, but sync subscription_status — e.g. a prior
                # invoice.payment_failed marked the user past_due and this
                # renewal/retry succeeded, so clear that flag.
                await db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"subscription_status": "active"}},
                )
        elif user_id and resolved_plan_code and status in ("canceled", "unpaid", "incomplete_expired"):
            # Subscription ended without a replacement — drop back to free.
            current_user = await db.users.find_one({"_id": ObjectId(user_id)})
            if (current_user or {}).get("plan_code") == resolved_plan_code:
                await db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"plan_code": "free", "subscription_status": "expired",
                              "credits_monthly_allowance": get_plan("free")["credits_per_month"]}},
                )
                await record_subscription_transition(
                    user_id=user_id, from_plan=resolved_plan_code, to_plan="free",
                    reason=event_type, stripe_subscription_id=sub_id or "",
                )

        if user_id:
            await record_billing_event(
                user_id=user_id, kind="subscription_event",
                amount_eur=None, status=status,
                stripe_event_id=payload.get("id", ""),
                description=f"Subscription {status}",
                metadata={"stripe_subscription_id": sub_id},
            )

    elif event_type == "invoice.payment_succeeded" and user_id:
        await record_billing_event(
            user_id=user_id, kind="invoice", status="paid",
            amount_eur=(obj.get("amount_paid", 0) or 0) / 100.0,
            currency=obj.get("currency", "eur"),
            stripe_event_id=payload.get("id", ""),
            description=obj.get("description") or "Invoice paid",
            metadata={"invoice_id": obj.get("id", "")},
        )

    elif event_type == "invoice.payment_failed" and user_id:
        await record_billing_event(
            user_id=user_id, kind="invoice", status="payment_failed",
            amount_eur=(obj.get("amount_due", 0) or 0) / 100.0,
            currency=obj.get("currency", "eur"),
            stripe_event_id=payload.get("id", ""),
            description="Invoice payment failed",
            metadata={"invoice_id": obj.get("id", "")},
        )
        # Mark active subs past_due so the UI nudges the user
        await db.subscriptions.update_many(
            {"user_id": user_id, "status": "active"},
            {"$set": {"status": "past_due",
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"subscription_status": "past_due"}},
        )

    elif event_type == "customer.subscription.deleted":
        sub_id = obj.get("id")
        local = await db.subscriptions.find_one({"stripe_subscription_id": sub_id})
        uid = (local or {}).get("user_id") or user_id or ""
        if uid:
            await db.users.update_one(
                {"_id": ObjectId(uid)},
                {"$set": {"plan_code": "free", "subscription_status": "expired"}},
            )
            await record_subscription_transition(
                user_id=uid, from_plan=(local or {}).get("plan_code"), to_plan="free",
                reason="customer.subscription.deleted",
                stripe_subscription_id=sub_id or "",
            )
        if sub_id:
            await db.subscriptions.update_one(
                {"stripe_subscription_id": sub_id},
                {"$set": {"status": "expired",
                          "updated_at": datetime.now(timezone.utc).isoformat()}},
            )

    elif event_type == "customer.subscription.trial_will_end":
        # Trial ends in 3 days — notify user so they can add a payment method.
        sub_id = obj.get("id")
        if not user_id:
            user_id = (obj.get("metadata") or {}).get("user_id", "")
        trial_end = obj.get("trial_end")
        if user_id:
            await db.notifications.insert_one({
                "user_id": user_id,
                "type": "trial_ending",
                "title": "Your trial ends soon",
                "body": "Your Synaptiq trial period ends in 3 days. Add a payment method to keep access.",
                "action_url": "/billing",
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"stripe_subscription_id": sub_id, "trial_end": trial_end},
            })
            await record_billing_event(
                user_id=user_id, kind="trial_ending",
                amount_eur=None, status="trialing",
                stripe_event_id=stripe_event_id,
                description="Trial period ends in 3 days",
                metadata={"stripe_subscription_id": sub_id},
            )

    elif event_type == "charge.refunded":
        # Record refund in billing history and credit any refunded pack balance.
        charge_id = obj.get("id", "")
        amount_refunded = (obj.get("amount_refunded", 0) or 0) / 100.0
        currency = obj.get("currency", "eur")
        if not user_id:
            user_id = (obj.get("metadata") or {}).get("user_id", "")
        if user_id:
            await record_billing_event(
                user_id=user_id, kind="refund", status="refunded",
                amount_eur=amount_refunded, currency=currency,
                stripe_event_id=stripe_event_id,
                description=f"Refund processed (charge {charge_id})",
                metadata={"charge_id": charge_id},
            )

    elif event_type == "charge.dispute.created":
        # Log dispute for admin review — do not auto-action; require manual resolution.
        charge_id = obj.get("charge", "")
        dispute_id = obj.get("id", "")
        if not user_id:
            user_id = (obj.get("metadata") or {}).get("user_id", "")
        await db.billing_disputes.insert_one({
            "stripe_dispute_id": dispute_id,
            "charge_id": charge_id,
            "user_id": user_id or "",
            "status": obj.get("status", "needs_response"),
            "reason": obj.get("reason", ""),
            "amount": (obj.get("amount", 0) or 0) / 100.0,
            "currency": obj.get("currency", "eur"),
            "stripe_event_id": stripe_event_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
        })
        logger.warning(
            "[billing/webhook] dispute opened charge=%s dispute=%s reason=%s",
            charge_id, dispute_id, obj.get("reason"),
        )

    elif event_type == "invoice.payment_action_required" and user_id:
        # 3DS / SCA authentication required — notify user to complete payment.
        invoice_id = obj.get("id", "")
        payment_url = obj.get("hosted_invoice_url", "")
        await db.notifications.insert_one({
            "user_id": user_id,
            "type": "payment_action_required",
            "title": "Payment authentication required",
            "body": "Your payment requires additional authentication. Please complete it to keep your subscription active.",
            "action_url": payment_url or "/billing",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"invoice_id": invoice_id},
        })
        await record_billing_event(
            user_id=user_id, kind="payment_action_required",
            amount_eur=(obj.get("amount_due", 0) or 0) / 100.0,
            currency=obj.get("currency", "eur"),
            stripe_event_id=stripe_event_id,
            description="Payment authentication required (SCA/3DS)",
            metadata={"invoice_id": invoice_id},
        )

    # Mark the event processed (best-effort — non-blocking if it fails)
    if stripe_event_id:
        try:
            await db.billing_events.update_one(
                {"stripe_event_id": stripe_event_id},
                {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc).isoformat()}},
            )
        except Exception:
            pass

    return {"received": True}
