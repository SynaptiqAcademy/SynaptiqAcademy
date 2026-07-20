"""Deterministic manuscript–reviewer matching."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .weighted_scorer import (
    jaccard_similarity, overlap_coefficient, weighted_score, rank_candidates,
)


@dataclass
class ReviewerMatch:
    reviewer_id: str
    score: float
    factors: dict[str, float] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer_id": self.reviewer_id,
            "score": self.score,
            "factors": self.factors,
            "conflicts": self.conflicts,
            "explanation": self.explanation,
        }


def match_reviewers(
    manuscript: dict,
    reviewers: list[dict],
    exclude_ids: list[str] | None = None,
    top_n: int = 10,
) -> list[ReviewerMatch]:
    """Score each reviewer candidate for a manuscript.

    Factors (match services/reviewer_marketplace/matching_engine.py):
    - Research area match: 0.40
    - Reviewer quality score: 0.30
    - Availability: 0.15
    - Institution diversity: 0.10
    - ORCID verified: 0.05
    """
    excluded = set(exclude_ids or [])
    ms_areas  = set(manuscript.get("research_areas") or manuscript.get("subject_areas") or [])
    ms_keywords = set(manuscript.get("keywords") or [])
    ms_author_ids = set(str(a) for a in (manuscript.get("author_ids") or []))
    ms_institution = (manuscript.get("institution") or "").lower()

    results: list[ReviewerMatch] = []

    for rev in reviewers:
        rev_id = str(rev.get("_id") or rev.get("id", ""))
        if rev_id in excluded:
            continue

        # Conflict-of-interest detection
        conflicts = _detect_conflicts(rev, ms_author_ids, ms_institution)

        rev_areas   = set(rev.get("research_areas") or [])
        rev_expertise = set(rev.get("professional_expertise") or []) | set(rev.get("skills") or [])
        rev_keywords  = set(rev.get("research_keywords") or [])

        area_sim  = jaccard_similarity(ms_areas, rev_areas)
        kw_sim    = jaccard_similarity(ms_keywords, rev_keywords | rev_expertise)
        combined_area = max(area_sim, kw_sim * 0.5)

        quality_raw = float(rev.get("reviewer_score") or rev.get("reputation_score") or 0)
        quality_norm = min(1.0, quality_raw / 100.0)

        availability = _availability_score(rev.get("availability"))
        inst_div  = 0.0 if (ms_institution and (rev.get("institution") or "").lower() == ms_institution) else 1.0
        orcid_ver = 1.0 if rev.get("orcid_id") else 0.0

        score = weighted_score({
            "area_match":    (combined_area, 0.40),
            "quality":       (quality_norm, 0.30),
            "availability":  (availability, 0.15),
            "inst_diversity":(inst_div, 0.10),
            "orcid_verified":(orcid_ver, 0.05),
        })

        # Penalize conflict-of-interest
        if conflicts:
            score = max(0.0, score - 30.0)

        results.append(ReviewerMatch(
            reviewer_id=rev_id,
            score=score,
            factors={
                "area_match": round(combined_area * 100, 1),
                "quality": round(quality_norm * 100, 1),
                "availability": round(availability * 100, 1),
                "institution_diversity": round(inst_div * 100, 1),
            },
            conflicts=conflicts,
            explanation=_explain(combined_area, quality_norm, conflicts),
        ))

    ranked = rank_candidates(
        [{"reviewer_id": r.reviewer_id, "score": r.score, "_result": r} for r in results],
        score_key="score",
        top_n=top_n,
        min_score=0.0,
    )
    return [r["_result"] for r in ranked]


def _detect_conflicts(reviewer: dict, author_ids: set[str], ms_institution: str) -> list[str]:
    conflicts: list[str] = []
    rev_id = str(reviewer.get("_id") or reviewer.get("id", ""))
    if rev_id in author_ids:
        conflicts.append("Reviewer is one of the manuscript authors.")
    rev_inst = (reviewer.get("institution") or "").lower()
    if ms_institution and rev_inst and rev_inst == ms_institution:
        conflicts.append("Reviewer is from the same institution as the authors.")
    collab_ids = set(str(c) for c in (reviewer.get("collaborator_ids") or []))
    shared = collab_ids & author_ids
    if shared:
        conflicts.append(f"Reviewer has {len(shared)} active collaboration(s) with the author(s).")
    return conflicts


def _availability_score(availability: str | None) -> float:
    if not availability:
        return 0.7
    av = availability.lower()
    if av in ("available", "open", "yes", "active"):
        return 1.0
    if av in ("busy", "limited", "partial"):
        return 0.5
    if av in ("unavailable", "closed", "no", "inactive"):
        return 0.0
    return 0.7


def _explain(area_sim: float, quality: float, conflicts: list[str]) -> str:
    if conflicts:
        return f"Potential conflict of interest: {conflicts[0]}"
    if area_sim >= 0.6 and quality >= 0.7:
        return "Excellent expertise match and strong reviewer track record."
    if area_sim >= 0.4:
        return "Good expertise alignment for this manuscript."
    if quality >= 0.6:
        return "Experienced reviewer; moderate expertise overlap."
    return "General reviewer match based on available profile data."
