"""Statistical Intelligence 2.0 — Telemetry (Phase X).

Thread-safe singleton for review metrics and latency tracking.
"""
from __future__ import annotations

import threading
from typing import Optional


class StatisticalTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._total_reviews: int = 0
            self._total_exports: int = 0
            self._review_errors: int = 0
            self._score_sum: float = 0.0
            self._depth_dist: dict[str, int] = {}
            self._verdict_dist: dict[str, int] = {}
            self._export_dist: dict[str, int] = {}
            self._latencies_ms: list[float] = []

    def record_review(
        self,
        depth: str,
        overall_score: float,
        verdict: str,
        latency_ms: float,
    ) -> None:
        with self._lock:
            self._total_reviews += 1
            self._score_sum += overall_score
            self._depth_dist[depth] = self._depth_dist.get(depth, 0) + 1
            self._verdict_dist[verdict] = self._verdict_dist.get(verdict, 0) + 1
            self._latencies_ms.append(latency_ms)
            if len(self._latencies_ms) > 10_000:
                self._latencies_ms = self._latencies_ms[-10_000:]

    def record_export(self, fmt: str) -> None:
        with self._lock:
            self._total_exports += 1
            self._export_dist[fmt] = self._export_dist.get(fmt, 0) + 1

    def record_error(self) -> None:
        with self._lock:
            self._review_errors += 1

    def get_stats(self) -> dict:
        with self._lock:
            n = self._total_reviews
            sorted_lat = sorted(self._latencies_ms)
            p50 = sorted_lat[int(len(sorted_lat) * 0.50)] if sorted_lat else 0.0
            p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0.0
            return {
                "total_reviews": n,
                "total_exports": self._total_exports,
                "review_errors": self._review_errors,
                "avg_overall_score": round(self._score_sum / n, 1) if n else 0.0,
                "depth_distribution": dict(self._depth_dist),
                "verdict_distribution": dict(self._verdict_dist),
                "export_format_distribution": dict(self._export_dist),
                "review_p50_ms": round(p50, 1),
                "review_p95_ms": round(p95, 1),
            }


_INSTANCE: Optional[StatisticalTelemetry] = None
_INSTANCE_LOCK = threading.Lock()


def get_statistical_telemetry() -> StatisticalTelemetry:
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = StatisticalTelemetry()
    return _INSTANCE
