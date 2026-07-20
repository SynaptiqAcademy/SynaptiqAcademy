"""Academic Career Intelligence — Visualization Builder (Phase XVI).

Returns serializable dicts describing 10 chart types for the frontend.
"""
from __future__ import annotations

import datetime

from .models import (
    CareerProfile, CareerRoadmap, CareerStage, PromotionReadiness,
    SkillGapReport, VizType,
)


def _now_year() -> int:
    return datetime.date.today().year


# ── 10 visualization functions ────────────────────────────────────────────────

def career_timeline_viz(profile: CareerProfile, roadmap: CareerRoadmap | None = None) -> dict:
    year = _now_year()
    events = [{"year": year - profile.years_active, "event": "Research career started",
                "type": "career_start"}]
    if profile.publication_count:
        events.append({"year": year - max(profile.years_active - 1, 0),
                        "event": f"{profile.publication_count} publications",
                        "type": "publication"})
    if profile.grant_count:
        events.append({"year": year - 1, "event": f"{profile.grant_count} grants secured",
                        "type": "grant"})
    if roadmap:
        for m in roadmap.milestones[:5]:
            events.append({"year": year + m.year, "event": m.description, "type": "future"})
    return {"type": VizType.CAREER_TIMELINE.value, "data": sorted(events, key=lambda e: e["year"])}


def goal_progress_viz(goals: list[dict]) -> dict:
    items = [
        {"label": g.get("description", "Goal"), "progress": g.get("progress", 0),
         "status": g.get("status", "not_started")}
        for g in goals
    ]
    return {"type": VizType.GOAL_PROGRESS.value, "data": items}


def skill_radar_viz(report: SkillGapReport) -> dict:
    axes = [a.to_dict() for a in report.assessments]
    return {
        "type":   VizType.SKILL_RADAR.value,
        "labels": [a["domain"] for a in axes],
        "values": [a["level_score"] for a in axes],
        "data":   axes,
    }


def publication_growth_viz(profile: CareerProfile) -> dict:
    years   = max(profile.years_active, 1)
    year    = _now_year()
    per_year = profile.publication_count / years
    series  = [{"year": year - years + i, "publications": round(per_year * (i + 1))}
               for i in range(years)]
    return {"type": VizType.PUBLICATION_GROWTH.value, "series": series,
            "total": profile.publication_count, "avg_per_year": round(per_year, 2)}


def citation_growth_viz(profile: CareerProfile) -> dict:
    years    = max(profile.years_active, 1)
    year     = _now_year()
    cites_py = profile.citation_count / years
    series   = [{"year": year - years + i, "citations": round(cites_py * (i + 1))}
                for i in range(years)]
    return {"type": VizType.CITATION_GROWTH.value, "series": series,
            "total": profile.citation_count, "h_index": profile.h_index}


def collaboration_network_viz(profile: CareerProfile) -> dict:
    nodes = [{"id": profile.user_id, "label": profile.name or "You", "type": "self",
               "weight": profile.h_index}]
    edges = []
    for i in range(min(profile.collaboration_count, 10)):
        nid = f"collab_{i+1}"
        nodes.append({"id": nid, "label": f"Collaborator {i+1}", "type": "collaborator", "weight": 1})
        edges.append({"source": profile.user_id, "target": nid, "weight": 1})
    return {"type": VizType.COLLABORATION_NETWORK.value, "nodes": nodes, "edges": edges,
            "total_collaborators": profile.collaboration_count,
            "international_ratio": profile.international_collab_ratio}


def career_readiness_viz(profile: CareerProfile) -> dict:
    dims = {
        "Research Output":   min(profile.publication_count / 50.0, 1.0),
        "Research Impact":   min(profile.h_index / 20.0, 1.0),
        "Grant Activity":    min(profile.grant_count / 5.0, 1.0),
        "Collaboration":     min(profile.collaboration_count / 20.0, 1.0),
        "Teaching":          1.0 if profile.teaching_areas else 0.0,
        "International":     min(profile.international_collab_ratio / 0.5, 1.0),
    }
    overall = round(sum(dims.values()) / len(dims), 3)
    return {"type": VizType.CAREER_READINESS.value,
            "dimensions": [{"name": k, "score": round(v, 3)} for k, v in dims.items()],
            "overall_readiness": overall}


