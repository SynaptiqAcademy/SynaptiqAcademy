"""SmartRouterTelemetry — thread-safe routing metrics and cost tracking."""
from __future__ import annotations

import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field


_LATENCY_WINDOW = 1000   # last N requests for percentile calculations


@dataclass
class _LatencyRecord:
    latency_ms: int
    layer: str
    feature: str
    timestamp: float = field(default_factory=time.time)


class SmartRouterTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self._total_requests: int = 0
        self._layer_counts: Counter[str] = Counter()
        self._feature_counts: Counter[str] = Counter()
        self._provider_counts: Counter[str] = Counter()
        self._total_cloud_cost_usd: float = 0.0
        self._total_saved_cost_usd: float = 0.0   # vs all-cloud baseline
        self._fallback_counts: Counter[str] = Counter()
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._budget_signals: Counter[str] = Counter()
        self._complexity_counts: Counter[str] = Counter()
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._latencies: deque[_LatencyRecord] = deque(maxlen=_LATENCY_WINDOW)

    def record(
        self,
        layer: str,
        feature: str,
        provider: str,
        latency_ms: int,
        actual_cost_usd: float,
        baseline_cost_usd: float,     # cost if this had gone to cloud
        fallback_reason: str = "",
        from_cache: bool = False,
        budget_signal: str = "proceed",
        complexity: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        with self._lock:
            self._total_requests += 1
            self._layer_counts[layer] += 1
            self._feature_counts[feature] += 1
            self._provider_counts[provider] += 1
            self._total_cloud_cost_usd += actual_cost_usd
            self._total_saved_cost_usd += max(0.0, baseline_cost_usd - actual_cost_usd)
            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens
            if fallback_reason:
                self._fallback_counts[fallback_reason] += 1
            if from_cache:
                self._cache_hits += 1
            else:
                self._cache_misses += 1
            self._budget_signals[budget_signal] += 1
            if complexity:
                self._complexity_counts[complexity] += 1
            self._latencies.append(_LatencyRecord(
                latency_ms=latency_ms, layer=layer, feature=feature
            ))

    def get_stats(self) -> dict:
        with self._lock:
            n = self._total_requests
            cache_total = self._cache_hits + self._cache_misses
            cache_rate = (self._cache_hits / cache_total * 100) if cache_total > 0 else 0.0

            lat_vals = [r.latency_ms for r in self._latencies]
            lat_vals_sorted = sorted(lat_vals)
            p50 = lat_vals_sorted[len(lat_vals_sorted) // 2] if lat_vals_sorted else 0
            p95 = lat_vals_sorted[int(len(lat_vals_sorted) * 0.95)] if lat_vals_sorted else 0
            p99 = lat_vals_sorted[int(len(lat_vals_sorted) * 0.99)] if lat_vals_sorted else 0

            layer_pct: dict[str, float] = {}
            for layer, count in self._layer_counts.items():
                layer_pct[layer] = round(count / n * 100, 1) if n > 0 else 0.0

            return {
                "total_requests": n,
                "layer_distribution": dict(self._layer_counts),
                "layer_distribution_pct": layer_pct,
                "top_features": self._feature_counts.most_common(10),
                "top_providers": dict(self._provider_counts),
                "total_cloud_cost_usd": round(self._total_cloud_cost_usd, 4),
                "total_cost_saved_usd": round(self._total_saved_cost_usd, 4),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_rate_pct": round(cache_rate, 1),
                "fallbacks": dict(self._fallback_counts),
                "budget_signals": dict(self._budget_signals),
                "complexity_distribution": dict(self._complexity_counts),
                "total_input_tokens": self._total_input_tokens,
                "total_output_tokens": self._total_output_tokens,
                "latency_p50_ms": p50,
                "latency_p95_ms": p95,
                "latency_p99_ms": p99,
                "avg_latency_ms": round(sum(lat_vals) / len(lat_vals), 1) if lat_vals else 0,
            }

    def reset(self) -> None:
        with self._lock:
            self._reset()

    def get_routing_accuracy(self) -> dict:
        """Percentage of requests served by the optimal layer (no fallback)."""
        with self._lock:
            n = self._total_requests
            fallbacks = sum(self._fallback_counts.values())
            accurate = n - fallbacks
            return {
                "total": n,
                "routed_correctly": accurate,
                "fallbacks": fallbacks,
                "accuracy_pct": round(accurate / n * 100, 1) if n > 0 else 100.0,
            }


_telemetry: SmartRouterTelemetry | None = None
_lock = threading.Lock()


def get_router_telemetry() -> SmartRouterTelemetry:
    global _telemetry
    if _telemetry is None:
        with _lock:
            if _telemetry is None:
                _telemetry = SmartRouterTelemetry()
    return _telemetry
