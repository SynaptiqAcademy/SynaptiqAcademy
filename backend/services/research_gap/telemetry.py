"""Research Gap Intelligence telemetry — thread-safe singleton metrics."""
from __future__ import annotations

import threading
from collections import Counter, deque
from dataclasses import dataclass, field


@dataclass
class _State:
    total_analyses: int = 0
    total_gaps_detected: int = 0
    total_exports: int = 0
    analysis_errors: int = 0

    depth_counts: Counter = field(default_factory=Counter)
    gap_type_counts: Counter = field(default_factory=Counter)
    export_format_counts: Counter = field(default_factory=Counter)
    source_counts: Counter = field(default_factory=Counter)

    analysis_latencies: deque = field(default_factory=lambda: deque(maxlen=500))
    avg_gaps_per_analysis: float = 0.0
    avg_opportunity_score: float = 0.0


class GapIntelligenceTelemetry:
    def __init__(self) -> None:
        self._state = _State()
        self._lock = threading.Lock()

    def record_analysis(
        self,
        depth: str,
        gap_count: int,
        avg_opp_score: float,
        latency_ms: float,
        sources: list[str],
    ) -> None:
        with self._lock:
            s = self._state
            s.total_analyses += 1
            s.total_gaps_detected += gap_count
            s.depth_counts[depth] += 1
            for src in sources:
                s.source_counts[src] += 1
            if latency_ms > 0:
                s.analysis_latencies.append(latency_ms)
            # Running average
            n = s.total_analyses
            s.avg_gaps_per_analysis = (s.avg_gaps_per_analysis * (n - 1) + gap_count) / n
            s.avg_opportunity_score = (s.avg_opportunity_score * (n - 1) + avg_opp_score) / n

    def record_gap_types(self, gap_types: list[str]) -> None:
        with self._lock:
            for gt in gap_types:
                self._state.gap_type_counts[gt] += 1

    def record_export(self, fmt: str) -> None:
        with self._lock:
            self._state.total_exports += 1
            self._state.export_format_counts[fmt] += 1

    def record_error(self) -> None:
        with self._lock:
            self._state.analysis_errors += 1

    def get_stats(self) -> dict:
        with self._lock:
            s = self._state
            lats = list(s.analysis_latencies)
            return {
                "total_analyses": s.total_analyses,
                "total_gaps_detected": s.total_gaps_detected,
                "total_exports": s.total_exports,
                "analysis_errors": s.analysis_errors,
                "avg_gaps_per_analysis": round(s.avg_gaps_per_analysis, 2),
                "avg_opportunity_score": round(s.avg_opportunity_score, 3),
                "depth_distribution": dict(s.depth_counts),
                "gap_type_distribution": dict(s.gap_type_counts.most_common(18)),
                "source_distribution": dict(s.source_counts),
                "export_format_distribution": dict(s.export_format_counts),
                "analysis_p50_ms": _pct(lats, 50),
                "analysis_p95_ms": _pct(lats, 95),
            }

    def reset(self) -> None:
        with self._lock:
            self._state = _State()


def _pct(data: list[float], pct: int) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = max(0, int(len(s) * pct / 100) - 1)
    return round(s[idx], 1)


_instance: GapIntelligenceTelemetry | None = None
_lock = threading.Lock()


def get_gap_telemetry() -> GapIntelligenceTelemetry:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = GapIntelligenceTelemetry()
    return _instance
