"""Citation Monitoring — snapshot-based citation tracking with delta detection and alerts.

Collections owned by this module:
  publication_citations  — point-in-time snapshots of citation counts per publication
  citation_sources       — individual citing works (populated from OpenAlex)
  citation_alerts        — alert records (new citation, milestone, highly-cited, velocity, smart)

Read-only from existing collections:
  publications           — owner_id, title, doi, year, journal, type, citations,
                           concepts, topics, coauthors, openalex_enriched_at
  users                  — orcid, openalex_metrics, full_name, institution, institution_id
  research_gap_reviews   — for gap-citations integration

Endpoints:
  POST /api/citations/import-orcid           — Feature 1: ORCID → pubs pipeline
  POST /api/citations/sync                   — Feature 2: sync all pubs via OpenAlex
  POST /api/citations/sync/{pub_id}          — Feature 2: sync single pub
  GET  /api/citations/dashboard              — full dashboard payload
  GET  /api/citations/publications           — paginated publication list
  GET  /api/citations/publications/{pub_id}  — per-publication detail + history
  GET  /api/citations/research-areas         — Feature 3: research area impact
  GET  /api/citations/impact-score           — Feature 4: transparent score
  GET  /api/citations/gap-opportunities      — Feature 5: gap-citations integration
  GET  /api/citations/alerts                 — list user's citation alerts
  PATCH /api/citations/alerts/{id}/read      — mark alert as read
  PATCH /api/citations/alerts/read-all       — mark all read
  POST /api/citations/snapshot               — manual snapshot (post-sync)
  GET  /api/citations/export                 — CSV export
"""
from __future__ import annotations

import csv
import io
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from db import get_db
from services.permissions import require_feature
from services.citations.sync_service import (
    take_snapshot as _take_snapshot,
    sync_user_citations,
    import_orcid_publications,
    _upsert_citing_work,
)
from services.citations.providers.openalex import OpenAlexProvider
from services.citations.impact_score import compute_user_impact_score, compute_publication_impact_score
from services.citations.aggregator import aggregate_research_areas, classify_areas
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.citations")
router = APIRouter(prefix="/api/citations", tags=["citations"])

_provider = OpenAlexProvider()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────── Feature 1: ORCID import ─────────────────────────

@router.post("/import-orcid")
async def import_orcid(user: dict = Depends(require_feature("citation_monitoring"))):
    """Import publications from ORCID and enrich with OpenAlex citations."""
    from services.orcid.oauth import get_valid_access_token

    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    u_doc = await db.users.find_one({"_id": ObjectId(uid)}, {"orcid": 1})
    orcid_data = (u_doc or {}).get("orcid") or {}
    orcid_id   = orcid_data.get("orcid_id")

    if not orcid_id:
        raise HTTPException(400, "No ORCID linked. Connect your ORCID in Settings to import publications.")

    # refresh token if needed
    try:
        access_token = await get_valid_access_token(db, uid)
    except Exception:
        access_token = orcid_data.get("access_token")

    if not access_token:
        raise HTTPException(400, "ORCID access token missing. Re-authorise in Settings.")

    try:
        result = await import_orcid_publications(
            db, uid, orcid_id, access_token)
    except Exception as e:
        log.warning("ORCID import failed for %s: %s", uid, e)
        raise HTTPException(502, f"ORCID import error: {e}")

    return {
        "imported":      result["imported"],
        "duplicates":    result["duplicates"],
        "enriched":      result["enriched"],
        "snapshots":     result["snapshotted"],
        "alerts":        result["alerts_created"],
        "new_citations": result["new_citations"],
    }


# ─────────────────────────── Feature 2: OpenAlex sync ────────────────────────

