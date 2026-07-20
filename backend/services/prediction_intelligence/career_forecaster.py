"""Academic Prediction — Career forecasting engine (Phase XVIII)."""
from __future__ import annotations

import math

from .confidence_model import compute_confidence, data_completeness, signal_quality
from .models import CareerForecast, ForecastHorizon, PredictionType, _make_prediction

_CAREER_KEYS = [
    "current_h_index", "total_citations", "total_publications",
    "publications_per_year", "citations_per_year", "career_stage",
    "years_active", "collaboration_count",
]

_HORIZON_YEARS = {
    ForecastHorizon.ONE_YEAR:   1,
    ForecastHorizon.THREE_YEAR: 3,
    ForecastHorizon.FIVE_YEAR:  5,
    ForecastHorizon.TEN_YEAR:  10,
}

_STAGE_MILESTONES: dict[str, list[str]] = {
    "phd_candidate":   ["First peer-reviewed publication", "PhD thesis submitted", "Conference presentation"],
    "postdoc":         ["First independent grant", "Faculty job applications", "Lab mentor role"],
    "early_career":    ["First lab established", "Tenure review", "Research group formation"],
    "mid_career":      ["Full professor candidacy", "Department leadership", "Major international grant"],
    "senior_faculty":  ["Endowed chair", "National academy nomination", "International advisory boards"],
    "professor":       ["Department chair", "Research institute leadership", "Mentoring legacy"],
    "undergraduate":   ["First research internship", "Undergraduate thesis", "Grad school applications"],
    "master_student":  ["Thesis completion", "First publication", "PhD applications"],
    "emeritus":        ["Book completion", "Legacy programme", "Mentoring network"],
    "industry":        ["Patent filing", "Startup founding", "Industry-academia bridge"],
    "independent_researcher": ["Fellowship award", "First major publication", "Research network growth"],
    "other":           ["Next career milestone", "Research output increase"],
}


def _h_index_growth(curr_h: int, cit_rate: float, years: int) -> float:
    """Approximate h-index growth: h grows ≈ sqrt(cumulative citations / avg_cit_per_paper)."""
    if curr_h <= 0 and cit_rate <= 0:
        return 0.0
    expected_new_cits = cit_rate * years
    # Each new h unit requires h additional citations; increment ≈ sqrt(new_cits) * 0.3
    increment = math.sqrt(max(0, expected_new_cits)) * 0.30
    return round(curr_h + increment, 1)


def _career_stage_factor(stage: str) -> float:
    """Productivity multiplier by career stage."""
    factors = {
        "phd_candidate":        0.60,
        "postdoc":              0.85,
        "early_career":         1.00,
        "mid_career":           1.10,
        "senior_faculty":       0.95,
        "professor":            0.90,
        "undergraduate":        0.30,
        "master_student":       0.45,
        "emeritus":             0.55,
        "industry":             0.70,
        "independent_researcher": 0.75,
        "other":                0.65,
    }
    return factors.get(stage.lower(), 0.75)


