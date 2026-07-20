"""Rule Engine orchestrator — routes deterministic tasks to the appropriate sub-service.

This is the single entry point for all rule-based computations. Each feature is
mapped to a handler that executes in pure Python with zero LLM/API calls.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from . import telemetry

logger = logging.getLogger("synaptiq.rule_engine")


# ── Feature → Handler dispatch table ──────────────────────────────────────────

def _handle_profile_score(data: dict) -> dict:
    from .scoring.profile_score import calculate_profile_score
    return calculate_profile_score(data).to_dict()


def _handle_research_score(data: dict) -> dict:
    from .scoring.research_score import calculate_research_score
    return calculate_research_score(**{
        k: data[k] for k in (
            "publications", "citations", "h_index", "grants_awarded",
            "reviews_completed", "collaborations", "career_years",
        ) if k in data
    }).to_dict()


def _handle_collaboration_score(data: dict) -> dict:
    from .scoring.collaboration_score import calculate_collaboration_score
    return calculate_collaboration_score(**{
        k: data[k] for k in (
            "owned_collaborations", "accepted_applications", "workspace_members",
            "completion_rate", "international_partners", "active_projects",
        ) if k in data
    }).to_dict()


def _handle_reviewer_score(data: dict) -> dict:
    from .scoring.reviewer_score import calculate_reviewer_score
    return calculate_reviewer_score(**{
        k: data[k] for k in (
            "reviews_completed", "avg_turnaround_days", "avg_quality_rating",
            "declined_invitations", "accepted_invitations",
        ) if k in data
    }).to_dict()


def _handle_teaching_score(data: dict) -> dict:
    from .scoring.teaching_score import calculate_teaching_score
    return calculate_teaching_score(**{
        k: data[k] for k in (
            "published_lessons", "assessments_created", "portfolio_items",
            "workspace_messages", "educational_collaborations",
            "ai_sessions", "student_reviews", "avg_student_rating",
        ) if k in data
    }).to_dict()


def _handle_institution_score(data: dict) -> dict:
    from .scoring.institution_score import calculate_institution_score
    return calculate_institution_score(**{
        k: data[k] for k in (
            "active_researchers", "publications_count", "total_citations",
            "avg_h_index", "grants_awarded", "total_grant_value_usd",
            "international_collaborations", "departments", "verified",
        ) if k in data
    }).to_dict()


def _handle_h_index(data: dict) -> dict:
    from .calculators.h_index import citation_summary
    counts = data.get("citation_counts") or []
    return citation_summary([int(c) for c in counts])


def _handle_validate_doi(data: dict) -> dict:
    from .validation.format_validator import validate_doi
    return vars(validate_doi(data.get("doi") or ""))


def _handle_validate_orcid(data: dict) -> dict:
    from .validation.format_validator import validate_orcid
    return vars(validate_orcid(data.get("orcid") or ""))


def _handle_validate_reference_apa(data: dict) -> dict:
    from .validation.reference_validator import validate_apa_reference
    return vars(validate_apa_reference(data.get("reference") or ""))


def _handle_validate_reference_ieee(data: dict) -> dict:
    from .validation.reference_validator import validate_ieee_reference
    return vars(validate_ieee_reference(data.get("reference") or ""))


def _handle_validate_manuscript(data: dict) -> dict:
    from .validation.manuscript_validator import validate_manuscript
    return validate_manuscript(
        title=data.get("title") or "",
        abstract=data.get("abstract") or "",
        keywords=data.get("keywords") or [],
        full_text=data.get("full_text") or "",
        references=data.get("references") or [],
        manuscript_type=data.get("manuscript_type") or "research_article",
    ).to_dict()


def _handle_extract_keywords(data: dict) -> dict:
    from .recommendations.keyword_extractor import extract_keywords_scored
    return {
        "keywords": extract_keywords_scored(
            data.get("text") or "",
            top_n=int(data.get("top_n") or 10),
            title=data.get("title") or "",
        )
    }


def _handle_format_apa(data: dict) -> dict:
    from .formatting.apa_formatter import build_apa_reference
    return {"formatted": build_apa_reference(data)}


def _handle_format_ieee(data: dict) -> dict:
    from .formatting.ieee_formatter import build_ieee_reference
    return {"formatted": build_ieee_reference(data, ref_number=data.get("ref_number"))}


def _handle_statistics(data: dict) -> dict:
    from .statistics.stats_engine import StatsEngine
    values = [float(v) for v in (data.get("values") or [])]
    operation = data.get("operation") or "summary"
    ops = {
        "summary": lambda: StatsEngine.summary(values),
        "mean": lambda: {"mean": StatsEngine.mean(values)},
        "median": lambda: {"median": StatsEngine.median(values)},
        "std_dev": lambda: {"std_dev": StatsEngine.std_dev(values)},
        "trend": lambda: StatsEngine.linear_trend(values),
        "forecast": lambda: {"forecast": StatsEngine.forecast(values, steps=int(data.get("steps") or 6))},
        "percentile": lambda: {"percentile": StatsEngine.percentile(values, float(data.get("p") or 50))},
        "normalize": lambda: {"normalized": StatsEngine.normalize(values)},
        "distribution": lambda: {"distribution": StatsEngine.distribution(values)},
        "growth_rate": lambda: {"growth_rate": StatsEngine.growth_rate(
            float(data.get("old") or 0), float(data.get("new") or 0)
        )},
    }
    fn = ops.get(operation)
    if fn is None:
        return StatsEngine.summary(values)
    return fn()


def _handle_generate_alerts(data: dict) -> dict:
    from .alerts.alert_engine import generate_all_alerts
    alerts = generate_all_alerts(
        profile=data.get("profile") or {},
        publications=data.get("publications"),
        grant_applications=data.get("grant_applications"),
        account=data.get("account"),
        activity_stats=data.get("activity_stats"),
    )
    return {"alerts": [a.to_dict() for a in alerts]}


def _handle_profile_recommendations(data: dict) -> dict:
    from .recommendations.profile_recommender import get_profile_recommendations
    recs = get_profile_recommendations(data.get("profile") or data)
    return {"recommendations": [r.to_dict() for r in recs]}


def _handle_action_recommendations(data: dict) -> dict:
    from .recommendations.action_recommender import get_next_actions
    actions = get_next_actions(
        profile=data.get("profile") or {},
        stats=data.get("stats"),
    )
    return {"actions": [a.to_dict() for a in actions]}


def _handle_profile_report(data: dict) -> dict:
    from .reports.profile_report import generate_profile_report
    return generate_profile_report(
        profile=data.get("profile") or {},
        publications=data.get("publications"),
        include_recommendations=bool(data.get("include_recommendations", True)),
    )


def _handle_match_researchers(data: dict) -> dict:
    from .matching.researcher_matcher import match_researchers
    results = match_researchers(
        user=data.get("user") or {},
        candidates=data.get("candidates") or [],
        top_n=int(data.get("top_n") or 10),
    )
    return {"matches": [r.to_dict() for r in results]}


def _handle_match_reviewers(data: dict) -> dict:
    from .matching.reviewer_matcher import match_reviewers
    results = match_reviewers(
        manuscript=data.get("manuscript") or {},
        reviewers=data.get("reviewers") or [],
        exclude_ids=data.get("exclude_ids"),
        top_n=int(data.get("top_n") or 10),
    )
    return {"matches": [r.to_dict() for r in results]}


def _handle_publication_analytics(data: dict) -> dict:
    from .analytics.publication_analytics import compute_publication_trends
    return compute_publication_trends(
        publications=data.get("publications") or [],
        period=data.get("period") or "year",
    )


def _handle_citation_analytics(data: dict) -> dict:
    from .analytics.citation_analytics import compute_per_publication_stats
    pubs = data.get("publications") or []
    return compute_per_publication_stats(pubs)


# ── Registry ──────────────────────────────────────────────────────────────────

_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "profile_score":              _handle_profile_score,
    "research_score":             _handle_research_score,
    "collaboration_score":        _handle_collaboration_score,
    "reviewer_score":             _handle_reviewer_score,
    "teaching_score":             _handle_teaching_score,
    "institution_score":          _handle_institution_score,
    "h_index":                    _handle_h_index,
    "validate_doi":               _handle_validate_doi,
    "validate_orcid":             _handle_validate_orcid,
    "validate_apa":               _handle_validate_reference_apa,
    "validate_ieee":              _handle_validate_reference_ieee,
    "validate_manuscript":        _handle_validate_manuscript,
    "extract_keywords":           _handle_extract_keywords,
    "format_apa":                 _handle_format_apa,
    "format_ieee":                _handle_format_ieee,
    "statistics":                 _handle_statistics,
    "generate_alerts":            _handle_generate_alerts,
    "profile_recommendations":    _handle_profile_recommendations,
    "action_recommendations":     _handle_action_recommendations,
    "profile_report":             _handle_profile_report,
    "match_researchers":          _handle_match_researchers,
    "match_reviewers":            _handle_match_reviewers,
    "publication_analytics":      _handle_publication_analytics,
    "citation_analytics":         _handle_citation_analytics,
}


class RuleEngine:
    """Stateless orchestrator. Thread-safe — all handlers are pure functions."""

    def supported_features(self) -> list[str]:
        return list(_HANDLERS.keys())

    def can_handle(self, feature: str) -> bool:
        return feature in _HANDLERS

    def execute(self, feature: str, data: dict) -> dict[str, Any]:
        """Execute a deterministic rule and return structured result.

        Never raises — returns {"error": ...} on failure.
        """
        handler = _HANDLERS.get(feature)
        if handler is None:
            return {"error": f"Unknown rule engine feature: '{feature}'",
                    "available": self.supported_features()}

        start = time.monotonic()
        error = False
        try:
            result = handler(data)
        except Exception as exc:
            logger.error("rule_engine.execute feature=%s error=%s", feature, exc)
            result = {"error": str(exc)}
            error = True

        elapsed_ms = int((time.monotonic() - start) * 1000)
        telemetry.record_execution(
            rule_name=feature,
            execution_time_ms=elapsed_ms,
            saved_ai_request=True,
            cached=False,
            error=error,
        )
        return result

    def execute_text(self, feature: str, data: dict) -> str:
        """Execute and return a human-readable text representation of the result."""
        result = self.execute(feature, data)
        if "error" in result:
            return f"Rule engine error: {result['error']}"
        return _result_to_text(feature, result)


def _result_to_text(feature: str, result: dict) -> str:
    """Convert rule engine result dict to plain-text response for LLM-layer compatibility."""
    if feature == "profile_score":
        return (
            f"Profile Completeness Score: {result.get('score', 0)}/100 ({result.get('label', '')}). "
            + (f"Recommendations: {'; '.join(result.get('recommendations', [])[:3])}"
               if result.get("recommendations") else "Profile is well-completed.")
        )
    if feature == "h_index":
        return (
            f"H-index: {result.get('h_index', 0)}. "
            f"Total citations: {result.get('total_citations', 0)}. "
            f"Publications: {result.get('publication_count', 0)}."
        )
    if feature == "extract_keywords":
        kws = [k["keyword"] for k in (result.get("keywords") or [])]
        return f"Suggested keywords: {', '.join(kws)}." if kws else "No keywords extracted."
    if feature == "generate_alerts":
        alerts = result.get("alerts") or []
        if not alerts:
            return "No alerts at this time."
        critical = [a for a in alerts if a["level"] == "critical"]
        warnings = [a for a in alerts if a["level"] == "warning"]
        lines = []
        if critical:
            lines.append(f"CRITICAL: {'; '.join(a['title'] for a in critical)}")
        if warnings:
            lines.append(f"WARNING: {'; '.join(a['title'] for a in warnings)}")
        return " | ".join(lines) if lines else "No urgent alerts."
    if feature == "statistics":
        return str(result)
    # Generic fallback: serialize key stats
    import json
    try:
        return json.dumps(result, default=str)[:500]
    except Exception:
        return str(result)[:500]


# Process-level singleton
_engine: RuleEngine | None = None
_engine_lock = __import__("threading").Lock()


def get_rule_engine() -> RuleEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = RuleEngine()
    return _engine
