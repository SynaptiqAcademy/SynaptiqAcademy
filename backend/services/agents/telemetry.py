"""Autonomous Research Agents — Thread-safe telemetry singleton (Phase XIII)."""
from __future__ import annotations

import threading
from collections import defaultdict


class AgentPlatformTelemetry:
    _instance: "AgentPlatformTelemetry | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "AgentPlatformTelemetry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    def _init(self) -> None:
        self._mu = threading.Lock()
        self._workflow_runs: int = 0
        self._ad_hoc_runs: int = 0
        self._agent_invocations: dict[str, int] = defaultdict(int)
        self._agent_failures: dict[str, int] = defaultdict(int)
        self._workflow_counts: dict[str, int] = defaultdict(int)
        self._errors: int = 0
        self._latencies: list[float] = []

    def record_workflow_run(self, workflow_type: str) -> None:
        with self._mu:
            self._workflow_runs += 1
            self._workflow_counts[workflow_type] += 1

    def record_ad_hoc_run(self) -> None:
        with self._mu:
            self._ad_hoc_runs += 1

    def record_agent_invocation(self, agent_type: str) -> None:
        with self._mu:
            self._agent_invocations[agent_type] += 1

    def record_agent_failure(self, agent_type: str) -> None:
        with self._mu:
            self._agent_failures[agent_type] += 1

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
                "workflow_runs":         self._workflow_runs,
                "ad_hoc_runs":           self._ad_hoc_runs,
                "total_agent_invocations": sum(self._agent_invocations.values()),
                "agent_invocations":     dict(self._agent_invocations),
                "agent_failures":        dict(self._agent_failures),
                "workflow_distribution": dict(self._workflow_counts),
                "errors":                self._errors,
                "latency_p50_s":         round(p50, 4),
                "latency_p95_s":         round(p95, 4),
                "latency_avg_s":         round(avg, 4),
                "sample_count":          n,
            }

    def reset(self) -> None:
        with self._mu:
            self._init()


def get_telemetry() -> AgentPlatformTelemetry:
    return AgentPlatformTelemetry()
