"""Deterministic multi-criteria researcher ranking."""
from __future__ import annotations

import math
from typing import Any


def _sat(v: float, scale: float) -> float:
    if v <= 0:
        return 0.0
    return min(1.0, math.log(1 + v / scale) / math.log(2))


def compute_researcher_rank_score(researcher: dict) -> float:
    """Composite ranking score for leaderboard placement (0–100).

    Weights:
    - H-index: 0.25
    - Total citations: 0.20
    - Publications: 0.20
    - Reputation score: 0.15
    - Collaborations: 0.10
    - Grants: 0.10
    """
    h = float(researcher.get("h_index") or 0)
    cit = float(researcher.get("total_citations") or researcher.get("citations") or 0)
    pubs = float(researcher.get("publications_count") or 0)
    rep = float(researcher.get("overall_reputation_score") or researcher.get("reputation_score") or 0)
    collab = float(researcher.get("collaboration_count") or 0)
    grants = float(researcher.get("grants_awarded") or 0)

    score = (
        _sat(h, 20.0) * 0.25 * 100
        + _sat(cit, 500.0) * 0.20 * 100
        + _sat(pubs, 30.0) * 0.20 * 100
        + (rep / 100.0) * 0.15 * 100
        + _sat(collab, 10.0) * 0.10 * 100
        + _sat(grants, 3.0) * 0.10 * 100
    )
    return round(min(score, 100.0), 2)


def rank_researchers(
    researchers: list[dict],
    filters: dict | None = None,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """Rank a list of researcher dicts. Returns ranked list with rank and score fields."""
    f = filters or {}
    field_filter   = f.get("research_area")
    country_filter = f.get("country")
    role_filter    = f.get("user_type")

    def _passes(r: dict) -> bool:
        if field_filter:
            areas = [a.lower() for a in (r.get("research_areas") or [])]
            if not any(field_filter.lower() in a for a in areas):
                return False
        if country_filter:
            if (r.get("country") or "").lower() != country_filter.lower():
                return False
        if role_filter:
            if r.get("user_type") != role_filter:
                return False
        return True

    scored = [
        {**r, "_rank_score": compute_researcher_rank_score(r)}
        for r in researchers if _passes(r)
    ]
    scored.sort(key=lambda x: -x["_rank_score"])

    result: list[dict[str, Any]] = []
    for i, r in enumerate(scored[:top_n] if top_n else scored, start=1):
        result.append({
            "rank": i,
            "id": str(r.get("_id") or r.get("id", "")),
            "full_name": r.get("full_name", ""),
            "institution": r.get("institution", ""),
            "country": r.get("country", ""),
            "user_type": r.get("user_type", ""),
            "research_areas": r.get("research_areas", []),
            "h_index": r.get("h_index") or 0,
            "total_citations": r.get("total_citations") or r.get("citations") or 0,
            "publications_count": r.get("publications_count") or 0,
            "rank_score": r["_rank_score"],
        })
    return result


def compute_leaderboard(
    researchers: list[dict],
    scope: str = "global",
    scope_value: str | None = None,
    top_n: int = 50,
) -> dict[str, Any]:
    """Generate a leaderboard for a given scope.

    scope: 'global' | 'country' | 'institution' | 'field'
    """
    filters: dict = {}
    if scope == "country" and scope_value:
        filters["country"] = scope_value
    elif scope == "institution" and scope_value:
        # filter by institution name substring
        researchers = [r for r in researchers
                       if scope_value.lower() in (r.get("institution") or "").lower()]
    elif scope == "field" and scope_value:
        filters["research_area"] = scope_value

    ranked = rank_researchers(researchers, filters=filters, top_n=top_n)
    return {
        "scope": scope,
        "scope_value": scope_value,
        "total_ranked": len(ranked),
        "leaderboard": ranked,
    }
