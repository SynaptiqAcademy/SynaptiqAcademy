"""Citation Monitoring dashboard — surfaces real OpenAlex citation data already
stored in the platform without any duplicate storage or external API calls.

Data sources (read-only):
  - users.openalex_metrics       : total citations, h-index, i10-index, works_count
  - publications                 : per-work citations, year, title, doi, type
  - reputation_scores            : publication sub-score components
  - institution_memberships      : institution comparison
  - users                        : institution member roll-up

Endpoints:
  GET /api/citation-monitoring/dashboard  — full dashboard payload
  GET /api/citation-monitoring/export     — CSV of publication impact table
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from db import get_db
from services.permissions import require_feature
from services.citations.impact_score import compute_user_impact_score
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.citation_monitoring")
router = APIRouter(prefix="/api/citation-monitoring", tags=["citation-monitoring"])


# ──────────────────────────────── helpers ────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_since(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (_now() - ts).days
    except Exception:
        return None


async def _institution_comparison(db, institution_id: str, user_citations: int,
                                   user_h_index: int) -> Optional[dict]:
    """Compare user metrics against institution members who have OpenAlex data."""
    if not institution_id:
        return None

    inst = await db.institutions.find_one({"_id": ObjectId(institution_id)}, {"name": 1})
    inst_name = (inst or {}).get("name")

    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved"},
        {"user_id": 1},
    ).to_list(2000)
    member_ids = [r["user_id"] for r in rows]
    if not member_ids:
        return None

    users = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in member_ids]},
         "openalex_metrics": {"$exists": True}},
        {"openalex_metrics": 1},
    ).to_list(2000)

    members_with_data = [
        {
            "citations": int((u.get("openalex_metrics") or {}).get("citations") or 0),
            "h_index":   int((u.get("openalex_metrics") or {}).get("h_index") or 0),
        }
        for u in users
        if (u.get("openalex_metrics") or {}).get("citations") is not None
    ]
    if len(members_with_data) < 2:
        return None

    all_cites = sorted(m["citations"] for m in members_with_data)
    all_h     = sorted(m["h_index"]   for m in members_with_data)
    n = len(all_cites)

    avg_citations = round(sum(all_cites) / n, 1)
    avg_h         = round(sum(all_h) / n, 1)
    pct_citations = round(sum(1 for c in all_cites if c < user_citations) / n * 100, 1)
    pct_h         = round(sum(1 for h in all_h if h < user_h_index) / n * 100, 1)
    median_cites  = all_cites[n // 2]
    median_h      = all_h[n // 2]

    return {
        "institution_name": inst_name,
        "member_count": n,
        "avg_citations": avg_citations,
        "median_citations": median_cites,
        "avg_h_index": avg_h,
        "median_h_index": median_h,
        "user_citation_percentile": pct_citations,
        "user_h_percentile": pct_h,
    }


# ──────────────────────────────── endpoints ──────────────────────────────────

@router.get("/dashboard")
async def citation_dashboard(
    user: dict = Depends(require_feature("citation_monitoring")),
):
    """Return the full citation monitoring dashboard payload.

    Reads exclusively from existing database collections — no live OpenAlex calls.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    now = _now()

    # ── 1. author-level metrics from openalex_metrics ────────────────────────
    u_doc = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {"openalex_metrics": 1, "h_index": 1, "publications_count": 1,
         "full_name": 1, "institution": 1, "institution_id": 1},
    )
    oam = (u_doc or {}).get("openalex_metrics") or {}
    total_citations = int(oam.get("citations") or 0)
    h_index         = int(oam.get("h_index")   or (u_doc or {}).get("h_index") or 0)
    i10_index       = int(oam.get("i10_index") or 0)
    works_count     = int(oam.get("works_count") or (u_doc or {}).get("publications_count") or 0)
    last_synced     = oam.get("last_synced")
    openalex_id     = oam.get("openalex_id")

    needs_sync = (last_synced is None) or ((_days_since(last_synced) or 9999) > 30)
    has_data   = total_citations > 0 or h_index > 0 or works_count > 0

    # ── 2. per-publication data ───────────────────────────────────────────────
    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "year": 1, "citations": 1, "type": 1, "doi": 1,
         "journal": 1, "openalex_enriched_at": 1, "openalex_id": 1},
    ).sort("citations", -1).to_list(500)

    enriched_count = sum(1 for p in pub_docs if p.get("openalex_enriched_at"))

    publications = []
    for p in pub_docs:
        cites = int(p.get("citations") or 0)
        enriched_at = p.get("openalex_enriched_at")
        publications.append({
            "id":          str(p["_id"]),
            "title":       p.get("title") or "Untitled",
            "year":        p.get("year"),
            "citations":   cites,
            "type":        p.get("type") or "journal_article",
            "doi":         p.get("doi"),
            "journal":     p.get("journal"),
            "enriched_at": enriched_at,
            "days_since_enriched": _days_since(enriched_at),
        })

    # ── 3. citation timeline — grouped by publication year ────────────────────
    by_year: dict[int, dict] = {}
    for p in pub_docs:
        yr = p.get("year")
        if yr and isinstance(yr, int) and 1970 <= yr <= now.year:
            if yr not in by_year:
                by_year[yr] = {"year": yr, "publications": 0, "total_citations": 0}
            by_year[yr]["publications"]   += 1
            by_year[yr]["total_citations"] += int(p.get("citations") or 0)

    timeline = sorted(by_year.values(), key=lambda x: x["year"])
    for row in timeline:
        pubs = row["publications"]
        row["avg_citations"] = round(row["total_citations"] / pubs, 1) if pubs else 0.0

    # Yearly growth: citation accumulation across cohorts, newest to oldest
    timeline_desc = sorted(timeline, key=lambda x: x["year"], reverse=True)

    # ── 4. citation alerts ────────────────────────────────────────────────────
    cutoff_30d  = (now - timedelta(days=30)).isoformat()
    cutoff_12m  = (now - timedelta(days=365)).isoformat()

    recently_enriched = [
        p for p in publications
        if p.get("enriched_at") and p["enriched_at"] >= cutoff_30d
    ]
    recently_cited = sorted(recently_enriched, key=lambda x: x["citations"], reverse=True)[:5]

    high_impact = [p for p in publications if p["citations"] > 0][:5]

    uncited_enriched = [
        p for p in publications
        if p.get("enriched_at") and p["citations"] == 0
    ][:5]

    # Unusual citation growth signal: papers with citations > (10 × years_since_pub)
    current_year = now.year
    high_velocity = [
        p for p in publications
        if p.get("year") and isinstance(p["year"], int)
        and (current_year - p["year"]) >= 1
        and p["citations"] > 10 * (current_year - p["year"])
    ][:5]

    alerts = {
        "recently_enriched": recently_cited,
        "high_impact":        high_impact,
        "high_velocity":      high_velocity,
        "uncited_enriched":   uncited_enriched,
    }

    # ── 5. research impact score (canonical 40/25/20/15 formula) ─────────────
    pub_years_citations = [
        (p.get("year"), int(p.get("citations") or 0))
        for p in pub_docs
        if p.get("year") and isinstance(p.get("year"), int)
    ]
    # delta from snapshot collection (best effort — graceful on empty)
    recent_delta = prev_total_snap = 0
    try:
        pipe_snap = [
            {"$match": {"user_id": uid}},
            {"$sort":  {"created_at": -1}},
            {"$group": {"_id": "$pub_id", "delta": {"$first": "$delta"},
                        "prev": {"$first": "$prev_count"}}},
            {"$group": {"_id": None, "total_new": {"$sum": "$delta"},
                        "prev_total": {"$sum": "$prev"}}},
        ]
        snap_res = await db.publication_citations.aggregate(pipe_snap).to_list(1)
        if snap_res:
            recent_delta     = int(snap_res[0].get("total_new") or 0)
            prev_total_snap  = int(snap_res[0].get("prev_total") or 0)
    except Exception:
        pass

    impact = compute_user_impact_score(
        total_citations=total_citations,
        h_index=h_index,
        i10_index=i10_index,
        works_count=works_count,
        enriched_count=enriched_count,
        recent_delta=recent_delta,
        prev_total=prev_total_snap,
        unique_coauthors=0,
        pub_years_citations=pub_years_citations,
    )

    # ── 6. author summary ─────────────────────────────────────────────────────
    author_summary = {
        "full_name":    (u_doc or {}).get("full_name"),
        "openalex_id":  openalex_id,
        "institution":  (u_doc or {}).get("institution"),
        "works_count":  works_count,
        "total_citations": total_citations,
        "h_index":      h_index,
        "i10_index":    i10_index,
        "last_synced":  last_synced,
        "needs_sync":   needs_sync,
    }

    # ── 7. institution comparison ─────────────────────────────────────────────
    institution_id = str((u_doc or {}).get("institution_id") or "")
    inst_cmp = None
    if institution_id:
        try:
            inst_cmp = await _institution_comparison(
                db, institution_id, total_citations, h_index)
        except Exception as exc:
            log.warning("Institution comparison failed: %s", exc)

    return {
        "summary": {
            "total_citations": total_citations,
            "h_index":         h_index,
            "i10_index":       i10_index,
            "works_count":     works_count,
            "enriched_count":  enriched_count,
            "last_synced":     last_synced,
            "needs_sync":      needs_sync,
            "has_data":        has_data,
        },
        "publications":          publications,
        "timeline":              timeline,
        "timeline_desc":         timeline_desc,
        "alerts":                alerts,
        "impact_score":          impact,
        "author_summary":        author_summary,
        "institution_comparison": inst_cmp,
        "data_note": (
            "Citation counts are sourced from OpenAlex and reflect the state "
            "at the time of your last sync. Use 'Sync OpenAlex' to refresh."
        ),
    }


@router.get("/export")
async def export_csv(
    user: dict = Depends(require_feature("citation_monitoring")),
):
    """Stream a CSV of the user's publication citation data."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "year": 1, "citations": 1, "type": 1, "doi": 1,
         "journal": 1, "openalex_enriched_at": 1},
    ).sort("citations", -1).to_list(1000)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Title", "Year", "Journal", "Type", "Citations", "DOI", "OpenAlex Enriched At"])
    for p in pub_docs:
        writer.writerow([
            p.get("title") or "",
            p.get("year") or "",
            p.get("journal") or "",
            p.get("type") or "",
            int(p.get("citations") or 0),
            p.get("doi") or "",
            p.get("openalex_enriched_at") or "",
        ])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=citations_{ts}.csv"},
    )
