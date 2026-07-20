"""Academic Career Intelligence — Research Productivity Analyzer (Phase XVI)."""
from __future__ import annotations

from .models import CareerProfile, ProductivityMetrics


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def analyse_productivity(profile: CareerProfile) -> ProductivityMetrics:
    """Compute detailed research productivity metrics from a CareerProfile."""
    years  = max(profile.years_active, 1)
    pubs   = profile.publication_count
    cites  = profile.citation_count
    grants = profile.grant_count

    # Publications per year
    pub_per_year = pubs / years

    # Citation growth rate (proxy: cites per publication)
    cites_per_pub = cites / max(pubs, 1)
    # Normalise to ~0–1: 20 cites/pub ≈ top quartile
    cite_growth = _clamp(cites_per_pub / 20.0)

    # Research diversity (number of distinct research areas)
    research_diversity = len(set(profile.research_areas))

    # Collaboration diversity
    collaboration_diversity = profile.collaboration_count

    # Grant activity (0–1 score)
    grant_activity = _clamp(grants / 5.0)

    # H-index trajectory proxy (h / years)
    h_trajectory = _clamp(profile.h_index / max(years, 1) / 3.0)

    # Output score (normalise pub/year: 5/year = excellent)
    output_score = _clamp(pub_per_year / 5.0)

    # Impact score (citations + h-index blend)
    impact_score = _clamp(cites_per_pub / 20.0 * 0.5 + profile.h_index / 30.0 * 0.5)

    # Consistency score (proxy: average of output and grant activity)
    consistency_score = _clamp((output_score + grant_activity) / 2.0)

    # Overall productivity
    overall = _clamp(
        output_score      * 0.25 +
        impact_score      * 0.30 +
        h_trajectory      * 0.15 +
        grant_activity    * 0.15 +
        consistency_score * 0.15
    )

    return ProductivityMetrics(
        user_id=profile.user_id,
        publications_per_year=round(pub_per_year, 2),
        citation_growth_rate=round(cite_growth, 3),
        research_diversity=research_diversity,
        collaboration_diversity=collaboration_diversity,
        grant_activity=round(grant_activity, 3),
        h_index_trajectory=round(h_trajectory, 3),
        output_score=round(output_score, 3),
        impact_score=round(impact_score, 3),
        consistency_score=round(consistency_score, 3),
        overall_productivity=round(overall, 3),
    )
