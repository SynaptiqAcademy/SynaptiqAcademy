"""Operational alerts sent to a chat webhook (Slack, Discord, Teams via an
incoming-webhook URL, or any service that accepts {"text": ...}).

Used for events a person must act on: a Stripe webhook that failed to
process, a scheduled job that failed, the database becoming unreachable,
background AI spend reaching its budget, abandoned credit reservations being
released. Uptime (the service not answering at all) is watched from outside by
the uptime monitor — see docs/MONITORING.md.

Delivery is de-duplicated across every worker and replica: an alert with the
same dedup_key is sent at most once per throttle window (MongoDB unique key).
Messages never contain secrets, tokens, personal data or raw exception text —
callers pass a short description and an identifier.

Env:
  ALERT_WEBHOOK_URL   incoming-webhook URL; when unset alerts are only logged
  ALERT_ENVIRONMENT   label added to every message (default: APP_ENV)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

logger = logging.getLogger("synaptiq.alerts")

DELIVERIES = "alert_deliveries"
_SEVERITY_ICON = {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}


def _env_label() -> str:
    return os.environ.get("ALERT_ENVIRONMENT") or os.environ.get("APP_ENV", "development")


async def _claim(dedup_key: str, throttle_minutes: int) -> bool:
    """True when this alert has not been sent in the current throttle window."""
    try:
        from db import get_db, is_db_down
        if is_db_down():
            return True  # cannot de-duplicate; better to send than to stay silent
        now = datetime.now(timezone.utc)
        bucket = int(now.timestamp() // (max(throttle_minutes, 1) * 60))
        await get_db()[DELIVERIES].insert_one({
            "_id": f"{dedup_key}:{bucket}", "dedup_key": dedup_key, "created_at": now,
        })
        return True
    except DuplicateKeyError:
        return False
    except Exception as exc:  # never let alerting break the caller
        logger.warning("alert de-duplication unavailable (%s) — sending anyway", type(exc).__name__)
        return True


async def ensure_indexes() -> None:
    from db import get_db
    await get_db()[DELIVERIES].create_index("created_at", expireAfterSeconds=7 * 86400)


async def send_alert(kind: str, message: str, severity: str = "error",
                     dedup_key: str | None = None, throttle_minutes: int = 30) -> bool:
    """Log the alert and post it to ALERT_WEBHOOK_URL. Returns True if posted."""
    log = logger.error if severity in ("critical", "error") else logger.warning
    log("[alert:%s] %s", kind, message)
    url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    if not url:
        return False
    if not await _claim(dedup_key or f"{kind}:{message}", throttle_minutes):
        return False
    text = f"{_SEVERITY_ICON.get(severity, '•')} [Synaptiq {_env_label()}] {kind}: {message}"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(url, json={"text": text, "content": text})
        if r.status_code >= 300:
            logger.warning("alert webhook answered %s", r.status_code)
            return False
        return True
    except Exception as exc:
        logger.warning("alert webhook delivery failed: %s", type(exc).__name__)
        return False
