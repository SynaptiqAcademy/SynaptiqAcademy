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


def stripe_mode() -> str:
    """'test' (default) or 'live'. TEST and LIVE are separated by configuration
    only: the same code runs with test keys + test price ids, or live keys +
    live price ids. A key that doesn't match the declared mode is refused."""
    return "live" if os.environ.get("STRIPE_MODE", "test").strip().lower() == "live" else "test"


def _key_matches_mode(key: str) -> bool:
    prefixes = ("sk_live_", "rk_live_") if stripe_mode() == "live" else ("sk_test_", "rk_test_")
    return key.startswith(prefixes)


def is_configured() -> bool:
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        return False
    if not _key_matches_mode(key):
        import logging
        logging.getLogger("synaptiq.stripe").error(
            "STRIPE_SECRET_KEY does not match STRIPE_MODE=%s — Stripe disabled (fail closed)", stripe_mode())
        return False
    return True


def checkout_ready() -> bool:
    """True only when a purchase can be completed AND fulfilled: a valid
    secret key for the configured mode plus a webhook signing secret. Without
    the webhook secret, Stripe would take payment but no subscription or
    credit grant could ever be applied, so checkout must stay closed."""
    return is_configured() and bool(os.environ.get("STRIPE_WEBHOOK_SECRET", ""))


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
    customer_id: str = "",
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
        client_reference_id=user_id,
        line_items=[{"price": stripe_price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=sub_metadata,
        subscription_data={"metadata": sub_metadata},
        allow_promotion_codes=True,
    )
    # Reuse the user's Stripe customer when known (never match by email alone).
    if customer_id:
        kwargs["customer"] = customer_id
    else:
        kwargs["customer_email"] = user_email
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
    customer_id: str = "",
) -> Optional[dict]:
    """One-time Stripe Checkout for a credit pack.

    Supports Stripe Tax and idempotency keys.
    """
    stripe = _stripe()
    if stripe is None:
        return None

    pack_metadata = {"user_id": user_id, "pack_code": pack_code, "kind": "credit_pack"}
    kwargs: dict = dict(
        mode="payment",
        client_reference_id=user_id,
        line_items=[{"price": stripe_price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=pack_metadata,
        # Copied onto the PaymentIntent/Charge so refunds can be attributed.
        payment_intent_data={"metadata": pack_metadata},
        allow_promotion_codes=False,
    )
    if customer_id:
        kwargs["customer"] = customer_id
    else:
        kwargs["customer_email"] = user_email
        kwargs["customer_creation"] = "always"
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
