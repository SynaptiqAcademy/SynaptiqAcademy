"""Institution Intelligence Engine — Autonomous Monitoring (Phase XV).

Continuously checks KPIs against thresholds and generates alerts.
"""
from __future__ import annotations

from .models import (
    AlertType, InstitutionInput, InstitutionKPIs,
    MonitoringAlert, RiskLevel,
)


_THRESHOLDS = {
    "grant_success_rate":         (0.25, "Grant success rate dropped below 25% — immediate action required."),
    "publication_growth":         (-0.05, "Publication output is declining — investigate immediately."),
    "internationalization_score": (0.15, "International collaboration ratio critically low."),
    "collaboration_score":        (0.15, "Collaboration score is critically low — isolation risk."),
    "reputation_score":           (0.30, "Institutional reputation score is critically low."),
    "faculty_performance":        (0.25, "Faculty performance score below threshold."),
    "research_efficiency":        (0.20, "Research efficiency is critically low."),
    "sustainability_score":       (0.20, "Funding sustainability is at risk."),
    "doctoral_activity_score":    (0.10, "Doctoral activity is critically low."),
    "q1_ratio":                   (0.15, "Q1 publication ratio is very low — quality at risk."),
}

_OPPORTUNITY_THRESHOLDS = {
    "avg_h_index":                (12.0, "Research impact is strong — consider applying for excellence grants."),
    "collaboration_score":        (0.60, "High collaboration score — leverage for international grant consortia."),
    "internationalization_score": (0.50, "Strong international network — target Marie Curie and Erasmus+ funding."),
    "innovation_score":           (0.50, "High innovation score — pursue technology transfer and industry partnerships."),
}


def _severity(value: float, threshold: float, is_decline: bool = True) -> RiskLevel:
    if is_decline:
        gap = threshold - value
    else:
        gap = value - threshold
    if gap > 0.3:
        return RiskLevel.CRITICAL
    if gap > 0.15:
        return RiskLevel.HIGH
    if gap > 0.05:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def monitor(inp: InstitutionInput, kpis: InstitutionKPIs) -> list[MonitoringAlert]:
    """Generate alerts based on KPI thresholds."""
    alerts: list[MonitoringAlert] = []
    kpi_dict = kpis.to_dict()

    # KPI threshold alerts (decline)
    for metric, (threshold, message) in _THRESHOLDS.items():
        value = float(kpi_dict.get(metric, 0.0))
        if metric == "publication_growth":
            is_decline = True
            triggered = value < threshold
        else:
            is_decline = True
            triggered = value < threshold

        if triggered:
            alerts.append(MonitoringAlert(
                alert_type=AlertType.KPI_DECLINE,
                severity=_severity(value, threshold, is_decline=True),
                metric=metric,
                entity="Institution",
                message=message,
                current_value=round(value, 3),
                threshold=threshold,
                recommended_action=f"Review {metric.replace('_', ' ')} and implement improvement plan.",
            ))

    # Opportunity alerts (above threshold)
    for metric, (threshold, message) in _OPPORTUNITY_THRESHOLDS.items():
        value = float(kpi_dict.get(metric, 0.0))
        if value >= threshold:
            alerts.append(MonitoringAlert(
                alert_type=AlertType.OPPORTUNITY,
                severity=RiskLevel.MINIMAL,
                metric=metric,
                entity="Institution",
                message=message,
                current_value=round(value, 3),
                threshold=threshold,
                recommended_action="Capitalise on this institutional strength.",
            ))

    # Grant income alert
    n = max(len(inp.researchers), 1)
    if kpis.research_income > 0 and kpis.research_income < n * 20000:
        alerts.append(MonitoringAlert(
            alert_type=AlertType.KPI_DECLINE,
            severity=RiskLevel.HIGH,
            metric="research_income",
            entity="Institution",
            message=f"Research income (€{kpis.research_income:,.0f}) is low relative to researcher count.",
            current_value=kpis.research_income,
            threshold=n * 20000,
            recommended_action="Increase grant applications; pursue industry partnerships.",
        ))

    # PhD supervision ratio
    phd_count  = sum(1 for r in inp.researchers if "phd" in (r.get("position") or "").lower())
    supervisors = sum(1 for r in inp.researchers
                     if (r.get("position") or "").lower() in ("professor", "full professor",
                                                               "associate professor", "assistant professor"))
    if supervisors > 0 and phd_count / supervisors > 8:
        alerts.append(MonitoringAlert(
            alert_type=AlertType.RISK_THRESHOLD,
            severity=RiskLevel.HIGH,
            metric="supervision_ratio",
            entity="Institution",
            message=f"PhD-to-supervisor ratio ({phd_count / supervisors:.1f}) exceeds safe limit (8:1).",
            current_value=phd_count / supervisors,
            threshold=8.0,
            recommended_action="Redistribute supervision load; consider co-supervisors.",
        ))

    # Sort: critical first
    level_order = {
        RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 3, RiskLevel.MINIMAL: 4,
    }
    return sorted(alerts, key=lambda a: level_order.get(a.severity, 5))