def forecast_career(profile: dict, horizon: ForecastHorizon = ForecastHorizon.THREE_YEAR) -> CareerForecast:
    p = profile or {}
    yrs = _HORIZON_YEARS.get(horizon, 3)

    curr_h       = int(p.get("current_h_index", 0))
    total_cit    = int(p.get("total_citations", 0))
    total_pub    = int(p.get("total_publications", 0))
    pub_rate     = float(p.get("publications_per_year", 2.0))
    cit_rate     = float(p.get("citations_per_year", 10.0))
    stage        = str(p.get("career_stage", "early_career"))
    collab_count = int(p.get("collaboration_count", 0))
    intl_collab  = int(p.get("international_collaboration_count", 0))
    grants       = int(p.get("current_grants", 0))
    teaching_load = float(p.get("teaching_load", 0.3))
    admin_load    = float(p.get("admin_load", 0.1))

    stage_factor   = _career_stage_factor(stage)
    collab_mult    = 1.0 + min(collab_count / 20.0, 0.50)
    intl_mult      = 1.0 + min(intl_collab / 5.0, 0.25)
    productivity   = stage_factor * (1.0 - teaching_load * 0.3) * (1.0 - admin_load * 0.2)
    grant_boost    = min(grants / 3.0, 1.0) * 0.15

    # H-index forecast
    effective_cit_rate = cit_rate * productivity * collab_mult
    h_forecast = _h_index_growth(curr_h, effective_cit_rate, yrs)

    # Citations forecast
    cit_growth = total_cit + effective_cit_rate * yrs * intl_mult

    # Publications forecast
    pub_forecast = total_pub + pub_rate * productivity * yrs

    # Promotion readiness (scaled 0-1 per stage trajectory)
    promo_base = {
        "phd_candidate": 0.30, "postdoc": 0.45, "early_career": 0.65,
        "mid_career": 0.80, "senior_faculty": 0.90, "professor": 0.95,
    }.get(stage, 0.50)
    promo_readiness = min(1.0, promo_base + (pub_rate / 8.0) * 0.15 + grant_boost)

    # International visibility
    intl_visibility = min(1.0, intl_mult - 1.0 + min(cit_rate / 100.0, 0.6) + grant_boost)
    intl_visibility = max(0.05, intl_visibility)

    # Research influence (pagerank proxy: h-index + collab network)
    influence = min(1.0, curr_h / 40.0 + collab_count / 30.0 + grants / 5.0 * 0.1)

    # Academic reputation (composite of citations + publications + grants)
    reputation = min(1.0, (
        0.35 * min(total_cit / 500.0, 1.0) +
        0.30 * min(total_pub / 50.0, 1.0) +
        0.20 * min(grants / 5.0, 1.0) +
        0.15 * min(collab_count / 20.0, 1.0)
    ))

    # Leadership potential
    leadership = min(1.0, (
        min(p.get("years_active", 0) / 20.0, 1.0) * 0.30 +
        min(grants / 3.0, 1.0) * 0.25 +
        min(collab_count / 15.0, 1.0) * 0.25 +
        float(p.get("admin_experience", 0.0)) * 0.20
    ))

    # Milestones
    stage_key = stage if stage in _STAGE_MILESTONES else "other"
    raw_milestones = _STAGE_MILESTONES[stage_key]
    milestones = [
        {"milestone": ms, "estimated_year": i + 1, "probability": round(max(0.3, promo_readiness - i * 0.1), 2)}
        for i, ms in enumerate(raw_milestones[:int(yrs)])
    ]

    # Confidence
    dc   = data_completeness(p, _CAREER_KEYS)
    sq   = signal_quality(pub_rate / 6.0, cit_rate / 80.0, stage_factor)
    conf = compute_confidence(dc, sq, "h_index_forecast")

    return CareerForecast(
        horizon=horizon.value,
        h_index=_make_prediction(
            PredictionType.H_INDEX_FORECAST, h_forecast, conf,
            unit="h_index", clamp_probability=False,
            evidence=[f"Current h: {curr_h}", f"Citation rate: {round(cit_rate,1)}/yr"],
            reasoning=f"{yrs}-year h-index forecast using citation velocity model.",
        ),
        citations=_make_prediction(
            PredictionType.CITATION_GROWTH, cit_growth, conf,
            unit="citations", clamp_probability=False,
            evidence=[f"Current: {total_cit}", f"Rate: {round(effective_cit_rate,1)}/yr"],
            reasoning=f"Cumulative citation growth over {yrs} years.",
        ),
        publications=_make_prediction(
            PredictionType.CITATION_VELOCITY, pub_forecast, conf,
            unit="publications", clamp_probability=False,
            evidence=[f"Current: {total_pub}", f"Rate: {round(pub_rate,1)}/yr"],
            reasoning=f"Publication forecast over {yrs} years with productivity factor.",
        ),
        productivity=_make_prediction(
            PredictionType.COLLABORATION_SUCCESS, productivity, conf,
            evidence=[f"Stage factor: {round(stage_factor,2)}", f"Teaching load: {round(teaching_load,2)}"],
            reasoning="Research productivity adjusted for career stage and teaching load.",
        ),
        promotion_readiness=_make_prediction(
            PredictionType.PROMOTION_READINESS, promo_readiness, conf,
            evidence=[f"Stage: {stage}", f"Grant activity: {grants}"],
            recommendations=["Increase publication rate", "Apply for research grants"],
            reasoning="Promotion readiness based on stage, output rate, and grant track record.",
        ),
        international_visibility=_make_prediction(
            PredictionType.COLLABORATION_SUCCESS, intl_visibility, conf * 0.85,
            evidence=[f"International collaborations: {intl_collab}"],
            reasoning="International visibility driven by collaboration network and citation impact.",
        ),
        research_influence=_make_prediction(
            PredictionType.LONG_TERM_IMPACT, influence, conf * 0.80,
            evidence=[f"H-index: {curr_h}", f"Collaborations: {collab_count}"],
            reasoning="Research influence proxy from h-index and network breadth.",
        ),
        academic_reputation=_make_prediction(
            PredictionType.LONG_TERM_IMPACT, reputation, conf,
            evidence=[f"Total citations: {total_cit}", f"Total publications: {total_pub}"],
            reasoning="Academic reputation from output, citations, grants, and collaborations.",
        ),
        leadership_potential=_make_prediction(
            PredictionType.PROMOTION_READINESS, leadership, conf * 0.75,
            evidence=[f"Years active: {p.get('years_active', 0)}", f"Grants: {grants}"],
            reasoning="Leadership potential from seniority, grants, and admin experience.",
        ),
        milestones=milestones,
        confidence=round(conf, 3),
    )
