"""Operational Cleanup Service — Phase 7 Commercial Readiness.

Runs at startup and then once a day. Cleans up expired or stale
records to prevent unbounded collection growth in production:

  • Expired password-reset tokens (TTL: 30 min)
  • Expired MFA / TOTP setup tokens (TTL: 10 min)
  • Stale worker schedule lock entries (already have MongoDB TTL index, but belt-and-suspenders)
  • Old billing event raw payloads (strip payload after 90 days; keep metadata)
  • Orphaned copilot sessions (in-DB references to expired sessions)
  • Stale API keys marked deleted (purge after 90-day tombstone window)
  • Everything with a period in retention_policy.py (consent records not
    linked to an account, read notifications, email delivery log, the
    automatic data-access audit trail, ...)

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


async def enforce_retention_schedule() -> int:
    """Delete documents older than their period in retention_policy.py
    (purge rules, plus any 'none' rule whose period was switched on by its
    environment variable). Dates may be stored as ISO strings or datetimes,
    so both forms are matched."""
    from retention_policy import purge_rules
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    total = 0
    for rule in purge_rules():
        cutoff = _now() - timedelta(days=rule.effective_days)
        flt = {"$or": [{rule.date_field: {"$lt": _iso(cutoff)}},
                       {rule.date_field: {"$lt": cutoff}}]}
        if rule.query:
            flt = {"$and": [rule.query, flt]}
        try:
            res = await getattr(db, rule.collection).delete_many(flt)
            logger.info("cleanup.retention.%s deleted=%s", rule.key, res.deleted_count)
            total += res.deleted_count
        except Exception as exc:
            logger.warning("cleanup.retention.%s failed: %s", rule.key, exc)
    return total


async def minimise_deletion_audit_records() -> int:
    """Remove the email address of deleted accounts from audit records.
    Earlier versions stored it with the deletion event; a record that an
    account was deleted needs only the account id."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    n = 0
    for coll, field in (("audit_log", "extra.original_email"), ("obs_audit", "extra.original_email"),
                        ("obs_audit", "details.original_email")):
        try:
            res = await getattr(db, coll).update_many({field: {"$exists": True}}, {"$unset": {field: ""}})
            n += res.modified_count
        except Exception as exc:
            logger.warning("cleanup.minimise_audit %s failed: %s", coll, exc)
    return n


async def _sync_discovery_preferences() -> int:
    from services.discovery_preferences import sync_all
    from services.public_profiles.visibility import apply_defaults_to_untouched, retract_unconsented_email
    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    return (await sync_all(db) + await apply_defaults_to_untouched(db)
            + await retract_unconsented_email(db))


_DAILY_STARTED = False
_DAILY_INTERVAL_S = 24 * 3600


def _ensure_daily_schedule() -> None:
    """Re-run every cleanup job once a day for the life of the process, so
    retention is enforced even when the service isn't restarted."""
    global _DAILY_STARTED
    if _DAILY_STARTED:
        return
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _DAILY_STARTED = True

    async def _loop():
        while True:
            await asyncio.sleep(_DAILY_INTERVAL_S)
            try:
                await run_all(schedule=False)
            except Exception as exc:  # never let the loop die
                logger.warning("cleanup.daily failed: %s", exc)

    loop.create_task(_loop())


async def run_all(schedule: bool = True) -> dict:
    """Run all cleanup jobs. Returns per-job counts. Non-fatal on any failure."""
    logger.info("cleanup.run_all starting")
    results = {
        "expired_password_resets": await _run_with_label("expired_password_resets", cleanup_expired_password_resets()),
        "expired_mfa_tokens":      await _run_with_label("expired_mfa_tokens", cleanup_expired_mfa_tokens()),
        "stale_billing_payloads":  await _run_with_label("stale_billing_payloads", cleanup_stale_billing_payloads()),
        "deleted_api_keys":        await _run_with_label("deleted_api_keys", cleanup_deleted_api_keys()),
        "expired_announcements":   await _run_with_label("expired_announcements", cleanup_expired_announcements()),
        "retention_schedule":      await _run_with_label("retention_schedule", enforce_retention_schedule()),
        "minimise_audit_records":  await _run_with_label("minimise_audit_records", minimise_deletion_audit_records()),
        "discovery_preferences":   await _run_with_label("discovery_preferences", _sync_discovery_preferences()),
        "ran_at": _iso(_now()),
    }
    total = sum(v for v in results.values() if isinstance(v, int))
    logger.info("cleanup.run_all complete total_deleted_or_modified=%d", total)
    if schedule:
        _ensure_daily_schedule()
    return results