@router.post("/sync")
async def sync_all(user: dict = Depends(require_feature("citation_monitoring"))):
    """Sync citation data for all user publications via OpenAlex."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    result = await sync_user_citations(db, uid)
    return {
        "synced":        result["synced"],
        "errors":        result["errors"],
        "sources_added": result["sources_added"],
        "new_citations": result["new_citations"],
        "alerts":        result["alerts_created"],
    }


@router.post("/sync/{pub_id}")
async def sync_single(
    pub_id: str,
    user: dict = Depends(require_feature("citation_monitoring")),
):
    """Sync citation data for a single publication via OpenAlex."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    now = _now()

    try:
        p = await db.publications.find_one({"_id": ObjectId(pub_id), "owner_id": uid})
    except Exception:
        raise HTTPException(404, "Publication not found")
    if not p:
        raise HTTPException(404, "Publication not found")

    result = await _provider.sync_publication(doi=p.get("doi"), title=p.get("title"))
    if not result.found:
        raise HTTPException(404, "No OpenAlex match found for this publication. Check DOI or title.")

    match = result.publication
    update = {
        "citations":            match.citation_count,
        "concepts":             match.concepts,
        "topics":               match.topics,
        "coauthors":            match.coauthors,
        "openalex_id":          match.provider_id,
        "counts_by_year":       match.counts_by_year,
        "openalex_enriched_at": now.isoformat(),
        "updated_at":           now.isoformat(),
    }
    if match.doi and not p.get("doi"):
        update["doi"] = match.doi
    if match.journal and not p.get("journal"):
        update["journal"] = match.journal
    if match.open_access_url:
        update["open_access_url"] = match.open_access_url

    await db.publications.update_one({"_id": p["_id"]}, {"$set": update})

    # upsert citing works (idempotent)
    sources_added = 0
    for cw in result.citing_works:
        added = await _upsert_citing_work(db, user_id=uid, pub_id=pub_id, cw=cw, now=now)
        if added:
            sources_added += 1

    snap = await _take_snapshot(db, uid)

    return {
        "publication": {
            "id":       pub_id,
            "citations": match.citation_count,
            "concepts":  match.concepts,
            "topics":    match.topics,
        },
        "sources_added": sources_added,
        "new_citations": snap.get("new_citations", 0),
        "alerts":        snap.get("alerts_created", 0),
    }


# ─────────────────────────── manual snapshot ─────────────────────────────────

@router.post("/snapshot")
async def take_snapshot(user: dict = Depends(require_feature("citation_monitoring"))):
    """Take a citation snapshot and generate alerts. Call after syncing OpenAlex."""
    db     = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await _take_snapshot(db, user["id"])
    return result


# ─────────────────────────── dashboard ───────────────────────────────────────

