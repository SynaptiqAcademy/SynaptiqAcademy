"""Institution Intelligence Engine — Predictive Analytics (Phase XV).

Linear-trend extrapolation with confidence bands. Pure Python, no scipy.
"""
from __future__ import annotations

import math

from .models import ForecastType, InstitutionForecast, InstitutionInput


def _sf(v, d: float = 0.0) -> float:
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _si(v, d: int = 0) -> int:
    try:
        return int(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _trend_label(growth: float) -> str:
    if growth > 0.05:
        return "improving"
    if growth < -0.05:
        return "declining"
    return "stable"


def _project(baseline: float, rate: float, horizon: int) -> list[float]:
    """Compound growth projection."""
    return [round(baseline * ((1 + rate) ** yr), 2) for yr in range(1, horizon + 1)]


def _ci(values: list[float], uncertainty: float = 0.15) -> tuple[list[float], list[float]]:
    lower = [round(max(0.0, v * (1 - uncertainty)), 2) for v in values]
    upper = [round(v * (1 + uncertainty), 2) for v in values]
    return lower, upper


# ── Individual forecasters ────────────────────────────────────────────────────

def _forecast_publications(inp: InstitutionInput, horizon: int) -> InstitutionForecast:
    baseline = sum(_si(r.get("publication_count", 0)) for r in inp.researchers)
    growths  = [_sf(r.get("publication_growth", 0)) for r in inp.researchers
                if r.get("publication_growth") is not None]
    rate     = _mean(growths) if growths else 0.05
    projected = _project(baseline, rate, horizon)
    lo, hi   = _ci(projected, 0.15)
    return InstitutionForecast(
        forecast_type=ForecastType.PUBLICATIONS,
        horizon_years=horizon,
        baseline_value=baseline,
        predicted_values=projected,
        ci_lower=lo, ci_upper=hi,
        key_drivers=["Researcher count growth", "Grant success rate", "International collaboration"],
        confidence=0.72,
        trend=_trend_label(rate),
    )


def _forecast_citations(inp: InstitutionInput, horizon: int) -> InstitutionForecast:
    baseline = sum(_si(r.get("citation_count", 0)) for r in inp.researchers)
    pub_out  = sum(_si(r.get("publication_count", 0)) for r in inp.researchers)
    # Citations lag publications by ~2 years; rate approximated
    rate = 0.06 + min(pub_out / max(len(inp.researchers), 1) / 50, 0.1)
    projected = _project(baseline, rate, horizon)
    lo, hi = _ci(projected, 0.2)
    return InstitutionForecast(
        forecast_type=ForecastType.CITATIONS,
        horizon_years=horizon,
        baseline_value=baseline,
        predicted_values=projected,
        ci_lower=lo, ci_upper=hi,
        key_drivers=["Publication volume and quality", "Open access adoption", "International visibility"],
        confidence=0.65,
        trend=_trend_label(rate),
    )


def _forecast_grant_income(inp: InstitutionInput, horizon: int) -> InstitutionForecast:
    baseline = sum(_sf(g.get("amount", 0)) for g in inp.grants)
    won      = sum(1 for g in inp.grants if g.get("status") in ("won", "awarded", "active"))
    success  = won / max(len(inp.grants), 1)
    rate     = (success - 0.3) * 0.2    # higher success → better growth
    projected = _project(baseline, max(rate, 0.0), horizon)
    lo, hi    = _ci(projected, 0.25)
    return InstitutionForecast(
        forecast_type=ForecastType.GRANT_INCOME,
        horizon_years=horizon,
        baseline_value=baseline,
        predicted_values=projected,
        ci_lower=lo, ci_upper=hi,
        key_drivers=["Grant success rate", "Number of applications", "EU funding landscape"],
        confidence=0.60,
        trend=_trend_label(rate),
    )


def _forecast_collaborations(inp: InstitutionInput, horizon: int) -> InstitutionForecast:
    baseline = _mean([_sf(r.get("collaboration_count", 0)) for r in inp.researchers]) * len(inp.researchers)
    intl     = _mean([_sf(r.get("international_collab_ratio", 0)) for r in inp.researchers])
    rate     = 0.04 + intl * 0.08
    projected = _project(baseline, rate, horizon)
    lo, hi   = _ci(projected, 0.15)
    return InstitutionForecast(
        forecast_type=ForecastType.COLLABORATIONS,
        horizon_years=horizon,
        baseline_value=baseline,
        predicted_values=projected,
        ci_lower=lo, ci_upper=hi,
        key_drivers=["Internationalization policy", "Collaboration incentive programs", "Joint grants"],
        confidence=0.68,
        trend=_trend_label(rate),
    )


def _forecast_h_index(inp: InstitutionInput, horizon: int) -> InstitutionForecast:
    h_vals   = [_sf(r.get("h_index", 0)) for r in inp.researchers]
    baseline = _mean(h_vals)
    # h-index grows ~0.5-2 pts/year for active researchers
    pub_per_r = sum(_si(r.get("publication_count", 0)) for r in inp.researchers) / max(len(inp.researchers), 1)
    annual_growth = min(pub_per_r * 0.08, 1.5)
    projected = [round(baseline + annual_growth * yr, 2) for yr in range(1, horizon + 1)]
    lo, hi   = _ci(projected, 0.12)
    return InstitutionForecast(
        forecast_type=ForecastType.H_INDEX,
        horizon_years=horizon,
        baseline_value=baseline,
        predicted_values=projected,
        ci_lower=lo, ci_upper=hi,
        key_drivers=["Publication quality", "Citation accumulation", "Open access"],
        confidence=0.70,
        trend="improving" if annual_growth > 0 else "stable",
    )


def _forecast_doctoral(inp: InstitutionInput, horizon: int) -> InstitutionForecast:
    phd_count = sum(
        1 for r in inp.researchers
        if "phd" in (r.get("position") or "").lower()
    )
    rate = 0.03
    projected = _project(float(phd_count), rate, horizon)
    lo, hi = _ci(projected, 0.20)
    return InstitutionForecast(
        forecast_type=ForecastType.DOCTORAL_COMPLETIONS,
        horizon_years=horizon,
        baseline_value=float(phd_count),
        predicted_values=projected,
        ci_lower=lo, ci_upper=hi,
        key_drivers=["PhD recruitment", "Supervision capacity", "Funding availability"],
        confidence=0.65,
        trend=_trend_label(rate),
    )


def _forecast_faculty(inp: InstitutionInput, horizon: int) -> InstitutionForecast:
    n = float(len(inp.researchers))
    rate = 0.02
    projected = _project(n, rate, horizon)
    lo, hi = _ci(projected, 0.10)
    return InstitutionForecast(
        forecast_type=ForecastType.FACULTY_SIZE,
        horizon_years=horizon,
        baseline_value=n,
        predicted_values=projected,
        ci_lower=lo, ci_upper=hi,
        key_drivers=["Budget allocation", "Retirement pipeline", "New positions approved"],
        confidence=0.60,
        trend="stable",
    )


def _forecast_research_income(inp: InstitutionInput, horizon: int) -> InstitutionForecast:
    baseline = float(inp.total_budget) if inp.total_budget else sum(
        _sf(g.get("amount", 0)) for g in inp.grants
    ) * 2  # grants are typically ~50% of research income
    rate = 0.04
    projected = _project(baseline, rate, horizon)
    lo, hi = _ci(projected, 0.20)
    return InstitutionForecast(
        forecast_type=ForecastType.RESEARCH_INCOME,
        horizon_years=horizon,
        baseline_value=baseline,
        predicted_values=projected,
        ci_lower=lo, ci_upper=hi,
        key_drivers=["National funding policy", "Industry partnerships", "Grant success"],
        confidence=0.58,
        trend="stable",
    )


# ── Public function ───────────────────────────────────────────────────────────

_FORECASTERS = {
    ForecastType.PUBLICATIONS:         _forecast_publications,
    ForecastType.CITATIONS:            _forecast_citations,
    ForecastType.GRANT_INCOME:         _forecast_grant_income,
    ForecastType.COLLABORATIONS:       _forecast_collaborations,
    ForecastType.H_INDEX:              _forecast_h_index,
    ForecastType.DOCTORAL_COMPLETIONS: _forecast_doctoral,
    ForecastType.FACULTY_SIZE:         _forecast_faculty,
    ForecastType.RESEARCH_INCOME:      _forecast_research_income,
}


def predict_institution(
    inp: InstitutionInput,
    forecast_types: list[ForecastType] | None = None,
    horizon: int = 3,
) -> list[InstitutionForecast]:
    """Generate forecasts for requested types (default: all 8)."""
    types = forecast_types or list(_FORECASTERS.keys())
    return [_FORECASTERS[t](inp, horizon) for t in types if t in _FORECASTERS]
