"""Research Collaboration Intelligence — Collaboration Prediction Engine (Phase XIV).

Logistic-style weighted scoring model predicting collaboration success,
publication probability, and grant probability.
"""
from __future__ import annotations

import math

from .models import CollabPrediction, ResearcherProfile
from .matching_engine import match_researchers


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _predict_success(m_score: float, a: ResearcherProfile, b: ResearcherProfile) -> float:
    """Collaboration success probability."""
    # Features: match score, both active, availability, response rate
    z = (
        m_score * 3.5
        - 1.5
        + (a.publication_count > 0) * 0.3
        + (b.publication_count > 0) * 0.3
        + a.availability * 0.5
        + b.availability * 0.5
        + a.response_rate * 0.4
        + b.response_rate * 0.4
        - (a.collaboration_count == 0 and b.collaboration_count == 0) * 0.5
    )
    return round(min(_sigmoid(z), 0.97), 3)


def _predict_publication(
    m_score: float,
    a: ResearcherProfile,
    b: ResearcherProfile,
    success_prob: float,
) -> float:
    z = (
        m_score * 2.5
        - 1.0
        + a.quality_score * 0.8
        + b.quality_score * 0.8
        + a.h_index / 20.0 * 0.5
        + b.h_index / 20.0 * 0.5
        + success_prob * 0.5
    )
    return round(min(_sigmoid(z), 0.95), 3)


def _predict_grant(
    m_score: float,
    a: ResearcherProfile,
    b: ResearcherProfile,
    diversity_score: float,
) -> float:
    a_grant = a.competency_graph.grant_success_rate if a.competency_graph else 0.0
    b_grant = b.competency_graph.grant_success_rate if b.competency_graph else 0.0
    z = (
        (a_grant + b_grant) * 2.0
        - 0.8
        + m_score * 1.5
        + diversity_score * 1.2
        + a.impact_score * 0.5
        + b.impact_score * 0.5
    )
    return round(min(_sigmoid(z), 0.90), 3)


def _citation_growth(a: ResearcherProfile, b: ResearcherProfile, pub_prob: float) -> float:
    avg_annual = (a.citation_count + b.citation_count) / 2 * 0.15  # 15% growth proxy
    collab_multiplier = 1.4  # collaboration typically boosts citations 40%
    return round(avg_annual * collab_multiplier * pub_prob, 1)


def _long_term_potential(
    success_prob: float,
    pub_prob: float,
    a: ResearcherProfile,
    b: ResearcherProfile,
) -> float:
    """Estimate 5-year collaboration potential."""
    return round(min(
        success_prob * 0.4
        + pub_prob * 0.3
        + (a.impact_score + b.impact_score) / 2 * 0.3,
        1.0,
    ), 3)


def _risk_factors(a: ResearcherProfile, b: ResearcherProfile, m_score: float) -> list[str]:
    risks: list[str] = []
    if a.availability < 0.3 or b.availability < 0.3:
        risks.append("Low availability — coordination may be challenging")
    if a.response_rate < 0.5 or b.response_rate < 0.5:
        risks.append("Low response rate — communication delays likely")
    if a.country != b.country and a.country and b.country:
        risks.append("Time zone differences may affect collaboration pace")
    if a.career_stage.value in ("student", "postdoc") and b.career_stage.value in ("student", "postdoc"):
        risks.append("Both early-career — limited institutional resources and network")
    if m_score < 0.45:
        risks.append("Moderate research alignment — ensure shared objectives before committing")
    return risks


def _success_factors(a: ResearcherProfile, b: ResearcherProfile, m_score: float) -> list[str]:
    factors: list[str] = []
    shared = a.all_interests() & b.all_interests()
    if shared:
        factors.append(f"Shared research interests: {', '.join(sorted(shared)[:3])}")
    if a.h_index + b.h_index > 20:
        factors.append("Combined strong research impact (h-index)")
    if a.country != b.country and a.country and b.country:
        factors.append("International diversity → citation boost potential")
    if a.institution != b.institution and a.institution and b.institution:
        factors.append("Cross-institutional resources and networks")
    a_g = a.competency_graph.grant_success_rate if a.competency_graph else 0
    b_g = b.competency_graph.grant_success_rate if b.competency_graph else 0
    if a_g + b_g > 0.5:
        factors.append("Strong combined grant track record")
    if m_score > 0.7:
        factors.append("High compatibility score → strong collaboration fit")
    return factors


def predict_collaboration(
    a: ResearcherProfile,
    b: ResearcherProfile,
) -> CollabPrediction:
    m          = match_researchers(a, b)
    m_score    = m.overall_score
    div        = m.diversity_score

    success    = _predict_success(m_score, a, b)
    pub        = _predict_publication(m_score, a, b, success)
    grant      = _predict_grant(m_score, a, b, div)
    cite_growth = _citation_growth(a, b, pub)
    long_term  = _long_term_potential(success, pub, a, b)

    # Estimate time to first output
    if m_score > 0.7 and a.publication_count > 5 and b.publication_count > 5:
        months = 8
    elif m_score > 0.5:
        months = 12
    else:
        months = 18

    # Confidence: based on how much profile data we have
    data_completeness = (
        (bool(a.domains) + bool(b.domains)) / 2.0 * 0.3
        + (bool(a.methods) + bool(b.methods)) / 2.0 * 0.2
        + (a.publication_count > 0) * 0.25
        + (b.publication_count > 0) * 0.25
    )
    confidence = round(min(0.5 + data_completeness * 0.5, 0.95), 3)

    return CollabPrediction(
        researcher_a_id=a.user_id,
        researcher_b_id=b.user_id,
        success_probability=success,
        publication_probability=pub,
        grant_probability=grant,
        expected_citation_growth=cite_growth,
        long_term_potential=long_term,
        risk_factors=_risk_factors(a, b, m_score),
        success_factors=_success_factors(a, b, m_score),
        confidence=confidence,
        time_to_first_output_months=months,
    )
