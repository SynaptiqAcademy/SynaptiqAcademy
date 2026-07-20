"""Copilot Integration — enrich Academic Copilot with self-improvement insights."""
from __future__ import annotations

from .models import DiagnosticReport, DiagnosticStatus, EnginePerformanceMetrics


def generate_improvement_suggestions(
    workflow:       str,
    all_metrics:    dict[str, EnginePerformanceMetrics],
    max_suggestions: int = 5,
) -> list[dict]:
    suggestions: list[dict] = []

    for engine_type, m in all_metrics.items():
        if m.samples_evaluated == 0:
            continue
        name = engine_type.replace("_", " ").title()

        if m.trend == "improving":
            suggestions.append({
                "type":       "performance_improving",
                "engine":     engine_type,
                "title":      f"{name} accuracy improving",
                "summary":    f"Accuracy trending up to {m.accuracy:.1%} over {m.samples_evaluated} observations.",
                "confidence": round(m.avg_confidence, 3),
                "urgency":    "low",
                "action":     "continue_using",
            })

        elif m.trend == "declining":
            suggestions.append({
                "type":       "performance_alert",
                "engine":     engine_type,
                "title":      f"{name} needs attention",
                "summary":    f"Performance declining: {m.accuracy:.1%} accuracy, calibration error {m.calibration_error:.3f}.",
                "confidence": round(m.avg_confidence, 3),
                "urgency":    "high",
                "action":     "review_recommendations",
            })

        if m.calibration_error > 0.10:
            suggestions.append({
                "type":       "calibration_drift",
                "engine":     engine_type,
                "title":      f"Confidence drift in {name}",
                "summary":    f"Predicted confidence deviates {m.calibration_error:.2%} from actual outcomes.",
                "confidence": 0.85,
                "urgency":    "medium",
                "action":     "request_recalibration",
            })

    if not suggestions:
        suggestions.append({
            "type":       "data_collection",
            "engine":     "platform",
            "title":      "Building learning signals",
            "summary":    "Submit feedback on recommendations to improve platform accuracy over time.",
            "confidence": 1.0,
            "urgency":    "low",
            "action":     "provide_feedback",
        })

    return suggestions[:max_suggestions]


def enrich_with_quality_context(
    prompt:      str,
    diagnostics: list[DiagnosticReport],
) -> str:
    if not diagnostics:
        return prompt

    healthy  = [d for d in diagnostics if d.status == DiagnosticStatus.HEALTHY.value]
    warnings = [d for d in diagnostics if d.status == DiagnosticStatus.WARNING.value]
    critical = [d for d in diagnostics if d.status == DiagnosticStatus.CRITICAL.value]
    avg_h    = sum(d.health_score for d in diagnostics) / len(diagnostics)

    parts = ["\n[Platform Quality Context]"]
    if healthy:
        parts.append(f"Engines nominal: {', '.join(d.engine_type for d in healthy)}")
    if warnings:
        parts.append(f"Engines with warnings: {', '.join(d.engine_type for d in warnings)}")
    if critical:
        parts.append(f"Engines needing attention: {', '.join(d.engine_type for d in critical)}")
    parts.append(f"Overall platform health: {avg_h:.1%}")

    return prompt + "\n".join(parts)
