"""APScheduler wrapper for the discovery suite, digests and citation sync.

Exactly one process runs these jobs, however many gunicorn workers and
replicas exist. Coordination is on MongoDB (services/coordination.py), which
every process shares — Redis is not required:

  * Every process runs a small election loop. The process holding the
    "discovery-scheduler" lease starts APScheduler and renews the lease every
    LEASE_RENEW seconds. Others retry every LEASE_RENEW seconds, so if the
    holder dies its lease expires (LEASE_TTL) and another process takes over.
  * Each job run additionally claims "<job>:<window>" (daily, ISO-week or
    6-hour window) before running, so even two schedulers running at the same
    moment — a lease handover, a clock skew — cannot send the same digest
    emails twice or repeat an import.

Schedules (UTC):
  - journals refresh:      daily at 02:00
  - conferences refresh:   every 6 hours
  - grants refresh:        daily at 04:00
  - citation daily sync:   daily at 05:00  (OpenAlex citation counts)
  - ORCID weekly sync:     Sunday at 03:30 (profile + publications)
  - digests:               daily 07:00, weekly Monday 07:00

Opt-in via env var DISCOVERY_SCHEDULER_ENABLED=1. Default off so dev / CI never
hammer external APIs.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from services.discovery.ingest import run_kind
from services.coordination import (
    LeaseLock, run_once, day_window, iso_week_window, hour_window, ensure_indexes as _ensure_coord,
)
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.discovery.scheduler")

LEASE_NAME = "discovery-scheduler"
LEASE_TTL = 300    # seconds — must exceed LEASE_RENEW comfortably
LEASE_RENEW = 60   # seconds

_scheduler: Optional[AsyncIOScheduler] = None
_election_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
_lease: Optional[LeaseLock] = None


def is_enabled() -> bool:
    return os.environ.get("DISCOVERY_SCHEDULER_ENABLED") == "1"


def _build_scheduler() -> AsyncIOScheduler:
    s = AsyncIOScheduler(timezone="UTC")
    s.add_job(_journals_job, CronTrigger(hour=2, minute=0), id="journals_refresh", coalesce=True, max_instances=1)
    s.add_job(_conferences_job, IntervalTrigger(hours=6), id="conferences_refresh", coalesce=True, max_instances=1)
    s.add_job(_grants_job, CronTrigger(hour=4, minute=0), id="grants_refresh", coalesce=True, max_instances=1)
    s.add_job(_daily_digest_job, CronTrigger(hour=7, minute=0), id="digest_daily", coalesce=True, max_instances=1)
    s.add_job(_weekly_digest_job, CronTrigger(day_of_week="mon", hour=7, minute=0), id="digest_weekly", coalesce=True, max_instances=1)
    s.add_job(_orcid_weekly_sync_job, CronTrigger(day_of_week="sun", hour=3, minute=30), id="orcid_weekly_sync", coalesce=True, max_instances=1)
    s.add_job(_citation_daily_sync_job, CronTrigger(hour=5, minute=0), id="citation_daily_sync", coalesce=True, max_instances=1)
    return s


async def _election_loop() -> None:
    """Hold the lease and run the scheduler while holding it; otherwise keep
    trying, so a crashed holder is replaced within LEASE_TTL."""
    global _scheduler
    while True:
        try:
            held = await _lease.acquire()
        except Exception as exc:
            logger.warning("Scheduler lease check failed (%s) — will retry", type(exc).__name__)
            held = False
        if held and _scheduler is None:
            _scheduler = _build_scheduler()
            _scheduler.start()
            logger.info("Discovery scheduler started in %s (lease holder)", _lease.holder)
        elif not held and _scheduler is not None:
            logger.warning("Discovery scheduler lease lost by %s — stopping jobs here", _lease.holder)
            _scheduler.shutdown(wait=False)
            _scheduler = None
        await asyncio.sleep(LEASE_RENEW)


async def start_scheduler() -> Optional[asyncio.Task]:  # type: ignore[type-arg]
    """Start this process's election loop (idempotent)."""
    global _election_task, _lease
    if _election_task is not None and not _election_task.done():
        return _election_task
    if not is_enabled():
        logger.info("Discovery scheduler disabled (set DISCOVERY_SCHEDULER_ENABLED=1 to enable)")
        return None
    await _ensure_coord()
    _lease = LeaseLock(LEASE_NAME, ttl_seconds=LEASE_TTL)
    _election_task = asyncio.create_task(_election_loop())
    return _election_task


async def stop_scheduler() -> None:
    global _scheduler, _election_task
    if _election_task and not _election_task.done():
        _election_task.cancel()
        try:
            await _election_task
        except asyncio.CancelledError:
            pass
    _election_task = None
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    if _lease is not None:
        try:
            await _lease.release()
        except Exception as exc:
            logger.warning("Failed to release scheduler lease: %s", type(exc).__name__)


def is_running_here() -> bool:
    return _scheduler is not None


# ------------------------------ job bodies -----------------------------------

async def _journals_job():
    await run_once("journals_refresh", day_window(), _journals_body)


async def _journals_body():
    logger.info("[scheduler] journals refresh starting")
    await run_kind("journal", providers=["openalex"], max_records_per_source=2000,
                   max_wall_seconds_per_source=180)


async def _conferences_job():
    await run_once("conferences_refresh", hour_window(every_hours=6), _conferences_body)


async def _conferences_body():
    logger.info("[scheduler] conferences refresh starting")
    await run_kind("conference", providers=["wikicfp"], max_records_per_source=1000,
                   max_wall_seconds_per_source=180)


async def _grants_job():
    await run_once("grants_refresh", day_window(), _grants_body)


async def _grants_body():
    logger.info("[scheduler] grants refresh starting")
    await run_kind("grant", providers=["nih", "ukri", "openaire"],
                   max_records_per_source=1000, max_wall_seconds_per_source=180)


async def _daily_digest_job():
    """Emails users: claimed per UTC day so it can never be sent twice."""
    from routers.assistant import _send_digests
    logger.info("[scheduler] daily digest starting")
    await run_once("digest_daily", day_window(), lambda: _send_digests("daily"))


async def _weekly_digest_job():
    """Emails users: claimed per ISO week so it can never be sent twice."""
    from routers.assistant import _send_digests
    logger.info("[scheduler] weekly digest starting")
    await run_once("digest_weekly", iso_week_window(), lambda: _send_digests("weekly"))


async def _orcid_weekly_sync_job():
    await run_once("orcid_weekly_sync", iso_week_window(), _orcid_weekly_sync_body)


async def _orcid_weekly_sync_body():
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
    await run_once("citation_daily_sync", day_window(), _citation_daily_sync_body)


async def _citation_daily_sync_body():
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
