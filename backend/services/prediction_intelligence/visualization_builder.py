"""Academic Prediction — Visualization builder (Phase XVIII).

Returns serializable dicts for 8 visualization types.
"""
from __future__ import annotations

from .models import VizType


def _safe(v) -> float:
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return 0.0


def prediction_dashboard_viz(predictions: dict) -> dict:
    items = []
    for key, pred in predictions.items():
        if isinstance(pred, dict):
            items.append({
                "label":      key.replace("_", " ").title(),
                "value":      _safe(pred.get("value", 0)),
                "confidence": _safe(pred.get("confidence", 0)),
                "unit":       pred.get("unit", "probability"),
            })
    return {
        "type":    VizType.PREDICTION_DASHBOARD.value,
        "items":   items,
        "summary": f"{len(items)} predictions available.",
    }


def career_forecast_viz(career_forecast: dict) -> dict:
    metrics = ["h_index", "citations", "publications", "promotion_readiness"]
    series = []
    for m in metrics:
        pred = career_forecast.get(m)
        if pred:
            series.append({
                "metric":     m.replace("_", " ").title(),
                "value":      _safe(pred.get("value")),
                "confidence": _safe(pred.get("confidence")),
                "unit":       pred.get("unit", "score"),
            })
    milestones = career_forecast.get("milestones", [])
    return {
        "type":      VizType.CAREER_FORECAST.value,
        "horizon":   career_forecast.get("horizon", "3y"),
        "series":    series,
        "milestones": milestones,
    }


def publication_forecast_viz(pub_prediction: dict) -> dict:
    stages = [
        ("Desk Rejection",   "desk_rejection"),
        ("Major Revision",   "major_revision"),
        ("Minor Revision",   "minor_revision"),
        ("Acceptance",       "acceptance"),
    ]
    distribution = [
        {"stage": label, "probability": _safe(pub_prediction.get(key, {}).get("value", 0))}
        for label, key in stages
    ]
    return {
        "type":         VizType.PUBLICATION_FORECAST.value,
        "distribution": distribution,
        "timeline": {
            "review_weeks":      _safe(pub_prediction.get("expected_review_weeks", {}).get("value")),
            "acceptance_months": _safe(pub_prediction.get("expected_acceptance_months", {}).get("value")),
            "publication_months":_safe(pub_prediction.get("expected_publication_months", {}).get("value")),
        },
        "confidence": _safe(pub_prediction.get("overall_confidence", 0)),
    }


def citation_forecast_viz(pub_prediction: dict) -> dict:
    vel_y1 = _safe(pub_prediction.get("citation_velocity_y1", {}).get("value"))
    gro_3y = _safe(pub_prediction.get("citation_growth_3y", {}).get("value"))
    return {
        "type": VizType.CITATION_FORECAST.value,
        "series": [
            {"year": 1, "expected_citations": round(vel_y1, 1)},
            {"year": 2, "expected_citations": round(vel_y1 * 2.1, 1)},
            {"year": 3, "expected_citations": round(gro_3y, 1)},
            {"year": 5, "expected_citations": round(gro_3y * 1.7, 1)},
        ],
        "long_term_impact": _safe(pub_prediction.get("long_term_impact", {}).get("value")),
    }


def grant_forecast_viz(grant_prediction: dict) -> dict:
    return {
        "type": VizType.GRANT_FORECAST.value,
        "funding_probability":  _safe(grant_prediction.get("funding_probability", {}).get("value")),
        "competitiveness":      _safe(grant_prediction.get("competitiveness", {}).get("value")),
        "evaluation_score":     _safe(grant_prediction.get("evaluation_score", {}).get("value")),
        "budget_adequacy":      _safe(grant_prediction.get("budget_adequacy", {}).get("value")),
        "reviewer_concerns":    grant_prediction.get("reviewer_concerns", []),
        "required_improvements":grant_prediction.get("required_improvements", []),
    }


def risk_matrix_viz(predictions: dict) -> dict:
    """2×2 risk matrix (probability vs impact)."""
    items = []
    for key, pred in predictions.items():
        if not isinstance(pred, dict):
            continue
        prob   = _safe(pred.get("value", 0))
        impact = _safe(pred.get("value", 0))  # impact proxy = value
        quadrant = (
            "high_risk"     if prob >= 0.5 and impact >= 0.5 else
            "monitor"       if prob >= 0.5 else
            "low_impact"    if impact < 0.5 else
            "low_risk"
        )
        items.append({"label": key, "probability": prob, "impact": impact, "quadrant": quadrant})
    return {"type": VizType.RISK_MATRIX.value, "items": items}


def scenario_comparison_viz(scenario_comparison: dict) -> dict:
    return {
        "type":       VizType.SCENARIO_COMPARISON.value,
        "scenarios":  scenario_comparison.get("scenarios", []),
        "matrix":     scenario_comparison.get("comparison_matrix", {}),
        "recommended":scenario_comparison.get("recommended_scenario", ""),
    }


def timeline_projection_viz(career_forecast: dict) -> dict:
    milestones = career_forecast.get("milestones", [])
    events = []
    for ms in milestones:
        events.append({
            "year":        ms.get("estimated_year", 1),
            "milestone":   ms.get("milestone", ""),
            "probability": _safe(ms.get("probability", 0.5)),
        })
    return {
        "type":   VizType.TIMELINE_PROJECTION.value,
        "horizon":career_forecast.get("horizon", "3y"),
        "events": events,
    }


def build_visualization(viz_type: str, data: dict) -> dict:
    """Dispatch to the correct builder."""
    try:
        vt = VizType(viz_type)
    except ValueError:
        return {"error": f"Unknown visualization type: {viz_type}"}

    if vt == VizType.PREDICTION_DASHBOARD:
        return prediction_dashboard_viz(data)
    if vt == VizType.CAREER_FORECAST:
        return career_forecast_viz(data)
    if vt == VizType.PUBLICATION_FORECAST:
        return publication_forecast_viz(data)
    if vt == VizType.CITATION_FORECAST:
        return citation_forecast_viz(data)
    if vt == VizType.GRANT_FORECAST:
        return grant_forecast_viz(data)
    if vt == VizType.RISK_MATRIX:
        return risk_matrix_viz(data)
    if vt == VizType.SCENARIO_COMPARISON:
        return scenario_comparison_viz(data)
    if vt == VizType.TIMELINE_PROJECTION:
        return timeline_projection_viz(data)
    return {"error": f"Unhandled viz type: {viz_type}"}
