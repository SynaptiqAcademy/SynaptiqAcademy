"""Research Impact Dashboard — premium flagship endpoint.

Gate: pro_researcher feature flag.
All data originates from real MongoDB collections — no fake stats.

Endpoints:
  GET  /api/research-impact/dashboard  — full parallel payload (all 12 sections)
  GET  /api/research-impact/citations  — interactive chart data (?period=30d|90d|365d|all)
  GET  /api/research-impact/goals      — load saved goals
  PUT  /api/research-impact/goals      — save goals
  GET  /api/research-impact/export     — CSV export of publications
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db import get_db
from services.permissions import require_feature
from services.impact.aggregator import (
    get_kpi_summary,
    get_publication_spotlight,
    get_citation_growth_chart,
    get_research_areas_impact,
    get_collaboration_impact,
    get_project_impact,
    get_opportunities,
    get_scorecard,
    get_goals_with_progress,
    generate_insights,
)
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.research_impact")
router = APIRouter(prefix="/api/research-impact", tags=["research-impact"])


# ─────────────────────────── models ──────────────────────────────────────────

class GoalsPayload(BaseModel):
    target_publications:   Optional[int]   = None
    target_citations:      Optional[int]   = None
    target_collaborations: Optional[int]   = None
    target_projects:       Optional[int]   = None
    target_h_index:        Optional[int]   = None
    deadline:              Optional[str]   = None


# ─────────────────────────── endpoints ───────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard(
    user: dict = Depends(require_feature("research_impact_dashboard")),
):
    """Full Research Impact Dashboard — all sections loaded in parallel."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    # Phase 1: KPI and base data (everything else depends on KPI)
    kpi = await get_kpi_summary(db, uid)

    # Phase 2: all independent aggregations in parallel
    (pub_spotlight, citation_growth, areas, collabs, projects, opportunities) = (
        await asyncio.gather(
            get_publication_spotlight(db, uid),
            get_citation_growth_chart(db, uid, period_days=365),
            get_research_areas_impact(db, uid),
            get_collaboration_impact(db, uid),
            get_project_impact(db, uid),
            get_opportunities(db, uid),
        )
    )

    # Phase 3: scorecard + goals (need kpi, areas, collabs, projects)
    scorecard, goals = await asyncio.gather(
        get_scorecard(db, uid, kpi=kpi, areas=areas,
                      collabs=collabs, projects=projects),
        get_goals_with_progress(db, uid, kpi),
    )

    # Phase 4: insights (pure CPU — synchronous)
    insights = generate_insights(
        kpi=kpi,
        areas=areas,
        pub_spotlight=pub_spotlight,
        scorecard=scorecard,
        opportunities=opportunities,
        collabs=collabs,
        projects=projects,
    )

    return {
        "kpi":             kpi,
        "pub_spotlight":   pub_spotlight,
        "citation_growth": citation_growth,
        "areas":           areas,
        "collabs":         collabs,
        "projects":        projects,
        "opportunities":   opportunities,
        "scorecard":       scorecard,
        "goals":           goals,
        "insights":        insights,
    }


@router.get("/citations")
async def get_citation_chart(
    period: str = Query("365d", regex=r"^(30d|90d|365d|all)$"),
    user: dict = Depends(require_feature("research_impact_dashboard")),
):
    """Interactive citation growth chart data for the given period."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    period_map = {"30d": 30, "90d": 90, "365d": 365, "all": 3650}
    days       = period_map.get(period, 365)
    data       = await get_citation_growth_chart(db, uid, period_days=days)
    return {"period": period, **data}


@router.get("/goals")
async def load_goals(
    user: dict = Depends(require_feature("research_impact_dashboard")),
):
    """Load saved research goals."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    doc = await db.user_research_goals.find_one({"user_id": uid})
    if not doc:
        return {"has_goals": False, "goals": None}

    doc.pop("_id", None)
    doc.pop("user_id", None)
    return {"has_goals": True, "goals": doc}


@router.put("/goals")
async def save_goals(
    payload: GoalsPayload,
    user: dict = Depends(require_feature("research_impact_dashboard")),
):
    """Upsert research goals for the current user."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    now = datetime.now(timezone.utc).isoformat()

    doc = payload.dict(exclude_none=True)
    doc["user_id"]    = uid
    doc["updated_at"] = now

    await db.user_research_goals.update_one(
        {"user_id": uid},
        {"$set": doc},
        upsert=True,
    )
    return {"status": "saved", "goals": doc}


@router.get("/export")
async def export_csv(
    user: dict = Depends(require_feature("research_impact_dashboard")),
):
    """CSV export of all publications with key impact metrics."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "year": 1, "journal": 1, "citations": 1,
         "doi": 1, "type": 1, "topics": 1, "concepts": 1,
         "openalex_enriched_at": 1, "coauthors": 1},
    ).sort("citations", -1).to_list(2000)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Title", "Year", "Journal", "Type", "Citations",
        "DOI", "Topics", "Co-Authors", "OpenAlex Enriched At",
    ])
    for p in pub_docs:
        topics = "; ".join((p.get("topics") or []) + (p.get("concepts") or []))
        coauthors = "; ".join(p.get("coauthors") or [])
        writer.writerow([
            p.get("title") or "",
            p.get("year") or "",
            p.get("journal") or "",
            p.get("type") or "",
            int(p.get("citations") or 0),
            p.get("doi") or "",
            topics,
            coauthors,
            p.get("openalex_enriched_at") or "",
        ])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=research_impact_{ts}.csv"},
    )
