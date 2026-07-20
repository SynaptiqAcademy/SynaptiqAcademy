"""Research Impact aggregation service.

Pure async functions — no FastAPI dependencies. Safe to call from HTTP
endpoints, schedulers, and background tasks alike.

Designed for reuse across:
  - Individual researcher dashboard (/research-impact)
  - Future: department, faculty, institution dashboards

Every function returns sensible empty/zero defaults when collections are empty.
"""
from __future__ import annotations

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId

log = logging.getLogger("synaptiq.impact")


# ─────────────────────────── internal helpers ─────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sat(x: float, scale: float) -> float:
    """Exponential saturation: approaches 100 asymptotically."""
    return round(min(100.0, 100.0 * (1.0 - math.exp(-max(0.0, x) / scale))), 2)


def _safe_iso(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


# ─────────────────────────── Section 1: KPI summary ──────────────────────────

async def get_kpi_summary(db, user_id: str) -> dict:
    """Core research KPIs: publications, citations, h-index, projects, collabs."""
    uid = user_id
    now = _now()

    # User-level metrics
    u_doc = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {"openalex_metrics": 1, "h_index": 1, "publications_count": 1,
         "full_name": 1, "institution": 1, "academic_role": 1},
    )
    oam         = (u_doc or {}).get("openalex_metrics") or {}
    h_index     = int(oam.get("h_index")   or (u_doc or {}).get("h_index") or 0)
    i10_index   = int(oam.get("i10_index") or 0)
    last_synced = oam.get("last_synced")

    # Publications aggregate (most accurate source)
    pub_agg = await db.publications.aggregate([
        {"$match": {"owner_id": uid}},
        {"$group": {
            "_id": None,
            "count":            {"$sum": 1},
            "total_citations":  {"$sum": {"$ifNull": ["$citations", 0]}},
            "enriched":         {"$sum": {"$cond": [{"$ifNull": ["$openalex_enriched_at", False]}, 1, 0]}},
            "max_year":         {"$max": "$year"},
        }},
    ]).to_list(1)
    pub_stats      = pub_agg[0] if pub_agg else {}
    works_count    = int(pub_stats.get("count") or int(oam.get("works_count") or 0))
    total_cits     = int(pub_stats.get("total_citations") or int(oam.get("citations") or 0))
    enriched_count = int(pub_stats.get("enriched") or 0)

    # Previous-period comparison (30 days ago snapshots)
    cutoff_30d   = now - timedelta(days=30)
    prev_snap    = await db.publication_citations.aggregate([
        {"$match": {"user_id": uid, "created_at": {"$lte": cutoff_30d}}},
        {"$sort":  {"created_at": -1}},
        {"$group": {"_id": "$pub_id", "count": {"$first": "$count"}}},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}},
    ]).to_list(1)
    prev_cits   = int((prev_snap[0].get("total") or 0) if prev_snap else 0)
    cit_delta   = max(0, total_cits - prev_cits)
    cit_pct     = round((cit_delta / max(1, prev_cits)) * 100, 1) if prev_cits else 0

    # Projects (no status field — count by owner + member)
    total_projects = await db.projects.count_documents(
        {"$or": [{"owner_id": uid}, {"members": uid}]})
    recent_projects = await db.projects.count_documents(
        {"$or": [{"owner_id": uid}, {"members": uid}],
         "created_at": {"$gte": (now - timedelta(days=90)).isoformat()}})

    # Collaborations
    accepted_collabs = await db.collaboration_requests.count_documents(
        {"$or": [{"sender_id": uid}, {"receiver_id": uid}], "status": "accepted"})

    # Citation velocity (citations/year for enriched pubs)
    velocity_agg = await db.publications.aggregate([
        {"$match": {"owner_id": uid, "year": {"$exists": True, "$ne": None}}},
        {"$project": {
            "citations": {"$ifNull": ["$citations", 0]},
            "age":       {"$max": [1, {"$subtract": [now.year, "$year"]}]},
        }},
        {"$project": {"velocity": {"$divide": ["$citations", "$age"]}}},
        {"$group": {"_id": None, "avg_velocity": {"$avg": "$velocity"}}},
    ]).to_list(1)
    avg_velocity = round((velocity_agg[0].get("avg_velocity") or 0) if velocity_agg else 0, 1)

    return {
        "publications":      works_count,
        "citations":         total_cits,
        "h_index":           h_index,
        "i10_index":         i10_index,
        "enriched_pubs":     enriched_count,
        "total_projects":    total_projects,
        "recent_projects":   recent_projects,
        "active_collabs":    accepted_collabs,
        "cit_delta_30d":     cit_delta,
        "cit_pct_30d":       cit_pct,
        "avg_velocity":      avg_velocity,
        "last_synced":       last_synced,
        "has_citations_data": total_cits > 0 or enriched_count > 0,
        "author": {
            "full_name":   (u_doc or {}).get("full_name"),
            "institution": (u_doc or {}).get("institution"),
            "role":        (u_doc or {}).get("academic_role"),
        },
    }