@router.get("/dashboard")
async def dashboard(user: dict = Depends(require_feature("citation_monitoring"))):
    """Full citation monitoring dashboard payload."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    now = _now()

    existing_snap = await db.publication_citations.find_one({"user_id": uid})
    if not existing_snap:
        await _take_snapshot(db, uid)

    u_doc = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {"openalex_metrics": 1, "h_index": 1, "publications_count": 1,
         "full_name": 1, "institution": 1, "institution_id": 1},
    )
    oam         = (u_doc or {}).get("openalex_metrics") or {}
    total_cites = int(oam.get("citations") or 0)
    h_index     = int(oam.get("h_index")   or (u_doc or {}).get("h_index") or 0)
    i10_index   = int(oam.get("i10_index") or 0)
    works_count = int(oam.get("works_count") or (u_doc or {}).get("publications_count") or 0)
    last_synced = oam.get("last_synced")

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "doi": 1, "year": 1, "citations": 1, "type": 1,
         "journal": 1, "concepts": 1, "topics": 1, "coauthors": 1,
         "openalex_enriched_at": 1, "openalex_id": 1},
    ).sort("citations", -1).to_list(500)

    enriched_count = sum(1 for p in pub_docs if p.get("openalex_enriched_at"))
    has_data       = total_cites > 0 or h_index > 0 or len(pub_docs) > 0

    publications = []
    pub_years_citations: list[tuple[int, int]] = []
    for p in pub_docs:
        cit = int(p.get("citations") or 0)
        yr  = p.get("year")
        publications.append({
            "id":         str(p["_id"]),
            "title":      p.get("title") or "Untitled",
            "doi":        p.get("doi"),
            "year":       yr,
            "journal":    p.get("journal"),
            "type":       p.get("type") or "journal_article",
            "citations":  cit,
            "concepts":   (p.get("concepts") or [])[:5],
            "topics":     (p.get("topics")   or [])[:5],
            "enriched_at": p.get("openalex_enriched_at"),
        })
        if yr and isinstance(yr, int):
            pub_years_citations.append((yr, cit))

    most_cited = publications[0] if publications else None

    # delta stats from snapshots
    pipeline_new = [
        {"$match":  {"user_id": uid}},
        {"$sort":   {"created_at": -1}},
        {"$group":  {"_id": "$pub_id", "latest_delta": {"$first": "$delta"},
                     "prev_count": {"$first": "$prev_count"}}},
        {"$group":  {"_id": None,
                     "total_new": {"$sum": "$latest_delta"},
                     "prev_total": {"$sum": "$prev_count"}}},
    ]
    new_res      = await db.publication_citations.aggregate(pipeline_new).to_list(1)
    new_citations = int((new_res[0].get("total_new") or 0) if new_res else 0)
    prev_total    = int((new_res[0].get("prev_total") or 0) if new_res else 0)

    month_start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_res    = await db.publication_citations.aggregate([
        {"$match":  {"user_id": uid, "created_at": {"$gte": month_start}}},
        {"$group":  {"_id": None, "total": {"$sum": "$delta"}}},
    ]).to_list(1)
    this_month   = int((month_res[0].get("total") or 0) if month_res else 0)

    # timeline by publication year
    by_year: dict[int, dict] = {}
    for p in pub_docs:
        yr = p.get("year")
        if yr and isinstance(yr, int) and 1970 <= yr <= now.year:
            if yr not in by_year:
                by_year[yr] = {"year": yr, "publications": 0, "total_citations": 0}
            by_year[yr]["publications"]    += 1
            by_year[yr]["total_citations"] += int(p.get("citations") or 0)
    timeline = sorted(by_year.values(), key=lambda x: x["year"])
    for row in timeline:
        n = row["publications"]
        row["avg_citations"] = round(row["total_citations"] / n, 1) if n else 0.0

    # alerts
    alert_docs = await db.citation_alerts.find(
        {"user_id": uid}, sort=[("created_at", -1)]).limit(20).to_list(20)
    alerts = [{
        "id":            str(a["_id"]),
        "alert_type":    a.get("alert_type"),
        "title":         a.get("title"),
        "message":       a.get("message"),
        "count":         a.get("count", 0),
        "delta":         a.get("delta", 0),
        "milestone_value": a.get("milestone_value"),
        "read":          a.get("read", False),
        "created_at":    (a.get("created_at") or now).isoformat() if not isinstance(a.get("created_at"), str) else a["created_at"],
    } for a in alert_docs]
    unread_count = sum(1 for a in alerts if not a["read"])

    # impact insights: top performing
    top_performing  = sorted(publications, key=lambda p: p["citations"], reverse=True)[:5]
    snap_deltas     = await db.publication_citations.aggregate([
        {"$match": {"user_id": uid}},
        {"$sort":  {"created_at": -1}},
        {"$group": {"_id": "$pub_id", "latest_delta": {"$first": "$delta"}}},
        {"$sort":  {"latest_delta": -1}},
        {"$limit": 5},
    ]).to_list(5)
    pub_lookup      = {p["id"]: p for p in publications}
    fastest_growing = []
    for s in snap_deltas:
        pub = pub_lookup.get(s.get("_id") or s.get("pub_id"))
        if pub and s["latest_delta"] > 0:
            fastest_growing.append({**pub, "recent_delta": s["latest_delta"]})

    # influential topics from OpenAlex concepts/topics
    topic_counts: dict[str, int] = {}
    for p in publications:
        for label in ((p.get("topics") or []) + (p.get("concepts") or []))[:3]:
            topic_counts[label] = topic_counts.get(label, 0) + p["citations"]
    influential_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    influential_topics = [{"topic": t, "citations": c} for t, c in influential_topics]

    # unique co-authors across all publications
    coauthor_names: set[str] = set()
    for p in pub_docs:
        for ca in (p.get("coauthors") or []):
            n = (ca.get("name") or "").strip()
            if n:
                coauthor_names.add(n)
    unique_coauthors = len(coauthor_names)

    # Feature 4: Transparent impact score
    impact = compute_user_impact_score(
        total_citations=total_cites,
        h_index=h_index,
        i10_index=i10_index,
        works_count=works_count,
        enriched_count=enriched_count,
        recent_delta=new_citations,
        prev_total=prev_total,
        unique_coauthors=unique_coauthors,
        pub_years_citations=pub_years_citations,
    )

    return {
        "summary": {
            "total_citations": total_cites,
            "new_citations":   new_citations,
            "this_month":      this_month,
            "h_index":         h_index,
            "i10_index":       i10_index,
            "works_count":     works_count,
            "enriched_count":  enriched_count,
            "last_synced":     last_synced,
            "has_data":        has_data,
            "unread_alerts":   unread_count,
        },
        "most_cited_pub":  most_cited,
        "publications":    publications,
        "timeline":        timeline,
        "alerts":          alerts,
        "impact_score":    impact,
        "impact_insights": {
            "top_performing":     top_performing,
            "fastest_growing":    fastest_growing,
            "influential_topics": influential_topics,
        },
        "author": {
            "full_name":     (u_doc or {}).get("full_name"),
            "institution":   (u_doc or {}).get("institution"),
            "openalex_id":   oam.get("openalex_id"),
            "h_index":       h_index,
            "i10_index":     i10_index,
            "total_citations": total_cites,
        },
    }


# ─────────────────────────── publications ────────────────────────────────────

@router.get("/publications")
async def list_publications(
    user: dict = Depends(require_feature("citation_monitoring")),
    sort:     str = Query("citations", enum=["citations", "year", "title"]),
    page:     int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    sort_field = {"citations": ("citations", -1), "year": ("year", -1), "title": ("title", 1)}[sort]
    skip  = (page - 1) * per_page
    total = await db.publications.count_documents({"owner_id": uid})

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "doi": 1, "year": 1, "citations": 1, "type": 1,
         "journal": 1, "concepts": 1, "topics": 1, "openalex_enriched_at": 1},
    ).sort(*sort_field).skip(skip).limit(per_page).to_list(per_page)

    pubs = [{
        "id":       str(p["_id"]),
        "title":    p.get("title") or "Untitled",
        "doi":      p.get("doi"),
        "year":     p.get("year"),
        "journal":  p.get("journal"),
        "type":     p.get("type") or "journal_article",
        "citations": int(p.get("citations") or 0),
        "concepts":  (p.get("concepts") or [])[:3],
        "topics":    (p.get("topics")   or [])[:3],
        "enriched_at": p.get("openalex_enriched_at"),
    } for p in pub_docs]

    return {"publications": pubs, "total": total, "page": page, "per_page": per_page}


@router.get("/publications/{pub_id}")
async def publication_detail(
    pub_id: str,
    user: dict = Depends(require_feature("citation_monitoring")),
):
    """Per-publication detail: metadata + citation history + sources + alerts + impact."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    now = _now()

    try:
        p = await db.publications.find_one({"_id": ObjectId(pub_id), "owner_id": uid})
    except Exception:
        raise HTTPException(404, "Publication not found")
    if not p:
        raise HTTPException(404, "Publication not found")

    citations = int(p.get("citations") or 0)

    # history snapshots (newest first)
    snap_docs = await db.publication_citations.find(
        {"user_id": uid, "pub_id": pub_id}, sort=[("created_at", -1)]).limit(50).to_list(50)
    history = [{
        "count":  s.get("count", 0),
        "delta":  s.get("delta", 0),
        "month":  s.get("snapshot_month"),
        "date":   s.get("created_at", now).isoformat() if not isinstance(s.get("created_at"), str) else s["created_at"],
    } for s in snap_docs]

    # prev snapshot for growth calcs
    prev_count = snap_docs[1].get("count", 0) if len(snap_docs) > 1 else 0
    recent_delta = snap_docs[0].get("delta", 0) if snap_docs else 0

    # citation sources
    source_docs = await db.citation_sources.find(
        {"user_id": uid, "pub_id": pub_id}, sort=[("detected_at", -1)]).limit(50).to_list(50)
    sources = [{
        "id":      str(s["_id"]),
        "doi":     s.get("citing_doi"),
        "title":   s.get("citing_title"),
        "year":    s.get("citing_year"),
        "journal": s.get("citing_journal"),
        "detected_at": (s.get("detected_at") or now).isoformat() if not isinstance(s.get("detected_at"), str) else s["detected_at"],
    } for s in source_docs]

    # related publications (same topics, different ids)
    pub_topics = list((p.get("topics") or []) + (p.get("concepts") or []))[:3]
    related_pubs = []
    if pub_topics:
        q = {"owner_id": uid, "_id": {"$ne": p["_id"]},
             "$or": [{"topics": {"$in": pub_topics}}, {"concepts": {"$in": pub_topics}}]}
        related_docs = await db.publications.find(
            q, {"title": 1, "citations": 1, "year": 1, "topics": 1, "concepts": 1}
        ).sort("citations", -1).limit(5).to_list(5)
        related_pubs = [{
            "id":       str(r["_id"]),
            "title":    r.get("title") or "Untitled",
            "citations": int(r.get("citations") or 0),
            "year":     r.get("year"),
            "topics":   ((r.get("topics") or []) + (r.get("concepts") or []))[:3],
        } for r in related_docs]

    # alerts
    alert_docs = await db.citation_alerts.find(
        {"user_id": uid, "pub_id": pub_id}, sort=[("created_at", -1)]).limit(20).to_list(20)
    alerts = [{
        "id":         str(a["_id"]),
        "alert_type": a.get("alert_type"),
        "message":    a.get("message"),
        "count":      a.get("count", 0),
        "read":       a.get("read", False),
        "created_at": a.get("created_at", now).isoformat() if not isinstance(a.get("created_at"), str) else a["created_at"],
    } for a in alert_docs]

    # Feature 8: transparent per-pub impact score + velocity + growth rate
    coauthor_count = len(p.get("coauthors") or [])
    pub_impact = compute_publication_impact_score(
        citations=citations,
        year=p.get("year"),
        coauthor_count=coauthor_count,
        recent_delta=recent_delta,
        prev_count=prev_count,
    )

    return {
        "publication": {
            "id":        str(p["_id"]),
            "title":     p.get("title") or "Untitled",
            "doi":       p.get("doi"),
            "year":      p.get("year"),
            "journal":   p.get("journal"),
            "type":      p.get("type") or "journal_article",
            "citations": citations,
            "concepts":  (p.get("concepts") or [])[:8],
            "topics":    (p.get("topics")   or [])[:8],
            "coauthors": (p.get("coauthors") or [])[:20],
            "counts_by_year": (p.get("counts_by_year") or []),
            "enriched_at": p.get("openalex_enriched_at"),
        },
        "history":       history,
        "sources":       sources,
        "related_pubs":  related_pubs,
        "alerts":        alerts,
        "impact_score":  pub_impact,
    }


