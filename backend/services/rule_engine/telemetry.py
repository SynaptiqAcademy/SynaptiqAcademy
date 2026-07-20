"""In-process telemetry for rule engine execution stats.

Thread-safe, in-memory. Periodically flushed to MongoDB by the admin endpoint.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleEngineStats:
    total_requests: int = 0
    ai_requests_saved: int = 0
    estimated_cost_saved_usd: float = 0.0
    total_execution_time_ms: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    error_count: int = 0
    rule_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    recent_executions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def avg_execution_time_ms(self) -> float:
        return round(self.total_execution_time_ms / max(self.total_requests, 1), 2)

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return round(self.cache_hits / max(total, 1) * 100, 1)

    @property
    def ai_cost_per_request_saved_usd(self) -> float:
        return round(
            self.estimated_cost_saved_usd / max(self.ai_requests_saved, 1), 6
        )

    def to_dict(self) -> dict[str, Any]:
        top_rules = sorted(self.rule_counts.items(), key=lambda x: -x[1])[:10]
        return {
            "total_requests": self.total_requests,
            "ai_requests_saved": self.ai_requests_saved,
            "estimated_cost_saved_usd": round(self.estimated_cost_saved_usd, 4),
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "cache_hit_rate_pct": self.cache_hit_rate,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "error_count": self.error_count,
            "top_rules": [{"rule": k, "count": v} for k, v in top_rules],
            "recent_executions": self.recent_executions[-20:],
        }


_COST_PER_SAVED_AI_REQUEST_USD = 0.0225  # ~1500 tokens × $0.015/1K tokens at Sonnet rate

_LOCK = threading.Lock()
_STATS = RuleEngineStats()
_MAX_RECENT = 100


def record_execution(
    rule_name: str,
    execution_time_ms: int,
    saved_ai_request: bool = True,
    cached: bool = False,
    error: bool = False,
) -> None:
    with _LOCK:
        _STATS.total_requests += 1
        _STATS.total_execution_time_ms += execution_time_ms
        _STATS.rule_counts[rule_name] += 1

        if saved_ai_request:
            _STATS.ai_requests_saved += 1
            _STATS.estimated_cost_saved_usd += _COST_PER_SAVED_AI_REQUEST_USD

        if cached:
            _STATS.cache_hits += 1
        else:
            _STATS.cache_misses += 1

        if error:
            _STATS.error_count += 1

        _STATS.recent_executions.append({
            "rule": rule_name,
            "ms": execution_time_ms,
            "cached": cached,
            "saved_ai": saved_ai_request,
            "error": error,
            "ts": time.time(),
        })
        # Keep recent bounded
        if len(_STATS.recent_executions) > _MAX_RECENT:
            _STATS.recent_executions = _STATS.recent_executions[-_MAX_RECENT:]


def get_stats() -> dict[str, Any]:
    with _LOCK:
        return _STATS.to_dict()


def reset_stats() -> None:
    global _STATS
    with _LOCK:
        _STATS = RuleEngineStats()
