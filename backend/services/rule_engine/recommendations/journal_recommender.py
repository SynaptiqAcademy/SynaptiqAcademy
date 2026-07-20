"""Rule-based journal recommendation (no LLM required)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..matching.weighted_scorer import jaccard_similarity, overlap_coefficient, rank_candidates


@dataclass
class JournalRecommendation:
    journal_id: str
    title: str
    score: float
    factors: dict[str, float] = field(default_factory=dict)
    rationale: str = ""
    impact_factor: float | None = None
    quartile: str | None = None
    open_access: bool = False
    apc_usd: int | None = None
    acceptance_rate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "journal_id": self.journal_id,
            "title": self.title,
            "score": self.score,
            "factors": self.factors,
            "rationale": self.rationale,
            "impact_factor": self.impact_factor,
            "quartile": self.quartile,
            "open_access": self.open_access,
            "apc_usd": self.apc_usd,
            "acceptance_rate": self.acceptance_rate,
        }


def recommend_journals(
    manuscript: dict,
    journals: list[dict],
    user_preferences: dict | None = None,
    top_n: int = 10,
) -> list[JournalRecommendation]:
    """Rank journals for a manuscript using deterministic weighted scoring.

    Factors:
    - Subject area match: 0.40
    - Keyword overlap: 0.20
    - Impact factor (normalized): 0.15
    - Open access preference: 0.10
    - Acceptance rate (if available): 0.10
    - Publication history: 0.05
    """
    pref = user_preferences or {}
    ms_areas    = set(manuscript.get("research_areas") or manuscript.get("subject_areas") or [])
    ms_keywords = set(manuscript.get("keywords") or [])
    ms_type     = (manuscript.get("manuscript_type") or "research_article").lower()
    prefer_oa   = pref.get("prefer_open_access", False)
    max_apc     = pref.get("max_apc_usd")
    min_if      = pref.get("min_impact_factor", 0.0)

    # Compute max impact factor across candidates for normalization
    ifs = [float(j.get("impact_factor") or 0) for j in journals]
    max_if = max(ifs, default=1.0) or 1.0

    results: list[JournalRecommendation] = []

    for j in journals:
        j_id = str(j.get("_id") or j.get("id", ""))
        j_title = j.get("title") or j.get("name") or ""
        j_if = float(j.get("impact_factor") or 0)
        j_oa = bool(j.get("open_access") or j.get("is_open_access"))
        j_apc = int(j.get("apc_usd") or j.get("apc") or 0)
        j_acceptance = j.get("acceptance_rate")  # e.g. 0.25 for 25%
        j_quartile = j.get("quartile") or j.get("scimago_quartile")
        j_areas = set(j.get("subject_areas") or j.get("research_areas") or [])
        j_keywords = set(j.get("keywords") or [])
        j_types = set((j.get("accepted_manuscript_types") or "").lower().split(","))

        # Hard filters
        if min_if and j_if < min_if:
            continue
        if max_apc and j_apc > max_apc:
            continue

        # Type compatibility
        type_compat = 1.0 if not j_types or ms_type in j_types else 0.5

        area_sim   = jaccard_similarity(ms_areas, j_areas)
        kw_sim     = overlap_coefficient(ms_keywords, j_keywords)
        if_score   = min(1.0, j_if / max_if)
        oa_score   = 1.0 if (prefer_oa and j_oa) or (not prefer_oa) else 0.6
        acc_score  = (
            min(1.0, (1.0 - float(j_acceptance)) * 1.5)
            if j_acceptance is not None else 0.5
        )
        quartile_bonus = {"Q1": 0.2, "Q2": 0.1, "Q3": 0.0, "Q4": -0.1}.get(j_quartile or "", 0.0)

        raw = (
            area_sim * 0.40
            + kw_sim * 0.20
            + if_score * 0.15
            + oa_score * 0.10
            + acc_score * 0.10
            + 0.05  # default baseline for publication history
        ) * type_compat + quartile_bonus

        score = round(min(raw * 100, 100.0), 1)
        rationale = _build_rationale(area_sim, kw_sim, j_if, j_oa, j_quartile)

        results.append(JournalRecommendation(
            journal_id=j_id,
            title=j_title,
            score=score,
            factors={
                "subject_area_match": round(area_sim * 100, 1),
                "keyword_overlap": round(kw_sim * 100, 1),
                "impact_factor_score": round(if_score * 100, 1),
            },
            rationale=rationale,
            impact_factor=j_if or None,
            quartile=j_quartile,
            open_access=j_oa,
            apc_usd=j_apc or None,
            acceptance_rate=float(j_acceptance) if j_acceptance is not None else None,
        ))

    ranked = rank_candidates(
        [{"id": r.journal_id, "score": r.score, "_r": r} for r in results],
        score_key="score",
        top_n=top_n,
    )
    return [r["_r"] for r in ranked]


def _build_rationale(
    area_sim: float, kw_sim: float, if_score: float, oa: bool, quartile: str | None
) -> str:
    parts: list[str] = []
    if area_sim >= 0.5:
        parts.append("strong subject area match")
    elif area_sim >= 0.25:
        parts.append("moderate subject area overlap")
    if kw_sim >= 0.3:
        parts.append("relevant keyword alignment")
    if if_score >= 2.0:
        parts.append(f"high impact factor ({if_score:.1f})")
    if quartile in ("Q1", "Q2"):
        parts.append(f"{quartile}-ranked journal")
    if oa:
        parts.append("open access")
    if not parts:
        return "General field compatibility."
    return "Recommended due to: " + ", ".join(parts) + "."