# ─────────────────────────── Feature 3: research areas ───────────────────────

@router.get("/research-areas")
async def research_areas(user: dict = Depends(require_feature("citation_monitoring"))):
    """Research area impact analysis: group publications by topic/concept."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "year": 1, "citations": 1, "concepts": 1, "topics": 1},
    ).to_list(500)

    if not pub_docs:
        return {"areas": [], "classified": {"top_areas": [], "fastest_growing": [], "declining": [], "emerging": []}}

    # latest snapshot per pub
    snap_pipeline = [
        {"$match":  {"user_id": uid}},
        {"$sort":   {"created_at": -1}},
        {"$group":  {"_id": "$pub_id", "delta": {"$first": "$delta"},
                     "count": {"$first": "$count"}, "prev_count": {"$first": "$prev_count"}}},
    ]
    snap_docs = await db.publication_citations.aggregate(snap_pipeline).to_list(1000)

    # normalise pub_docs for aggregator
    pubs_norm = [{"id": str(p["_id"]), "year": p.get("year"),
                  "citations": int(p.get("citations") or 0),
                  "concepts":  p.get("concepts") or [],
                  "topics":    p.get("topics")   or []} for p in pub_docs]
    snaps_norm = [{"pub_id": s["_id"], "delta": s.get("delta", 0),
                   "count": s.get("count", 0), "prev_count": s.get("prev_count", 0)}
                  for s in snap_docs]

    areas      = aggregate_research_areas(pubs_norm, snaps_norm)
    classified = classify_areas(areas)

    return {"areas": areas, "classified": classified}


# ─────────────────────────── Feature 4: impact score ─────────────────────────

@router.get("/impact-score")
async def impact_score_detail(user: dict = Depends(require_feature("citation_monitoring"))):
    """Transparent user-level impact score with full component breakdown."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    u_doc = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {"openalex_metrics": 1, "h_index": 1, "publications_count": 1},
    )
    oam         = (u_doc or {}).get("openalex_metrics") or {}
    total_cites = int(oam.get("citations") or 0)
    h_index     = int(oam.get("h_index")   or 0)
    i10_index   = int(oam.get("i10_index") or 0)
    works_count = int(oam.get("works_count") or 0)

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"year": 1, "citations": 1, "coauthors": 1, "openalex_enriched_at": 1},
    ).to_list(500)
    enriched_count = sum(1 for p in pub_docs if p.get("openalex_enriched_at"))

    pub_years_citations = [(p["year"], int(p.get("citations") or 0))
                           for p in pub_docs if p.get("year") and isinstance(p["year"], int)]

    coauthor_names: set[str] = set()
    for p in pub_docs:
        for ca in (p.get("coauthors") or []):
            n = (ca.get("name") or "").strip()
            if n:
                coauthor_names.add(n)

    pipe = [
        {"$match": {"user_id": uid}},
        {"$sort":  {"created_at": -1}},
        {"$group": {"_id": "$pub_id", "delta": {"$first": "$delta"}, "prev": {"$first": "$prev_count"}}},
        {"$group": {"_id": None, "total_new": {"$sum": "$delta"}, "prev_total": {"$sum": "$prev"}}},
    ]
    new_res    = await db.publication_citations.aggregate(pipe).to_list(1)
    recent_del = int((new_res[0].get("total_new") or 0) if new_res else 0)
    prev_tot   = int((new_res[0].get("prev_total") or 0) if new_res else 0)

    score = compute_user_impact_score(
        total_citations=total_cites,
        h_index=h_index,
        i10_index=i10_index,
        works_count=works_count,
        enriched_count=enriched_count,
        recent_delta=recent_del,
        prev_total=prev_tot,
        unique_coauthors=len(coauthor_names),
        pub_years_citations=pub_years_citations,
    )
    return score


