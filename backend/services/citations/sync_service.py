"""Citation sync service — pure async functions callable from both HTTP endpoints
and the APScheduler background jobs.

All functions accept a ``db`` object (motor AsyncIOMotorDatabase) and a string
``user_id``. They never touch FastAPI request state.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bson import ObjectId

from services.citations.providers.openalex import OpenAlexProvider

log = logging.getLogger("synaptiq.citations.sync")

MILESTONES = [10, 25, 50, 100, 250, 500, 1_000, 2_500, 5_000, 10_000]

# module-level provider singleton (no state — safe to share)
_provider = OpenAlexProvider()


# ─────────────────────────── time helpers ────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _month_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _current_year() -> int:
    return _now().year


# ─────────────────────────── smart alerts ────────────────────────────────────

def _check_smart_alerts(
    *,
    pub_id:     str,
    title:      str,
    count:      int,
    prev_count: int,
    delta:      int,
    year:       Optional[int],
    now:        datetime,
) -> list[dict]:
    """Generate smart alert dicts for a single publication snapshot."""
    alerts: list[dict] = []
    if delta <= 0:
        return alerts

    # rapid growth: >30% increase in one snapshot
    if prev_count > 0 and delta / prev_count >= 0.30:
        pct = round(delta / prev_count * 100, 1)
        alerts.append({
            "alert_type": "rapid_growth",
            "message":    f"Rapid citation growth: \"{title[:60]}\" gained +{delta} citations ({pct}% increase).",
            "count": count, "delta": delta, "read": False, "created_at": now,
        })

    # emerging: <5 → ≥5 citations
    if prev_count < 5 <= count:
        alerts.append({
            "alert_type": "emerging_topic",
            "message":    f"\"{title[:60]}\" is gaining traction ({count} citations reached).",
            "count": count, "delta": delta, "read": False, "created_at": now,
        })

    # top performer: crossing 50
    if prev_count < 50 <= count:
        alerts.append({
            "alert_type": "top_performer",
            "message":    f"\"{title[:60]}\" reached 50 citations — top performer threshold.",
            "count": count, "delta": delta, "read": False, "created_at": now,
        })

    # high velocity: >20 citations/year
    if year and isinstance(year, int):
        age = max(1, _current_year() - year)
        velocity      = count      / age
        prev_velocity = prev_count / age
        if prev_velocity < 20.0 <= velocity:
            alerts.append({
                "alert_type": "high_velocity",
                "message":    f"\"{title[:60]}\" now accumulates {round(velocity, 1)} citations/year (high velocity).",
                "count": count, "delta": delta, "read": False, "created_at": now,
            })

    return alerts


# ─────────────────────────── snapshot engine ─────────────────────────────────

async def take_snapshot(db, user_id: str) -> dict:
    """Compare current publication citation counts against the last recorded snapshot.

    Creates new ``publication_citations`` records and fires ``citation_alerts``
    for: new citations, milestones, highly-cited, high-velocity, and smart alerts.

    Returns a stats dict: {snapshotted, new_citations, alerts_created}.
    """
    now   = _now()
    month = _month_str(now)
    uid   = user_id

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "doi": 1, "year": 1, "citations": 1},
    ).to_list(2000)

    if not pub_docs:
        return {"snapshotted": 0, "new_citations": 0, "alerts_created": 0}

    total_new        = 0
    alerts_created   = 0
    snaps_to_insert  = []
    alerts_to_insert = []

    for p in pub_docs:
        pub_id = str(p["_id"])
        count  = int(p.get("citations") or 0)
        title  = p.get("title") or "Untitled"
        year   = p.get("year")

        last  = await db.publication_citations.find_one(
            {"user_id": uid, "pub_id": pub_id}, sort=[("created_at", -1)])
        prev  = int((last or {}).get("count", 0))
        delta = max(0, count - prev)
        total_new += delta

        if last is None or count != prev:
            snaps_to_insert.append({
                "user_id":        uid,
                "pub_id":         pub_id,
                "doi":            p.get("doi"),
                "count":          count,
                "prev_count":     prev,
                "delta":          delta,
                "snapshot_month": month,
                "created_at":     now,
            })

        if delta == 0:
            continue

        # new citations
        alerts_to_insert.append({
            "user_id": uid, "pub_id": pub_id, "alert_type": "new_citation",
            "title": title,
            "message": f"+{delta} new citation{'s' if delta > 1 else ''} on \"{title[:60]}\"",
            "count": count, "delta": delta, "created_at": now, "read": False,
        })
        alerts_created += 1

        # milestones
        for ms in MILESTONES:
            if prev < ms <= count:
                alerts_to_insert.append({
                    "user_id": uid, "pub_id": pub_id, "alert_type": "milestone",
                    "title": title,
                    "message": f"\"{title[:60]}\" reached {ms:,} citations!",
                    "count": count, "delta": delta, "milestone_value": ms,
                    "created_at": now, "read": False,
                })
                alerts_created += 1

        # highly cited (only fire once per publication)
        if prev < 100 <= count:
            existing = await db.citation_alerts.find_one(
                {"user_id": uid, "pub_id": pub_id, "alert_type": "highly_cited"})
            if not existing:
                alerts_to_insert.append({
                    "user_id": uid, "pub_id": pub_id, "alert_type": "highly_cited",
                    "title": title,
                    "message": f"\"{title[:60]}\" entered the highly-cited category (100+ citations).",
                    "count": count, "delta": delta, "created_at": now, "read": False,
                })
                alerts_created += 1

        # basic velocity: citations > 10 × age
        if year and isinstance(year, int):
            age = max(1, _current_year() - year)
            if count > 10 * age and prev <= 10 * age:
                alerts_to_insert.append({
                    "user_id": uid, "pub_id": pub_id, "alert_type": "velocity",
                    "title": title,
                    "message": f"\"{title[:60]}\" is a high-velocity paper ({count} cit. in {age} yr{'s' if age > 1 else ''}).",
                    "count": count, "delta": delta, "created_at": now, "read": False,
                })
                alerts_created += 1

        # smart alerts
        for sa in _check_smart_alerts(
            pub_id=pub_id, title=title, count=count,
            prev_count=prev, delta=delta, year=year, now=now,
        ):
            sa.update({"user_id": uid, "pub_id": pub_id, "title": title})
            alerts_to_insert.append(sa)
            alerts_created += 1

    if snaps_to_insert:
        await db.publication_citations.insert_many(snaps_to_insert)
    if alerts_to_insert:
        await db.citation_alerts.insert_many(alerts_to_insert)

    return {
        "snapshotted":    len(snaps_to_insert),
        "new_citations":  total_new,
        "alerts_created": alerts_created,
    }


# ─────────────────────────── OpenAlex sync ───────────────────────────────────

async def _upsert_citing_work(db, *, user_id: str, pub_id: str, cw, now: datetime) -> bool:
    """Upsert a single citing work. Returns True if a new record was created."""
    if not cw.doi:
        return False
    result = await db.citation_sources.update_one(
        {"user_id": user_id, "pub_id": pub_id, "citing_doi": cw.doi},
        {"$setOnInsert": {
            "user_id":        user_id,
            "pub_id":         pub_id,
            "citing_doi":     cw.doi,
            "citing_title":   cw.title,
            "citing_year":    cw.year,
            "citing_journal": cw.journal,
            "source":         "openalex",
            "detected_at":    now.isoformat(),
        }},
        upsert=True,
    )
    return result.upserted_id is not None


async def sync_user_citations(
    db,
    user_id: str,
    *,
    pub_limit: int = 500,
    inter_pub_delay: float = 0.15,
) -> dict:
    """Sync citation data for all of a user's publications via OpenAlex.

    For each publication:
      1. Query OpenAlex by DOI (preferred) or title.
      2. Update citation count + history + concepts + topics + coauthors.
      3. Upsert citing works in ``citation_sources`` (deduped by doi).
      4. Take a citation snapshot and generate alerts.

    ``inter_pub_delay`` (seconds) throttles OpenAlex requests to stay within
    the polite-pool rate limit (≈10 req/s). Default 0.15 s ≈ 6–7 req/s.

    Returns a stats dict: {synced, errors, sources_added, new_citations, alerts_created}.
    """
    uid = user_id
    now = _now()

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "doi": 1, "year": 1, "journal": 1, "openalex_id": 1},
    ).to_list(pub_limit)

    synced = errors = sources_added = 0

    for p in pub_docs:
        pub_id = str(p["_id"])
        doi    = p.get("doi")
        title  = p.get("title")

        try:
            result = await _provider.sync_publication(doi=doi, title=title)
            if not result.found:
                continue

            match  = result.publication
            update: dict = {
                "citations":            match.citation_count,
                "concepts":             match.concepts,
                "topics":               match.topics,
                "coauthors":            match.coauthors,
                "openalex_id":          match.provider_id,
                "counts_by_year":       match.counts_by_year,
                "openalex_enriched_at": now.isoformat(),
                "updated_at":           now.isoformat(),
            }
            if match.doi and not doi:
                update["doi"] = match.doi
            if match.journal and not p.get("journal"):
                update["journal"] = match.journal
            if match.open_access_url:
                update["open_access_url"] = match.open_access_url

            await db.publications.update_one({"_id": p["_id"]}, {"$set": update})
            synced += 1

            # upsert citing works (idempotent on doi)
            for cw in result.citing_works:
                added = await _upsert_citing_work(db, user_id=uid, pub_id=pub_id, cw=cw, now=now)
                if added:
                    sources_added += 1

        except Exception as e:
            log.warning("OpenAlex sync failed for pub %s (user %s): %s", pub_id, uid, e)
            errors += 1

        if inter_pub_delay > 0:
            await asyncio.sleep(inter_pub_delay)

    # snapshot after all publications updated
    snap = await take_snapshot(db, uid)

    return {
        "synced":         synced,
        "errors":         errors,
        "sources_added":  sources_added,
        "new_citations":  snap.get("new_citations", 0),
        "alerts_created": snap.get("alerts_created", 0),
    }


# ─────────────────────────── ORCID import pipeline ───────────────────────────

async def import_orcid_publications(
    db,
    user_id:      str,
    orcid_id:     str,
    access_token: str,
    orcid_api_base: str = "https://pub.orcid.org/v3.0",
) -> dict:
    """Fetch works from ORCID, deduplicate, insert into publications, enrich via OpenAlex.

    Returns stats: {imported, duplicates, enriched, snapshotted, alerts_created, new_citations}.
    """
    from services.orcid.sync import enrich_publications_with_openalex

    uid = user_id
    now = _now()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept":        "application/vnd.orcid+json",
    }

    imported = errors = duplicates = 0

    WORK_TYPE_MAP = {
        "journal-article":  "journal_article",
        "conference-paper": "conference_paper",
        "book":             "book",
        "book-chapter":     "book_chapter",
        "preprint":         "preprint",
        "review":           "review",
    }

    try:
        async with httpx.AsyncClient(timeout=20, headers=headers) as cli:
            r = await cli.get(f"{orcid_api_base}/{orcid_id}/works")
            if r.status_code != 200:
                raise RuntimeError(f"ORCID API returned {r.status_code}")
            groups = (r.json().get("group") or [])

        for group in groups:
            work_summaries = group.get("work-summary") or []
            if not work_summaries:
                continue
            ws = work_summaries[0]  # canonical / most recent

            # extract DOI
            doi = None
            for eid in ((ws.get("external-ids") or {}).get("external-id") or []):
                if (eid.get("external-id-type") or "").lower() == "doi":
                    doi = (eid.get("external-id-value") or "").strip().lower()
                    if doi.startswith("http"):
                        doi = doi.split("doi.org/", 1)[-1]
                    break

            title_raw = (ws.get("title") or {}).get("title") or {}
            title     = title_raw.get("value") or "Untitled"
            year_raw  = (ws.get("publication-date") or {}).get("year") or {}
            year      = int(year_raw.get("value") or 0) or None

            jt = ws.get("journal-title")
            journal = jt.get("value") if isinstance(jt, dict) else jt

            wtype     = ws.get("type") or "other"
            norm_type = WORK_TYPE_MAP.get(wtype, wtype.replace("-", "_"))
            title_norm = re.sub(r"\s+", " ", title.lower().strip())

            # deduplicate
            existing = None
            if doi:
                existing = await db.publications.find_one({"owner_id": uid, "doi": doi})
            if not existing:
                existing = await db.publications.find_one(
                    {"owner_id": uid, "title_norm": title_norm})

            if existing:
                duplicates += 1
                continue

            await db.publications.insert_one({
                "owner_id":   uid,
                "title":      title,
                "title_norm": title_norm,
                "year":       year,
                "doi":        doi,
                "journal":    journal,
                "type":       norm_type,
                "citations":  0,
                "source":     "orcid",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            })
            imported += 1

    except Exception as e:
        log.warning("ORCID import failed for user %s: %s", uid, e)
        errors += 1

    # enrich newly imported pubs via OpenAlex
    enrich = await enrich_publications_with_openalex(uid, limit=100)

    # snapshot
    snap = await take_snapshot(db, uid)

    # record sync timestamp
    await db.users.update_one(
        {"_id": ObjectId(uid)},
        {
            "$set":  {"orcid.citation_sync_at": now.isoformat()},
            "$push": {"orcid.citation_sync_history": {
                "synced_at":  now.isoformat(),
                "imported":   imported,
                "duplicates": duplicates,
                "enriched":   enrich.get("enriched", 0),
                "errors":     errors,
            }},
        },
    )

    return {
        "imported":      imported,
        "duplicates":    duplicates,
        "enriched":      enrich.get("enriched", 0),
        "snapshotted":   snap.get("snapshotted", 0),
        "alerts_created": snap.get("alerts_created", 0),
        "new_citations": snap.get("new_citations", 0),
        "errors":        errors,
    }
