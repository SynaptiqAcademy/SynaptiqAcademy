"""Academic Career Intelligence — Telemetry singleton (Phase XVI)."""
from __future__ import annotations

import threading
import time


class CareerTelemetry:
    _instance: "CareerTelemetry | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "CareerTelemetry":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._data_lock = threading.Lock()
                inst._reset()
                cls._instance = inst
        return cls._instance

    def _reset(self) -> None:
        self.profile_builds:      int   = 0
        self.roadmap_builds:      int   = 0
        self.goal_evaluations:    int   = 0
        self.skill_analyses:      int   = 0
        self.promotion_checks:    int   = 0
        self.productivity_checks: int   = 0
        self.risk_analyses:       int   = 0
        self.recommendation_runs: int   = 0
        self.copilot_suggestions: int   = 0
        self.visualizations:      int   = 0
        self.exports:             int   = 0
        self.full_analyses:       int   = 0
        self.errors:              int   = 0
        self.latencies:           list  = []

    def inc(self, counter: str) -> None:
        with self._data_lock:
            current = getattr(self, counter, 0)
            setattr(self, counter, current + 1)

    def record_latency(self, seconds: float) -> None:
        with self._data_lock:
            self.latencies.append(round(seconds, 3))
            if len(self.latencies) > 500:
                self.latencies = self.latencies[-500:]

    def to_dict(self) -> dict:
        with self._data_lock:
            avg_lat = round(sum(self.latencies) / max(len(self.latencies), 1), 3)
            return {
                "profile_builds":      self.profile_builds,
                "roadmap_builds":      self.roadmap_builds,
                "goal_evaluations":    self.goal_evaluations,
                "skill_analyses":      self.skill_analyses,
                "promotion_checks":    self.promotion_checks,
                "productivity_checks": self.productivity_checks,
                "risk_analyses":       self.risk_analyses,
                "recommendation_runs": self.recommendation_runs,
                "copilot_suggestions": self.copilot_suggestions,
                "visualizations":      self.visualizations,
                "exports":             self.exports,
                "full_analyses":       self.full_analyses,
                "errors":              self.errors,
                "avg_latency_seconds": avg_lat,
                "total_requests":      sum([
                    self.profile_builds, self.roadmap_builds, self.goal_evaluations,
                    self.skill_analyses, self.promotion_checks, self.productivity_checks,
                    self.risk_analyses, self.recommendation_runs, self.copilot_suggestions,
                    self.visualizations, self.exports, self.full_analyses,
                ]),
            }


def get_telemetry() -> CareerTelemetry:
    return CareerTelemetry()
