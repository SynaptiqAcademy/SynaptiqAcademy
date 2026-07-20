"""Institution Intelligence Engine — KPI Calculator (Phase XV).

All 20 KPIs computed from raw InstitutionInput. Pure Python, deterministic.
"""
from __future__ import annotations

import math
from typing import Any

from .models import InstitutionInput, InstitutionKPIs


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ── KPI calculators ───────────────────────────────────────────────────────────

def _publication_output(inp: InstitutionInput) -> int:
    return sum(_si(r.get("publication_count", 0)) for r in inp.researchers)


def _publication_growth(inp: InstitutionInput) -> float:
    """Inferred from researcher-level growth fields if available."""
    growths = [_sf(r.get("publication_growth", 0)) for r in inp.researchers
               if r.get("publication_growth") is not None]
    return _clamp(_mean(growths) if growths else 0.05)


def _citation_growth(inp: InstitutionInput) -> float:
    growths = [_sf(r.get("citation_growth", 0)) for r in inp.researchers
               if r.get("citation_growth") is not None]
    return _clamp(_mean(growths) if growths else 0.03)


def _avg_h_index(inp: InstitutionInput) -> float:
    values = [_sf(r.get("h_index", 0)) for r in inp.researchers]
    return round(_mean(values), 2)


def _avg_fwci(inp: InstitutionInput) -> float:
    """
    Field-Weighted Citation Impact proxy.
    FWCI ≈ citations_per_pub / field_average (we approximate field avg as 5).
    """
    total_pubs  = sum(_si(r.get("publication_count", 0)) for r in inp.researchers)
    total_cites = sum(_si(r.get("citation_count", 0)) for r in inp.researchers)
    if total_pubs == 0:
        return 0.0
    cites_per_pub = total_cites / total_pubs
    return round(_clamp(cites_per_pub / 5.0, 0.0, 5.0), 3)


def _research_income(inp: InstitutionInput) -> float:
    return round(sum(_sf(g.get("amount", 0)) for g in inp.grants), 2)


def _grant_success_rate(inp: InstitutionInput) -> float:
    won      = sum(1 for g in inp.grants if g.get("status") in ("won", "awarded", "active"))
    total    = len(inp.grants)
    applied  = sum(1 for g in inp.grants if g.get("status") not in ("draft",))
    denom    = max(applied, total, 1)
    return round(_clamp(won / denom), 3)


def _acceptance_rate(inp: InstitutionInput) -> float:
    """Conference / journal acceptance as reported by researchers."""
    rates = [_sf(r.get("acceptance_rate", 0)) for r in inp.researchers
             if r.get("acceptance_rate") is not None]
    return round(_clamp(_mean(rates) if rates else 0.35), 3)


def _q1_ratio(inp: InstitutionInput) -> float:
    """Fraction of publications in Q1 journals (if field reported)."""
    ratios = [_sf(r.get("q1_ratio", 0)) for r in inp.researchers
              if r.get("q1_ratio") is not None]
    if ratios:
        return round(_clamp(_mean(ratios)), 3)
    # Approximate: top h-index researchers tend to publish Q1
    h_vals = [_sf(r.get("h_index", 0)) for r in inp.researchers]
    avg_h  = _mean(h_vals)
    return round(_clamp(avg_h / 25.0 * 0.6 + 0.1), 3)


def _conference_performance(inp: InstitutionInput) -> float:
    vals = [_sf(r.get("conference_performance", 0)) for r in inp.researchers
            if r.get("conference_performance") is not None]
    if vals:
        return round(_clamp(_mean(vals)), 3)
    # Approximate from publication + h-index signals
    total_pubs = sum(_si(r.get("publication_count", 0)) for r in inp.researchers)
    n = max(len(inp.researchers), 1)
    return round(_clamp(total_pubs / (n * 4)), 3)


def _collaboration_score(inp: InstitutionInput) -> float:
    vals = [_sf(r.get("collaboration_count", 0)) for r in inp.researchers]
    avg  = _mean(vals)
    return round(_clamp(avg / 10.0), 3)


def _internationalization_score(inp: InstitutionInput) -> float:
    vals = [_sf(r.get("international_collab_ratio", 0)) for r in inp.researchers]
    return round(_clamp(_mean(vals)), 3)


def _innovation_score(inp: InstitutionInput) -> float:
    """
    Proxied from patent count, industry collabs, and tech-transfer projects.
    """
    patent_count    = sum(_si(r.get("patent_count", 0)) for r in inp.researchers)
    industry_collab = sum(1 for p in inp.projects
                          if "industry" in str(p.get("type", "")).lower())
    tech_transfer   = sum(1 for p in inp.projects
                          if "transfer" in str(p.get("type", "")).lower())
    n = max(len(inp.researchers), 1)
    raw = (patent_count / n * 2.0 + industry_collab / n + tech_transfer / n)
    return round(_clamp(raw / 3.0), 3)


