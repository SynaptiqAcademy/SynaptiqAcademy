"""Research Collaboration Intelligence — Telemetry singleton (Phase XIV)."""
from __future__ import annotations

import threading
from collections import defaultdict


class CollabTelemetry:
    _instance: "CollabTelemetry | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "CollabTelemetry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    def _init(self) -> None:
        self._mu = threading.Lock()
        self._profile_builds: int    = 0
        self._match_computations: int = 0
        self._team_builds: int       = 0
        self._team_simulations: int  = 0
        self._opportunity_scans: int = 0
        self._introductions: int     = 0
        self._predictions: int       = 0
        self._network_analyses: int  = 0
        self._recommendation_runs: int = 0
        self._insight_runs: int      = 0
        self._errors: int            = 0
        self._latencies: list[float] = []

    def record(self, event: str) -> None:
        with self._mu:
            counter = f"_{event}"
            if hasattr(self, counter):
                setattr(self, counter, getattr(self, counter) + 1)

    def record_error(self) -> None:
        with self._mu:
            self._errors += 1

    def record_latency(self, seconds: float) -> None:
        with self._mu:
            self._latencies.append(seconds)
            if len(self._latencies) > 2000:
                self._latencies = self._latencies[-2000:]

    def snapshot(self) -> dict:
        with self._mu:
            lats = sorted(self._latencies)
            n = len(lats)
            p50 = lats[int(n * 0.50)] if n else 0.0
            p95 = lats[int(n * 0.95)] if n else 0.0
            avg = sum(lats) / n if n else 0.0
            return {
                "profile_builds":       self._profile_builds,
                "match_computations":   self._match_computations,
                "team_builds":          self._team_builds,
                "team_simulations":     self._team_simulations,
                "opportunity_scans":    self._opportunity_scans,
                "introductions":        self._introductions,
                "predictions":          self._predictions,
                "network_analyses":     self._network_analyses,
                "recommendation_runs":  self._recommendation_runs,
                "insight_runs":         self._insight_runs,
                "errors":               self._errors,
                "latency_p50_s":        round(p50, 4),
                "latency_p95_s":        round(p95, 4),
                "latency_avg_s":        round(avg, 4),
                "sample_count":         n,
            }

    def reset(self) -> None:
        with self._mu:
            self._init()


def get_telemetry() -> CollabTelemetry:
    return CollabTelemetry()
