"""
Performance Profiler — Phase XXXV.6

Automatically tracks operation latencies across all subsystems and
identifies slow endpoints, queries, workers, and prompts.

The profiler maintains a rolling window of recent samples and computes
P50/P95/P99 per operation. Operations exceeding their threshold are
flagged as slow and surfaced in the Operations Center.

Usage:
    from obs.profiler import get_profiler
    p = get_profiler()
    p.record("api.POST./api/ai", 342.1, "api")
    slow = p.slow_operations()
    hints = p.recommendations()
"""
from __future__ import annotations

import math
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Thresholds (ms) above which an operation is considered slow for its category
_THRESHOLDS: dict[str, float] = {
    "api":       500.0,
    "db":        200.0,
    "ai":       5000.0,
    "worker":   3000.0,
    "graph":    1000.0,
    "twin":     2000.0,
    "mission":  30000.0,
    "cache":     100.0,
    "scheduler":  500.0,
}
_DEFAULT_THRESHOLD = 1000.0
_MAX_SAMPLES       = 500


@dataclass
class OperationStats:
    name:       str
    component:  str
    count:      int = 0
    total_ms:   float = 0.0
    slow_count: int = 0
    min_ms:     float = math.inf
    max_ms:     float = -math.inf
    samples:    deque = field(default_factory=lambda: deque(maxlen=_MAX_SAMPLES))
    last_seen:  str = ""

    def record(self, duration_ms: float) -> None:
        self.count     += 1
        self.total_ms  += duration_ms
        self.last_seen  = datetime.utcnow().isoformat()
        if duration_ms < self.min_ms: self.min_ms = duration_ms
        if duration_ms > self.max_ms: self.max_ms = duration_ms
        self.samples.append(duration_ms)
        threshold = _THRESHOLDS.get(self.component, _DEFAULT_THRESHOLD)
        if duration_ms > threshold:
            self.slow_count += 1

    @property
    def mean_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0.0

    @property
    def slow_pct(self) -> float:
        return self.slow_count / self.count * 100 if self.count else 0.0

    def _pct(self, p: float) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        idx = max(0, min(int(math.ceil(p / 100 * len(s))) - 1, len(s) - 1))
        return s[idx]

    def to_dict(self) -> dict:
        threshold = _THRESHOLDS.get(self.component, _DEFAULT_THRESHOLD)
        return {
            "name":        self.name,
            "component":   self.component,
            "count":       self.count,
            "mean_ms":     round(self.mean_ms, 1),
            "p50_ms":      round(self._pct(50), 1),
            "p95_ms":      round(self._pct(95), 1),
            "p99_ms":      round(self._pct(99), 1),
            "min_ms":      round(self.min_ms, 1) if self.count else 0.0,
            "max_ms":      round(self.max_ms, 1) if self.count else 0.0,
            "slow_count":  self.slow_count,
            "slow_pct":    round(self.slow_pct, 1),
            "threshold_ms": threshold,
            "last_seen":   self.last_seen,
        }


class PerformanceProfiler:

    def __init__(self) -> None:
        self._lock:  threading.Lock = threading.Lock()
        self._stats: dict[str, OperationStats] = {}

    def record(
        self,
        operation:  str,
        duration_ms: float,
        component:  str = "unknown",
        tags:       dict | None = None,
    ) -> None:
        key = f"{component}.{operation}"
        with self._lock:
            if key not in self._stats:
                self._stats[key] = OperationStats(name=operation, component=component)
            self._stats[key].record(duration_ms)

    def slow_operations(self, limit: int = 20) -> list[dict]:
        """Return operations sorted by P95 latency descending."""
        with self._lock:
            ops = [s.to_dict() for s in self._stats.values() if s.count > 0]
        ops.sort(key=lambda x: x["p95_ms"], reverse=True)
        return ops[:limit]

    def all_stats(self) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in self._stats.values()]

    def component_stats(self, component: str) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in self._stats.values() if s.component == component]

    def recommendations(self) -> list[dict]:
        """Generate optimization hints for slow operations."""
        hints: list[dict] = []
        with self._lock:
            ops = list(self._stats.values())
        for op in ops:
            if op.slow_pct > 20:
                threshold = _THRESHOLDS.get(op.component, _DEFAULT_THRESHOLD)
                hints.append({
                    "operation":   op.name,
                    "component":   op.component,
                    "p95_ms":      round(op._pct(95), 1),
                    "slow_pct":    round(op.slow_pct, 1),
                    "suggestion":  _suggest(op.component, op.name, op._pct(95)),
                    "priority":    "high" if op.slow_pct > 50 else "medium",
                })
        hints.sort(key=lambda x: x["slow_pct"], reverse=True)
        return hints

    def reset(self) -> None:
        with self._lock:
            self._stats.clear()


def _suggest(component: str, operation: str, p95_ms: float) -> str:
    suggestions = {
        "api":       "Add response caching or optimise database queries for this endpoint",
        "db":        "Add an index or use projection to reduce document size",
        "ai":        "Use caching for repeated prompts or switch to a faster model",
        "worker":    "Increase worker concurrency or optimise the handler",
        "graph":     "Add graph indexes or reduce traversal depth",
        "twin":      "Cache twin computations or run simulations asynchronously",
        "mission":   "Break mission into smaller steps or parallelise agent execution",
        "cache":     "Review cache key design — high latency may indicate large payloads",
        "scheduler": "Verify scheduled jobs are not overlapping",
    }
    return suggestions.get(component, "Investigate the operation for bottlenecks")


# ── Singleton ─────────────────────────────────────────────────────────────────

_profiler: PerformanceProfiler | None = None


def init_profiler() -> PerformanceProfiler:
    global _profiler
    _profiler = PerformanceProfiler()
    return _profiler


def get_profiler() -> PerformanceProfiler:
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler()
    return _profiler


def reset_profiler() -> None:
    global _profiler
    _profiler = PerformanceProfiler()
