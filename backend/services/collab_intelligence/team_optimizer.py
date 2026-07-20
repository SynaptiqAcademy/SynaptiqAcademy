"""Research Collaboration Intelligence — Team Optimizer (Phase XIV).

Greedy coverage algorithm that maximises expertise coverage + diversity
while minimising skill gaps for a given research objective.
"""
from __future__ import annotations

from .models import (
    CareerStage, ResearcherProfile, TeamComposition, TeamMember, TeamType,
)
from .matching_engine import match_researchers

# Max team sizes per type
_TEAM_SIZE: dict[TeamType, int] = {
    TeamType.GRANT:           5,
    TeamType.JOURNAL:         4,
    TeamType.CONFERENCE:      4,
    TeamType.DOCTORAL:        3,
    TeamType.TEACHING:        4,
    TeamType.INNOVATION:      6,
    TeamType.INDUSTRY:        5,
    TeamType.INTERNATIONAL:   6,
    TeamType.INTERDISCIPLINARY: 6,
}

# Required skills/concepts for each team type
_REQUIRED_CONCEPTS: dict[TeamType, list[str]] = {
    TeamType.GRANT:           ["research_planning", "writing", "statistics", "methodology", "grant"],
    TeamType.JOURNAL:         ["writing", "methodology", "statistics", "peer_review"],
    TeamType.DOCTORAL:        ["supervision", "methodology", "writing"],
    TeamType.TEACHING:        ["curriculum_design", "lecturing", "assessment"],
    TeamType.INNOVATION:      ["commercialization", "project_management", "writing"],
    TeamType.INDUSTRY:        ["project_management", "innovation", "commercialization"],
    TeamType.INTERNATIONAL:   ["international", "writing", "methodology"],
}


def _coverage(team: list[ResearcherProfile]) -> set[str]:
    """Union of all expertise concepts across team members."""
    covered: set[str] = set()
    for p in team:
        covered.update(p.all_interests())
        covered.update(p.all_methods())
        covered.update(p.all_skills())
        if p.competency_graph:
            covered.update(p.competency_graph.all_concepts())
    return covered


def _diversity(team: list[ResearcherProfile]) -> float:
    """Diversity = fraction of unique institutions + countries, normalised."""
    institutions = {p.institution.lower() for p in team if p.institution}
    countries    = {p.country.lower()      for p in team if p.country}
    n = len(team)
    if n <= 1:
        return 0.0
    inst_div  = min(len(institutions) / n, 1.0)
    cntr_div  = min(len(countries)    / n, 1.0)
    stage_set = {p.career_stage for p in team}
    stage_div = min(len(stage_set) / len(CareerStage), 1.0)
    return round((inst_div * 0.4 + cntr_div * 0.4 + stage_div * 0.2), 3)


def _score_candidate(
    candidate: ResearcherProfile,
    current_team: list[ResearcherProfile],
    required_coverage: set[str],
) -> float:
    """Score how much value a candidate adds to the current team."""
    current_cov   = _coverage(current_team)
    with_cand_cov = _coverage(current_team + [candidate])

    # How many new skills does candidate add?
    new_skills = len(with_cand_cov - current_cov)
    # How many required skills does candidate cover?
    req_filled = len(required_coverage & (with_cand_cov - current_cov))
    # Diversity bonus
    div_bonus = _diversity(current_team + [candidate]) - _diversity(current_team)

    return new_skills * 0.4 + req_filled * 0.4 + div_bonus * 0.2


def _assign_role(profile: ResearcherProfile, team_type: TeamType, idx: int) -> str:
    if idx == 0:
        return "Principal Investigator"
    if profile.career_stage in (CareerStage.SENIOR, CareerStage.MID_CAREER) and idx == 1:
        return "Co-Investigator"
    if profile.career_stage == CareerStage.POSTDOC:
        return "Postdoctoral Researcher"
    if profile.career_stage == CareerStage.STUDENT:
        return "PhD Student"
    if team_type == TeamType.TEACHING:
        return "Teaching Fellow"
    return "Researcher"


def build_team(
    candidates: list[ResearcherProfile],
    objective: str,
    team_type: TeamType = TeamType.INTERDISCIPLINARY,
    required_concepts: list[str] | None = None,
    max_size: int | None = None,
) -> TeamComposition:
    """Greedy team builder: maximise coverage + diversity for the objective."""
    if not candidates:
        return TeamComposition(
            objective=objective,
            team_type=team_type,
            skill_gaps=["No candidates provided"],
        )

    size_limit  = max_size or _TEAM_SIZE.get(team_type, 5)
    req_set     = set(required_concepts or []) | set(_REQUIRED_CONCEPTS.get(team_type, []))

    # Sort by impact score → start with highest-impact researcher
    pool = sorted(candidates, key=lambda p: -p.impact_score)
    team: list[ResearcherProfile] = []

    # Greedy selection
    while len(team) < size_limit and pool:
        best: ResearcherProfile | None = None
        best_score = -1.0
        for candidate in pool:
            s = _score_candidate(candidate, team, req_set)
            if s > best_score:
                best_score = s
                best = candidate
        if best is None:
            break
        team.append(best)
        pool.remove(best)

    if not team:
        return TeamComposition(objective=objective, team_type=team_type)

    # Build members list with roles
    members = [
        TeamMember(
            user_id=p.user_id,
            name=p.name,
            role=_assign_role(p, team_type, i),
            expertise_coverage=list(p.all_interests())[:5],
            contribution_weight=round((p.impact_score * 0.5 + p.quality_score * 0.5 + 0.1), 3),
        )
        for i, p in enumerate(team)
    ]

    team_coverage = _coverage(team)
    all_required  = set(_REQUIRED_CONCEPTS.get(team_type, []))
    skill_gaps    = sorted(all_required - team_coverage)[:5]

    # Strengths: top covered concepts
    top_interests = sorted(
        team_coverage, key=lambda c: sum(1 for p in team if c in p.all_interests()), reverse=True
    )[:5]

    avg_impact    = sum(p.impact_score   for p in team) / len(team)
    avg_quality   = sum(p.quality_score  for p in team) / len(team)
    avg_h_index   = sum(p.h_index        for p in team) / len(team)

    # Predicted outputs
    pred_productivity  = round(min(avg_impact + len(team) * 0.05, 1.0), 3)
    pred_grant         = round(min(avg_impact * 0.8 + _diversity(team) * 0.2, 1.0), 3)
    pred_pub_quality   = round(min(avg_quality * 0.7 + avg_h_index / 20.0 * 0.3, 1.0), 3)

    coverage_ratio = len(team_coverage) / max(len(req_set), 1)

    return TeamComposition(
        objective=objective,
        team_type=team_type,
        members=members,
        overall_score=round(min(coverage_ratio, 1.0) * 0.4 + _diversity(team) * 0.3 + avg_impact * 0.3, 3),
        expertise_coverage=round(min(coverage_ratio, 1.0), 3),
        diversity_score=_diversity(team),
        skill_gaps=skill_gaps,
        strengths=top_interests,
        predicted_productivity=pred_productivity,
        predicted_grant_success=pred_grant,
        predicted_publication_quality=pred_pub_quality,
    )
