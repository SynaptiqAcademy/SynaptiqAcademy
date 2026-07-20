"""Academic Prediction — Academic Copilot integration (Phase XVIII).

Proactively generates forecasts during every academic workflow.
"""
from __future__ import annotations

from .publication_predictor import predict_publication
from .trend_forecaster import forecast_trends


def generate_copilot_forecasts(
    workflow: str,
    profile: dict,
    max_suggestions: int = 6,
) -> list[dict]:
    """
    Return proactive forecast suggestions for a given academic workflow.

    workflow values: submission, grant, career, collaboration, trend, general
    """
    p = profile or {}
    suggestions: list[dict] = []

    # Always include publication prediction if manuscript data present
    if p.get("target_journal") or p.get("manuscript_quality"):
        pub = predict_publication(p)
        suggestions.append({
            "type":       "publication_forecast",
            "title":      "Publication Outcome Forecast",
            "summary":    f"Predicted acceptance: {round(pub.acceptance.value*100)}%. {pub.strategic_recommendation}",
            "confidence": round(pub.overall_confidence, 3),
            "urgency":    "high" if pub.acceptance.value >= 0.6 else "medium",
            "action":     pub.strategic_recommendation,
        })

    # Career forecast if profile contains career data
    if p.get("current_h_index") is not None or p.get("total_publications"):
        from .career_forecaster import forecast_career, ForecastHorizon
        cf = forecast_career(p, ForecastHorizon.THREE_YEAR)
        suggestions.append({
            "type":       "career_forecast",
            "title":      "3-Year Career Forecast",
            "summary":    f"Projected h-index: {round(cf.h_index.value, 1)}. Promotion readiness: {round(cf.promotion_readiness.value*100)}%.",
            "confidence": round(cf.confidence, 3),
            "urgency":    "low",
            "action":     "Review career milestones and adjust research strategy.",
        })

    # Grant forecast if grant data present
    if p.get("novelty_score") or p.get("pi_h_index"):
        from .grant_predictor import predict_grant
        gp = predict_grant(p)
        suggestions.append({
            "type":       "grant_forecast",
            "title":      "Grant Funding Probability",
            "summary":    f"Funding probability: {round(gp.funding_probability.value*100)}%. {gp.required_improvements[0] if gp.required_improvements else ''}",
            "confidence": round(gp.confidence, 3),
            "urgency":    "high" if gp.funding_probability.value >= 0.35 else "medium",
            "action":     gp.required_improvements[0] if gp.required_improvements else "Strengthen proposal.",
        })

    # Trend forecast (always included)
    tf = forecast_trends(p)
    if tf.hot_topics:
        hot = tf.hot_topics[0]
        suggestions.append({
            "type":       "trend_alert",
            "title":      f"Emerging Trend: {hot.topic}",
            "summary":    f"'{hot.topic}' is a hot research area with {round(hot.score*100)}% relevance score.",
            "confidence": round(hot.confidence, 3),
            "urgency":    "medium",
            "action":     f"Consider positioning research in '{hot.topic}' for maximum impact.",
        })

    # Strategic recommendation based on workflow
    if workflow == "submission":
        suggestions.append({
            "type":    "strategic_advice",
            "title":   "Submission Strategy",
            "summary": "Use scenario simulation to compare journal options before submitting.",
            "confidence": 0.85,
            "urgency": "high",
            "action":  "Run multi-scenario simulation to optimise submission strategy.",
        })
    elif workflow == "collaboration":
        suggestions.append({
            "type":    "strategic_advice",
            "title":   "Collaboration Intelligence",
            "summary": "Collaboration with international researchers increases citation impact by 25% on average.",
            "confidence": 0.80,
            "urgency": "medium",
            "action":  "Request collaboration forecast to evaluate potential partners.",
        })
    elif workflow == "career":
        suggestions.append({
            "type":    "strategic_advice",
            "title":   "Career Planning",
            "summary": "5-year career forecast available — includes h-index, promotion readiness, and milestones.",
            "confidence": 0.78,
            "urgency": "low",
            "action":  "Generate full career forecast with 5-year horizon.",
        })

    return suggestions[:max_suggestions]


def enrich_prompt_with_predictions(
    prompt: str,
    profile: dict,
) -> str:
    """Return the original prompt enriched with forecast context."""
    p = profile or {}
    context_lines: list[str] = []

    if p.get("target_journal"):
        pub = predict_publication(p)
        context_lines.append(
            f"[Forecast] Publication acceptance: {round(pub.acceptance.value*100)}% "
            f"(confidence: {round(pub.overall_confidence*100)}%). "
            f"{pub.strategic_recommendation}"
        )

    tf = forecast_trends(p)
    if tf.hot_topics:
        top3 = [t.topic for t in tf.hot_topics[:3]]
        context_lines.append(f"[Trends] Current hot topics: {', '.join(top3)}.")

    if context_lines:
        return prompt + "\n\n[Prediction Context]\n" + "\n".join(context_lines)
    return prompt
