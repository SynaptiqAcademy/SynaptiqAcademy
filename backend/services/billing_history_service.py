"""Billing-history and subscription-history helpers.

These are append-only event logs that power:
  - /api/billing/history — user-facing invoices + subscription events
  - /api/billing/subscription-history — admin-facing state-transition log

The Stripe webhook handler writes to both via `record_billing_event` /
`record_subscription_transition`. UI reads via the routes above.
"""
from datetime import datetime, timezone
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


async def record_billing_event(*, user_id: str, kind: str, amount_eur: float | None = None,
                               currency: str = "eur", status: str = "paid",
                               stripe_event_id: str = "", description: str = "",
                               metadata: dict | None = None):
    """User-visible billing event (invoice, refund, pack purchase, plan change)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.billing_history.insert_one({
        "user_id": user_id,
        "kind": kind,                      # 'invoice' | 'pack_purchase' | 'refund' | 'plan_change'
        "amount_eur": amount_eur,
        "currency": currency,
        "status": status,
        "stripe_event_id": stripe_event_id,
        "description": description,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    })


async def record_subscription_transition(*, user_id: str, from_plan: str | None,
                                          to_plan: str | None, reason: str = "",
                                          stripe_subscription_id: str = "",
                                          metadata: dict | None = None):
    """State-transition log for subscription lifecycle (plan changes, cancellations)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.subscription_history.insert_one({
        "user_id": user_id,
        "from_plan": from_plan,
        "to_plan": to_plan,
        "reason": reason,
        "stripe_subscription_id": stripe_subscription_id,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    })