# ─────────────────────────── Feature 5: gap opportunities ────────────────────

@router.get("/gap-opportunities")
async def gap_opportunities(
    user: dict = Depends(require_feature("citation_monitoring")),
    topic:    str = Query(""),
    keywords: str = Query(""),
    gap_id:   Optional[str] = Query(None),
):
    """Compare a research gap topic against citation trends.

    Returns:
      publication_potential_score  — how many citations exist in this area
      citation_opportunity_score   — gap vs. existing citation density
      research_momentum_score      — recent growth in related areas
      topics_receiving_citations   — areas with active citation activity
      growing_velocity_topics      — fastest-growing related areas
      low_competition_rising       — low-density but rising topics
    """
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    kw_list = [k.strip().lower() for k in keywords.split(",") if k.strip()] if keywords else []
    topic_lc = topic.lower().strip()

    # all user publications with concepts/topics
    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"citations": 1, "concepts": 1, "topics": 1, "year": 1},
    ).to_list(500)

    # research areas already computed
    snap_pipeline = [
        {"$match":  {"user_id": uid}},
        {"$sort":   {"created_at": -1}},
        {"$group":  {"_id": "$pub_id", "delta": {"$first": "$delta"},
                     "prev_count": {"$first": "$prev_count"}}},
    ]
    snap_docs  = await db.publication_citations.aggregate(snap_pipeline).to_list(500)
    pubs_norm  = [{"id": str(p["_id"]), "year": p.get("year"),
                   "citations": int(p.get("citations") or 0),
                   "concepts": p.get("concepts") or [], "topics": p.get("topics") or []}
                  for p in pub_docs]
    snaps_norm = [{"pub_id": s["_id"], "delta": s.get("delta", 0),
                   "prev_count": s.get("prev_count", 0)} for s in snap_docs]
    all_areas  = aggregate_research_areas(pubs_norm, snaps_norm)

    # match areas to the gap topic/keywords
    def _relevance(area: dict) -> float:
        label = area["area"].lower()
        score = 0.0
        if topic_lc and (topic_lc in label or label in topic_lc):
            score += 3.0
        for kw in kw_list:
            if kw in label:
                score += 1.0
        return score

    scored_areas = [(a, _relevance(a)) for a in all_areas]
    scored_areas.sort(key=lambda x: x[1], reverse=True)

    # areas currently receiving citations (top overlapping)
    topics_receiving = [{"area": a["area"], "citations": a["total_citations"],
                         "trend": a["trend"], "growth_rate": a["growth_rate"]}
                        for a, rel in scored_areas if a["total_citations"] > 0][:8]

    growing_velocity = sorted(
        [a for a in all_areas if a["growth_rate"] > 0],
        key=lambda x: x["growth_rate"], reverse=True
    )[:5]
    growing_velocity = [{"area": a["area"], "growth_rate": a["growth_rate"],
                         "citations": a["total_citations"]} for a in growing_velocity]

    low_comp_rising = [a for a in all_areas
                       if a["trend"] in ("emerging", "rising") and a["total_citations"] < 50][:5]
    low_comp_rising = [{"area": a["area"], "citations": a["total_citations"],
                        "trend": a["trend"]} for a in low_comp_rising]

    # compute opportunity scores
    total_cites_in_area = sum(a["total_citations"] for a, rel in scored_areas if rel > 0)
    max_area_cites = max((a["total_citations"] for a in all_areas), default=1)

    # publication potential: how much citation activity is in this space
    pub_potential = min(100, int((total_cites_in_area / max(1, max_area_cites)) * 100))

    # citation opportunity: inverse of density (high score = less crowded = more opportunity)
    density = total_cites_in_area / max(1, len(all_areas))
    citation_opp = max(0, min(100, int(100 - (density / max(1, max_area_cites)) * 100)))

    # research momentum: avg growth rate in matching areas
    matching_growth = [a["growth_rate"] for a, rel in scored_areas if rel > 0 and a["growth_rate"] > 0]
    momentum = min(100, int(sum(matching_growth) / max(1, len(matching_growth)) * 2)) if matching_growth else 0

    # pull gap context if gap_id provided
    gap_context = None
    if gap_id:
        try:
            g = await db.research_gap_reviews.find_one({"_id": ObjectId(gap_id), "user_id": uid})
            if g:
                gap_json = g.get("gap_json") or {}
                gap_context = {
                    "topic":    g.get("topic"),
                    "question": g.get("research_question"),
                    "score":    (gap_json.get("publication_potential") or {}).get("score"),
                }
        except Exception:
            pass

    return {
        "publication_potential_score": pub_potential,
        "citation_opportunity_score":  citation_opp,
        "research_momentum_score":     momentum,
        "topics_receiving_citations":  topics_receiving,
        "growing_velocity_topics":     growing_velocity,
        "low_competition_rising":      low_comp_rising,
        "gap_context":                 gap_context,
        "matched_areas":               len([r for _, r in scored_areas if r > 0]),
    }


