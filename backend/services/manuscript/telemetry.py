"""Thread-safe telemetry singleton — Phase IX Manuscript Intelligence."""
from __future__ import annotations

import threading
from typing import Optional


class ManuscriptTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._total_reviews = 0
            self._total_exports = 0
            self._errors = 0
            self._depth_counts: dict[str, int] = {}
            self._recommendation_counts: dict[str, int] = {}
            self._format_counts: dict[str, int] = {}
            self._latencies: list[float] = []
            self._avg_score: float = 0.0
            self._score_sum: float = 0.0

    def record_review(
        self,
        depth: str,
        overall_score: float,
        recommendation: str,
        latency_ms: float,
    ) -> None:
        with self._lock:
            self._total_reviews += 1
            self._depth_counts[depth] = self._depth_counts.get(depth, 0) + 1
            self._recommendation_counts[recommendation] = (
                self._recommendation_counts.get(recommendation, 0) + 1
            )
            self._latencies.append(latency_ms)
            if len(self._latencies) > 1000:
                self._latencies = self._latencies[-1000:]
            self._score_sum += overall_score
            self._avg_score = self._score_sum / self._total_reviews

    def record_export(self, fmt: str) -> None:
        with self._lock:
            self._total_exports += 1
            self._format_counts[fmt] = self._format_counts.get(fmt, 0) + 1

    def record_error(self) -> None:
        with self._lock:
            self._errors += 1

    def get_stats(self) -> dict:
        with self._lock:
            n = len(self._latencies)
            if n == 0:
                p50 = p95 = 0.0
            else:
                sorted_lat = sorted(self._latencies)
                p50 = sorted_lat[int(n * 0.50)]
                p95 = sorted_lat[int(n * 0.95)]
            return {
                "total_reviews": self._total_reviews,
                "total_exports": self._total_exports,
                "review_errors": self._errors,
                "avg_overall_score": round(self._avg_score, 2),
                "depth_distribution": dict(self._depth_counts),
                "recommendation_distribution": dict(self._recommendation_counts),
                "export_format_distribution": dict(self._format_counts),
                "review_p50_ms": round(p50, 1),
                "review_p95_ms": round(p95, 1),
            }


_instance: Optional[ManuscriptTelemetry] = None
_instance_lock = threading.Lock()


def get_manuscript_telemetry() -> ManuscriptTelemetry:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ManuscriptTelemetry()
    return _instance
