"""Research Collaboration Intelligence — Team Simulator (Phase XIV).

Simulates expected research outputs, strengths, and weaknesses of a
given team composition before commitment.
"""
from __future__ import annotations

from .models import ResearcherProfile, TeamSimulation
from .team_optimizer import _coverage, _diversity


def simulate_team(
    profiles: list[ResearcherProfile],
    objective: str,
) -> TeamSimulation:
    """Simulate expected outcomes for a team of researchers."""
    if not profiles:
        return TeamSimulation(
            team_member_ids=[],
            objective=objective,
            recommendations=["No team members provided — add researchers to simulate."],
        )

    n = len(profiles)

    # Coverage and diversity
    coverage_set = _coverage(profiles)
    div_score    = _diversity(profiles)

    # Aggregate scores
    avg_productivity = sum(p.productivity_score for p in profiles) / n
    avg_quality      = sum(p.quality_score      for p in profiles) / n
    avg_impact       = sum(p.impact_score        for p in profiles) / n
    avg_availability = sum(p.availability        for p in profiles) / n
    total_h          = sum(p.h_index             for p in profiles)
    total_pubs       = sum(p.publication_count   for p in profiles)

    # Estimated outputs
    expected_productivity = round(
        min(avg_productivity * 0.5 + min(n / 6.0, 1.0) * 0.3 + avg_availability * 0.2, 1.0), 3
    )
    pub_quality = round(min(avg_quality * 0.7 + total_h / (n * 20.0) * 0.3, 1.0), 3)

    # Grant competitiveness: needs diversity + impact
    grant_score = round(
        min(avg_impact * 0.4 + div_score * 0.3 + min(n / 5.0, 1.0) * 0.3, 1.0), 3
    )

    # Expertise coverage as fraction of objective keywords covered
    objective_tokens = set(objective.lower().split())
    covered_obj = {t for t in objective_tokens if any(t in c for c in coverage_set)}
    coverage_frac = round(len(covered_obj) / max(len(objective_tokens), 1), 3)
    expertise_cov = round((len(coverage_set) / 50.0 * 0.5 + coverage_frac * 0.5), 3)

    # Skill gaps — keywords in objective not covered
    skill_gaps = sorted(
        t for t in objective_tokens
        if not any(t in c for c in coverage_set) and len(t) > 3
    )[:5]

    # Potential weaknesses
    weaknesses: list[str] = []
    if avg_availability < 0.4:
        weaknesses.append("Low team availability — meetings and deadlines may be challenging")
    if n < 3:
        weaknesses.append("Small team — limited bandwidth and perspective diversity")
    institutions = {p.institution.lower() for p in profiles if p.institution}
    if len(institutions) == 1:
        weaknesses.append("All members from same institution — limited external perspectives")
    countries = {p.country.lower() for p in profiles if p.country}
    if len(countries) == 1:
        weaknesses.append("No international collaboration — weakens funding competitiveness")
    if all(p.career_stage.value in ("student", "postdoc") for p in profiles):
        weaknesses.append("No senior researcher — team may lack institutional leadership")

    # Recommendations
    recommendations: list[str] = []
    if expertise_cov < 0.5:
        recommendations.append("Consider adding researchers with expertise in: " + ", ".join(skill_gaps[:3]))
    if div_score < 0.3:
        recommendations.append("Add international members to increase funding competitiveness")
    if pub_quality > 0.7:
        recommendations.append("Strong publication quality — target high-impact journals (Q1)")
    if grant_score > 0.65:
        recommendations.append("Competitive grant team — apply for EU Horizon or NSF funding")
    if n > 6:
        recommendations.append("Large team — assign clear roles and a dedicated project coordinator")
    if not recommendations:
        recommendations.append("Well-balanced team — proceed with research objectives")

    return TeamSimulation(
        team_member_ids=[p.user_id for p in profiles],
        objective=objective,
        expected_productivity=expected_productivity,
        publication_quality_estimate=pub_quality,
        grant_competitiveness=grant_score,
        expertise_coverage=min(expertise_cov, 1.0),
        diversity_score=div_score,
        skill_gaps=skill_gaps,
        potential_weaknesses=weaknesses,
        recommendations=recommendations,
    )
