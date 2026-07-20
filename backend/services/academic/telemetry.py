"""AcademicIntelligenceTelemetry — thread-safe metrics for the Academic Intelligence Engine."""
from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class _TelemetryState:
    total_requests: int = 0
    enriched_requests: int = 0
    post_processed_responses: int = 0
    total_weaknesses_detected: int = 0
    validation_passes: int = 0
    validation_failures: int = 0
    quality_checks: int = 0
    quality_improvements_needed: int = 0
    domain_counts: Counter = field(default_factory=Counter)
    feature_counts: Counter = field(default_factory=Counter)
    weakness_counts: Counter = field(default_factory=Counter)
    quality_scores: list[float] = field(default_factory=list)
    confidence_scores: list[float] = field(default_factory=list)


class AcademicIntelligenceTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = _TelemetryState()

    def record_enrichment(
        self,
        feature: str,
        domain: str,
        weakness_count: int,
        confidence: float,
    ) -> None:
        with self._lock:
            self._state.total_requests += 1
            self._state.enriched_requests += 1
            self._state.total_weaknesses_detected += weakness_count
            self._state.feature_counts[feature] += 1
            self._state.domain_counts[domain] += 1
            if confidence > 0:
                self._state.confidence_scores.append(confidence)
            if len(self._state.confidence_scores) > 1000:
                self._state.confidence_scores = self._state.confidence_scores[-500:]

    def record_weakness(self, weakness_type: str) -> None:
        with self._lock:
            self._state.weakness_counts[weakness_type] += 1

    def record_validation(self, passed: bool) -> None:
        with self._lock:
            self._state.post_processed_responses += 1
            if passed:
                self._state.validation_passes += 1
            else:
                self._state.validation_failures += 1

    def record_quality(self, score: float, needs_improvement: bool) -> None:
        with self._lock:
            self._state.quality_checks += 1
            self._state.quality_scores.append(score)
            if needs_improvement:
                self._state.quality_improvements_needed += 1
            if len(self._state.quality_scores) > 1000:
                self._state.quality_scores = self._state.quality_scores[-500:]

    def get_stats(self) -> dict:
        with self._lock:
            n = self._state.total_requests
            q = self._state.quality_scores
            c = self._state.confidence_scores
            v_total = self._state.validation_passes + self._state.validation_failures

            return {
                "total_requests": n,
                "enriched_requests": self._state.enriched_requests,
                "post_processed_responses": self._state.post_processed_responses,
                "total_weaknesses_detected": self._state.total_weaknesses_detected,
                "avg_weaknesses_per_request": round(
                    self._state.total_weaknesses_detected / max(n, 1), 2
                ),
                "validation_passes": self._state.validation_passes,
                "validation_failures": self._state.validation_failures,
                "validation_pass_rate_pct": round(
                    self._state.validation_passes / max(v_total, 1) * 100, 1
                ),
                "quality_checks": self._state.quality_checks,
                "quality_improvement_rate_pct": round(
                    self._state.quality_improvements_needed / max(self._state.quality_checks, 1) * 100, 1
                ),
                "avg_quality_score": round(sum(q) / len(q), 3) if q else 0.0,
                "avg_confidence_score": round(sum(c) / len(c), 3) if c else 0.0,
                "top_features": self._state.feature_counts.most_common(10),
                "top_domains": dict(self._state.domain_counts.most_common(10)),
                "most_common_weaknesses": dict(self._state.weakness_counts.most_common(15)),
            }

    def reset(self) -> None:
        with self._lock:
            self._state = _TelemetryState()


_instance: AcademicIntelligenceTelemetry | None = None
_lock = threading.Lock()


def get_academic_telemetry() -> AcademicIntelligenceTelemetry:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = AcademicIntelligenceTelemetry()
    return _instance
