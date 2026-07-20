"""Deterministic research productivity score — delegates math to existing services."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoreResult:
    score: float
    label: str = ""
    breakdown: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "label": self.label,
                "breakdown": self.breakdown, "recommendations": self.recommendations}


def _sat(value: float, scale: float = 10.0) -> float:
    if value <= 0:
        return 0.0
    return min(100.0, 100.0 * math.log(1 + value / scale) / math.log(2))


_LABELS = [(85, "Distinguished"), (70, "Advanced"), (55, "Established"),
           (35, "Emerging"), (0, "Early Stage")]


def calculate_research_score(
    publications: int = 0,
    citations: int = 0,
    h_index: int = 0,
    grants_awarded: int = 0,
    reviews_completed: int = 0,
    collaborations: int = 0,
    career_years: float = 1.0,
) -> ScoreResult:
    """0–100 research productivity score using weighted formula."""
    pub_pts     = _sat(publications / max(career_years, 1), scale=3.0) * 0.30
    cit_pts     = _sat(citations / max(career_years, 1), scale=15.0) * 0.25
    h_pts       = _sat(h_index, scale=8.0) * 0.20
    grant_pts   = _sat(grants_awarded, scale=1.0) * 0.15
    collab_pts  = _sat(collaborations, scale=3.0) * 0.05
    review_pts  = _sat(reviews_completed, scale=5.0) * 0.05

    total = pub_pts + cit_pts + h_pts + grant_pts + collab_pts + review_pts
    score = round(min(total, 100.0), 1)
    label = next(lbl for threshold, lbl in _LABELS if score >= threshold)

    recommendations: list[str] = []
    if publications < 3:
        recommendations.append("Publish your first peer-reviewed articles to establish a record.")
    if h_index == 0:
        recommendations.append("Work toward an h-index by publishing in indexed journals.")
    if grants_awarded == 0:
        recommendations.append("Apply for grant funding to strengthen your research profile.")
    if collaborations < 2:
        recommendations.append("Join collaborations to increase your citation network.")

    return ScoreResult(
        score=score,
        label=label,
        breakdown={
            "publications": round(pub_pts, 2),
            "citations": round(cit_pts, 2),
            "h_index": round(h_pts, 2),
            "grants": round(grant_pts, 2),
            "collaborations": round(collab_pts, 2),
            "reviews": round(review_pts, 2),
        },
        recommendations=recommendations,
    )
