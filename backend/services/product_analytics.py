"""Server-side product analytics events (monetization funnel).

Written to the same `session_events` collection the client-side tracker
(routers/growth.py::session_event) uses, so one stream powers the admin
funnel. Server events are authoritative for billing facts (a subscription
starting, credits being exhausted) — the client cannot forge them.
Best-effort: never raises into the caller.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.product_analytics")

SERVER_EVENTS = frozenset({
    "subscription_started", "subscription_upgraded", "subscription_downgraded",
    "subscription_cancelled", "subscription_renewed", "subscription_payment_failed",
    "credits_exhausted", "credit_pack_purchased",
    "ai_operation_started", "ai_operation_completed", "ai_operation_failed",
    "paid_feature_attempted",
})

# Events the browser may send to POST /api/session/event.
CLIENT_MONETIZATION_EVENTS = frozenset({
    "pricing_viewed", "upgrade_clicked", "paid_feature_attempted", "paywall_viewed",
    "checkout_started", "credit_pack_viewed", "credit_pack_checkout_started",
})


async def track_server_event(user_id: str | None, event: str, properties: dict | None = None) -> None:
    if event not in SERVER_EVENTS:
        logger.warning("track_server_event: unknown event %s ignored", event)
        return
    try:
        db = DBProxy(get_db(), SecurityContext.system())
        await db.session_events.insert_one({
            "user_id": user_id,
            "event": event,
            "source": "server",
            "feature": (properties or {}).get("feature"),
            "metadata": properties or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.warning("track_server_event failed (non-blocking): %s", exc)