def _open_science_score(inp: InstitutionInput) -> float:
    vals = [_sf(r.get("open_science_score", 0)) for r in inp.researchers
            if r.get("open_science_score") is not None]
    if vals:
        return round(_clamp(_mean(vals)), 3)
    # Approximate: grad-level researchers tend to adopt open science
    student_ratio = sum(
        1 for r in inp.researchers
        if r.get("position", "").lower() in ("phd student", "postdoc", "researcher")
    ) / max(len(inp.researchers), 1)
    return round(_clamp(0.2 + student_ratio * 0.3), 3)


def _research_efficiency(inp: InstitutionInput) -> float:
    """Publications + citations per researcher, normalised."""
    n = max(len(inp.researchers), 1)
    total_pubs  = sum(_si(r.get("publication_count", 0)) for r in inp.researchers)
    total_cites = sum(_si(r.get("citation_count", 0)) for r in inp.researchers)
    pub_eff    = _clamp(total_pubs / (n * 5.0))
    cite_eff   = _clamp(total_cites / (n * 200.0))
    return round((pub_eff * 0.5 + cite_eff * 0.5), 3)


def _sustainability_score(inp: InstitutionInput) -> float:
    """
    Measures grant diversity (multiple funders) + collaboration diversity.
    """
    funders   = {g.get("funding_organization") or g.get("funder") for g in inp.grants} - {None}
    countries = {r.get("country") for r in inp.researchers} - {None, ""}
    n_funders  = len(funders)
    n_countries = len(countries)
    funder_score  = _clamp(n_funders / 5.0)
    country_score = _clamp(n_countries / 10.0)
    return round((funder_score * 0.5 + country_score * 0.5), 3)


def _reputation_score(inp: InstitutionInput) -> float:
    """
    Composite of avg h-index, citation growth, internationalization, grant income.
    """
    h_vals     = [_sf(r.get("h_index", 0)) for r in inp.researchers]
    avg_h      = _mean(h_vals)
    intl       = _internationalization_score(inp)
    grant_inc  = _research_income(inp)
    total_pubs = sum(_si(r.get("publication_count", 0)) for r in inp.researchers)
    n          = max(len(inp.researchers), 1)

    h_score    = _clamp(avg_h / 20.0)
    grant_score = _clamp(math.log1p(grant_inc) / 16.0)
    pub_score  = _clamp(total_pubs / (n * 6.0))
    return round((h_score * 0.4 + intl * 0.2 + grant_score * 0.2 + pub_score * 0.2), 3)


def _faculty_performance(inp: InstitutionInput) -> float:
    """Mean researcher-level performance score."""
    perf_vals = [_sf(r.get("productivity_score", 0)) for r in inp.researchers
                 if r.get("productivity_score") is not None]
    if perf_vals:
        return round(_clamp(_mean(perf_vals)), 3)
    # Approximate: combine h-index + pub count signals
    n = max(len(inp.researchers), 1)
    total_pubs = sum(_si(r.get("publication_count", 0)) for r in inp.researchers)
    h_vals = [_sf(r.get("h_index", 0)) for r in inp.researchers]
    avg_h  = _mean(h_vals)
    return round(_clamp((total_pubs / (n * 4)) * 0.5 + (avg_h / 15.0) * 0.5), 3)


def _department_performance(inp: InstitutionInput) -> float:
    """
    Average publication-per-researcher across all departments.
    """
    from collections import defaultdict
    dept_map: dict[str, list[int]] = defaultdict(list)
    for r in inp.researchers:
        dept = r.get("department") or "General"
        dept_map[dept].append(_si(r.get("publication_count", 0)))
    if not dept_map:
        return 0.0
    per_dept_avg = [_mean(pubs) for pubs in dept_map.values()]
    overall = _mean(per_dept_avg)
    return round(_clamp(overall / 4.0), 3)


def _doctoral_activity(inp: InstitutionInput) -> float:
    """PhD candidate ratio + supervision activity."""
    phd_count = sum(
        1 for r in inp.researchers
        if r.get("position", "").lower() in ("phd student", "phd candidate")
    )
    n = max(len(inp.researchers), 1)
    phd_ratio = phd_count / n
    return round(_clamp(phd_ratio * 2.0 + 0.1), 3)


# ── Public function ───────────────────────────────────────────────────────────

def compute_kpis(inp: InstitutionInput) -> InstitutionKPIs:
    """Compute all 20 institutional KPIs from InstitutionInput."""
    return InstitutionKPIs(
        publication_output=_publication_output(inp),
        publication_growth=_publication_growth(inp),
        citation_growth=_citation_growth(inp),
        avg_h_index=_avg_h_index(inp),
        avg_fwci=_avg_fwci(inp),
        research_income=_research_income(inp),
        grant_success_rate=_grant_success_rate(inp),
        acceptance_rate=_acceptance_rate(inp),
        q1_ratio=_q1_ratio(inp),
        conference_performance=_conference_performance(inp),
        collaboration_score=_collaboration_score(inp),
        internationalization_score=_internationalization_score(inp),
        innovation_score=_innovation_score(inp),
        open_science_score=_open_science_score(inp),
        research_efficiency=_research_efficiency(inp),
        sustainability_score=_sustainability_score(inp),
        reputation_score=_reputation_score(inp),
        faculty_performance=_faculty_performance(inp),
        department_performance=_department_performance(inp),
        doctoral_activity_score=_doctoral_activity(inp),
    )
