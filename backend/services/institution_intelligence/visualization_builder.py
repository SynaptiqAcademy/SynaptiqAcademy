"""Institution Intelligence Engine — Visualization Builder (Phase XV).

Builds 12 visualization payloads for the executive dashboard.
All functions return serializable dicts — frontend renders them.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import (
    InstitutionInput, InstitutionKPIs, InstitutionProfile,
    InstitutionRisk, PortfolioArea, TalentProfile, VizType,
)


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(v) if v is not None else d
    except (TypeError, ValueError):
        return d


# ── 1. Institution knowledge graph ────────────────────────────────────────────

def knowledge_graph_viz(profile: InstitutionProfile) -> dict:
    nodes = [{"id": "inst", "label": profile.name, "type": "institution", "size": 5}]
    edges = []
    for dept in profile.departments[:10]:
        did = f"dept_{dept.name}"
        nodes.append({"id": did, "label": dept.name, "type": "department",
                       "size": 2 + dept.researcher_count * 0.1})
        edges.append({"from": "inst", "to": did, "relation": "has_department"})
        for researcher in dept.top_researchers[:3]:
            rid = f"r_{researcher}"
            nodes.append({"id": rid, "label": researcher, "type": "researcher", "size": 1.5})
            edges.append({"from": did, "to": rid, "relation": "employs"})
    return {
        "viz_type": VizType.KNOWLEDGE_GRAPH.value,
        "data": {"nodes": nodes, "edges": edges},
        "metadata": {"node_count": len(nodes), "edge_count": len(edges)},
    }


# ── 2. Research portfolio map ─────────────────────────────────────────────────

def research_portfolio_viz(portfolio: list[PortfolioArea]) -> dict:
    bubbles = [
        {
            "name": p.name,
            "x": p.growth_rate,
            "y": p.publication_count,
            "size": max(p.researcher_count * 10, 5),
            "color": {"invest": "#10b981", "grow": "#3b82f6",
                       "maintain": "#6b7280", "divest": "#ef4444"}.get(p.strategic_priority, "#6b7280"),
            "priority": p.strategic_priority,
            "maturity": p.maturity,
        }
        for p in portfolio
    ]
    return {
        "viz_type": VizType.RESEARCH_PORTFOLIO.value,
        "data": {
            "bubbles": bubbles,
            "x_label": "Publication Growth Rate",
            "y_label": "Publication Count",
        },
        "metadata": {"total_areas": len(portfolio)},
    }


# ── 3. Faculty performance map ────────────────────────────────────────────────

def faculty_performance_viz(researchers: list[dict]) -> dict:
    points = []
    for r in researchers[:100]:
        name = r.get("full_name") or r.get("name") or "Unknown"
        points.append({
            "name":     name,
            "h_index":  _sf(r.get("h_index", 0)),
            "pubs":     _si(r.get("publication_count", 0)),
            "intl":     _sf(r.get("international_collab_ratio", 0)),
            "dept":     r.get("department") or "General",
        })
    return {
        "viz_type": VizType.FACULTY_PERFORMANCE.value,
        "data": {"points": points, "x_label": "h-index", "y_label": "Publication Count"},
        "metadata": {"total_researchers": len(researchers)},
    }


# ── 4. Department heatmap ─────────────────────────────────────────────────────

def department_heatmap_viz(profile: InstitutionProfile) -> dict:
    metrics = ["researcher_count", "publication_count", "citation_count",
               "avg_h_index", "grant_count", "collaboration_score"]
    rows = []
    for dept in profile.departments:
        d = dept.to_dict()
        rows.append({m: d.get(m, 0) for m in metrics} | {"department": dept.name})
    return {
        "viz_type": VizType.DEPARTMENT_HEATMAP.value,
        "data": {"rows": rows, "metrics": metrics},
        "metadata": {"departments": len(rows)},
    }


# ── 5. Grant dashboard ────────────────────────────────────────────────────────

def grant_dashboard_viz(grants: list[dict]) -> dict:
    funder_totals: dict[str, float] = defaultdict(float)
    status_totals: dict[str, int]   = defaultdict(int)
    for g in grants:
        funder = g.get("funding_organization") or g.get("funder") or "Unknown"
        amount = _sf(g.get("amount", 0))
        status = g.get("status") or "unknown"
        funder_totals[funder] += amount
        status_totals[status] += 1

    return {
        "viz_type": VizType.GRANT_DASHBOARD.value,
        "data": {
            "by_funder": [{"funder": k, "total": round(v, 2)} for k, v in
                          sorted(funder_totals.items(), key=lambda x: -x[1])[:10]],
            "by_status": dict(status_totals),
            "total_income": round(sum(funder_totals.values()), 2),
            "total_grants": len(grants),
        },
        "metadata": {},
    }


# ── 6. Funding flow ───────────────────────────────────────────────────────────

def funding_flow_viz(grants: list[dict], departments: list[dict]) -> dict:
    sources: list[dict] = []
    flows:   list[dict] = []
    funder_map: dict[str, float] = defaultdict(float)
    dept_map:   dict[str, float] = defaultdict(float)

    for g in grants:
        funder = g.get("funding_organization") or "Unknown"
        dept   = g.get("department") or "Institution"
        amount = _sf(g.get("amount", 0))
        funder_map[funder] += amount
        dept_map[dept] += amount

    for funder, amt in sorted(funder_map.items(), key=lambda x: -x[1])[:8]:
        sources.append({"name": funder, "total": round(amt, 2)})
        for dept, d_amt in sorted(dept_map.items(), key=lambda x: -x[1])[:6]:
            flows.append({"from": funder, "to": dept, "value": round(min(amt, d_amt) * 0.3, 2)})

    return {
        "viz_type": VizType.FUNDING_FLOW.value,
        "data": {"sources": sources, "flows": flows},
        "metadata": {},
    }


# ── 7. Citation growth timeline ───────────────────────────────────────────────

def citation_growth_viz(kpis: InstitutionKPIs) -> dict:
    baseline = _si(kpis.publication_output) * 10   # rough proxy
    rate     = kpis.citation_growth
    years    = list(range(-4, 1))
    citations = [round(max(baseline * ((1 - rate) ** (-yr)), 0)) for yr in years]
    return {
        "viz_type": VizType.CITATION_GROWTH.value,
        "data": {
            "years":     [str(2021 + i) for i in range(len(years))],
            "citations": citations,
            "growth_rate": kpis.citation_growth,
        },
        "metadata": {},
    }


# ── 8. Publication timeline ────────────────────────────────────────────────────

def publication_timeline_viz(kpis: InstitutionKPIs) -> dict:
    baseline = kpis.publication_output
    rate     = kpis.publication_growth
    years    = list(range(-4, 1))
    pubs     = [round(max(baseline * ((1 - rate) ** (-yr)), 0)) for yr in years]
    return {
        "viz_type": VizType.PUBLICATION_TIMELINE.value,
        "data": {
            "years":        [str(2021 + i) for i in range(len(years))],
            "publications": pubs,
        },
        "metadata": {},
    }


# ── 9. International collaboration map ────────────────────────────────────────

def international_collaboration_viz(researchers: list[dict]) -> dict:
    country_counts: dict[str, int] = defaultdict(int)
    for r in researchers:
        country = r.get("country") or "Unknown"
        if country:
            country_counts[country] += 1
    return {
        "viz_type": VizType.INTERNATIONAL_MAP.value,
        "data": {
            "countries": [{"country": k, "count": v}
                          for k, v in sorted(country_counts.items(), key=lambda x: -x[1])],
        },
        "metadata": {"total_countries": len(country_counts)},
    }


# ── 10. Talent pipeline ────────────────────────────────────────────────────────

def talent_pipeline_viz(talent: dict[str, list]) -> dict:
    stages = ["doctoral", "postdoc", "early_career", "mid_career", "senior"]
    counts_by_stage: dict[str, int] = defaultdict(int)
    for category, profiles in talent.items():
        for p in profiles:
            stage = p.get("career_stage") if isinstance(p, dict) else p.career_stage
            if stage:
                counts_by_stage[stage] += 1
    return {
        "viz_type": VizType.TALENT_PIPELINE.value,
        "data": {
            "stages": stages,
            "counts": [counts_by_stage.get(s, 0) for s in stages],
            "categories": {k: len(v) for k, v in talent.items()},
        },
        "metadata": {},
    }


# ── 11. Strategic risk matrix ─────────────────────────────────────────────────

def risk_matrix_viz(risks: list[InstitutionRisk]) -> dict:
    points = [
        {
            "risk_type":   r.risk_type.value,
            "probability": r.probability,
            "impact":      r.impact,
            "severity":    r.severity.value,
            "description": r.description[:80],
        }
        for r in risks
    ]
    return {
        "viz_type": VizType.RISK_MATRIX.value,
        "data": {
            "points": points,
            "x_label": "Probability",
            "y_label": "Impact",
        },
        "metadata": {"total_risks": len(risks)},
    }


# ── 12. Institution forecast dashboard ────────────────────────────────────────

def forecast_dashboard_viz(forecasts: list) -> dict:
    series = []
    for f in forecasts:
        fd = f.to_dict() if hasattr(f, "to_dict") else f
        series.append({
            "type":     fd.get("forecast_type"),
            "baseline": fd.get("baseline_value"),
            "values":   fd.get("predicted_values", []),
            "trend":    fd.get("trend"),
        })
    return {
        "viz_type": VizType.FORECAST_DASHBOARD.value,
        "data": {"series": series},
        "metadata": {"forecasts": len(series)},
    }


# ── Dispatcher ─────────────────────────────────────────────────────────────────

_VIZ_NAMES = {v.value for v in VizType}


def build_visualization(
    viz_type: str,
    profile: InstitutionProfile | None = None,
    kpis: InstitutionKPIs | None = None,
    inp: InstitutionInput | None = None,
    portfolio: list[PortfolioArea] | None = None,
    risks: list[InstitutionRisk] | None = None,
    talent: dict | None = None,
    forecasts: list | None = None,
) -> dict:
    """Dispatch to the correct visualization builder."""
    if viz_type == VizType.KNOWLEDGE_GRAPH.value and profile:
        return knowledge_graph_viz(profile)
    if viz_type == VizType.RESEARCH_PORTFOLIO.value:
        return research_portfolio_viz(portfolio or [])
    if viz_type == VizType.FACULTY_PERFORMANCE.value and inp:
        return faculty_performance_viz(inp.researchers)
    if viz_type == VizType.DEPARTMENT_HEATMAP.value and profile:
        return department_heatmap_viz(profile)
    if viz_type == VizType.GRANT_DASHBOARD.value and inp:
        return grant_dashboard_viz(inp.grants)
    if viz_type == VizType.FUNDING_FLOW.value and inp:
        return funding_flow_viz(inp.grants, [{"name": d} for d in inp.departments])
    if viz_type == VizType.CITATION_GROWTH.value and kpis:
        return citation_growth_viz(kpis)
    if viz_type == VizType.PUBLICATION_TIMELINE.value and kpis:
        return publication_timeline_viz(kpis)
    if viz_type == VizType.INTERNATIONAL_MAP.value and inp:
        return international_collaboration_viz(inp.researchers)
    if viz_type == VizType.TALENT_PIPELINE.value:
        return talent_pipeline_viz(talent or {})
    if viz_type == VizType.RISK_MATRIX.value:
        return risk_matrix_viz(risks or [])
    if viz_type == VizType.FORECAST_DASHBOARD.value:
        return forecast_dashboard_viz(forecasts or [])
    return {"viz_type": viz_type, "data": {}, "metadata": {"error": "Unknown visualization type"}}
