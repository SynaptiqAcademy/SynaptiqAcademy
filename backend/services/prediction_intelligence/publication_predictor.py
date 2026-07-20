"""Academic Prediction — Publication outcome predictor (Phase XVIII)."""
from __future__ import annotations

import math

from .confidence_model import compute_confidence, data_completeness, signal_quality
from .models import (
    PredictionType, PublicationPrediction, _make_prediction,
)

_PUB_KEYS = [
    "word_count", "reference_count", "methodology_score", "novelty_score",
    "statistical_quality", "scope_match", "authors", "target_journal",
]


def _quality_composite(m: dict) -> float:
    """Overall manuscript quality score in [0, 1]."""
    wc       = m.get("word_count", 5000)
    word_ok  = 1.0 if 3000 <= wc <= 12000 else max(0.3, 1.0 - abs(wc - 7000) / 15000)
    ref_q    = min(m.get("reference_count", 30) / 50.0, 1.0)
    meth     = float(m.get("methodology_score", 0.5))
    novelty  = float(m.get("novelty_score", 0.5))
    stat     = float(m.get("statistical_quality", 0.5))

    authors  = m.get("authors", [])
    if authors:
        max_h   = max(a.get("h_index", 0) for a in authors)
        auth_rep = min(max_h / 30.0, 1.0)
    else:
        auth_rep = 0.1

    return max(0.0, min(1.0, (
        0.25 * max(0.0, min(1.0, meth)) +
        0.20 * max(0.0, min(1.0, novelty)) +
        0.15 * max(0.0, min(1.0, stat)) +
        0.15 * ref_q +
        0.15 * word_ok +
        0.10 * auth_rep
    )))


