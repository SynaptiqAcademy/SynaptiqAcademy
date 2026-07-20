"""Statistical Intelligence 2.0 — Visualization builder (Phase X).

All visualizations are pure JSON — no image generation.
9 visualization types, all serialisable.
"""
from __future__ import annotations

from .models import (
    AssumptionCheck, AssumptionStatus, DataQualityMetrics,
    PublicationReadiness, ResearchDesign, ResultsInterpretation,
    SamplingAnalysis, StatisticalDimensions, StatisticalIssue,
    ValidityAnalysis,
)


def build_statistical_quality_dashboard(dims: StatisticalDimensions) -> dict:
    """Radar chart of 6 quality dimensions."""
    dim_list = [
        ("Methodological Rigour", dims.methodological_rigor.score),
        ("Sample Adequacy", dims.sample_adequacy.score),
        ("Data Quality", dims.data_quality.score),
        ("Result Validity", dims.result_validity.score),
        ("Construct Validity", dims.construct_validity.score),
        ("Reporting Quality", dims.reporting_quality.score),
    ]
    return {
        "type": "statistical_quality_dashboard",
        "title": "Statistical Quality Radar",
        "axes": [{"name": name, "value": round(score, 1), "max": 100} for name, score in dim_list],
        "overall": round(dims.weighted_score(), 1),
        "legend": {"min": 0, "max": 100, "adequate": 60, "strong": 80},
    }


def build_assumption_status_chart(checks: list[AssumptionCheck]) -> dict:
    """Bar chart showing assumption verification status by method."""
    status_counts = {s.value: 0 for s in AssumptionStatus}
    by_method: dict[str, dict[str, int]] = {}
    for check in checks:
        status_counts[check.status.value] += 1
        if check.method not in by_method:
            by_method[check.method] = {s.value: 0 for s in AssumptionStatus}
        by_method[check.method][check.status.value] += 1

    total = len(checks)
    met_pct = round(status_counts.get("met", 0) / max(total, 1) * 100, 1)
    return {
        "type": "assumption_status_chart",
        "title": "Assumption Verification Status",
        "summary": {
            "total": total,
            "met": status_counts.get("met", 0),
            "violated": status_counts.get("violated", 0),
            "not_tested": status_counts.get("not_tested", 0),
            "cannot_determine": status_counts.get("cannot_determine", 0),
            "compliance_pct": met_pct,
        },
        "by_method": [
            {"method": method, "counts": counts}
            for method, counts in by_method.items()
        ],
        "bars": [
            {"label": "Met", "value": status_counts.get("met", 0), "color": "#22c55e"},
            {"label": "Violated", "value": status_counts.get("violated", 0), "color": "#ef4444"},
            {"label": "Not Tested", "value": status_counts.get("not_tested", 0), "color": "#f59e0b"},
            {"label": "Cannot Determine", "value": status_counts.get("cannot_determine", 0), "color": "#94a3b8"},
        ],
    }


def build_effect_size_summary(interp: ResultsInterpretation) -> dict:
    """Forest-plot style effect size visualisation."""
    effects = [
        {
            "measure": e.measure,
            "value": e.value,
            "magnitude": e.magnitude,
            "context": e.context,
            "colour": {
                "negligible": "#94a3b8",
                "small": "#60a5fa",
                "medium": "#22c55e",
                "large": "#f59e0b",
                "unknown": "#94a3b8",
            }.get(e.magnitude, "#94a3b8"),
        }
        for e in interp.effect_sizes
    ]
    return {
        "type": "effect_size_summary",
        "title": "Effect Size Summary",
        "effects": effects,
        "has_effect_sizes": interp.has_effect_sizes,
        "has_p_values": interp.has_p_values,
        "has_cis": interp.has_confidence_intervals,
        "model_fit": interp.model_fit_indices,
        "significance_summary": interp.statistical_significance_summary,
        "practical_significance": interp.practical_significance_note,
    }


