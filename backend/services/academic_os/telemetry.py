"""Academic OS telemetry — thread-safe singleton."""
from __future__ import annotations

import threading
import time

_MAX_LATENCY = 500


class AOSTelemetry:
    _instance: "AOSTelemetry | None" = None
    _lock = threading.Lock()

    def __init__(self):
        self._data_lock  = threading.Lock()
        self._counters: dict[str, int]   = {
            "workflows_created":      0,
            "workflow_steps_advanced": 0,
            "projects_created":       0,
            "searches_run":           0,
            "entities_indexed":       0,
            "timeline_events":        0,
            "notifications_sent":     0,
            "automation_triggered":   0,
            "sync_events_emitted":    0,
            "dashboards_generated":   0,
            "errors":                 0,
        }
        self._latencies: list[float]     = []

    @classmethod
    def get(cls) -> "AOSTelemetry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None

    def inc(self, counter: str, amount: int = 1) -> None:
        with self._data_lock:
            if counter in self._counters:
                self._counters[counter] += amount

    def record_latency(self, seconds: float) -> None:
        with self._data_lock:
            self._latencies.append(seconds)
            if len(self._latencies) > _MAX_LATENCY:
                self._latencies.pop(0)

    def snapshot(self) -> dict:
        with self._data_lock:
            lats = list(self._latencies)
            ctrs = dict(self._counters)
        avg_lat = round(sum(lats) / len(lats), 4) if lats else 0.0
        return {
            "counters": ctrs,
            "latency": {
                "avg_seconds": avg_lat,
                "samples":     len(lats),
            },
            "captured_at": time.time(),
        }


def get_aos_telemetry() -> AOSTelemetry:
    return AOSTelemetry.get()


def reset_aos_telemetry() -> None:
    AOSTelemetry.reset()
