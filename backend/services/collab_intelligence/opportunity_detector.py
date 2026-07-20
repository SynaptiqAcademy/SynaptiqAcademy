"""Research Collaboration Intelligence — Collaboration Opportunity Detector (Phase XIV)."""
from __future__ import annotations

from .models import (
    CareerStage, CollabOpportunity, OpportunityType, ResearcherProfile,
)
from .matching_engine import match_researchers


def _co_author_opportunity(
    source: ResearcherProfile,
    candidate: ResearcherProfile,
    match_score: float,
) -> CollabOpportunity | None:
    if match_score < 0.4:
        return None
    shared = sorted(source.all_interests() & candidate.all_interests())[:4]
    return CollabOpportunity(
        opportunity_type=OpportunityType.CO_AUTHOR,
        target_researcher_id=candidate.user_id,
        target_name=candidate.name,
        score=match_score,
        reason=(
            f"Strong research alignment (score {match_score:.2f}). "
            f"Shared interests: {', '.join(shared) if shared else 'overlapping domains'}."
        ),
        shared_interests=shared,
        complementary_skills=sorted(
            (source.all_skills() | source.all_methods()) ^ (candidate.all_skills() | candidate.all_methods())
        )[:4],
        action_recommended="Send a collaboration request to explore co-authorship.",
    )


def _mentor_opportunity(
    source: ResearcherProfile,
    candidate: ResearcherProfile,
) -> CollabOpportunity | None:
    senior_stages = {CareerStage.MID_CAREER, CareerStage.SENIOR}
    junior_stages = {CareerStage.STUDENT, CareerStage.POSTDOC, CareerStage.EARLY_CAREER}
    if candidate.career_stage not in senior_stages or source.career_stage not in junior_stages:
        return None
    shared = sorted(source.all_interests() & candidate.all_interests())[:3]
    if not shared:
        return None
    return CollabOpportunity(
        opportunity_type=OpportunityType.MENTOR,
        target_researcher_id=candidate.user_id,
        target_name=candidate.name,
        score=min(candidate.h_index / 20.0 * 0.5 + len(shared) / 5.0 * 0.5, 1.0),
        reason=f"Mentorship opportunity: {candidate.name} is an experienced researcher in your field.",
        shared_interests=shared,
        action_recommended="Request mentorship to accelerate your research career.",
    )


def _supervisor_opportunity(
    source: ResearcherProfile,
    candidate: ResearcherProfile,
) -> CollabOpportunity | None:
    if source.career_stage not in {CareerStage.STUDENT, CareerStage.POSTDOC}:
        return None
    if candidate.career_stage not in {CareerStage.SENIOR, CareerStage.MID_CAREER}:
        return None
    shared = sorted(source.all_interests() & candidate.all_interests())[:3]
    # Career stage match alone is sufficient for supervision (different fields can mentor)
    cg = candidate.competency_graph
    has_supervision = cg and any(
        n.concept == "supervision" for n in cg.teaching_skills
    )
    # Accept if any of: shared interests, supervision skill detected, or candidate has high impact
    if not shared and not has_supervision and candidate.impact_score < 0.1:
        return None
    return CollabOpportunity(
        opportunity_type=OpportunityType.SUPERVISOR,
        target_researcher_id=candidate.user_id,
        target_name=candidate.name,
        score=min(candidate.impact_score * 0.6 + len(shared) / 5.0 * 0.4, 1.0),
        reason=f"Doctoral supervision opportunity with {candidate.name}.",
        shared_interests=shared,
        action_recommended="Request doctoral supervision or research guidance.",
    )


