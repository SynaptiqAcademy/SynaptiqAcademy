"""Deterministic institution quality scoring."""
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


def _sat(v: float, scale: float, cap: float = 100.0) -> float:
    if v <= 0:
        return 0.0
    return min(cap, cap * math.log(1 + v / scale) / math.log(2))


_LABELS = [(90, "World-Class"), (75, "Research-Intensive"), (60, "Established"),
           (40, "Growing"), (0, "Early Stage")]


def calculate_institution_score(
    active_researchers: int = 0,
    publications_count: int = 0,
    total_citations: int = 0,
    avg_h_index: float = 0.0,
    grants_awarded: int = 0,
    total_grant_value_usd: float = 0.0,
    international_collaborations: int = 0,
    departments: int = 0,
    verified: bool = False,
) -> ScoreResult:
    researchers_pts = _sat(active_researchers, scale=50.0) * 0.20
    pubs_pts        = _sat(publications_count, scale=200.0) * 0.20
    citations_pts   = _sat(total_citations, scale=5000.0) * 0.15
    h_pts           = _sat(avg_h_index, scale=15.0) * 0.15
    grants_pts      = _sat(grants_awarded, scale=10.0) * 0.10
    grant_val_pts   = _sat(total_grant_value_usd / 1_000_000, scale=5.0) * 0.10
    intl_pts        = _sat(international_collaborations, scale=20.0) * 0.05
    verified_bonus  = 5.0 if verified else 0.0
    dept_pts        = min(departments * 2.0, 5.0)

    raw = (researchers_pts + pubs_pts + citations_pts + h_pts + grants_pts
           + grant_val_pts + intl_pts + verified_bonus + dept_pts)
    score = round(min(raw, 100.0), 1)
    label = next(lbl for threshold, lbl in _LABELS if score >= threshold)

    recommendations: list[str] = []
    if not verified:
        recommendations.append("Verify your institution to unlock trust badges.")
    if active_researchers < 10:
        recommendations.append("Grow your researcher base by inviting faculty members.")
    if international_collaborations < 3:
        recommendations.append("Establish international collaborations to improve global reach.")
    if grants_awarded == 0:
        recommendations.append("Track grant awards to demonstrate funding success.")

    return ScoreResult(
        score=score,
        label=label,
        breakdown={
            "active_researchers": active_researchers,
            "publications_count": publications_count,
            "total_citations": total_citations,
            "avg_h_index": avg_h_index,
            "grants_awarded": grants_awarded,
            "international_collaborations": international_collaborations,
            "verified_bonus": verified_bonus,
        },
        recommendations=recommendations,
    )
