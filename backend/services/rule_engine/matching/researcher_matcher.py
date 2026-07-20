"""Deterministic researcher–researcher compatibility matching."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .weighted_scorer import (
    jaccard_similarity, overlap_coefficient, weighted_score,
    rank_candidates, build_match_explanation,
)


@dataclass
class MatchResult:
    candidate_id: str
    score: float  # 0–100
    factors: dict[str, float] = field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "score": self.score,
            "factors": self.factors,
            "explanation": self.explanation,
        }


def match_researchers(
    user: dict,
    candidates: list[dict],
    top_n: int = 10,
    min_score: float = 10.0,
) -> list[MatchResult]:
    """Score each candidate researcher against the user profile.

    Weights (sum to 1.0):
    - Research area overlap: 0.35
    - Expertise/skills overlap: 0.20
    - Teaching area overlap: 0.10
    - Complementary role: 0.10
    - Institution diversity: 0.10
    - ORCID verified: 0.05
    - Publication activity: 0.10
    """
    results: list[MatchResult] = []
    user_areas    = set(user.get("research_areas") or [])
    user_teaching = set(user.get("teaching_areas") or [])
    user_skills   = set(user.get("skills") or []) | set(user.get("professional_expertise") or [])
    user_inst     = (user.get("institution") or "").lower()
    user_type     = user.get("user_type") or "researcher"

    for cand in candidates:
        cand_id = str(cand.get("_id") or cand.get("id", ""))
        cand_areas    = set(cand.get("research_areas") or [])
        cand_teaching = set(cand.get("teaching_areas") or [])
        cand_skills   = set(cand.get("skills") or []) | set(cand.get("professional_expertise") or [])
        cand_inst     = (cand.get("institution") or "").lower()
        cand_type     = cand.get("user_type") or "researcher"

        area_sim   = jaccard_similarity(user_areas, cand_areas)
        teach_sim  = jaccard_similarity(user_teaching, cand_teaching)
        skill_sim  = overlap_coefficient(user_skills, cand_skills)
        role_comp  = _role_complementarity(user_type, cand_type)
        inst_div   = 0.0 if (user_inst and cand_inst and user_inst == cand_inst) else 1.0
        orcid_ver  = 1.0 if cand.get("orcid_id") else 0.0
        pub_score  = min(1.0, int(cand.get("publications_count") or 0) / 20.0)

        factors = {
            "research_areas":    (area_sim,   0.35, "Research area overlap"),
            "expertise_skills":  (skill_sim,  0.20, "Expertise/skills match"),
            "teaching_areas":    (teach_sim,  0.10, "Teaching area overlap"),
            "role_complementarity": (role_comp, 0.10, "Role complementarity"),
            "institution_diversity": (inst_div, 0.10, "Institution diversity"),
            "orcid_verified":    (orcid_ver,  0.05, "ORCID verified"),
            "publication_activity": (pub_score, 0.10, "Publication activity"),
        }

        score = weighted_score({k: (v, w) for k, (v, w, _) in factors.items()})
        explanation = build_match_explanation(factors)
        results.append(MatchResult(
            candidate_id=cand_id,
            score=score,
            factors={k: round(v * 100, 1) for k, (v, w, _) in factors.items()},
            explanation=explanation,
        ))

    ranked = rank_candidates(
        [{"candidate_id": r.candidate_id, "score": r.score, "_result": r} for r in results],
        score_key="score",
        top_n=top_n,
        min_score=min_score,
    )
    return [r["_result"] for r in ranked]


_COMPLEMENTARY_ROLES = {
    "phd_candidate": {"university_faculty", "postdoctoral_researcher", "researcher"},
    "postdoctoral_researcher": {"researcher", "university_faculty", "phd_candidate"},
    "university_faculty": {"phd_candidate", "postdoctoral_researcher", "researcher"},
    "researcher": {"phd_candidate", "university_faculty", "industry_professional"},
    "industry_professional": {"researcher", "university_faculty"},
    "educator": {"educator", "university_faculty", "phd_candidate"},
    "masters_student": {"phd_candidate", "researcher"},
}


def _role_complementarity(role_a: str, role_b: str) -> float:
    if role_a == role_b:
        return 0.7  # Same role — some complementarity
    complementary = _COMPLEMENTARY_ROLES.get(role_a, set())
    return 1.0 if role_b in complementary else 0.3
