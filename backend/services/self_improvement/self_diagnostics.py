"""Self-Diagnostics — continuous health evaluation of every intelligence engine."""
from __future__ import annotations

import time

from .models import DiagnosticReport, DiagnosticStatus, EnginePerformanceMetrics

_THRESHOLDS = {
    "accuracy_critical":          0.50,
    "accuracy_warning":           0.65,
    "calibration_critical":       0.25,
    "calibration_warning":        0.15,
    "acceptance_critical":        0.20,
    "acceptance_warning":         0.35,
}


def _health_score(m: EnginePerformanceMetrics) -> float:
    if m.samples_evaluated == 0:
        return 0.5

    # 0–0.35: accuracy
    score  = min(m.accuracy, 1.0) * 0.35
    # 0–0.25: calibration (lower error = better)
    score += max(0.0, 1.0 - m.calibration_error * 4) * 0.25
    # 0–0.25: user acceptance
    score += min(m.user_acceptance_rate, 1.0) * 0.25
    # 0–0.15: confidence alignment
    score += max(0.0, 1.0 - abs(m.avg_confidence - m.accuracy)) * 0.15

    return round(min(score, 1.0), 4)


def check_engine_health(
    engine_type: str,
    metrics:     EnginePerformanceMetrics,
) -> DiagnosticReport:
    health  = _health_score(metrics)
    issues: list[str] = []
    recs:   list[str] = []

    if metrics.samples_evaluated == 0:
        return DiagnosticReport(
            engine_type=engine_type,
            status=DiagnosticStatus.UNKNOWN.value,
            health_score=health,
            issues=["No observations recorded yet"],
            metrics=metrics.to_dict(),
            recommendations=["Collect at least 10 feedback signals before evaluation"],
        )

    if metrics.accuracy < _THRESHOLDS["accuracy_critical"]:
        issues.append(f"Accuracy critically low: {metrics.accuracy:.3f} < {_THRESHOLDS['accuracy_critical']}")
        recs.append("Review recommendation logic and data quality")
    elif metrics.accuracy < _THRESHOLDS["accuracy_warning"]:
        issues.append(f"Accuracy below warning threshold: {metrics.accuracy:.3f}")
        recs.append("Monitor closely; consider optimization candidate")

    if metrics.calibration_error > _THRESHOLDS["calibration_critical"]:
        issues.append(f"Calibration error critical: {metrics.calibration_error:.3f}")
        recs.append("Apply confidence recalibration optimization")
    elif metrics.calibration_error > _THRESHOLDS["calibration_warning"]:
        issues.append(f"Calibration error elevated: {metrics.calibration_error:.3f}")

    if metrics.user_acceptance_rate < _THRESHOLDS["acceptance_critical"]:
        issues.append(f"Acceptance rate critically low: {metrics.user_acceptance_rate:.3f}")
        recs.append("Investigate recommendation relevance and phrasing")
    elif metrics.user_acceptance_rate < _THRESHOLDS["acceptance_warning"]:
        issues.append(f"Acceptance rate below warning: {metrics.user_acceptance_rate:.3f}")

    if metrics.trend == "declining":
        issues.append("Performance trend declining")
        recs.append("Generate optimization candidates and run A/B experiment")

    if not issues:
        status = DiagnosticStatus.HEALTHY.value
        recs.append("Engine performing within normal parameters")
    elif any("critical" in i.lower() for i in issues):
        status = DiagnosticStatus.CRITICAL.value
    else:
        status = DiagnosticStatus.WARNING.value

    return DiagnosticReport(
        engine_type=engine_type,
        status=status,
        health_score=health,
        issues=issues,
        metrics=metrics.to_dict(),
        recommendations=recs,
        checked_at=time.time(),
    )


def check_all_engines(
    all_metrics: dict[str, EnginePerformanceMetrics],
) -> list[DiagnosticReport]:
    return [check_engine_health(et, m) for et, m in all_metrics.items()]


def platform_health_score(reports: list[DiagnosticReport]) -> float:
    if not reports:
        return 0.5
    return round(sum(r.health_score for r in reports) / len(reports), 4)