# ─────────────────────────── Section 2: Publication spotlight ─────────────────

async def get_publication_spotlight(db, user_id: str) -> dict:
    """Most cited, fastest growing, highest velocity, top-journal publications."""
    uid = user_id
    now = _now()

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"title": 1, "doi": 1, "year": 1, "journal": 1, "citations": 1,
         "topics": 1, "concepts": 1, "coauthors": 1, "openalex_enriched_at": 1},
    ).sort("citations", -1).to_list(200)

    if not pub_docs:
        return {"most_cited": None, "fastest_growing": None,
                "highest_velocity": None, "top_journal": None,
                "influential_area": None}

    def _pub_card(p, *, extra=None) -> dict:
        cit = int(p.get("citations") or 0)
        yr  = p.get("year")
        age = max(1, now.year - yr) if yr else 1
        return {
            "id":       str(p["_id"]),
            "title":    p.get("title") or "Untitled",
            "doi":      p.get("doi"),
            "year":     yr,
            "journal":  p.get("journal"),
            "citations": cit,
            "velocity":  round(cit / age, 1),
            "topics":   ((p.get("topics") or []) + (p.get("concepts") or []))[:3],
            **(extra or {}),
        }

    most_cited = _pub_card(pub_docs[0]) if pub_docs else None

    # Fastest growing: highest delta from latest snapshot
    delta_agg = await db.publication_citations.aggregate([
        {"$match": {"user_id": uid}},
        {"$sort":  {"created_at": -1}},
        {"$group": {"_id": "$pub_id", "delta": {"$first": "$delta"},
                    "prev": {"$first": "$prev_count"}}},
        {"$sort":  {"delta": -1}},
        {"$limit": 1},
    ]).to_list(1)

    fastest_growing = None
    if delta_agg:
        fg_id  = delta_agg[0]["_id"]
        delta  = delta_agg[0]["delta"]
        prev   = max(1, delta_agg[0].get("prev") or 1)
        fg_pub = next((p for p in pub_docs if str(p["_id"]) == fg_id), None)
        if fg_pub and delta > 0:
            fastest_growing = _pub_card(fg_pub, extra={
                "recent_delta":   delta,
                "growth_pct":     round(delta / prev * 100, 1),
            })

    # Highest velocity (citations per year)
    velocity_pubs = [p for p in pub_docs if p.get("year")]
    if velocity_pubs:
        vp = max(velocity_pubs, key=lambda p: int(p.get("citations") or 0) / max(1, now.year - p["year"]))
        yr  = vp["year"]
        cit = int(vp.get("citations") or 0)
        highest_velocity = _pub_card(vp, extra={
            "velocity": round(cit / max(1, now.year - yr), 1)})
    else:
        highest_velocity = None

    # Top journal (highest citations among pubs with journal name)
    journal_pubs = [p for p in pub_docs if p.get("journal")]
    top_journal = _pub_card(journal_pubs[0]) if journal_pubs else None

    # Most influential research area
    topic_cits: dict[str, int] = {}
    for p in pub_docs:
        cit = int(p.get("citations") or 0)
        for t in ((p.get("topics") or []) + (p.get("concepts") or []))[:3]:
            topic_cits[t] = topic_cits.get(t, 0) + cit
    influential_area = max(topic_cits.items(), key=lambda x: x[1])[0] if topic_cits else None

    return {
        "most_cited":       most_cited,
        "fastest_growing":  fastest_growing,
        "highest_velocity": highest_velocity,
        "top_journal":      top_journal,
        "influential_area": influential_area,
    }


# ─────────────────────────── Section 3: Citation growth chart ─────────────────