# ─────────────────────────── alerts ──────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(
    user: dict = Depends(require_feature("citation_monitoring")),
    unread_only: bool = Query(False),
    limit:       int  = Query(50, ge=1, le=200),
):
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    now = _now()
    q   = {"user_id": uid}
    if unread_only:
        q["read"] = False

    docs = await db.citation_alerts.find(q, sort=[("created_at", -1)]).limit(limit).to_list(limit)
    alerts = [{
        "id":             str(a["_id"]),
        "pub_id":         a.get("pub_id"),
        "alert_type":     a.get("alert_type"),
        "title":          a.get("title"),
        "message":        a.get("message"),
        "count":          a.get("count", 0),
        "delta":          a.get("delta", 0),
        "milestone_value": a.get("milestone_value"),
        "read":           a.get("read", False),
        "created_at":     a.get("created_at", now).isoformat() if not isinstance(a.get("created_at"), str) else a["created_at"],
    } for a in docs]

    unread_count = await db.citation_alerts.count_documents({"user_id": uid, "read": False})
    return {"alerts": alerts, "unread_count": unread_count}


@router.patch("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str, user: dict = Depends(require_feature("citation_monitoring"))):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        res = await db.citation_alerts.update_one(
            {"_id": ObjectId(alert_id), "user_id": user["id"]}, {"$set": {"read": True}})
    except Exception:
        raise HTTPException(400, "Invalid alert id")
    if res.matched_count == 0:
        raise HTTPException(404, "Alert not found")
    return {"ok": True}


@router.patch("/alerts/read-all")
async def mark_all_alerts_read(user: dict = Depends(require_feature("citation_monitoring"))):
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    res = await db.citation_alerts.update_many(
        {"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"marked": res.modified_count}


# ─────────────────────────── export ──────────────────────────────────────────

@router.get("/export")
async def export_csv(user: dict = Depends(require_feature("citation_monitoring"))):
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "doi": 1, "year": 1, "citations": 1, "type": 1,
         "journal": 1, "topics": 1, "openalex_enriched_at": 1},
    ).sort("citations", -1).to_list(1000)

    buf    = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Title", "DOI", "Year", "Journal", "Type", "Citations",
                     "Topics", "OpenAlex Enriched At"])
    for p in pub_docs:
        writer.writerow([
            p.get("title") or "",
            p.get("doi") or "",
            p.get("year") or "",
            p.get("journal") or "",
            p.get("type") or "",
            int(p.get("citations") or 0),
            "; ".join((p.get("topics") or [])[:5]),
            p.get("openalex_enriched_at") or "",
        ])

    ts  = datetime.now(timezone.utc).strftime("%Y%m%d")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=citations_{ts}.csv"},
    )
