"""Stripe-ready architecture. Real Stripe SDK shape, gracefully degrades without keys.

When STRIPE_SECRET_KEY is set, this module activates. Until then, checkout/portal endpoints
return a 503 with a clear message — no mocks, no fake checkout URLs.

Opt-in features (controlled via env vars):
  STRIPE_TAX_ENABLED=1      — enable Stripe Tax (automatic_tax) on all checkout sessions
  STRIPE_IDEMPOTENCY=1      — attach idempotency keys to checkout calls (recommended in prod)
"""
import hashlib
import os
import time
from typing import Optional


def is_configured() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def _tax_enabled() -> bool:
    return os.environ.get("STRIPE_TAX_ENABLED", "").lower() in ("1", "true", "yes")


def _idempotency_enabled() -> bool:
    return os.environ.get("STRIPE_IDEMPOTENCY", "1").lower() not in ("0", "false", "no")


def _idempotency_key(*parts: str) -> str:
    """Idempotency key from user_id + price_id + a 10-minute window.

    Double-clicks and client retries within the window return the same
    Checkout Session (no duplicate sessions); a deliberate new purchase later
    (e.g. a second credit pack) gets a fresh session. A purely deterministic
    key would hand back the first — already completed — session for 24h.
    """
    window = str(int(time.time() // 600))
    raw = ":".join(p for p in (*parts, window) if p)
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def _stripe():
    """Lazy import — Stripe SDK only required when actually enabled."""
    if not is_configured():
        return None
    try:
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        return stripe
    except ImportError:
        return None


def create_checkout_session(
    user_email: str,
    user_id: str,
    plan_code: str,
    billing_period: str,
    success_url: str,
    cancel_url: str,
    stripe_price_id: str,
) -> Optional[dict]:
    """Create a Stripe Checkout Session for a subscription plan.

    Returns None if Stripe is not configured. Caller MUST handle that.
    Supports Stripe Tax (set STRIPE_TAX_ENABLED=1) and idempotency keys.
    """
    stripe = _stripe()
    if stripe is None:
        return None

    # Checkout Session metadata is NOT copied onto the Subscription object by
    # Stripe — subscription_data.metadata must be set explicitly, or the
    # webhook's customer.subscription.created/updated handlers have no
    # metadata to resolve which plan the subscription belongs to.
    sub_metadata = {"user_id": user_id, "plan_code": plan_code, "billing_period": billing_period}
    kwargs: dict = dict(
        mode="subscription",
        customer_email=user_email,
        client_reference_id=user_id,
        line_items=[{"price": stripe_price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=sub_metadata,
        subscription_data={"metadata": sub_metadata},
        allow_promotion_codes=True,
    )
    if _tax_enabled():
        kwargs["automatic_tax"] = {"enabled": True}
        kwargs["tax_id_collection"] = {"enabled": True}

    idempotency_kwargs: dict = {}
    if _idempotency_enabled():
        idempotency_kwargs["idempotency_key"] = _idempotency_key(user_id, stripe_price_id, billing_period)

    session = stripe.checkout.Session.create(**kwargs, **idempotency_kwargs)
    return {"id": session.id, "url": session.url}


def create_credit_pack_checkout_session(
    user_email: str,
    user_id: str,
    pack_code: str,
    credits: int,
    success_url: str,
    cancel_url: str,
    stripe_price_id: str,
) -> Optional[dict]:
    """One-time Stripe Checkout for a credit pack.

    Supports Stripe Tax and idempotency keys.
    """
    stripe = _stripe()
    if stripe is None:
        return None

    kwargs: dict = dict(
        mode="payment",
        customer_email=user_email,
        client_reference_id=user_id,
        line_items=[{"price": stripe_price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user_id, "pack_code": pack_code, "credits": str(credits),
                  "kind": "credit_pack"},
        allow_promotion_codes=True,
    )
    if _tax_enabled():
        kwargs["automatic_tax"] = {"enabled": True}
        kwargs["tax_id_collection"] = {"enabled": True}

    idempotency_kwargs: dict = {}
    if _idempotency_enabled():
        idempotency_kwargs["idempotency_key"] = _idempotency_key(user_id, pack_code, stripe_price_id)

    session = stripe.checkout.Session.create(**kwargs, **idempotency_kwargs)
    return {"id": session.id, "url": session.url}


def change_subscription_plan(stripe_subscription_id: str, *, new_price_id: str,
                             plan_code: str, upgrade: bool) -> Optional[dict]:
    """Switch an existing subscription to another plan's price (no second
    subscription). Upgrades are prorated and invoiced immediately; downgrades
    are prorated as account credit on the next invoice. Credits/plan in our
    DB change only when the resulting customer.subscription.updated webhook
    arrives — never from this call's return value."""
    stripe = _stripe()
    if stripe is None:
        return None
    sub = stripe.Subscription.retrieve(stripe_subscription_id)
    item_id = sub["items"]["data"][0]["id"]
    metadata = dict(sub.get("metadata") or {})
    metadata["plan_code"] = plan_code
    updated = stripe.Subscription.modify(
        stripe_subscription_id,
        items=[{"id": item_id, "price": new_price_id}],
        proration_behavior="always_invoice" if upgrade else "create_prorations",
        cancel_at_period_end=False,
        metadata=metadata,
    )
    return {"id": updated["id"], "status": updated["status"]}


def create_billing_portal_session(customer_id: str, return_url: str) -> Optional[str]:
    stripe = _stripe()
    if stripe is None:
        return None
    portal = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return portal.url


def construct_event(payload: bytes, sig_header: str, webhook_secret: str):
    """Verify and parse a Stripe webhook event. Raises on signature failure."""
    stripe = _stripe()
    if stripe is None:
        return None
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