def build_data_quality_heatmap(dq: DataQualityMetrics, design: ResearchDesign) -> dict:
    """Heatmap of data quality dimensions."""
    dimensions = [
        {"name": "Missing Data", "status": "pass" if dq.overall_missing_rate < 0.05 else
                                           "warn" if dq.overall_missing_rate < 0.20 else "fail",
         "value": f"{dq.overall_missing_rate*100:.1f}%"},
        {"name": "Outliers", "status": "pass" if dq.has_outliers_mentioned else "warn",
         "value": "Reported" if dq.has_outliers_mentioned else "Not assessed"},
        {"name": "Normality", "status": "pass" if dq.normality_met else
                                         "warn" if dq.normality_tested else "fail",
         "value": ("Met" if dq.normality_met else
                   "Violated" if dq.normality_tested else "Not tested")},
        {"name": "Homoscedasticity", "status": "pass" if dq.homoscedasticity_tested else "warn",
         "value": "Tested" if dq.homoscedasticity_tested else "Not tested"},
        {"name": "Multicollinearity",
         "status": ("fail" if dq.max_vif and dq.max_vif >= 10 else
                    "warn" if dq.max_vif and dq.max_vif >= 5 else
                    "pass" if dq.multicollinearity_tested else "warn"),
         "value": f"VIF={dq.max_vif:.1f}" if dq.max_vif else
                  "Assessed" if dq.multicollinearity_tested else "Not assessed"},
        {"name": "Independence", "status": "pass" if dq.independence_met else "warn",
         "value": "Tested" if dq.independence_met else "Not tested"},
        {"name": "Linearity", "status": "pass" if dq.linearity_mentioned else "warn",
         "value": "Verified" if dq.linearity_mentioned else "Not verified"},
    ]
    return {
        "type": "data_quality_heatmap",
        "title": "Data Quality Assessment",
        "dimensions": dimensions,
        "overall_score": round(dq.score, 1),
        "grade": dq.grade,
        "colour_key": {"pass": "#22c55e", "warn": "#f59e0b", "fail": "#ef4444"},
    }


def build_power_analysis_chart(sampling: SamplingAnalysis) -> dict:
    """Power analysis summary chart."""
    power_pct = round(sampling.power_estimate * 100, 1) if sampling.power_estimate else 0

    # Generate illustrative power curve points (effect size vs power)
    curve_points = []
    if sampling.sample_size:
        import math
        for es_idx, es_val in enumerate([0.1, 0.2, 0.3, 0.5, 0.8]):
            # Simplified Cohen formula approximation
            n = sampling.sample_size
            d = es_val
            ncp = d * math.sqrt(n / 2)
            # Rough power approximation via normal distribution
            z_alpha = 1.96
            approx_power = max(0.0, min(1.0, 1 - (z_alpha - ncp) / 2))
            curve_points.append({"effect_size": es_val, "power": round(approx_power, 3)})

    return {
        "type": "power_analysis_chart",
        "title": "Statistical Power Analysis",
        "sample_size": sampling.sample_size,
        "recommended_min": sampling.recommended_min,
        "power_estimate": power_pct,
        "is_adequate": sampling.is_adequate,
        "adequacy_verdict": sampling.adequacy_verdict,
        "power_curve": curve_points,
        "thresholds": {"minimum_power": 80, "adequate": 0.80, "strong": 0.95},
    }


def build_validity_matrix(validity: ValidityAnalysis) -> dict:
    """Matrix visualising validity threats across dimensions."""
    types = ["internal", "external", "construct", "statistical_conclusion"]
    counts = {t: 0 for t in types}
    for threat in validity.threats:
        counts[threat.threat_type] = counts.get(threat.threat_type, 0) + 1

    cells = [
        {
            "type": vtype,
            "threat_count": counts.get(vtype, 0),
            "score": getattr(validity, f"{vtype}_validity_score", validity.overall_validity_score),
            "status": ("low_risk" if counts.get(vtype, 0) == 0 else
                       "moderate_risk" if counts.get(vtype, 0) <= 2 else "high_risk"),
        }
        for vtype in ["internal", "external", "construct"]
    ]
    cells.append({
        "type": "statistical_conclusion",
        "threat_count": counts.get("statistical_conclusion", 0),
        "score": validity.overall_validity_score,
        "status": "low_risk" if counts.get("statistical_conclusion", 0) == 0 else "high_risk",
    })

    return {
        "type": "validity_matrix",
        "title": "Validity Threat Analysis",
        "cells": cells,
        "overall_validity_score": round(validity.overall_validity_score, 1),
        "grade": validity.grade,
        "reliability": validity.reliability.to_dict(),
        "colour_key": {
            "low_risk": "#22c55e", "moderate_risk": "#f59e0b", "high_risk": "#ef4444"
        },
    }


