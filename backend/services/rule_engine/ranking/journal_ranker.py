"""Deterministic journal ranking by multiple quality criteria."""
from __future__ import annotations

from typing import Any


def compute_journal_quality_score(journal: dict) -> float:
    """0–100 journal quality score.

    Factors:
    - Impact factor (normalized): 0.35
    - Quartile: 0.30
    - Acceptance rate (inverse): 0.15
    - CiteScore (normalized): 0.10
    - Open access: 0.05
    - Age (established): 0.05
    """
    impact = float(journal.get("impact_factor") or 0)
    cite_score = float(journal.get("cite_score") or 0)
    acceptance = journal.get("acceptance_rate")  # 0.0–1.0
    quartile = journal.get("quartile") or journal.get("scimago_quartile")
    is_oa = bool(journal.get("open_access") or journal.get("is_open_access"))
    founded_year = journal.get("founded_year")

    # Normalize impact factor against a rough ceiling of 50
    if_norm = min(1.0, impact / 50.0)
    cs_norm = min(1.0, cite_score / 20.0)

    # Quartile score
    q_scores = {"Q1": 1.0, "Q2": 0.75, "Q3": 0.50, "Q4": 0.25}
    q_score = q_scores.get(quartile or "", 0.3)

    # Acceptance rate (lower = more selective = higher quality signal)
    if acceptance is not None:
        acc_score = 1.0 - float(acceptance)
    else:
        acc_score = 0.5

    oa_score = 0.7 if is_oa else 0.5  # slight preference for OA

    # Age bonus (journals founded >20 years ago are more established)
    if founded_year:
        from ..utils.date_utils import utcnow
        age = utcnow().year - int(founded_year)
        age_score = min(1.0, age / 30.0)
    else:
        age_score = 0.5

    raw = (
        if_norm * 0.35
        + q_score * 0.30
        + acc_score * 0.15
        + cs_norm * 0.10
        + oa_score * 0.05
        + age_score * 0.05
    )
    return round(min(raw * 100, 100.0), 1)


def rank_journals(
    journals: list[dict],
    filters: dict | None = None,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    f = filters or {}
    field_filter = f.get("field")
    oa_only = f.get("open_access_only", False)
    min_if = float(f.get("min_impact_factor") or 0)
    quartile_filter = f.get("quartile")
    max_apc = f.get("max_apc_usd")

    def _passes(j: dict) -> bool:
        if oa_only and not (j.get("open_access") or j.get("is_open_access")):
            return False
        if min_if and float(j.get("impact_factor") or 0) < min_if:
            return False
        if quartile_filter and j.get("quartile") != quartile_filter:
            return False
        if max_apc:
            apc = int(j.get("apc_usd") or j.get("apc") or 0)
            if apc > max_apc:
                return False
        if field_filter:
            fields = [s.lower() for s in (j.get("subject_areas") or [])]
            if not any(field_filter.lower() in s for s in fields):
                return False
        return True

    scored = [
        {**j, "_quality_score": compute_journal_quality_score(j)}
        for j in journals if _passes(j)
    ]
    scored.sort(key=lambda x: -x["_quality_score"])

    result: list[dict[str, Any]] = []
    for i, j in enumerate(scored[:top_n] if top_n else scored, start=1):
        result.append({
            "rank": i,
            "id": str(j.get("_id") or j.get("id", "")),
            "title": j.get("title") or j.get("name") or "",
            "publisher": j.get("publisher") or "",
            "impact_factor": j.get("impact_factor"),
            "quartile": j.get("quartile"),
            "open_access": bool(j.get("open_access") or j.get("is_open_access")),
            "acceptance_rate": j.get("acceptance_rate"),
            "apc_usd": j.get("apc_usd") or j.get("apc"),
            "quality_score": j["_quality_score"],
        })
    return result