def promotion_readiness_viz(readiness: PromotionReadiness) -> dict:
    total = len(readiness.requirements_met) + len(readiness.requirements_missing)
    return {
        "type":    VizType.PROMOTION_READINESS.value,
        "target":  readiness.target.value,
        "overall": readiness.overall_readiness,
        "met":     readiness.requirements_met,
        "missing": readiness.requirements_missing,
        "gauge":   {"value": readiness.overall_readiness, "max": 1.0},
        "bar":     [
            {"label": "Requirements met",     "count": len(readiness.requirements_met)},
            {"label": "Requirements missing", "count": len(readiness.requirements_missing)},
        ],
        "estimated_months": readiness.estimated_months,
    }


def research_impact_viz(profile: CareerProfile) -> dict:
    return {
        "type": VizType.RESEARCH_IMPACT.value,
        "metrics": [
            {"name": "H-index",      "value": profile.h_index},
            {"name": "Publications", "value": profile.publication_count},
            {"name": "Citations",    "value": profile.citation_count},
        ],
        "productivity_score": profile.productivity_score,
        "quality_score":      profile.quality_score,
        "impact_score":       profile.impact_score,
        "overall_score":      profile.overall_score,
    }


def development_roadmap_viz(roadmap: CareerRoadmap) -> dict:
    year = _now_year()
    timeline = {}
    for m in roadmap.milestones:
        y = year + m.year
        timeline.setdefault(y, []).append({
            "type": m.milestone_type.value, "description": m.description, "priority": m.priority,
        })
    return {
        "type":     VizType.DEVELOPMENT_ROADMAP.value,
        "horizon":  roadmap.horizon.value,
        "stage":    roadmap.career_stage.value,
        "timeline": [{"year": k, "milestones": v} for k, v in sorted(timeline.items())],
        "key_focus": roadmap.key_focus_areas,
    }


# ── Dispatch ──────────────────────────────────────────────────────────────────

def build_visualization(
    viz_type: str,
    profile: CareerProfile | None = None,
    roadmap: CareerRoadmap | None = None,
    goals: list[dict] | None = None,
    skill_report: SkillGapReport | None = None,
    readiness: PromotionReadiness | None = None,
) -> dict:
    """Main dispatch function for visualization requests."""
    try:
        vt = VizType(viz_type)
    except ValueError:
        return {"error": f"Unknown visualization type: {viz_type}"}

    if vt == VizType.CAREER_TIMELINE:
        return career_timeline_viz(profile or _empty_profile(), roadmap)
    if vt == VizType.GOAL_PROGRESS:
        return goal_progress_viz(goals or [])
    if vt == VizType.SKILL_RADAR:
        if skill_report is None:
            return {"type": vt.value, "data": []}
        return skill_radar_viz(skill_report)
    if vt == VizType.PUBLICATION_GROWTH:
        return publication_growth_viz(profile or _empty_profile())
    if vt == VizType.CITATION_GROWTH:
        return citation_growth_viz(profile or _empty_profile())
    if vt == VizType.COLLABORATION_NETWORK:
        return collaboration_network_viz(profile or _empty_profile())
    if vt == VizType.CAREER_READINESS:
        return career_readiness_viz(profile or _empty_profile())
    if vt == VizType.PROMOTION_READINESS:
        if readiness is None:
            return {"type": vt.value, "data": []}
        return promotion_readiness_viz(readiness)
    if vt == VizType.RESEARCH_IMPACT:
        return research_impact_viz(profile or _empty_profile())
    if vt == VizType.DEVELOPMENT_ROADMAP:
        if roadmap is None:
            return {"type": vt.value, "data": []}
        return development_roadmap_viz(roadmap)
    return {"error": f"Unhandled viz type: {viz_type}"}


def _empty_profile() -> CareerProfile:
    return CareerProfile(user_id="unknown", career_stage=CareerStage.RESEARCHER)
