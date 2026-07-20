"""Literature Intelligence telemetry — session-level and corpus-level metrics."""
from __future__ import annotations

import threading
from collections import Counter, deque
from dataclasses import dataclass, field


@dataclass
class _TelemetryState:
    total_sessions: int = 0
    total_papers_ingested: int = 0
    total_papers_analyzed: int = 0
    total_reviews_generated: int = 0
    total_exports: int = 0
    total_gaps_detected: int = 0

    source_counts: Counter = field(default_factory=Counter)
    review_type_counts: Counter = field(default_factory=Counter)
    export_format_counts: Counter = field(default_factory=Counter)
    ingestion_errors: int = 0

    avg_papers_per_session: float = 0.0
    avg_session_quality: float = 0.0

    # Rolling latency for ingestion and analysis
    ingestion_latencies: deque = field(default_factory=lambda: deque(maxlen=500))
    analysis_latencies: deque = field(default_factory=lambda: deque(maxlen=500))


class LiteratureIntelligenceTelemetry:
    def __init__(self) -> None:
        self._state = _TelemetryState()
        self._lock = threading.Lock()

    def record_session_created(self) -> None:
        with self._lock:
            self._state.total_sessions += 1

    def record_papers_ingested(self, count: int, source: str, errors: int = 0) -> None:
        with self._lock:
            self._state.total_papers_ingested += count
            self._state.source_counts[source] += count
            self._state.ingestion_errors += errors

    def record_papers_analyzed(self, count: int, latency_ms: float = 0.0) -> None:
        with self._lock:
            self._state.total_papers_analyzed += count
            if latency_ms > 0:
                self._state.analysis_latencies.append(latency_ms)

    def record_review_generated(self, review_type: str) -> None:
        with self._lock:
            self._state.total_reviews_generated += 1
            self._state.review_type_counts[review_type] += 1

    def record_export(self, fmt: str) -> None:
        with self._lock:
            self._state.total_exports += 1
            self._state.export_format_counts[fmt] += 1

    def record_gaps_detected(self, count: int) -> None:
        with self._lock:
            self._state.total_gaps_detected += count

    def get_stats(self) -> dict:
        with self._lock:
            s = self._state
            lats = list(s.analysis_latencies)

            p50 = _percentile(lats, 50)
            p95 = _percentile(lats, 95)

            return {
                "total_sessions": s.total_sessions,
                "total_papers_ingested": s.total_papers_ingested,
                "total_papers_analyzed": s.total_papers_analyzed,
                "total_reviews_generated": s.total_reviews_generated,
                "total_exports": s.total_exports,
                "total_gaps_detected": s.total_gaps_detected,
                "ingestion_errors": s.ingestion_errors,
                "source_distribution": dict(s.source_counts),
                "review_type_distribution": dict(s.review_type_counts),
                "export_format_distribution": dict(s.export_format_counts),
                "analysis_p50_ms": p50,
                "analysis_p95_ms": p95,
            }

    def reset(self) -> None:
        with self._lock:
            self._state = _TelemetryState()


def _percentile(data: list[float], pct: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = max(0, int(len(sorted_data) * pct / 100) - 1)
    return round(sorted_data[idx], 1)


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: LiteratureIntelligenceTelemetry | None = None
_lock = threading.Lock()


def get_literature_telemetry() -> LiteratureIntelligenceTelemetry:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = LiteratureIntelligenceTelemetry()
    return _instance