async def get_citation_growth_chart(db, user_id: str, period_days: int = 365) -> dict:
    """Citation growth over time from publication_citations snapshots."""
    uid    = user_id
    now    = _now()
    cutoff = now - timedelta(days=period_days)

    # Monthly aggregation of deltas
    monthly = await db.publication_citations.aggregate([
        {"$match": {"user_id": uid, "created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id":          "$snapshot_month",
            "new_citations": {"$sum": "$delta"},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(120)

    # Build cumulative series
    cumulative = 0
    series = []
    for row in monthly:
        new_cit    = int(row.get("new_citations") or 0)
        cumulative += new_cit
        series.append({
            "month":         row["_id"],
            "new_citations": new_cit,
            "cumulative":    cumulative,
        })

    # Publication citation distribution (buckets)
    all_pubs = await db.publications.find(
        {"owner_id": uid}, {"citations": 1}).to_list(500)
    buckets = {"uncited": 0, "low": 0, "growing": 0, "established": 0, "highly_cited": 0}
    for p in all_pubs:
        c = int(p.get("citations") or 0)
        if c == 0:     buckets["uncited"]      += 1
        elif c <= 10:  buckets["low"]           += 1
        elif c <= 50:  buckets["growing"]        += 1
        elif c <= 200: buckets["established"]    += 1
        else:          buckets["highly_cited"]   += 1

    distribution = [
        {"label": "Uncited",      "count": buckets["uncited"],       "range": "0"},
        {"label": "Low (1–10)",   "count": buckets["low"],           "range": "1–10"},
        {"label": "Growing",      "count": buckets["growing"],       "range": "11–50"},
        {"label": "Established",  "count": buckets["established"],   "range": "51–200"},
        {"label": "Highly Cited", "count": buckets["highly_cited"],  "range": "200+"},
    ]

    # Velocity: last 6 months moving average
    velocity_raw = series[-6:] if len(series) >= 6 else series
    avg_velocity = round(sum(r["new_citations"] for r in velocity_raw) / max(1, len(velocity_raw)), 1)

    return {
        "series":          series,
        "distribution":    distribution,
        "avg_monthly_velocity": avg_velocity,
        "total_new":       cumulative,
        "period_days":     period_days,
    }


# ─────────────────────────── Section 4: Research areas ───────────────────────

async def get_research_areas_impact(db, user_id: str) -> dict:
    """Research area breakdown — wraps the citation aggregator."""
    from services.citations.aggregator import aggregate_research_areas, classify_areas

    uid = user_id

    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"year": 1, "citations": 1, "concepts": 1, "topics": 1},
    ).to_list(500)

    snap_pipeline = [
        {"$match":  {"user_id": uid}},
        {"$sort":   {"created_at": -1}},
        {"$group":  {"_id": "$pub_id", "delta": {"$first": "$delta"},
                     "count": {"$first": "$count"}, "prev_count": {"$first": "$prev_count"}}},
    ]
    snap_docs = await db.publication_citations.aggregate(snap_pipeline).to_list(1000)

    pubs_norm  = [{"id": str(p["_id"]), "year": p.get("year"),
                   "citations":  int(p.get("citations") or 0),
                   "concepts":   p.get("concepts") or [],
                   "topics":     p.get("topics")   or []} for p in pub_docs]
    snaps_norm = [{"pub_id": s["_id"], "delta": s.get("delta", 0),
                   "count": s.get("count", 0), "prev_count": s.get("prev_count", 0)}
                  for s in snap_docs]

    areas      = aggregate_research_areas(pubs_norm, snaps_norm)
    classified = classify_areas(areas)

    return {"areas": areas, "classified": classified}


# ─────────────────────────── Section 5: Collaboration impact ──────────────────

async def get_collaboration_impact(db, user_id: str) -> dict:
    """Collaboration impact from collaboration_requests and projects."""
    uid = user_id

    sent_total     = await db.collaboration_requests.count_documents({"sender_id": uid})
    recv_total     = await db.collaboration_requests.count_documents({"receiver_id": uid})
    accepted       = await db.collaboration_requests.count_documents(
        {"$or": [{"sender_id": uid}, {"receiver_id": uid}], "status": "accepted"})
    declined       = await db.collaboration_requests.count_documents(
        {"$or": [{"sender_id": uid}, {"receiver_id": uid}], "status": "declined"})

    total_sent_recv = sent_total + recv_total
    success_rate = round(accepted / max(1, total_sent_recv) * 100, 1) if total_sent_recv else 0.0

    # Projects that include collaborators
    collab_projects = await db.projects.count_documents(
        {"owner_id": uid, "members": {"$exists": True, "$not": {"$size": 0}}})

    # Top collaborators: accepted requests, lookup partner profile
    top_req_docs = await db.collaboration_requests.find(
        {"$or": [{"sender_id": uid}, {"receiver_id": uid}], "status": "accepted"},
        {"sender_id": 1, "receiver_id": 1, "project_title": 1, "source": 1},
    ).sort("created_at", -1).limit(10).to_list(10)

    partner_ids: set[str] = set()
    for r in top_req_docs:
        pid = r["receiver_id"] if r.get("sender_id") == uid else r.get("sender_id")
        if pid and pid != uid:
            partner_ids.add(pid)

    top_collaborators = []
    if partner_ids:
        partner_docs = await db.users.find(
            {"_id": {"$in": [ObjectId(p) for p in partner_ids if len(p) == 24]}},
            {"full_name": 1, "institution": 1, "academic_role": 1, "avatar_url": 1},
        ).to_list(10)
        for pd in partner_docs:
            top_collaborators.append({
                "id":          str(pd["_id"]),
                "full_name":   pd.get("full_name") or "Unknown",
                "institution": pd.get("institution"),
                "role":        pd.get("academic_role"),
                "avatar_url":  pd.get("avatar_url"),
            })

    return {
        "sent_total":       sent_total,
        "received_total":   recv_total,
        "accepted":         accepted,
        "success_rate":     success_rate,
        "collab_projects":  collab_projects,
        "top_collaborators": top_collaborators,
    }


# ─────────────────────────── Section 6: Project impact ───────────────────────

async def get_project_impact(db, user_id: str) -> dict:
    """Project impact from projects collection."""
    uid = user_id

    proj_docs = await db.projects.find(
        {"$or": [{"owner_id": uid}, {"members": uid}]},
        {"title": 1, "description": 1, "visibility": 1, "keywords": 1,
         "source": 1, "research_gap": 1, "members": 1, "owner_id": 1,
         "created_at": 1},
    ).sort("created_at", -1).to_list(100)

    from_gap      = sum(1 for p in proj_docs if p.get("source") == "gap_finder")
    from_collab   = sum(1 for p in proj_docs if p.get("source") == "collab_intel")
    with_team     = sum(1 for p in proj_docs if (p.get("members") or []))

    project_cards = []
    for p in proj_docs[:12]:
        members      = p.get("members") or []
        team_size    = len(set([p.get("owner_id"), *members])) if p.get("owner_id") else len(members)
        kws          = (p.get("keywords") or [])[:3]
        project_cards.append({
            "id":          str(p["_id"]),
            "title":       p.get("title") or "Untitled",
            "description": (p.get("description") or "")[:200],
            "visibility":  p.get("visibility") or "private",
            "team_size":   team_size,
            "keywords":    kws,
            "source":      p.get("source"),
            "has_gap":     bool(p.get("research_gap")),
            "created_at":  _safe_iso(p.get("created_at")),
        })

    return {
        "total":          len(proj_docs),
        "from_gap":       from_gap,
        "from_collab":    from_collab,
        "with_team":      with_team,
        "project_cards":  project_cards,
    }


# ─────────────────────────── Section 7: Opportunities ────────────────────────

async def get_opportunities(db, user_id: str) -> dict:
    """Research opportunities combining gap analyses, citation areas, and collabs."""
    uid = user_id

    # Recent gap analyses
    gap_docs = await db.research_gap_reviews.find(
        {"user_id": uid},
        {"topic": 1, "keywords": 1, "gap_json": 1, "publication_score": 1, "created_at": 1},
    ).sort("created_at", -1).limit(3).to_list(3)

    gap_opportunities: list[dict] = []
    for g in gap_docs:
        gj       = g.get("gap_json") or {}
        pub_pot  = gj.get("publication_potential") or {}
        underx   = (gj.get("underexplored_areas") or [])[:3]
        score    = pub_pot.get("score") or g.get("publication_score") or 0
        for u in underx:
            gap_opportunities.append({
                "topic":        g.get("topic"),
                "area":         u.get("area") or "Unknown",
                "explanation":  u.get("explanation"),
                "opportunity_level": u.get("opportunity_level") or "medium",
                "pub_score":    score,
                "why":          pub_pot.get("assessment"),
                "source":       "gap_finder",
                "created_at":   _safe_iso(g.get("created_at")),
            })

    # Research areas: find emerging / low-competition rising
    areas_data = await get_research_areas_impact(db, uid)
    all_areas  = areas_data.get("areas") or []
    classified = areas_data.get("classified") or {}

    citation_opps: list[dict] = []
    for a in (classified.get("emerging") or []) + (classified.get("fastest_growing") or []):
        citation_opps.append({
            "area":        a.get("area"),
            "trend":       a.get("trend"),
            "growth_rate": a.get("growth_rate"),
            "citations":   a.get("total_citations"),
            "why":         f"{a.get('trend', '').title()} area with {a.get('total_citations', 0)} citations and {a.get('growth_rate', 0)}% growth rate.",
            "priority":    "high" if a.get("growth_rate", 0) > 30 else "medium",
        })

    return {
        "gap_opportunities":  gap_opportunities[:6],
        "citation_opps":      citation_opps[:6],
        "has_gap_data":       len(gap_docs) > 0,
        "has_area_data":      len(all_areas) > 0,
    }


# ─────────────────────────── Section 8: Scorecard ────────────────────────────

async def get_scorecard(db, user_id: str, *,
                        kpi: dict,
                        areas: dict,
                        collabs: dict,
                        projects: dict) -> dict:
    """Transparent research impact scorecard using reputation_scores + live data.

    Weights: Publication 25% | Citation 30% | Collaboration 20% | Project 15% | Growth 10%
    """
    uid = user_id

    # Pull existing reputation scores if cached
    rep = await db.reputation_scores.find_one(
        {"user_id": uid},
        {"publication": 1, "collaboration": 1, "overall": 1, "computed_at": 1},
    )
    rep_pub   = ((rep or {}).get("publication")   or {}).get("score", 0)
    rep_collab = ((rep or {}).get("collaboration") or {}).get("score", 0)

    # Citation Score (30%)
    total_cits = kpi.get("citations", 0)
    h_index    = kpi.get("h_index",   0)
    cit_volume = _sat(math.log1p(total_cits), scale=4.0)
    h_comp     = _sat(h_index, scale=8.0)
    cit_score  = round(0.6 * cit_volume + 0.4 * h_comp, 1)

    # Publication Score (25%)
    works      = kpi.get("publications", 0)
    enriched   = kpi.get("enriched_pubs", 0)
    avg_cit    = total_cits / max(1, works)
    raw_pub    = _sat(works * 0.5 + math.log1p(avg_cit) * 8, scale=12.0)
    # Blend with reputation score if available
    pub_score  = round(0.7 * raw_pub + 0.3 * rep_pub, 1) if rep_pub else round(raw_pub, 1)

    # Collaboration Score (20%)
    accepted    = collabs.get("accepted", 0)
    succ_rate   = collabs.get("success_rate", 0)
    raw_collab  = _sat(accepted * 5 + succ_rate * 0.3, scale=15.0)
    collab_score = round(0.6 * raw_collab + 0.4 * rep_collab, 1) if rep_collab else round(raw_collab, 1)

    # Project Score (15%)
    total_proj  = projects.get("total", 0)
    with_team   = projects.get("with_team", 0)
    from_gap    = projects.get("from_gap", 0)
    proj_score  = round(_sat(total_proj * 4 + with_team * 3 + from_gap * 5, scale=12.0), 1)

    # Research Growth Score (10%)
    all_areas  = (areas.get("areas") or [])
    max_growth = max((a.get("growth_rate", 0) for a in all_areas), default=0) if all_areas else 0
    velocity   = kpi.get("avg_velocity", 0)
    growth_score = round(_sat(max(0, max_growth) * 0.8 + velocity * 2, scale=15.0), 1)

    overall = round(
        0.25 * pub_score + 0.30 * cit_score + 0.20 * collab_score +
        0.15 * proj_score + 0.10 * growth_score, 1
    )

    return {
        "overall": int(overall),
        "formula": "Overall = 25%×Publication + 30%×Citation + 20%×Collaboration + 15%×Project + 10%×Growth",
        "components": {
            "publication": {
                "score": pub_score, "weight": 0.25, "contribution": round(0.25 * pub_score, 1),
                "label": "Publication Score",
                "formula": "sat(works×0.5 + log(avg_citations)×8, scale=12) blended with reputation",
                "reasoning": f"{works} publications, {enriched} enriched via OpenAlex, avg {round(avg_cit, 1)} citations/pub.",
            },
            "citation": {
                "score": cit_score, "weight": 0.30, "contribution": round(0.30 * cit_score, 1),
                "label": "Citation Score",
                "formula": "0.6×sat(log(total_citations), scale=4) + 0.4×sat(h_index, scale=8)",
                "reasoning": f"{total_cits:,} total citations, h-index {h_index}.",
            },
            "collaboration": {
                "score": collab_score, "weight": 0.20, "contribution": round(0.20 * collab_score, 1),
                "label": "Collaboration Score",
                "formula": "sat(accepted×5 + success_rate×0.3, scale=15) blended with reputation",
                "reasoning": f"{accepted} accepted collaborations, {succ_rate}% success rate.",
            },
            "project": {
                "score": proj_score, "weight": 0.15, "contribution": round(0.15 * proj_score, 1),
                "label": "Project Score",
                "formula": "sat(total×4 + with_team×3 + from_gap×5, scale=12)",
                "reasoning": f"{total_proj} projects, {with_team} with collaborators, {from_gap} from gap analyses.",
            },
            "growth": {
                "score": growth_score, "weight": 0.10, "contribution": round(0.10 * growth_score, 1),
                "label": "Research Growth Score",
                "formula": "sat(max_area_growth×0.8 + avg_velocity×2, scale=15)",
                "reasoning": f"{velocity} avg citations/year velocity, {round(max_growth, 1)}% max area growth.",
            },
        },
        "reputation_used": bool(rep),
    }


# ─────────────────────────── Section 9: AI insights ──────────────────────────

def generate_insights(*, kpi: dict, areas: dict, pub_spotlight: dict,
                       scorecard: dict, opportunities: dict,
                       collabs: dict, projects: dict) -> list[dict]:
    """Rule-based executive insights derived entirely from real data."""
    insights: list[dict] = []

    all_areas = (areas.get("areas") or [])
    classified = (areas.get("classified") or {})

    # 1. Strongest research area
    top_areas = classified.get("top_areas") or []
    if top_areas:
        a = top_areas[0]
        insights.append({
            "type":     "top_area",
            "priority": "high",
            "icon":     "award",
            "text":     f"Your strongest research area is \"{a['area']}\" with {a['total_citations']:,} total citations across {a['publication_count']} publication{'s' if a['publication_count'] != 1 else ''}.",
        })

    # 2. Fastest growing publication
    fg = pub_spotlight.get("fastest_growing")
    if fg and fg.get("recent_delta", 0) > 0:
        pct = fg.get("growth_pct", 0)
        insights.append({
            "type":     "fastest_pub",
            "priority": "high",
            "icon":     "trending-up",
            "text":     f"\"{fg['title'][:70]}\" gained +{fg['recent_delta']} citation{'s' if fg['recent_delta'] != 1 else ''} recently ({pct}% growth) — your fastest-growing publication.",
        })

    # 3. Emerging research area
    emerging = classified.get("emerging") or []
    if emerging:
        a = emerging[0]
        insights.append({
            "type":     "emerging_area",
            "priority": "medium",
            "icon":     "zap",
            "text":     f"Research area \"{a['area']}\" is emerging with {a['growth_rate']}% citation growth — a rising opportunity before it becomes competitive.",
        })

    # 4. Collaboration insight
    sr = collabs.get("success_rate", 0)
    ac = collabs.get("accepted", 0)
    if ac == 0:
        insights.append({
            "type":     "collab_cta",
            "priority": "medium",
            "icon":     "users",
            "text":     "You have no active collaborations yet. Researchers who collaborate typically publish 3× more and accumulate citations faster.",
        })
    elif sr < 40:
        insights.append({
            "type":     "collab_rate",
            "priority": "medium",
            "icon":     "users",
            "text":     f"Your collaboration success rate is {sr}%. Improving your outreach message could significantly increase accepted collaborations.",
        })
    else:
        insights.append({
            "type":     "collab_strong",
            "priority": "low",
            "icon":     "users",
            "text":     f"Strong collaboration network: {ac} active collaboration{'s' if ac != 1 else ''} with {sr}% success rate. Keep building your research community.",
        })

    # 5. High velocity publication
    hv = pub_spotlight.get("highest_velocity")
    if hv and hv.get("velocity", 0) > 10:
        insights.append({
            "type":     "high_velocity",
            "priority": "high",
            "icon":     "zap",
            "text":     f"\"{hv['title'][:70]}\" accumulates {hv['velocity']} citations/year — a high-velocity publication likely to become a landmark in your field.",
        })

    # 6. Citation score vs h-index insight
    h = kpi.get("h_index", 0)
    total = kpi.get("citations", 0)
    if h == 0 and total > 0:
        insights.append({
            "type":     "openalex_sync",
            "priority": "medium",
            "icon":     "refresh",
            "text":     f"You have {total:,} citations recorded but no h-index. Sync via OpenAlex to compute your h-index and unlock deeper impact metrics.",
        })
    elif h > 0:
        insights.append({
            "type":     "h_index",
            "priority": "low",
            "icon":     "bar-chart",
            "text":     f"Your h-index of {h} means {h} of your publications have each received at least {h} citations — a robust indicator of sustained research quality.",
        })

    # 7. Gap opportunity
    gap_opps = opportunities.get("gap_opportunities") or []
    if gap_opps:
        g = gap_opps[0]
        insights.append({
            "type":     "gap_opportunity",
            "priority": "high",
            "icon":     "target",
            "text":     f"Your recent gap analysis identified \"{g.get('area') or g.get('topic')}\" as underexplored. This is a high-potential area for your next publication.",
        })

    # 8. Project insight
    total_proj = projects.get("total", 0)
    from_gap   = projects.get("from_gap", 0)
    if total_proj == 0:
        insights.append({
            "type":     "project_cta",
            "priority": "low",
            "icon":     "folder",
            "text":     "No projects yet. Converting your gap analyses and collaboration plans into structured projects can significantly improve research productivity.",
        })
    elif from_gap > 0:
        insights.append({
            "type":     "project_gap",
            "priority": "low",
            "icon":     "folder",
            "text":     f"{from_gap} of your {total_proj} project{'s' if total_proj != 1 else ''} originated from gap analyses — evidence of data-driven research planning.",
        })

    # Sort: high > medium > low
    order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda x: order.get(x.get("priority", "low"), 2))

    return insights[:8]


# ─────────────────────────── Section 10: Goals ────────────────────────────────

async def get_goals_with_progress(db, user_id: str, kpi: dict) -> dict:
    """Load user goals and compute current progress against targets."""
    uid = user_id

    goal_doc = await db.user_research_goals.find_one({"user_id": uid})
    if not goal_doc:
        return {
            "goals":    None,
            "progress": None,
            "has_goals": False,
        }

    goals = {
        "target_publications":   goal_doc.get("target_publications"),
        "target_citations":      goal_doc.get("target_citations"),
        "target_collaborations": goal_doc.get("target_collaborations"),
        "target_projects":       goal_doc.get("target_projects"),
        "target_h_index":        goal_doc.get("target_h_index"),
        "deadline":              _safe_iso(goal_doc.get("deadline")),
        "updated_at":            _safe_iso(goal_doc.get("updated_at")),
    }

    def _pct(current, target):
        if not target:
            return None
        return min(100, round(current / target * 100, 1))

    progress = {
        "publications":   {"current": kpi.get("publications", 0),
                           "target":  goals["target_publications"],
                           "pct":     _pct(kpi.get("publications", 0), goals["target_publications"])},
        "citations":      {"current": kpi.get("citations", 0),
                           "target":  goals["target_citations"],
                           "pct":     _pct(kpi.get("citations", 0), goals["target_citations"])},
        "collaborations": {"current": kpi.get("active_collabs", 0),
                           "target":  goals["target_collaborations"],
                           "pct":     _pct(kpi.get("active_collabs", 0), goals["target_collaborations"])},
        "projects":       {"current": kpi.get("total_projects", 0),
                           "target":  goals["target_projects"],
                           "pct":     _pct(kpi.get("total_projects", 0), goals["target_projects"])},
        "h_index":        {"current": kpi.get("h_index", 0),
                           "target":  goals["target_h_index"],
                           "pct":     _pct(kpi.get("h_index", 0), goals["target_h_index"])},
    }

    return {"goals": goals, "progress": progress, "has_goals": True}
