"""Academic Career Intelligence — Promotion Readiness Assessor (Phase XVI).

Evaluates readiness for 8 promotion targets with requirement checklists.
"""
from __future__ import annotations

from .models import CareerProfile, CareerStage, PromotionReadiness, PromotionTarget

# ── Requirement definitions ───────────────────────────────────────────────────
# Each requirement is a (label, test_fn) pair

def _gte(field: str, threshold: float):
    def test(p: CareerProfile) -> bool:
        return float(getattr(p, field, 0)) >= threshold
    test.__doc__ = f"{field} >= {threshold}"
    return (f"{field.replace('_', ' ').title()} ≥ {threshold}", test)


def _req(label: str, fn):
    return (label, fn)


_REQUIREMENTS: dict[PromotionTarget, list[tuple[str, callable]]] = {

    PromotionTarget.PHD_COMPLETION: [
        ("Publication count ≥ 2",            lambda p: p.publication_count >= 2),
        ("Attended ≥ 2 conferences",          lambda p: p.conference_count >= 2),
        ("H-index ≥ 1",                       lambda p: p.h_index >= 1),
        ("Has research methods",              lambda p: len(p.research_methods) > 0),
    ],

    PromotionTarget.POSTDOC: [
        ("Publication count ≥ 4",             lambda p: p.publication_count >= 4),
        ("H-index ≥ 3",                       lambda p: p.h_index >= 3),
        ("At least 1 international collaboration", lambda p: p.international_collab_ratio > 0),
        ("Attended ≥ 3 conferences",          lambda p: p.conference_count >= 3),
    ],

    PromotionTarget.ASSISTANT_PROF: [
        ("Publication count ≥ 10",            lambda p: p.publication_count >= 10),
        ("H-index ≥ 6",                       lambda p: p.h_index >= 6),
        ("At least 1 grant",                  lambda p: p.grant_count >= 1),
        ("Teaching experience",               lambda p: len(p.teaching_areas) > 0),
        ("Collaboration network ≥ 5",         lambda p: p.collaboration_count >= 5),
        ("International collaboration ratio ≥ 0.2", lambda p: p.international_collab_ratio >= 0.2),
    ],

    PromotionTarget.ASSOCIATE_PROF: [
        ("Publication count ≥ 30",            lambda p: p.publication_count >= 30),
        ("H-index ≥ 12",                      lambda p: p.h_index >= 12),
        ("Grant count ≥ 3",                   lambda p: p.grant_count >= 3),
        ("Grant income ≥ €100K",              lambda p: p.grant_income >= 100_000),
        ("Teaching areas ≥ 2",                lambda p: len(p.teaching_areas) >= 2),
        ("Collaboration count ≥ 15",          lambda p: p.collaboration_count >= 15),
        ("Review count ≥ 10",                 lambda p: p.review_count >= 10),
    ],

    PromotionTarget.PROFESSOR: [
        ("Publication count ≥ 60",            lambda p: p.publication_count >= 60),
        ("H-index ≥ 20",                      lambda p: p.h_index >= 20),
        ("Citation count ≥ 2000",             lambda p: p.citation_count >= 2000),
        ("Grant count ≥ 5",                   lambda p: p.grant_count >= 5),
        ("Grant income ≥ €300K",              lambda p: p.grant_income >= 300_000),
        ("International collaboration ratio ≥ 0.4", lambda p: p.international_collab_ratio >= 0.4),
        ("Collaboration count ≥ 25",          lambda p: p.collaboration_count >= 25),
        ("Review count ≥ 25",                 lambda p: p.review_count >= 25),
    ],

    PromotionTarget.RESEARCH_DIRECTOR: [
        ("H-index ≥ 25",                      lambda p: p.h_index >= 25),
        ("Publication count ≥ 80",            lambda p: p.publication_count >= 80),
        ("Grant income ≥ €500K",              lambda p: p.grant_income >= 500_000),
        ("Grant count ≥ 8",                   lambda p: p.grant_count >= 8),
        ("Collaboration count ≥ 30",          lambda p: p.collaboration_count >= 30),
    ],

    PromotionTarget.DEPARTMENT_HEAD: [
        ("Professor-level publications (≥ 60)",lambda p: p.publication_count >= 60),
        ("H-index ≥ 20",                      lambda p: p.h_index >= 20),
        ("Administrative experience",         lambda p: p.career_stage in (
                                                  CareerStage.PROFESSOR, CareerStage.ASSOCIATE_PROF,
                                                  CareerStage.SENIOR_RESEARCHER)),
        ("Grant income ≥ €200K",              lambda p: p.grant_income >= 200_000),
        ("Collaboration count ≥ 20",          lambda p: p.collaboration_count >= 20),
    ],

    PromotionTarget.DEAN: [
        ("H-index ≥ 30",                      lambda p: p.h_index >= 30),
        ("Publication count ≥ 100",           lambda p: p.publication_count >= 100),
        ("Professor-level or equivalent",     lambda p: p.career_stage in (
                                                  CareerStage.PROFESSOR, CareerStage.ADMINISTRATOR,
                                                  CareerStage.SENIOR_RESEARCHER)),
        ("Grant income ≥ €1M",                lambda p: p.grant_income >= 1_000_000),
        ("Collaboration count ≥ 40",          lambda p: p.collaboration_count >= 40),
    ],
}

_ACTIONS: dict[str, str] = {
    "Publication count": "Increase publication rate by targeting 4+ papers per year.",
    "H-index": "Improve citation profile via open access and collaboration with highly-cited researchers.",
    "Grant": "Apply to national/EU funding calls; use institution's grant office support.",
    "Teaching": "Volunteer for module coordination and attend teaching certification.",
    "Collaboration": "Join research consortia and present at international conferences.",
    "International": "Pursue international mobility grants and co-authorship with overseas partners.",
    "Review": "Register on Publons and request review assignments from editors.",
    "Citation": "Increase citation visibility with preprints, data sharing, and social media.",
    "Administrative": "Take on departmental leadership roles or committee membership.",
}


def _action_for(label: str) -> str:
    for key, action in _ACTIONS.items():
        if key.lower() in label.lower():
            return action
    return "Address this requirement through targeted professional development."


def _estimate_months(readiness: float) -> int:
    if readiness >= 0.9:
        return 6
    if readiness >= 0.7:
        return 12
    if readiness >= 0.5:
        return 24
    if readiness >= 0.3:
        return 36
    return 60


def assess_promotion_readiness(profile: CareerProfile, target: PromotionTarget) -> PromotionReadiness:
    """
    Evaluate how ready a researcher is for a given promotion target.
    Returns overall readiness score 0–1, met/missing requirements, actions, and estimate.
    """
    reqs = _REQUIREMENTS.get(target, [])
    if not reqs:
        return PromotionReadiness(target=target, overall_readiness=0.0,
                                  requirements_missing=["Unknown promotion target"])

    met: list[str] = []
    missing: list[str] = []
    for label, test_fn in reqs:
        try:
            passed = test_fn(profile)
        except Exception:
            passed = False
        if passed:
            met.append(label)
        else:
            missing.append(label)

    overall = round(len(met) / max(len(reqs), 1), 3)
    actions = [_action_for(m) for m in missing][:5]
    estimated = _estimate_months(overall)

    return PromotionReadiness(
        target=target,
        overall_readiness=overall,
        requirements_met=met,
        requirements_missing=missing,
        recommended_actions=actions,
        confidence=min(0.95, overall + 0.05),
        estimated_months=estimated,
    )
