"""Deterministic teaching quality and productivity scoring."""
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


def _sat(v: float, scale: float) -> float:
    if v <= 0:
        return 0.0
    return min(100.0, 100.0 * math.log(1 + v / scale) / math.log(2))


_LABELS = [(85, "Master Educator"), (65, "Advanced Educator"),
           (45, "Active Educator"), (20, "Developing Educator"), (0, "Beginner")]


def calculate_teaching_score(
    published_lessons: int = 0,
    assessments_created: int = 0,
    portfolio_items: int = 0,
    workspace_messages: int = 0,
    educational_collaborations: int = 0,
    ai_sessions: int = 0,
    student_reviews: int = 0,
    avg_student_rating: float = 0.0,
) -> ScoreResult:
    """Mirrors logic from services/reputation/scorer.py _teaching_score."""
    content_pts  = _sat(published_lessons * 3.0 + assessments_created * 3.0, scale=15.0) * 0.35
    collab_pts   = _sat(educational_collaborations * 4.0 + workspace_messages * 0.3, scale=12.0) * 0.25
    portfolio_pt = _sat(portfolio_items * 2.0, scale=6.0) * 0.15
    ai_pts       = _sat(ai_sessions * 0.5, scale=5.0) * 0.10
    rating_pts   = (avg_student_rating / 5.0) * 15.0 if student_reviews > 0 else 0.0

    raw = content_pts + collab_pts + portfolio_pt + ai_pts + rating_pts
    score = round(min(raw, 100.0), 1)
    label = next(lbl for threshold, lbl in _LABELS if score >= threshold)

    recommendations: list[str] = []
    if published_lessons == 0:
        recommendations.append("Publish your first lesson to start building your teaching portfolio.")
    if assessments_created == 0:
        recommendations.append("Create assessments to enhance student engagement.")
    if educational_collaborations == 0:
        recommendations.append("Join an educational collaboration to expand your teaching network.")
    if portfolio_items < 3:
        recommendations.append("Add teaching materials to your portfolio.")

    return ScoreResult(
        score=score,
        label=label,
        breakdown={
            "published_lessons": published_lessons,
            "assessments_created": assessments_created,
            "educational_collaborations": educational_collaborations,
            "portfolio_items": portfolio_items,
            "content_points": round(content_pts, 2),
            "collaboration_points": round(collab_pts, 2),
            "portfolio_points": round(portfolio_pt, 2),
            "rating_points": round(rating_pts, 2),
        },
        recommendations=recommendations,
    )