def _grant_partner_opportunity(
    source: ResearcherProfile,
    candidate: ResearcherProfile,
    match_score: float,
) -> CollabOpportunity | None:
    if match_score < 0.35:
        return None
    c_grant = (candidate.competency_graph.grant_success_rate if candidate.competency_graph else 0)
    s_grant = (source.competency_graph.grant_success_rate    if source.competency_graph else 0)
    combined = c_grant + s_grant
    if combined < 0.1 and match_score < 0.6:
        return None
    return CollabOpportunity(
        opportunity_type=OpportunityType.GRANT_PARTNER,
        target_researcher_id=candidate.user_id,
        target_name=candidate.name,
        score=round(match_score * 0.6 + combined * 0.4, 3),
        reason=f"Grant collaboration opportunity. Combined grant success rate: {combined:.0%}.",
        shared_interests=sorted(source.all_interests() & candidate.all_interests())[:3],
        action_recommended="Explore grant collaboration — submit a joint funding application.",
    )


def _peer_reviewer_opportunity(
    source: ResearcherProfile,
    candidate: ResearcherProfile,
) -> CollabOpportunity | None:
    cg = candidate.competency_graph
    if not cg or cg.peer_review_count < 3:
        return None
    shared = sorted(source.all_interests() & candidate.all_interests())[:3]
    if not shared:
        return None
    return CollabOpportunity(
        opportunity_type=OpportunityType.PEER_REVIEWER,
        target_researcher_id=candidate.user_id,
        target_name=candidate.name,
        score=round(min(cg.peer_review_count / 20.0, 1.0) * 0.5 + len(shared) / 5.0 * 0.5, 3),
        reason=f"{candidate.name} is an experienced peer reviewer in your field.",
        shared_interests=shared,
        action_recommended="Invite as peer reviewer for your next manuscript.",
    )


def _international_opportunity(
    source: ResearcherProfile,
    candidate: ResearcherProfile,
    match_score: float,
) -> CollabOpportunity | None:
    if not source.country or not candidate.country:
        return None
    if source.country.lower() == candidate.country.lower():
        return None
    if match_score < 0.35:
        return None
    return CollabOpportunity(
        opportunity_type=OpportunityType.INTERNATIONAL,
        target_researcher_id=candidate.user_id,
        target_name=candidate.name,
        score=round(match_score * 0.7 + 0.3, 3),
        reason=(
            f"International collaboration with {candidate.name} "
            f"({candidate.country}). Cross-border partnerships boost citation impact."
        ),
        shared_interests=sorted(source.all_interests() & candidate.all_interests())[:3],
        action_recommended="Initiate an international research partnership.",
    )


def detect_opportunities(
    source: ResearcherProfile,
    candidates: list[ResearcherProfile],
    top_n: int = 10,
) -> list[CollabOpportunity]:
    """Detect all opportunity types across the candidate pool."""
    opportunities: list[CollabOpportunity] = []

    for candidate in candidates:
        if candidate.user_id == source.user_id:
            continue
        m = match_researchers(source, candidate)
        score = m.overall_score

        # Co-author
        opp = _co_author_opportunity(source, candidate, score)
        if opp:
            opportunities.append(opp)

        # Mentor
        opp = _mentor_opportunity(source, candidate)
        if opp:
            opportunities.append(opp)

        # Supervisor
        opp = _supervisor_opportunity(source, candidate)
        if opp:
            opportunities.append(opp)

        # Grant partner
        opp = _grant_partner_opportunity(source, candidate, score)
        if opp:
            opportunities.append(opp)

        # Peer reviewer
        opp = _peer_reviewer_opportunity(source, candidate)
        if opp:
            opportunities.append(opp)

        # International
        opp = _international_opportunity(source, candidate, score)
        if opp:
            opportunities.append(opp)

    # Deduplicate by target_id (keep best score per target per type)
    seen: dict[tuple[str, str], CollabOpportunity] = {}
    for opp in opportunities:
        key = (opp.target_researcher_id, opp.opportunity_type.value)
        if key not in seen or opp.score > seen[key].score:
            seen[key] = opp

    return sorted(seen.values(), key=lambda o: -o.score)[:top_n]
