"""Academic Prediction — Confidence scoring engine (Phase XVIII).

Every prediction aggregates four independent signal sources:
  1. data_completeness  — how much of the input profile is filled
  2. signal_strength    — how predictive the available signals are
  3. historical_base    — calibration quality for this prediction type
  4. graph_evidence     — knowledge graph supporting evidence count
"""
from __future__ import annotations


# ── Base calibration per prediction type ─────────────────────────────────────

_BASE_CALIBRATION: dict[str, float] = {
    "publication_acceptance": 0.70,
    "desk_rejection":         0.65,
    "major_revision":         0.55,
    "minor_revision":         0.55,
    "review_time":            0.65,
    "acceptance_time":        0.60,
    "publication_time":       0.58,
    "delay_risk":             0.62,
    "citation_velocity":      0.60,
    "citation_growth":        0.55,
    "long_term_impact":       0.50,
    "funding_probability":    0.65,
    "grant_score":            0.62,
    "promotion_readiness":    0.68,
    "h_index_forecast":       0.62,
    "collaboration_success":  0.60,
    "trend_emergence":        0.55,
}


def compute_confidence(
    data_completeness: float,
    signal_strength: float,
    prediction_type: str = "",
    graph_evidence_count: int = 0,
) -> float:
    """Aggregate confidence for a prediction. Returns float in [0, 1]."""
    calibration = _BASE_CALIBRATION.get(prediction_type, 0.60)
    graph_evidence = min(graph_evidence_count / 10.0, 1.0)
    confidence = (
        0.35 * max(0.0, min(1.0, data_completeness)) +
        0.35 * max(0.0, min(1.0, signal_strength)) +
        0.15 * calibration +
        0.15 * graph_evidence
    )
    return max(0.05, min(0.95, confidence))


def data_completeness(profile: dict, required_keys: list[str]) -> float:
    """Fraction of required_keys that are non-None/non-empty in profile."""
    if not required_keys:
        return 0.5
    present = sum(
        1 for k in required_keys
        if profile.get(k) not in (None, "", [], {}, 0)
    )
    return present / len(required_keys)


def signal_quality(*signals: float) -> float:
    """Average of provided signal scores, each expected in [0, 1]."""
    valid = [max(0.0, min(1.0, s)) for s in signals if s is not None]
    return sum(valid) / max(len(valid), 1)
