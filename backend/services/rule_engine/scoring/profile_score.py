"""Profile completeness scorer — deterministic, no AI required."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoreResult:
    score: float
    label: str = ""
    breakdown: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "label": self.label,
            "breakdown": self.breakdown,
            "recommendations": self.recommendations,
        }


_FIELDS: list[tuple[str, str, int, str]] = [
    ("avatar_url",          "Profile photo",          10, "Add a professional profile photo."),
    ("bio",                 "Biography",              10, "Write a biography (at least 50 characters)."),
    ("institution",         "Institution",            10, "Add your current institution."),
    ("research_keywords",   "Research keywords",      10, "Add research keywords (at least 3)."),
    ("research_methods",    "Research methods",        5, "Add your research methods/techniques."),
    ("social_links",        "Social/academic links",   5, "Add links to Google Scholar, LinkedIn, or personal website."),
    ("availability",        "Collaboration status",    5, "Set your collaboration availability."),
    ("orcid_id",            "ORCID iD",               15, "Connect your ORCID iD to verify your identity."),
    ("publications_linked", "Publications",           15, "Import publications via ORCID or add manually."),
    ("employment",          "Employment history",     10, "Add at least one employment entry."),
    ("education",           "Education history",       5, "Add your highest degree."),
]

_LABELS = [(90, "Exemplary"), (75, "Strong"), (60, "Moderate"), (40, "Developing"), (0, "Minimal")]


def _field_present(profile: dict, key: str) -> bool:
    val = profile.get(key)
    if val is None or val == "" or val == [] or val == {}:
        return False
    if key == "bio" and len(str(val)) < 50:
        return False
    if key == "research_keywords" and isinstance(val, list) and len(val) < 3:
        return False
    if key == "publications_linked":
        # Accept either openalex_id or publications_count > 0
        return bool(profile.get("openalex_id")) or int(profile.get("publications_count", 0)) > 0
    return True


def calculate_profile_score(profile: dict) -> ScoreResult:
    breakdown: dict[str, Any] = {}
    recommendations: list[str] = []
    earned = 0
    total = sum(pts for _, _, pts, _ in _FIELDS)

    for key, label, pts, suggestion in _FIELDS:
        present = _field_present(profile, key)
        breakdown[key] = {"label": label, "points": pts, "complete": present}
        if present:
            earned += pts
        else:
            recommendations.append(suggestion)

    score = round(earned / total * 100, 1)
    label = next(lbl for threshold, lbl in _LABELS if score >= threshold)
    return ScoreResult(
        score=score,
        label=label,
        breakdown=breakdown,
        recommendations=recommendations[:5],
    )
