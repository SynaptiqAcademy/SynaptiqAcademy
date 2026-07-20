"""APScheduler wrapper for the discovery suite and citation sync.

Distributed-lock safety: only ONE replica runs the scheduler at a time.
The active holder acquires a Redis lock (synaptiq:scheduler:lock) with
a 300-second TTL and renews it every 60 seconds. If the holder crashes,
the lock expires and the next replica that polls takes over within 300 s.

When Redis is unavailable, all replicas fall back to running independently
(same as the original single-instance behavior — acceptable for dev/staging).

Schedules (UTC):
  - journals refresh:      daily at 02:00
  - conferences refresh:   every 6 hours
  - grants refresh:        daily at 04:00
  - citation daily sync:   daily at 05:00  (OpenAlex citation counts)
  - ORCID weekly sync:     Sunday at 03:30 (profile + publications)

Opt-in via env var DISCOVERY_SCHEDULER_ENABLED=1. Default off so dev / CI never
hammer external APIs.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from services.discovery.ingest import run_kind
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.discovery.scheduler")

_scheduler: Optional[AsyncIOScheduler] = None
_lock_renewal_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
_LOCK_KEY = "synaptiq:scheduler:lock"
_LOCK_TTL = 300   # seconds — must be > renewal interval
_LOCK_RENEW = 60  # seconds


def _lock_value() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def is_enabled() -> bool:
    return os.environ.get("DISCOVERY_SCHEDULER_ENABLED") == "1"


async def _try_acquire_lock() -> bool:
    """Return True if this instance should run the scheduler.

    Tries to SET NX the Redis lock. Falls back to True (run anyway)
    when Redis is unavailable so the scheduler still works in single-instance mode.
    """
    from services.redis_client import get_redis
    r = await get_redis()
    if r is None:
        logger.warning(
            "Redis unavailable — scheduler starting without distributed lock "
            "(single-instance mode; acceptable in dev/staging)"
        )
        return True
    acquired = await r.set(_LOCK_KEY, _lock_value(), nx=True, ex=_LOCK_TTL)
    if acquired:
        logger.info("Scheduler distributed lock acquired by %s", _lock_value())
        return True
    holder = await r.get(_LOCK_KEY)
    logger.info(
        "Scheduler lock held by %s — this replica will not run scheduled jobs", holder
    )
    return False


async def _renew_lock() -> None:
    """Background task: renew the Redis lock every LOCK_RENEW seconds."""
    from services.redis_client import get_redis
    val = _lock_value()
    while True:
        await asyncio.sleep(_LOCK_RENEW)
        try:
            r = await get_redis()
            if r is None:
                continue
            holder = await r.get(_LOCK_KEY)
            if holder == val:
                await r.expire(_LOCK_KEY, _LOCK_TTL)
                logger.debug("Scheduler lock renewed by %s", val)
            else:
                # Someone else holds the lock — this replica lost it (shouldn't happen normally)
                logger.warning(
                    "Scheduler lock unexpectedly held by %s (expected %s) — stopping scheduler",
                    holder, val,
                )
                await stop_scheduler()
                return
        except Exception as exc:
            logger.warning("Scheduler lock renewal error: %s", exc)


async def start_scheduler() -> Optional[AsyncIOScheduler]:
    global _scheduler, _lock_renewal_task
    if _scheduler is not None:
        return _scheduler
    if not is_enabled():
        logger.info("Discovery scheduler disabled (set DISCOVERY_SCHEDULER_ENABLED=1 to enable)")
        return None

    if not await _try_acquire_lock():
        return None  # Another replica holds the lock

    s = AsyncIOScheduler(timezone="UTC")
    s.add_job(_journals_job, CronTrigger(hour=2, minute=0), id="journals_refresh", coalesce=True, max_instances=1)
    s.add_job(_conferences_job, IntervalTrigger(hours=6), id="conferences_refresh", coalesce=True, max_instances=1)
    s.add_job(_grants_job, CronTrigger(hour=4, minute=0), id="grants_refresh", coalesce=True, max_instances=1)
    s.add_job(_daily_digest_job, CronTrigger(hour=7, minute=0), id="digest_daily", coalesce=True, max_instances=1)
    s.add_job(_weekly_digest_job, CronTrigger(day_of_week="mon", hour=7, minute=0), id="digest_weekly", coalesce=True, max_instances=1)
    s.add_job(_orcid_weekly_sync_job, CronTrigger(day_of_week="sun", hour=3, minute=30), id="orcid_weekly_sync", coalesce=True, max_instances=1)
    s.add_job(_citation_daily_sync_job, CronTrigger(hour=5, minute=0), id="citation_daily_sync", coalesce=True, max_instances=1)
    s.start()
    _scheduler = s

    _lock_renewal_task = asyncio.create_task(_renew_lock())
    logger.info(
        "Discovery scheduler started: journals 02:00, conferences /6h, grants 04:00, "
        "citations 05:00, ORCID weekly Sun 03:30 (all UTC)"
    )
    return s


async def stop_scheduler() -> None:
    global _scheduler, _lock_renewal_task
    if _lock_renewal_task and not _lock_renewal_task.done():
        _lock_renewal_task.cancel()
        try:
            await _lock_renewal_task
        except asyncio.CancelledError:
            pass
        _lock_renewal_task = None

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

    # Release the distributed lock
    try:
        from services.redis_client import get_redis
        r = await get_redis()
        if r is not None:
            holder = await r.get(_LOCK_KEY)
            if holder == _lock_value():
                await r.delete(_LOCK_KEY)
                logger.info("Scheduler distributed lock released by %s", _lock_value())
    except Exception as exc:
        logger.warning("Failed to release scheduler lock: %s", exc)


# ------------------------------ job bodies -----------------------------------

async def _journals_job():
    logger.info("[scheduler] journals refresh starting")
    await run_kind("journal", providers=["openalex"], max_records_per_source=2000,
                   max_wall_seconds_per_source=180)


async def _conferences_job():
    logger.info("[scheduler] conferences refresh starting")
    await run_kind("conference", providers=["wikicfp"], max_records_per_source=1000,
                   max_wall_seconds_per_source=180)


async def _grants_job():
    logger.info("[scheduler] grants refresh starting")
    await run_kind("grant", providers=["nih", "ukri", "openaire"],
                   max_records_per_source=1000, max_wall_seconds_per_source=180)


async def _daily_digest_job():
    from routers.assistant import _send_digests
    logger.info("[scheduler] daily digest starting")
    await _send_digests("daily")


async def _weekly_digest_job():
    from routers.assistant import _send_digests
    logger.info("[scheduler] weekly digest starting")
    await _send_digests("weekly")


async def _orcid_weekly_sync_job():
    """Weekly: re-pull each connected user's ORCID record + enrich via OpenAlex."""
    from db import get_db
    from services.orcid.sync import sync_user, enrich_publications_with_openalex
    from services.orcid.oauth import is_configured, get_valid_access_token
    if not is_configured():
        logger.info("[scheduler] ORCID weekly sync skipped — credentials not configured")
        return
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    users = await db.users.find(
        {"orcid.orcid_id": {"$exists": True, "$ne": None}}, {"_id": 1}
    ).to_list(2000)
    logger.info("[scheduler] ORCID weekly sync: %d users", len(users))
    for u in users:
        uid = str(u["_id"])
        try:
            await get_valid_access_token(db, uid)
            await sync_user(uid, trigger="weekly")
            await enrich_publications_with_openalex(uid)
        except Exception as e:
            logger.warning("ORCID weekly sync failed for %s: %s", u["_id"], e)


async def _citation_daily_sync_job():
    """Daily: sync OpenAlex citation counts for all users who have publications."""
    from db import get_db
    from services.citations.sync_service import sync_user_citations

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await db.publications.distinct("owner_id")
    logger.info("[scheduler] Citation daily sync: %d users with publications", len(user_ids))

    for uid in user_ids:
        try:
            stats = await sync_user_citations(db, uid, inter_pub_delay=0.2)
            logger.info(
                "[scheduler] Citation sync user %s: synced=%s errors=%s new_citations=%s alerts=%s",
                uid, stats["synced"], stats["errors"],
                stats["new_citations"], stats["alerts_created"],
            )
        except Exception as e:
            logger.warning("[scheduler] Citation sync failed for user %s: %s", uid, e)
        await asyncio.sleep(2.0)  # 2-second gap between users (OpenAlex polite-pool)
