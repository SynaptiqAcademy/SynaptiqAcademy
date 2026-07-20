"""Deterministic peer-review quality scoring."""
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


_LABELS = [(85, "Expert Reviewer"), (65, "Experienced Reviewer"),
           (45, "Active Reviewer"), (20, "Junior Reviewer"), (0, "Inactive")]


def calculate_reviewer_score(
    reviews_completed: int = 0,
    avg_turnaround_days: float = 14.0,
    avg_quality_rating: float = 0.0,
    declined_invitations: int = 0,
    accepted_invitations: int = 0,
) -> ScoreResult:
    volume_pts = _sat(reviews_completed, scale=8.0)

    # Speed: ≤7 days = 1.2×, 8–14 = 1.0×, 15–30 = 0.85×, >30 = 0.70×
    if avg_turnaround_days <= 7:
        speed_mult = 1.20
    elif avg_turnaround_days <= 14:
        speed_mult = 1.00
    elif avg_turnaround_days <= 30:
        speed_mult = 0.85
    else:
        speed_mult = 0.70

    quality_mult = 0.85 + 0.30 * min(avg_quality_rating / 5.0, 1.0)

    acceptance_rate = (
        accepted_invitations / max(accepted_invitations + declined_invitations, 1)
    )
    acceptance_bonus = min(acceptance_rate * 10.0, 10.0)

    raw = volume_pts * speed_mult * quality_mult + acceptance_bonus
    score = round(min(raw, 100.0), 1)
    label = next(lbl for threshold, lbl in _LABELS if score >= threshold)

    recommendations: list[str] = []
    if reviews_completed == 0:
        recommendations.append("Accept review invitations to build your reviewer profile.")
    if avg_turnaround_days > 21:
        recommendations.append("Aim to complete reviews within 14 days to improve turnaround score.")
    if avg_quality_rating > 0 and avg_quality_rating < 3.5:
        recommendations.append("Provide more detailed feedback to improve quality ratings.")

    return ScoreResult(
        score=score,
        label=label,
        breakdown={
            "reviews_completed": reviews_completed,
            "volume_points": round(volume_pts, 2),
            "speed_multiplier": speed_mult,
            "quality_multiplier": round(quality_mult, 3),
            "acceptance_bonus": round(acceptance_bonus, 2),
            "avg_turnaround_days": avg_turnaround_days,
            "avg_quality_rating": avg_quality_rating,
        },
        recommendations=recommendations,
    )
