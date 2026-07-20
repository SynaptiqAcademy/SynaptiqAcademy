"""Self-Improvement Telemetry — thread-safe singleton (Phase XX)."""
from __future__ import annotations

import threading


class SelfImprovementTelemetry:
    _instance: "SelfImprovementTelemetry | None" = None
    _lock:     threading.Lock                     = threading.Lock()

    def __new__(cls) -> "SelfImprovementTelemetry":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._data_lock = threading.Lock()
                inst._reset()
                cls._instance = inst
        return cls._instance

    def _reset(self) -> None:
        self.signals_received:             int  = 0
        self.optimizations_generated:      int  = 0
        self.optimizations_applied:        int  = 0
        self.optimizations_rolled_back:    int  = 0
        self.experiments_created:          int  = 0
        self.experiments_completed:        int  = 0
        self.experiments_deployed:         int  = 0
        self.knowledge_updates_detected:   int  = 0
        self.knowledge_updates_integrated: int  = 0
        self.diagnostics_run:              int  = 0
        self.benchmarks_run:               int  = 0
        self.errors:                       int  = 0
        self.latencies:                    list = []

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
            avg = round(sum(self.latencies) / len(self.latencies), 4) if self.latencies else 0.0
            return {
                "signals_received":             self.signals_received,
                "optimizations_generated":      self.optimizations_generated,
                "optimizations_applied":        self.optimizations_applied,
                "optimizations_rolled_back":    self.optimizations_rolled_back,
                "experiments_created":          self.experiments_created,
                "experiments_completed":        self.experiments_completed,
                "experiments_deployed":         self.experiments_deployed,
                "knowledge_updates_detected":   self.knowledge_updates_detected,
                "knowledge_updates_integrated": self.knowledge_updates_integrated,
                "diagnostics_run":              self.diagnostics_run,
                "benchmarks_run":               self.benchmarks_run,
                "errors":                       self.errors,
                "avg_latency_seconds":          avg,
            }


def get_telemetry() -> SelfImprovementTelemetry:
    return SelfImprovementTelemetry()
