"""Academic Prediction — Institution-level forecaster (Phase XVIII)."""
from __future__ import annotations

from .confidence_model import compute_confidence, data_completeness, signal_quality
from .models import ForecastHorizon, InstitutionForecast, PredictionType, _make_prediction

_INST_KEYS = ["total_faculty", "avg_faculty_h_index", "publications_per_year",
              "citations_per_year", "active_grants", "total_funding_eur"]

_HORIZON_YEARS = {
    ForecastHorizon.ONE_YEAR: 1, ForecastHorizon.THREE_YEAR: 3,
    ForecastHorizon.FIVE_YEAR: 5, ForecastHorizon.TEN_YEAR: 10,
}


def forecast_institution(profile: dict, horizon: ForecastHorizon = ForecastHorizon.THREE_YEAR) -> InstitutionForecast:
    p   = profile or {}
    yrs = _HORIZON_YEARS.get(horizon, 3)

    faculty     = max(1, int(p.get("total_faculty", 50)))
    avg_h       = float(p.get("avg_faculty_h_index", 10))
    pub_rate    = float(p.get("publications_per_year", 100))
    cit_rate    = float(p.get("citations_per_year", 1000))
    grants      = int(p.get("active_grants", 10))
    funding     = float(p.get("total_funding_eur", 1_000_000))
    intl_pct    = float(p.get("international_collaboration_pct", 0.30))
    domains     = list(p.get("research_domains") or [])
    rankings    = dict(p.get("rankings") or {})

    quality_score = min(1.0, (
        0.30 * min(avg_h / 25.0, 1.0) +
        0.25 * min(pub_rate / 500.0, 1.0) +
        0.25 * min(cit_rate / 5000.0, 1.0) +
        0.20 * min(grants / 100.0, 1.0)
    ))

    # Publication output forecast
    pub_growth_rate = 1.05 + quality_score * 0.05  # 5-10% annual growth
    pub_forecast    = pub_rate * (pub_growth_rate ** yrs)

    # Funding growth forecast
    fund_growth = funding * (1.0 + min(quality_score, 0.8) * 0.08) ** yrs
    fund_prob   = min(1.0, quality_score * 0.70 + intl_pct * 0.30)

    # Citation growth
    cit_growth_rate = 1.04 + quality_score * 0.06
    cit_forecast    = cit_rate * (cit_growth_rate ** yrs)

    # Ranking trend (0 = declining, 0.5 = stable, 1 = improving)
    ranking_score   = quality_score
    if rankings:
        avg_rank = sum(rankings.values()) / len(rankings)
        ranking_score = max(0.0, min(1.0, quality_score + (1.0 - min(avg_rank / 100.0, 1.0)) * 0.3))

    # Research impact
    research_impact = min(1.0, (
        0.35 * min(avg_h / 25.0, 1.0) +
        0.35 * min(cit_rate / 5000.0, 1.0) +
        0.30 * intl_pct
    ))

    # Strategic risks
    risks: list[str] = []
    if intl_pct < 0.20:
        risks.append("Low international collaboration — ranking may stagnate.")
    if grants < 5:
        risks.append("Limited grant portfolio — funding volatility risk.")
    if quality_score < 0.40:
        risks.append("Below-average faculty output — talent retention risk.")
    if len(domains) < 3:
        risks.append("Narrow research domain focus — interdisciplinary risk.")
    if not risks:
        risks.append("No critical institutional risks identified in current period.")

    # Department highlights (synthetic)
    dept_highlights = []
    for domain in domains[:3]:
        dept_highlights.append({
            "domain": domain,
            "performance": round(quality_score + (0.1 if intl_pct > 0.5 else 0), 2),
            "outlook": "growing" if quality_score > 0.5 else "stable",
        })

    dc   = data_completeness(p, _INST_KEYS)
    sq   = signal_quality(quality_score, intl_pct, min(pub_rate / 200.0, 1.0))
    conf = compute_confidence(dc, sq, "h_index_forecast")

    return InstitutionForecast(
        horizon=horizon.value,
        publication_output=_make_prediction(
            PredictionType.CITATION_VELOCITY, pub_forecast, conf,
            unit="publications/year", clamp_probability=False,
            evidence=[f"Current rate: {int(pub_rate)}/yr", f"Faculty: {faculty}"],
            reasoning=f"Annual publication output projected at {round(pub_growth_rate*100-100,1)}% growth.",
        ),
        funding_growth=_make_prediction(
            PredictionType.FUNDING_PROBABILITY, fund_prob, conf,
            evidence=[f"Current funding: €{int(funding/1_000_000):.1f}M", f"Active grants: {grants}"],
            reasoning=f"Funding growth probability over {yrs} years.",
        ),
        citation_growth=_make_prediction(
            PredictionType.CITATION_GROWTH, cit_forecast, conf,
            unit="citations/year", clamp_probability=False,
            evidence=[f"Current: {int(cit_rate)}/yr", f"International: {round(intl_pct*100)}%"],
            reasoning=f"Citation forecast at {round(cit_growth_rate*100-100,1)}% annual growth.",
        ),
        ranking_trend=_make_prediction(
            PredictionType.TREND_EMERGENCE, ranking_score, conf * 0.80,
            evidence=[f"Rankings: {rankings}", f"Quality score: {round(quality_score,2)}"],
            reasoning="Ranking trend based on output quality and international collaboration.",
        ),
        research_impact=_make_prediction(
            PredictionType.LONG_TERM_IMPACT, research_impact, conf,
            evidence=[f"Avg h-index: {avg_h}", f"Citation rate: {int(cit_rate)}/yr"],
            reasoning="Institutional research impact from h-index, citations, and global reach.",
        ),
        strategic_risks=risks,
        department_highlights=dept_highlights,
        confidence=round(conf, 3),
    )
