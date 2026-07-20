"""Transparent Citation Impact Score calculator.

Formula (user-level):
  40% Citation Volume   — log-normalised total citations
  25% Citation Growth   — weighted recent delta vs. historical baseline
  20% Collaboration Impact — co-author network breadth from publications
  15% Recency Impact    — recency-weighted citation accumulation

Each component is returned with its exact value and the reasoning, so the UI
can display a complete, auditable breakdown to the user.

Per-publication scores follow the same decomposition but use single-pub data.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────── helpers ─────────────────────────────────────────

def _now_year() -> int:
    return datetime.now(timezone.utc).year


def _sat(x: float, scale: float) -> float:
    """Saturation curve: approaches 100 exponentially. x must be >= 0."""
    return round(min(100.0, 100.0 * (1.0 - math.exp(-max(0.0, x) / scale))), 2)


# ─────────────────────────── user-level score ─────────────────────────────────

def compute_user_impact_score(
    *,
    total_citations:  int,
    h_index:          int,
    i10_index:        int,
    works_count:      int,
    enriched_count:   int,
    # delta stats (from publication_citations snapshots)
    recent_delta:     int = 0,
    prev_total:       int = 0,
    # collaboration: unique co-author count across all publications
    unique_coauthors: int = 0,
    # recency: list of (year, citations) for each publication
    pub_years_citations: Optional[list[tuple[int, int]]] = None,
) -> dict:
    """Compute the transparent 40/25/20/15 composite impact score.

    Returns a dict with: score, components (each with value + reasoning),
    and weights so the UI can render a full breakdown.
    """
    current_year = _now_year()
    pub_years_citations = pub_years_citations or []

    # ── 40% Citation Volume ───────────────────────────────────────────────────
    # log-normalised against a reference scale (500 = ~63 points)
    citation_volume = _sat(math.log1p(total_citations), scale=4.0)
    volume_reasoning = (
        f"You have {total_citations:,} total citation{'s' if total_citations != 1 else ''}. "
        f"Score uses log-saturation (500 cit. ≈ 63 pts, 5 000 ≈ 86 pts, 50 000 ≈ 97 pts)."
    )

    # ── 25% Citation Growth ───────────────────────────────────────────────────
    # growth = recent_delta / (baseline + 1), capped and log-scaled
    baseline = max(1, prev_total)
    growth_ratio = recent_delta / baseline
    citation_growth = _sat(growth_ratio * 10, scale=2.0)  # 20 % growth ≈ 63 pts
    if recent_delta == 0:
        growth_reasoning = "No recent citation change recorded. Sync to detect new citations."
    else:
        pct = round(growth_ratio * 100, 1)
        growth_reasoning = (
            f"+{recent_delta} citations since last snapshot "
            f"({pct}% growth over baseline of {prev_total:,}). "
            f"20%+ growth earns max growth score."
        )

    # ── 20% Collaboration Impact ──────────────────────────────────────────────
    # log-scaled unique co-authors across all publications
    collab_impact = _sat(math.log1p(unique_coauthors), scale=2.5)
    if unique_coauthors == 0:
        collab_reasoning = "No co-author data found. Sync publications with OpenAlex to populate."
    else:
        collab_reasoning = (
            f"{unique_coauthors} unique co-author{'s' if unique_coauthors != 1 else ''} "
            f"across your publications. Broader networks score higher "
            f"(25 co-authors ≈ 63 pts, 100 ≈ 86 pts)."
        )

    # ── 15% Recency Impact ────────────────────────────────────────────────────
    # exponential decay: papers published recently contribute more weight
    # weight = exp(-0.1 * age_years); then sum(weight * citations) / max_possible
    if pub_years_citations:
        weighted_sum   = sum(
            math.exp(-0.1 * max(0, current_year - yr)) * cit
            for yr, cit in pub_years_citations
        )
        max_possible   = sum(cit for _, cit in pub_years_citations) or 1
        recency_ratio  = weighted_sum / max_possible
        recency_impact = round(min(100.0, recency_ratio * 120), 2)
        newest_year    = max(yr for yr, _ in pub_years_citations)
        recency_reasoning = (
            f"Most recent publication: {newest_year}. "
            f"Recent publications contribute exponentially more to this component. "
            f"Recency weight: {round(recency_ratio * 100, 1)}% of max possible."
        )
    else:
        recency_impact    = 0.0
        recency_reasoning = "No publication year data. Ensure publications are synced."

    # ── composite ─────────────────────────────────────────────────────────────
    composite = round(
        0.40 * citation_volume +
        0.25 * citation_growth +
        0.20 * collab_impact   +
        0.15 * recency_impact,
        1,
    )

    return {
        "score": int(composite),
        "formula": "40% Citation Volume + 25% Citation Growth + 20% Collaboration Impact + 15% Recency Impact",
        "components": {
            "citation_volume": {
                "value":     citation_volume,
                "weight":    0.40,
                "contribution": round(0.40 * citation_volume, 1),
                "label":     "Citation Volume",
                "reasoning": volume_reasoning,
            },
            "citation_growth": {
                "value":     citation_growth,
                "weight":    0.25,
                "contribution": round(0.25 * citation_growth, 1),
                "label":     "Citation Growth",
                "reasoning": growth_reasoning,
            },
            "collaboration_impact": {
                "value":     collab_impact,
                "weight":    0.20,
                "contribution": round(0.20 * collab_impact, 1),
                "label":     "Collaboration Impact",
                "reasoning": collab_reasoning,
            },
            "recency_impact": {
                "value":     recency_impact,
                "weight":    0.15,
                "contribution": round(0.15 * recency_impact, 1),
                "label":     "Recency Impact",
                "reasoning": recency_reasoning,
            },
        },
    }


# ─────────────────────────── per-publication score ────────────────────────────

def compute_publication_impact_score(
    *,
    citations:        int,
    year:             Optional[int],
    coauthor_count:   int = 0,
    recent_delta:     int = 0,
    prev_count:       int = 0,
) -> dict:
    """Transparent impact score for a single publication."""
    current_year = _now_year()

    # Citation Volume
    citation_volume = _sat(math.log1p(citations), scale=3.5)

    # Growth
    baseline = max(1, prev_count)
    growth_ratio = recent_delta / baseline
    citation_growth = _sat(growth_ratio * 10, scale=2.0)

    # Collaboration
    collab_impact = _sat(math.log1p(coauthor_count), scale=2.5)

    # Recency
    if year and isinstance(year, int):
        age = max(0, current_year - year)
        decay = math.exp(-0.05 * age)
        recency_impact = round(decay * 100, 2)
        recency_reasoning = f"Published {year} ({age} year{'s' if age != 1 else ''} ago). Decay: {round(decay * 100, 1)}% of max."
    else:
        recency_impact    = 0.0
        recency_reasoning = "Publication year unknown."

    composite = round(
        0.40 * citation_volume +
        0.25 * citation_growth +
        0.20 * collab_impact   +
        0.15 * recency_impact,
        1,
    )

    # citation velocity (citations per year since publication)
    if year and isinstance(year, int):
        age_years = max(1, current_year - year)
        velocity  = round(citations / age_years, 2)
    else:
        velocity  = 0.0

    # growth rate (% change from prev snapshot)
    if prev_count > 0:
        growth_rate = round((citations - prev_count) / prev_count * 100, 1)
    else:
        growth_rate = 0.0

    return {
        "score":       int(composite),
        "formula":     "40% Citation Volume + 25% Citation Growth + 20% Collaboration Impact + 15% Recency Impact",
        "velocity":    velocity,
        "growth_rate": growth_rate,
        "recent_delta": recent_delta,
        "components": {
            "citation_volume": {
                "value":        citation_volume,
                "weight":       0.40,
                "contribution": round(0.40 * citation_volume, 1),
                "label":        "Citation Volume",
                "reasoning":    f"{citations:,} citations. Log-saturation scale (100 cit. ≈ 47 pts).",
            },
            "citation_growth": {
                "value":        citation_growth,
                "weight":       0.25,
                "contribution": round(0.25 * citation_growth, 1),
                "label":        "Citation Growth",
                "reasoning":    f"+{recent_delta} new vs. baseline {prev_count}." if recent_delta else "No recent change.",
            },
            "collaboration_impact": {
                "value":        collab_impact,
                "weight":       0.20,
                "contribution": round(0.20 * collab_impact, 1),
                "label":        "Collaboration Impact",
                "reasoning":    f"{coauthor_count} co-author{'s' if coauthor_count != 1 else ''}.",
            },
            "recency_impact": {
                "value":        recency_impact,
                "weight":       0.15,
                "contribution": round(0.15 * recency_impact, 1),
                "label":        "Recency Impact",
                "reasoning":    recency_reasoning,
            },
        },
    }
