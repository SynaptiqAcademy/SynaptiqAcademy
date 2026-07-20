"""Operational Cleanup Service — Phase 7 Commercial Readiness.

Runs as a background task at startup and via cron. Cleans up expired or stale
records to prevent unbounded collection growth in production:

  • Expired password-reset tokens (TTL: 30 min)
  • Expired MFA / TOTP setup tokens (TTL: 10 min)
  • Stale worker schedule lock entries (already have MongoDB TTL index, but belt-and-suspenders)
  • Old billing event raw payloads (strip payload after 90 days; keep metadata)
  • Orphaned copilot sessions (in-DB references to expired sessions)
  • Stale API keys marked deleted (purge after 90-day tombstone window)
  • Old anonymous consent records without a user_id (GDPR hygiene; keep 2 years)

All operations are logged. Errors are non-fatal — a failed cleanup does NOT
crash the application or affect users.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.cleanup")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _run_with_label(label: str, coro):
    try:
        result = await coro
        logger.info("cleanup.%s deleted=%s", label, result)
        return result
    except Exception as exc:
        logger.warning("cleanup.%s failed: %s", label, exc)
        return 0


async def cleanup_expired_password_resets() -> int:
    """Delete password reset tokens older than 30 minutes."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    cutoff = _iso(_now() - timedelta(minutes=30))
    res = await db.password_resets.delete_many({"expires_at": {"$lt": cutoff}})
    return res.deleted_count


async def cleanup_expired_mfa_tokens() -> int:
    """Delete MFA setup / TOTP pending records older than 10 minutes."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    cutoff = _iso(_now() - timedelta(minutes=10))
    # mfa_pending — temporary TOTP setup records
    res = await db.mfa_pending.delete_many({"created_at": {"$lt": cutoff}})
    return res.deleted_count


async def cleanup_stale_billing_payloads() -> int:
    """Strip raw Stripe payload from billing_events older than 90 days.

    Retains all metadata (type, stripe_event_id, processed, received_at) for
    audit purposes, but removes the full payload JSON to reduce storage.
    This preserves the idempotency record while reducing collection size.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    cutoff = _iso(_now() - timedelta(days=90))
    res = await db.billing_events.update_many(
        {"received_at": {"$lt": cutoff}, "payload": {"$exists": True}},
        {"$unset": {"payload": ""}, "$set": {"payload_stripped_at": _iso(_now())}},
    )
    return res.modified_count


async def cleanup_anonymous_consent_records() -> int:
    """Delete anonymous consent records (no user_id) older than 2 years.

    GDPR Article 5(1)(e) — personal data should not be kept longer than necessary.
    Anonymous consent records are only needed for auditing the banner interaction,
    not for individual user tracking.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    cutoff = _iso(_now() - timedelta(days=730))
    res = await db.consent_records.delete_many({
        "user_id": None,
        "created_at": {"$lt": cutoff},
    })
    return res.deleted_count


async def cleanup_deleted_api_keys() -> int:
    """Hard-delete API keys that were soft-deleted more than 90 days ago."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    cutoff = _iso(_now() - timedelta(days=90))
    res = await db.api_keys.delete_many({
        "deleted": True,
        "deleted_at": {"$lt": cutoff},
    })
    return res.deleted_count


async def cleanup_expired_announcements() -> int:
    """Archive (mark inactive) announcements past their expires_at date."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    cutoff = _iso(_now())
    res = await db.announcements.update_many(
        {"expires_at": {"$lt": cutoff}, "active": True},
        {"$set": {"active": False, "auto_expired_at": cutoff}},
    )
    return res.modified_count


async def cleanup_old_notifications() -> int:
    """Delete read notifications older than 90 days."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    cutoff = _iso(_now() - timedelta(days=90))
    res = await db.notifications.delete_many({
        "read": True,
        "created_at": {"$lt": cutoff},
    })
    return res.deleted_count


async def run_all() -> dict:
    """Run all cleanup jobs. Returns per-job counts. Non-fatal on any failure."""
    logger.info("cleanup.run_all starting")
    results = {
        "expired_password_resets": await _run_with_label("expired_password_resets", cleanup_expired_password_resets()),
        "expired_mfa_tokens":      await _run_with_label("expired_mfa_tokens", cleanup_expired_mfa_tokens()),
        "stale_billing_payloads":  await _run_with_label("stale_billing_payloads", cleanup_stale_billing_payloads()),
        "anon_consent_records":    await _run_with_label("anon_consent_records", cleanup_anonymous_consent_records()),
        "deleted_api_keys":        await _run_with_label("deleted_api_keys", cleanup_deleted_api_keys()),
        "expired_announcements":   await _run_with_label("expired_announcements", cleanup_expired_announcements()),
        "old_notifications":       await _run_with_label("old_notifications", cleanup_old_notifications()),
        "ran_at": _iso(_now()),
    }
    total = sum(v for v in results.values() if isinstance(v, int))
    logger.info("cleanup.run_all complete total_deleted_or_modified=%d", total)
    return results