def build_issue_breakdown(
    critical: list[StatisticalIssue],
    major: list[StatisticalIssue],
    moderate: list[StatisticalIssue],
    minor: list[StatisticalIssue],
) -> dict:
    """Stacked bar — issue count by severity and category."""
    all_issues = critical + major + moderate + minor
    by_category: dict[str, dict[str, int]] = {}
    for issue in all_issues:
        cat = issue.category
        if cat not in by_category:
            by_category[cat] = {"critical": 0, "major": 0, "moderate": 0, "minor": 0}
        by_category[cat][issue.severity.value] = by_category[cat].get(issue.severity.value, 0) + 1

    return {
        "type": "issue_breakdown",
        "title": "Statistical Issues by Severity & Category",
        "summary": {
            "critical": len(critical),
            "major": len(major),
            "moderate": len(moderate),
            "minor": len(minor),
            "total": len(all_issues),
        },
        "by_category": [
            {"category": cat, "counts": counts}
            for cat, counts in by_category.items()
        ],
        "bars": [
            {"label": "Critical", "value": len(critical), "color": "#dc2626"},
            {"label": "Major",    "value": len(major),    "color": "#ea580c"},
            {"label": "Moderate", "value": len(moderate), "color": "#f59e0b"},
            {"label": "Minor",    "value": len(minor),    "color": "#84cc16"},
        ],
    }


def build_publication_readiness_gauge(pr: PublicationReadiness) -> dict:
    """Gauge showing publication readiness with probability breakdown."""
    score = pr.overall_score
    if score >= 80:
        band = "publication_ready"
        label = "Publication Ready"
        colour = "#22c55e"
    elif score >= 65:
        band = "minor_revisions"
        label = "Minor Revisions Needed"
        colour = "#84cc16"
    elif score >= 50:
        band = "major_revisions"
        label = "Major Revisions Required"
        colour = "#f59e0b"
    elif score >= 35:
        band = "substantial_rework"
        label = "Substantial Rework Needed"
        colour = "#ea580c"
    else:
        band = "not_ready"
        label = "Not Ready for Submission"
        colour = "#dc2626"

    return {
        "type": "publication_readiness_gauge",
        "title": "Publication Readiness Assessment",
        "score": round(score, 1),
        "band": band,
        "label": label,
        "colour": colour,
        "probabilities": {
            "acceptance": round(pr.acceptance_probability * 100, 1),
            "desk_rejection": round(pr.desk_rejection_risk * 100, 1),
            "revision": round((1 - pr.acceptance_probability - pr.desk_rejection_risk) * 100, 1),
        },
        "verdict": pr.verdict.value,
        "strongest_element": pr.strongest_element,
        "critical_barrier": pr.critical_barrier,
    }


def build_revision_priority_chart(roadmap: list) -> dict:
    """Gantt-like revision priority timeline."""
    effort_days = {
        "1-2 days":   2,
        "3-5 days":   5,
        "1 week":     7,
        "1-2 weeks":  10,
        "2-4 weeks":  21,
        "4-6 weeks":  35,
        "1-2 months": 45,
        "unknown":    14,
    }
    phases = []
    cumulative = 0
    for phase_dict in roadmap:
        effort_str = phase_dict.get("estimated_effort", "unknown")
        # Match effort string to closest key
        days = next(
            (v for k, v in effort_days.items() if k in effort_str.lower()),
            14
        )
        phases.append({
            "phase": phase_dict.get("phase", len(phases) + 1),
            "title": phase_dict.get("title", ""),
            "priority": phase_dict.get("priority", "medium"),
            "start_day": cumulative,
            "duration_days": days,
            "actions": phase_dict.get("actions", []),
        })
        cumulative += days
    return {
        "type": "revision_priority_chart",
        "title": "Revision Priority Timeline",
        "phases": phases,
        "total_estimated_days": cumulative,
    }


def build_all_visualizations(
    dims: StatisticalDimensions,
    assumption_checks: list,
    results_interp: ResultsInterpretation,
    data_quality: DataQualityMetrics,
    design: ResearchDesign,
    sampling: SamplingAnalysis,
    validity: ValidityAnalysis,
    critical: list,
    major: list,
    moderate: list,
    minor: list,
    publication_readiness: PublicationReadiness,
    roadmap: list,
) -> dict:
    return {
        "statistical_quality_dashboard": build_statistical_quality_dashboard(dims),
        "assumption_status_chart":       build_assumption_status_chart(assumption_checks),
        "effect_size_summary":           build_effect_size_summary(results_interp),
        "data_quality_heatmap":          build_data_quality_heatmap(data_quality, design),
        "power_analysis_chart":          build_power_analysis_chart(sampling),
        "validity_matrix":               build_validity_matrix(validity),
        "issue_breakdown":               build_issue_breakdown(critical, major, moderate, minor),
        "publication_readiness_gauge":   build_publication_readiness_gauge(publication_readiness),
        "revision_priority_chart":       build_revision_priority_chart(roadmap),
    }
