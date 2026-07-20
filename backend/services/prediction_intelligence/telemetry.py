"""Academic Prediction — Telemetry singleton (Phase XVIII)."""
from __future__ import annotations

import threading


class PredictionTelemetry:
    _instance: "PredictionTelemetry | None" = None
    _lock:     threading.Lock               = threading.Lock()

    def __new__(cls) -> "PredictionTelemetry":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._data_lock = threading.Lock()
                inst._reset()
                cls._instance = inst
        return cls._instance

    def _reset(self) -> None:
        self.publication_predictions: int = 0
        self.journal_predictions:     int = 0
        self.conference_predictions:  int = 0
        self.grant_predictions:       int = 0
        self.career_forecasts:        int = 0
        self.collaboration_forecasts: int = 0
        self.institution_forecasts:   int = 0
        self.trend_forecasts:         int = 0
        self.scenario_simulations:    int = 0
        self.what_if_analyses:        int = 0
        self.strategic_decisions:     int = 0
        self.visualizations:          int = 0
        self.copilot_enrichments:     int = 0
        self.errors:                  int = 0
        self.latencies:               list = []

    def inc(self, counter: str, amount: int = 1) -> None:
        with self._data_lock:
            setattr(self, counter, getattr(self, counter, 0) + amount)

    def record_latency(self, seconds: float) -> None:
        with self._data_lock:
            self.latencies.append(round(seconds, 4))
            if len(self.latencies) > 500:
                self.latencies = self.latencies[-500:]

    def to_dict(self) -> dict:
        with self._data_lock:
            avg_lat = round(sum(self.latencies) / len(self.latencies), 4) if self.latencies else 0.0
            return {
                "publication_predictions": self.publication_predictions,
                "journal_predictions":     self.journal_predictions,
                "conference_predictions":  self.conference_predictions,
                "grant_predictions":       self.grant_predictions,
                "career_forecasts":        self.career_forecasts,
                "collaboration_forecasts": self.collaboration_forecasts,
                "institution_forecasts":   self.institution_forecasts,
                "trend_forecasts":         self.trend_forecasts,
                "scenario_simulations":    self.scenario_simulations,
                "what_if_analyses":        self.what_if_analyses,
                "strategic_decisions":     self.strategic_decisions,
                "visualizations":          self.visualizations,
                "copilot_enrichments":     self.copilot_enrichments,
                "errors":                  self.errors,
                "avg_latency_seconds":     avg_lat,
            }


def get_telemetry() -> PredictionTelemetry:
    return PredictionTelemetry()
