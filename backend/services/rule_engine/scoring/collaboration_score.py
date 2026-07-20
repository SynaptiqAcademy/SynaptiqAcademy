"""Deterministic collaboration and community scoring."""
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


_LABELS = [(80, "Leader"), (60, "Active"), (40, "Engaged"), (20, "Beginning"), (0, "Inactive")]


def calculate_collaboration_score(
    owned_collaborations: int = 0,
    accepted_applications: int = 0,
    workspace_members: int = 0,
    completion_rate: float = 0.0,
    international_partners: int = 0,
    active_projects: int = 0,
) -> ScoreResult:
    """Mirrors logic from services/reputation/scorer.py with unified interface."""
    base = (
        owned_collaborations * 1.0
        + accepted_applications * 1.5
        + workspace_members * 0.5
        + active_projects * 0.8
    )
    quality_multiplier = 0.85 + 0.30 * min(completion_rate, 1.0)
    intl_bonus = min(international_partners * 5.0, 20.0)

    raw = _sat(base, scale=8.0) * quality_multiplier + intl_bonus
    score = round(min(raw, 100.0), 1)
    label = next(lbl for threshold, lbl in _LABELS if score >= threshold)

    recommendations: list[str] = []
    if owned_collaborations == 0:
        recommendations.append("Post your first collaboration opportunity to attract partners.")
    if completion_rate < 0.5 and owned_collaborations > 0:
        recommendations.append("Focus on completing existing collaborations to improve your completion rate.")
    if international_partners == 0:
        recommendations.append("Seek international collaborators to diversify your network.")

    return ScoreResult(
        score=score,
        label=label,
        breakdown={
            "owned_collaborations": owned_collaborations,
            "accepted_applications": accepted_applications,
            "workspace_members": workspace_members,
            "completion_rate": round(completion_rate, 2),
            "international_partners": international_partners,
            "quality_multiplier": round(quality_multiplier, 3),
        },
        recommendations=recommendations,
    )
