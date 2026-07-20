"""Institution Intelligence Engine — Thread-safe telemetry singleton (Phase XV)."""
from __future__ import annotations

import threading
import time
from typing import ClassVar


class InstitutionTelemetry:
    _instance: ClassVar["InstitutionTelemetry | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._data_lock = threading.Lock()
        self._counters: dict[str, int] = {
            "profile_builds": 0,
            "kpi_computations": 0,
            "org_intelligence_runs": 0,
            "predictions": 0,
            "resource_optimizations": 0,
            "talent_analyses": 0,
            "portfolio_analyses": 0,
            "benchmarks": 0,
            "risk_detections": 0,
            "decision_support_runs": 0,
            "monitoring_runs": 0,
            "knowledge_graph_builds": 0,
            "visualization_builds": 0,
            "export_generations": 0,
            "errors": 0,
        }
        self._latencies: list[float] = []

    def record(self, counter: str, n: int = 1) -> None:
        with self._data_lock:
            self._counters[counter] = self._counters.get(counter, 0) + n

    def record_error(self) -> None:
        self.record("errors")

    def record_latency(self, seconds: float) -> None:
        with self._data_lock:
            self._latencies.append(seconds)
            if len(self._latencies) > 1000:
                self._latencies = self._latencies[-500:]

    def snapshot(self) -> dict:
        with self._data_lock:
            lat = self._latencies.copy()
        avg = sum(lat) / len(lat) if lat else 0.0
        return {
            **self._counters,
            "latency_avg_s": round(avg, 4),
            "sample_count":  len(lat),
        }

    def reset(self) -> None:
        with self._data_lock:
            for k in self._counters:
                self._counters[k] = 0
            self._latencies.clear()


def get_telemetry() -> InstitutionTelemetry:
    if InstitutionTelemetry._instance is None:
        with InstitutionTelemetry._lock:
            if InstitutionTelemetry._instance is None:
                InstitutionTelemetry._instance = InstitutionTelemetry()
    return InstitutionTelemetry._instance
