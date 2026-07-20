"""Academic Knowledge Graph — Telemetry singleton (Phase XVII)."""
from __future__ import annotations

import threading


class KGTelemetry:
    _instance: "KGTelemetry | None" = None
    _lock: threading.Lock           = threading.Lock()

    def __new__(cls) -> "KGTelemetry":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._data_lock = threading.Lock()
                inst._reset()
                cls._instance = inst
        return cls._instance

    def _reset(self) -> None:
        self.nodes_added:       int   = 0
        self.edges_added:       int   = 0
        self.queries:           int   = 0
        self.community_runs:    int   = 0
        self.pagerank_runs:     int   = 0
        self.embedding_runs:    int   = 0
        self.reasoning_calls:   int   = 0
        self.discovery_calls:   int   = 0
        self.viz_builds:        int   = 0
        self.copilot_enrichments: int = 0
        self.admin_calls:       int   = 0
        self.import_calls:      int   = 0
        self.errors:            int   = 0
        self.latencies:         list  = []

    def inc(self, counter: str, amount: int = 1) -> None:
        with self._data_lock:
            current = getattr(self, counter, 0)
            setattr(self, counter, current + amount)

    def record_latency(self, seconds: float) -> None:
        with self._data_lock:
            self.latencies.append(round(seconds, 4))
            if len(self.latencies) > 500:
                self.latencies = self.latencies[-500:]

    def to_dict(self) -> dict:
        with self._data_lock:
            avg_lat = (round(sum(self.latencies) / len(self.latencies), 4)
                       if self.latencies else 0.0)
            return {
                "nodes_added":         self.nodes_added,
                "edges_added":         self.edges_added,
                "queries":             self.queries,
                "community_runs":      self.community_runs,
                "pagerank_runs":       self.pagerank_runs,
                "embedding_runs":      self.embedding_runs,
                "reasoning_calls":     self.reasoning_calls,
                "discovery_calls":     self.discovery_calls,
                "viz_builds":          self.viz_builds,
                "copilot_enrichments": self.copilot_enrichments,
                "admin_calls":         self.admin_calls,
                "import_calls":        self.import_calls,
                "errors":              self.errors,
                "avg_latency_seconds": avg_lat,
            }


def get_telemetry() -> KGTelemetry:
    return KGTelemetry()
