"""10-dimension opportunity scoring engine for Research Gap Intelligence.

Computes and normalises overall opportunity scores. Each dimension is separately
explainable. The overall_score combines all 9 dimensions via fixed weights.
"""
from __future__ import annotations

from .models import DetectedGap, GapType, GapSeverity, OpportunityScore
from .taxonomy import SCORE_WEIGHTS, GAP_METADATA


def score_gap(gap: DetectedGap) -> DetectedGap:
    """Compute or refine the opportunity score for a gap and return the enriched gap."""
    os = gap.opportunity_score

    # ── Dimension adjustments based on gap type ────────────────────────────────
    meta = GAP_METADATA.get(gap.gap_type, {})

    # Anchor novel score to taxonomy baseline if AI left it default-ish
    if os.novelty_score < 0.01:
        os.novelty_score = meta.get("base_novelty", 0.60)
    if os.research_impact < 0.01:
        os.research_impact = meta.get("base_impact", 0.60)
    if os.funding_potential < 0.01:
        os.funding_potential = meta.get("base_funding", 0.55)

    # Confidence adjusts novelty (lower confidence → lower effective novelty)
    os.novelty_score = _blend(os.novelty_score, gap.confidence_score, w=0.15)

    # Severity adjusts impact
    severity_multiplier = {
        GapSeverity.CRITICAL: 1.15,
        GapSeverity.HIGH: 1.05,
        GapSeverity.MEDIUM: 1.00,
        GapSeverity.LOW: 0.90,
    }.get(gap.severity, 1.00)
    os.research_impact = _clamp(os.research_impact * severity_multiplier)

    # Interdisciplinary gaps get boosted interdisciplinary_potential
    if gap.gap_type == GapType.INTERDISCIPLINARY:
        os.interdisciplinary_potential = max(os.interdisciplinary_potential, 0.85)

    # AI/tech gaps get commercialisation boost
    if gap.gap_type in (GapType.AI_GAP, GapType.TECHNOLOGICAL, GapType.DIGITAL_TRANSFORMATION):
        os.commercialization_potential = max(os.commercialization_potential, 0.60)

    # Healthcare/policy gaps get funding boost
    if gap.gap_type in (GapType.HEALTHCARE, GapType.POLICY, GapType.SUSTAINABILITY):
        os.funding_potential = max(os.funding_potential, 0.72)

    # ── Compute overall score ─────────────────────────────────────────────────
    os.overall_score = _weighted_overall(os)

    gap.opportunity_score = os
    return gap


def score_all(gaps: list[DetectedGap]) -> list[DetectedGap]:
    """Score all gaps and return sorted by overall_score descending."""
    scored = [score_gap(g) for g in gaps]
    return sorted(scored, key=lambda g: -g.opportunity_score.overall_score)


def compute_field_metrics(gaps: list[DetectedGap]) -> tuple[float, float]:
    """Return (field_novelty_index, field_opportunity_score) across all gaps."""
    if not gaps:
        return 0.0, 0.0
    noveltys = [g.opportunity_score.novelty_score for g in gaps]
    overalls = [g.opportunity_score.overall_score for g in gaps]
    return (
        round(sum(noveltys) / len(noveltys), 3),
        round(sum(overalls) / len(overalls), 3),
    )


def _weighted_overall(os: OpportunityScore) -> float:
    """Weighted combination of all 9 active dimensions."""
    total = (
        os.novelty_score * SCORE_WEIGHTS["novelty_score"]
        + os.publication_probability * SCORE_WEIGHTS["publication_probability"]
        + os.research_impact * SCORE_WEIGHTS["research_impact"]
        + os.feasibility_score * SCORE_WEIGHTS["feasibility_score"]
        + os.funding_potential * SCORE_WEIGHTS["funding_potential"]
        + os.citation_potential * SCORE_WEIGHTS["citation_potential"]
        + os.interdisciplinary_potential * SCORE_WEIGHTS["interdisciplinary_potential"]
        + (1.0 - os.implementation_difficulty) * SCORE_WEIGHTS["implementation_difficulty_inv"]
        + os.commercialization_potential * SCORE_WEIGHTS["commercialization_potential"]
    )
    return _clamp(round(total, 4))


def _blend(base: float, modifier: float, w: float = 0.20) -> float:
    """Blend base value with modifier: base*(1-w) + modifier*w."""
    return _clamp(base * (1 - w) + modifier * w)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))
