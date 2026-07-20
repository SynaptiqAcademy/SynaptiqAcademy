"""Academic Prediction — Grant funding predictor (Phase XVIII)."""
from __future__ import annotations

from .confidence_model import compute_confidence, data_completeness, signal_quality
from .models import GrantPrediction, PredictionType, _make_prediction

_GRANT_KEYS = [
    "novelty_score", "relevance_to_priorities", "preliminary_data_score",
    "methodology_rigor", "budget_justification_score", "pi_h_index",
]

_BASE_SUCCESS_RATE = 0.20  # typical grant success across schemes


def _quality_composite(g: dict) -> float:
    return max(0.0, min(1.0, (
        0.25 * float(g.get("novelty_score", 0.5)) +
        0.20 * float(g.get("relevance_to_priorities", 0.5)) +
        0.20 * float(g.get("preliminary_data_score", 0.5)) +
        0.20 * float(g.get("methodology_rigor", 0.5)) +
        0.15 * float(g.get("budget_justification_score", 0.5))
    )))


def _missing_partners(g: dict) -> list[str]:
    gaps: list[str] = []
    if g.get("international_partners", 0) == 0:
        gaps.append("International collaborators — strengthen global impact narrative.")
    if g.get("industry_partners", 0) == 0 and g.get("grant_type", "") == "applied":
        gaps.append("Industry partners — applied grants benefit from industry validation.")
    if g.get("team_size", 1) < 3:
        gaps.append("Larger team — multi-PI grants score higher on feasibility.")
    return gaps


def predict_grant(grant: dict) -> GrantPrediction:
    g = grant or {}

    q            = _quality_composite(g)
    pi_h         = int(g.get("pi_h_index", 0))
    pi_track     = min(pi_h / 25.0, 1.0) * 0.10
    collab       = min(int(g.get("collaboration_breadth", 0)) / 5.0, 1.0) * 0.05
    prior_grants = min(int(g.get("prior_grants", 0)) / 5.0, 1.0) * 0.05

    funding_prob = max(0.01, min(0.90,
        _BASE_SUCCESS_RATE + (q - 0.5) * 0.35 + pi_track + collab + prior_grants
    ))

    # Competitiveness (how the proposal ranks against peers)
    competitiveness = max(0.0, min(1.0, q * 0.70 + pi_track * 2.0 + collab * 2.0))

    # Evaluation score (1-10 normalized to 0-1)
    eval_score = max(0.0, min(1.0,
        q * 0.60 + pi_track * 2.0 + 0.10 * float(g.get("preliminary_data_score", 0.5))
    ))

    # Budget adequacy
    budget     = float(g.get("budget_requested", 100000))
    br         = g.get("typical_budget_range") or [50000, 500000]
    mid        = (float(br[0]) + float(br[1])) / 2.0
    budget_adeq = max(0.0, min(1.0, 1.0 - abs(budget - mid) / max(mid, 1)))

    # Reviewer concerns
    concerns: list[str] = []
    if float(g.get("preliminary_data_score", 0.5)) < 0.5:
        concerns.append("Preliminary data is insufficient — reviewers will likely request more evidence.")
    if float(g.get("novelty_score", 0.5)) < 0.45:
        concerns.append("Novelty of research questions needs stronger justification.")
    if float(g.get("relevance_to_priorities", 0.5)) < 0.50:
        concerns.append("Alignment with funding priorities is weak — revise specific aims.")
    if budget_adeq < 0.5:
        concerns.append("Budget may be over/under the expected range — justify carefully.")
    if not concerns:
        concerns.append("Standard reviewer scrutiny on feasibility and timeline expected.")

    # Required improvements
    improvements: list[str] = []
    if q < 0.6:
        improvements.append("Strengthen methodology section with power calculations.")
    if float(g.get("relevance_to_priorities", 0.5)) < 0.65:
        improvements.append("Re-align specific aims with current funder priority areas.")
    if float(g.get("budget_justification_score", 0.5)) < 0.60:
        improvements.append("Improve budget justification with detailed cost breakdown.")
    if not improvements:
        improvements.append("Proposal is competitive — focus on clarity of deliverables.")

    # Missing partners
    missing = _missing_partners(g)

    # Confidence
    dc   = data_completeness(g, _GRANT_KEYS)
    sq   = signal_quality(q, float(g.get("preliminary_data_score", 0.5)))
    conf = compute_confidence(dc, sq, "funding_probability")

    evidence = [
        f"Proposal quality score: {round(q * 100)}%",
        f"PI h-index: {pi_h}",
        f"Prior grants: {g.get('prior_grants', 0)}",
        f"Collaboration breadth: {g.get('collaboration_breadth', 0)} institutions",
    ]

    return GrantPrediction(
        funding_probability=_make_prediction(
            PredictionType.FUNDING_PROBABILITY, funding_prob, conf,
            evidence=evidence,
            risk_factors=concerns,
            recommendations=improvements,
            reasoning=f"Base rate {round(_BASE_SUCCESS_RATE*100)}%, quality-boosted to {round(funding_prob*100)}%.",
        ),
        competitiveness=_make_prediction(
            PredictionType.GRANT_SCORE, competitiveness, conf,
            evidence=[f"Quality composite: {round(q,2)}", f"PI track record: {round(pi_track*10,1)}/10"],
            reasoning="Competitiveness based on quality, track record, and collaboration breadth.",
        ),
        evaluation_score=_make_prediction(
            PredictionType.GRANT_SCORE, eval_score, conf * 0.90,
            unit="score", reasoning="Predicted panel evaluation score (0=rejected, 1=top-rated).",
        ),
        budget_adequacy=_make_prediction(
            PredictionType.GRANT_SCORE, budget_adeq, conf * 0.85,
            evidence=[f"Budget requested: €{int(budget):,}", f"Expected range: €{int(br[0]):,}–€{int(br[1]):,}"],
            reasoning="Budget adequacy based on deviation from scheme mid-range.",
        ),
        reviewer_concerns=concerns,
        required_improvements=improvements,
        missing_partners=missing,
        expected_success_rate=round(funding_prob, 3),
        confidence=round(conf, 3),
    )