def predict_publication(manuscript: dict) -> PublicationPrediction:
    """Predict full outcome set for a manuscript."""
    m   = manuscript or {}
    jnl = m.get("target_journal") or {}

    q              = _quality_composite(m)
    scope_match    = max(0.0, min(1.0, float(m.get("scope_match", 0.65))))
    base_rate      = max(0.01, min(0.99, float(jnl.get("acceptance_rate", 0.30))))
    prior_subs     = int(m.get("prior_submissions", 0))
    sub_penalty    = max(0.50, 1.0 - prior_subs * 0.08)
    novelty        = max(0.0, min(1.0, float(m.get("novelty_score", 0.5))))
    if_score       = max(0.5, float(jnl.get("impact_factor", 2.0)))

    # Acceptance probability
    acc = base_rate + (q - 0.5) * 0.40 + (scope_match - 0.5) * 0.10
    acc = max(0.02, min(0.96, acc * sub_penalty))

    # Desk rejection — high if low scope match or very low quality
    desk_rej = max(0.01, (1.0 - scope_match) * 0.60 + (1.0 - q) * 0.20 - 0.05)
    desk_rej = min(0.90, desk_rej)

    # Major revision — peaks for medium quality
    major_rev = max(0.03, min(0.65, 0.30 + (0.5 - abs(q - 0.55)) * 0.50))
    major_rev = major_rev * (1.0 - acc)

    # Minor revision
    minor_rev = max(0.02, min(0.45, acc * 0.40 + q * 0.10))

    # Review time
    avg_rev_wk    = max(4.0, float(jnl.get("avg_review_weeks", 12)))
    exp_rev_wk    = avg_rev_wk * (1.0 + (1.0 - q) * 0.50)

    # Acceptance time = review + possible revision round
    exp_acc_mo    = exp_rev_wk / 4.3 + (1.5 if major_rev > 0.25 else 0.5)

    # Publication time
    exp_pub_mo    = exp_acc_mo + 3.0  # production

    # Delay risk
    delay         = max(0.0, min(1.0, (1.0 - acc) * 0.65 + (1.0 - q) * 0.35))

    # Citation velocity (first year)
    cit_vel       = max(0.0, if_score * q * novelty * 2.5)

    # Citation growth 3 years
    cit_3y        = max(0.0, cit_vel * 3.0 * (1.0 + novelty * 0.40))

    # Long-term impact (1-10 scale, stored as raw value)
    lt_impact     = min(10.0, if_score * novelty * q * 4.0)

    # Confidence
    dc   = data_completeness(m, _PUB_KEYS)
    sq   = signal_quality(q, scope_match, novelty)
    conf = compute_confidence(dc, sq, "publication_acceptance")
    time_conf = compute_confidence(dc, signal_quality(q), "review_time")
    cit_conf  = compute_confidence(dc, signal_quality(novelty, q), "citation_velocity")

    # Evidence
    evidence = [
        f"Manuscript quality score: {round(q, 2)}",
        f"Journal acceptance rate: {round(base_rate * 100)}%",
        f"Scope match: {round(scope_match * 100)}%",
        f"Prior submissions to this journal: {prior_subs}",
    ]
    if m.get("authors"):
        max_h = max(a.get("h_index", 0) for a in m["authors"])
        evidence.append(f"Lead author h-index: {max_h}")

    # Recommendation
    if acc >= 0.60:
        rec = "Strong manuscript — submit now. High acceptance probability."
    elif acc >= 0.40:
        rec = "Good manuscript — consider minor revisions before submission."
    elif desk_rej >= 0.50:
        rec = "High desk-rejection risk — revise scope alignment or target another journal."
    else:
        rec = "Substantial revisions needed — strengthen methodology and novelty before submission."

    return PublicationPrediction(
        acceptance=_make_prediction(
            PredictionType.PUBLICATION_ACCEPTANCE, acc, conf,
            evidence=evidence,
            risk_factors=[f"Prior submissions: {prior_subs}", "Peer review uncertainty"],
            recommendations=["Polish abstract", "Ensure scope alignment"],
            reasoning=f"Base rate {round(base_rate*100)}%, quality-adjusted to {round(acc*100)}%.",
        ),
        desk_rejection=_make_prediction(
            PredictionType.DESK_REJECTION, desk_rej, conf,
            evidence=[f"Scope match: {round(scope_match*100)}%", f"Quality: {round(q*100)}%"],
            risk_factors=["Low scope alignment", "Low novelty"],
            recommendations=["Align abstract with journal aims", "Emphasise novelty upfront"],
            reasoning="Desk rejection risk driven by scope alignment and manuscript quality.",
        ),
        major_revision=_make_prediction(
            PredictionType.MAJOR_REVISION, major_rev, conf * 0.85,
            evidence=[f"Methodology score: {round(float(m.get('methodology_score', 0.5))*100)}%"],
            reasoning="Major revision likelihood inversely proportional to acceptance probability.",
        ),
        minor_revision=_make_prediction(
            PredictionType.MINOR_REVISION, minor_rev, conf * 0.80,
            evidence=[f"Statistical quality: {round(float(m.get('statistical_quality', 0.5))*100)}%"],
            reasoning="Minor revision probability scales with acceptance likelihood.",
        ),
        expected_review_weeks=_make_prediction(
            PredictionType.REVIEW_TIME, exp_rev_wk, time_conf,
            unit="weeks", clamp_probability=False,
            reasoning=f"Journal average {avg_rev_wk:.0f} wk, adjusted for manuscript quality.",
        ),
        expected_acceptance_months=_make_prediction(
            PredictionType.ACCEPTANCE_TIME, exp_acc_mo, time_conf,
            unit="months", clamp_probability=False,
            reasoning="Review time plus expected revision round.",
        ),
        expected_publication_months=_make_prediction(
            PredictionType.PUBLICATION_TIME, exp_pub_mo, time_conf * 0.90,
            unit="months", clamp_probability=False,
            reasoning="Acceptance time plus production pipeline (~3 months).",
        ),
        delay_risk=_make_prediction(
            PredictionType.DELAY_RISK, delay, conf,
            evidence=["Low acceptance increases revision cycles"],
            reasoning="Delay risk driven by acceptance probability and quality.",
        ),
        citation_velocity_y1=_make_prediction(
            PredictionType.CITATION_VELOCITY, cit_vel, cit_conf,
            unit="citations/year", clamp_probability=False,
            reasoning=f"IF {if_score:.1f} × quality {round(q,2)} × novelty {round(novelty,2)}.",
        ),
        citation_growth_3y=_make_prediction(
            PredictionType.CITATION_GROWTH, cit_3y, cit_conf * 0.85,
            unit="citations", clamp_probability=False,
            reasoning="Three-year citation accumulation with novelty growth multiplier.",
        ),
        long_term_impact=_make_prediction(
            PredictionType.LONG_TERM_IMPACT, lt_impact, cit_conf * 0.70,
            unit="impact_score", clamp_probability=False,
            reasoning="Long-term impact on 1–10 scale based on IF, novelty, and quality.",
        ),
        overall_confidence=round(conf, 3),
        strategic_recommendation=rec,
        manuscript_score=round(q, 3),
    )
