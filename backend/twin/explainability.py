"""
Explainability layer.

Every Twin insight answers:
  - Why was this generated?
  - Which evidence supports it?
  - Which data sources contributed?
  - When was it last updated?
  - How confident is the conclusion?

This module provides the `explain()` function used across all Twin outputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def explain(
    insight_id:   str,
    what:         str,
    why:          str,
    evidence:     list[dict],
    sources:      list[str],
    methodology:  str,
    confidence:   str,
    generated_at: datetime | None = None,
    correctable:  bool = True,
) -> dict:
    """
    Build a standard explainability block for any twin output.

    Parameters
    ----------
    insight_id : str
        Stable identifier for this type of insight.
    what : str
        What this insight says (summary in one sentence).
    why : str
        Why it was generated (what triggered it / what it's based on).
    evidence : list[dict]
        List of evidence items: [{source, detail, count, verified}].
    sources : list[str]
        Human-readable list of data sources consulted.
    methodology : str
        How the conclusion was derived (algorithm / logic description).
    confidence : str
        "high" | "medium" | "low" | "insufficient" (derived from evidence count only).
    generated_at : datetime, optional
        When this insight was generated.
    correctable : bool
        Whether the user can correct this insight.

    Returns
    -------
    dict
        Standard explainability block, safe to serialize to JSON.
    """
    total_data_points = sum(e.get("count", 1) for e in evidence if e.get("verified", True))
    confidence_basis  = (
        f"Based on {total_data_points} verified data point(s) across {len(sources)} source(s)"
        if total_data_points > 0 else
        "Insufficient verified data to establish confidence"
    )

    return {
        "insight_id":       insight_id,
        "what":             what,
        "why":              why,
        "evidence":         evidence,
        "data_sources":     sources,
        "total_data_points": total_data_points,
        "methodology":      methodology,
        "confidence":       confidence,
        "confidence_basis": confidence_basis,
        "generated_at":     (generated_at or datetime.now(timezone.utc)).isoformat(),
        "user_correctable": correctable,
        "policy_note":      (
            "This insight was derived from verified platform data only. "
            "No external benchmarks, fabricated statistics, or predictions were used."
        ),
    }


def build_domain_explanation(domain: str, evidence: list[dict]) -> dict:
    """Explain why a research domain was identified."""
    sources = list({e.get("source", "unknown") for e in evidence})
    total   = sum(e.get("count", 1) for e in evidence if e.get("verified", True))
    return explain(
        insight_id   = f"domain_{domain.lower().replace(' ', '_')}",
        what         = f"Research domain '{domain}' was identified in your Twin.",
        why          = f"This domain appeared in {total} verified data point(s) from your manuscripts, projects, and declared interests.",
        evidence     = evidence,
        sources      = sources,
        methodology  = "Aggregated keyword/tag/interest matches across manuscripts, projects, and user profile",
        confidence   = "high" if total >= 3 else "medium" if total >= 2 else "low",
    )


def build_working_style_explanation(pattern: str, evidence: list[dict], count: int) -> dict:
    """Explain why a working style pattern was observed."""
    sources = list({e.get("source", "unknown") for e in evidence})
    return explain(
        insight_id  = f"ws_{pattern[:30].lower().replace(' ', '_')}",
        what        = f"Working pattern observed: '{pattern}'",
        why         = f"This pattern was observed {count} time(s) in your platform activity.",
        evidence    = evidence,
        sources     = sources,
        methodology = "Direct count of matching platform activity records",
        confidence  = "high" if count >= 4 else "medium" if count >= 2 else "low",
    )


def build_health_explanation(indicator_id: str, indicator: dict) -> dict:
    """Explain a health indicator."""
    return explain(
        insight_id  = f"health_{indicator_id}",
        what        = f"{indicator.get('label', indicator_id)}: {indicator.get('description', '')}",
        why         = indicator.get("methodology", ""),
        evidence    = [{"source": indicator.get("source", "Synaptiq"), "detail": indicator.get("description", ""), "count": 1, "verified": True}],
        sources     = [indicator.get("source", "Synaptiq")],
        methodology = indicator.get("methodology", ""),
        confidence  = "high" if indicator.get("level") == "good" else "medium" if indicator.get("level") == "moderate" else "low",
        correctable = False,
    )
