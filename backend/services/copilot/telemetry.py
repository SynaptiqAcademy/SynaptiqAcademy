"""Academic Copilot — Thread-safe telemetry singleton (Phase XI)."""
from __future__ import annotations

import threading
import statistics
from datetime import datetime, timezone


class CopilotTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._total_chats: int = 0
            self._total_workflows: int = 0
            self._total_roadmaps: int = 0
            self._total_dashboards: int = 0
            self._errors: int = 0
            self._latencies_ms: list[float] = []
            self._intent_distribution: dict[str, int] = {}
            self._engine_dispatch_counts: dict[str, int] = {}
            self._engine_error_counts: dict[str, int] = {}
            self._workflow_statuses: dict[str, int] = {}
            self._agent_distribution: dict[str, int] = {}

    def record_chat(
        self,
        primary_intent: str,
        agent_type: str,
        engines_invoked: list[str],
        latency_ms: float,
        error: bool = False,
    ) -> None:
        with self._lock:
            self._total_chats += 1
            if error:
                self._errors += 1
            self._latencies_ms.append(latency_ms)
            if len(self._latencies_ms) > 1000:
                self._latencies_ms = self._latencies_ms[-1000:]
            self._intent_distribution[primary_intent] = (
                self._intent_distribution.get(primary_intent, 0) + 1
            )
            self._agent_distribution[agent_type] = (
                self._agent_distribution.get(agent_type, 0) + 1
            )
            for eng in engines_invoked:
                self._engine_dispatch_counts[eng] = (
                    self._engine_dispatch_counts.get(eng, 0) + 1
                )

    def record_workflow(self, status: str, engines: list[str]) -> None:
        with self._lock:
            self._total_workflows += 1
            self._workflow_statuses[status] = self._workflow_statuses.get(status, 0) + 1
            for eng in engines:
                self._engine_dispatch_counts[eng] = self._engine_dispatch_counts.get(eng, 0) + 1

    def record_roadmap(self) -> None:
        with self._lock:
            self._total_roadmaps += 1

    def record_dashboard(self) -> None:
        with self._lock:
            self._total_dashboards += 1

    def record_engine_error(self, engine: str) -> None:
        with self._lock:
            self._engine_error_counts[engine] = self._engine_error_counts.get(engine, 0) + 1

    def get_stats(self) -> dict:
        with self._lock:
            lats = list(self._latencies_ms)

        p50 = round(statistics.median(lats), 1) if lats else 0.0
        p95 = round(sorted(lats)[int(len(lats) * 0.95)], 1) if len(lats) >= 20 else (max(lats) if lats else 0.0)
        avg = round(statistics.mean(lats), 1) if lats else 0.0

        return {
            "total_chats": self._total_chats,
            "total_workflows": self._total_workflows,
            "total_roadmaps": self._total_roadmaps,
            "total_dashboards": self._total_dashboards,
            "errors": self._errors,
            "error_rate": round(self._errors / max(self._total_chats, 1), 3),
            "p50_ms": p50,
            "p95_ms": p95,
            "avg_ms": avg,
            "intent_distribution": dict(self._intent_distribution),
            "agent_distribution": dict(self._agent_distribution),
            "engine_dispatch_counts": dict(self._engine_dispatch_counts),
            "engine_error_counts": dict(self._engine_error_counts),
            "workflow_statuses": dict(self._workflow_statuses),
        }


_instance: CopilotTelemetry | None = None
_instance_lock = threading.Lock()


def get_copilot_telemetry() -> CopilotTelemetry:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = CopilotTelemetry()
    return _instance
