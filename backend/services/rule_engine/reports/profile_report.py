"""Template-based profile quality and research reports."""
from __future__ import annotations

from typing import Any

from ..scoring.profile_score import calculate_profile_score
from ..scoring.research_score import calculate_research_score
from ..alerts.alert_engine import generate_profile_alerts, generate_publication_alerts
from ..recommendations.profile_recommender import get_profile_recommendations
from ..calculators.h_index import citation_summary
from ..utils.date_utils import utcnow


def generate_profile_report(
    profile: dict,
    publications: list[dict] | None = None,
    include_recommendations: bool = True,
) -> dict[str, Any]:
    """Generate a comprehensive profile quality report."""
    pubs = publications or []
    citation_counts = [int(p.get("citation_count") or 0) for p in pubs]

    profile_score = calculate_profile_score(profile)
    research_score = calculate_research_score(
        publications=int(profile.get("publications_count") or len(pubs)),
        citations=sum(citation_counts),
        h_index=int(profile.get("h_index") or 0),
        grants_awarded=int(profile.get("grants_awarded_count") or 0),
        reviews_completed=int(profile.get("reviews_completed") or 0),
        collaborations=int(profile.get("collaboration_count") or 0),
        career_years=float(profile.get("career_years") or 1),
    )
    cit_summary = citation_summary(citation_counts) if citation_counts else {}
    alerts = generate_profile_alerts(profile)
    if pubs:
        alerts.extend(generate_publication_alerts(pubs, profile))
    recs = get_profile_recommendations(profile) if include_recommendations else []

    return {
        "generated_at": utcnow().isoformat(),
        "user_id": str(profile.get("_id") or profile.get("id", "")),
        "full_name": profile.get("full_name", ""),
        "profile_completeness": profile_score.to_dict(),
        "research_productivity": research_score.to_dict(),
        "citation_summary": cit_summary,
        "active_alerts": [a.to_dict() for a in alerts],
        "top_recommendations": [r.to_dict() for r in recs[:5]] if include_recommendations else [],
        "summary": _build_summary_text(profile_score.score, research_score.score, alerts),
    }


def generate_research_impact_report(
    profile: dict,
    publications: list[dict],
    citation_history: list[dict] | None = None,
) -> dict[str, Any]:
    """Generate a research impact summary report."""
    from ..analytics.publication_analytics import (
        compute_publication_trends, compute_productivity_rate, compute_collaboration_patterns,
    )
    from ..analytics.citation_analytics import compute_per_publication_stats, compute_citation_milestones
    from ..calculators.impact_calculator import (
        sis_research_output, sis_citation_impact, compute_sis,
    )

    citation_counts = [int(p.get("citation_count") or 0) for p in publications]
    total_cit = sum(citation_counts)
    h_index = int(profile.get("h_index") or 0)

    pub_trends = compute_publication_trends(publications)
    productivity = compute_productivity_rate(
        publications,
        career_start_year=int(profile.get("career_start_year") or
                               utcnow().year - max(int(profile.get("career_years") or 1), 1)),
    )
    collab_patterns = compute_collaboration_patterns(publications)
    cit_stats = compute_per_publication_stats(publications)
    milestones = compute_citation_milestones(total_cit)

    # Quick SIS approximation
    sis_research = sis_research_output(
        n_published=sum(1 for p in publications if p.get("status") == "published"),
        n_submitted=sum(1 for p in publications if p.get("status") == "submitted"),
        n_drafted=sum(1 for p in publications if p.get("status") == "draft"),
    )
    sis_cit = sis_citation_impact(h_index=h_index, total_citations=total_cit)

    return {
        "generated_at": utcnow().isoformat(),
        "user_id": str(profile.get("_id") or profile.get("id", "")),
        "publication_trends": pub_trends,
        "productivity": productivity,
        "collaboration_patterns": collab_patterns,
        "citation_stats": cit_stats,
        "citation_milestones": milestones,
        "sis_components": {
            "research_output": round(sis_research, 1),
            "citation_impact": round(sis_cit, 1),
        },
    }


def _build_summary_text(profile_score: float, research_score: float, alerts: list) -> str:
    critical = sum(1 for a in alerts if a.level == "critical")
    warnings = sum(1 for a in alerts if a.level == "warning")

    lines: list[str] = []
    if profile_score >= 80:
        lines.append(f"Your profile is highly complete ({profile_score:.0f}/100).")
    elif profile_score >= 50:
        lines.append(f"Your profile is moderately complete ({profile_score:.0f}/100).")
    else:
        lines.append(f"Your profile needs significant improvement ({profile_score:.0f}/100).")

    if research_score >= 70:
        lines.append(f"Research productivity is strong ({research_score:.0f}/100).")
    elif research_score >= 40:
        lines.append(f"Research productivity is developing ({research_score:.0f}/100).")
    else:
        lines.append(f"Research productivity needs attention ({research_score:.0f}/100).")

    if critical:
        lines.append(f"There are {critical} critical issue(s) requiring immediate action.")
    elif warnings:
        lines.append(f"There are {warnings} warning(s) to address.")
    else:
        lines.append("No critical issues detected.")

    return " ".join(lines)
