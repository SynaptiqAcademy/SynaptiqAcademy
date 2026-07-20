"""Thread-safe telemetry for the Local AI Engine."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

# Estimated cost saved per local request (vs. cloud AI at Sonnet rate)
_COST_PER_SAVED_CLOUD_REQUEST_USD = 0.0225  # ~1500 tokens × $0.015/1K

_MAX_HISTORY = 200


@dataclass
class _Execution:
    feature: str
    provider: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    from_cache: bool
    fallback_to_cloud: bool
    error: bool
    timestamp: float = field(default_factory=time.time)


class LocalAITelemetry:
    """Process-level telemetry for local AI usage."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self._total_requests: int = 0
        self._cache_hits: int = 0
        self._fallback_count: int = 0
        self._error_count: int = 0
        self._total_latency_ms: int = 0
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._provider_counts: dict[str, int] = {}
        self._feature_counts: dict[str, int] = {}
        self._model_counts: dict[str, int] = {}
        self._history: deque[_Execution] = deque(maxlen=_MAX_HISTORY)

    def record(
        self,
        feature: str,
        provider: str,
        model: str,
        latency_ms: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        from_cache: bool = False,
        fallback_to_cloud: bool = False,
        error: bool = False,
    ) -> None:
        with self._lock:
            self._total_requests += 1
            if from_cache:
                self._cache_hits += 1
            if fallback_to_cloud:
                self._fallback_count += 1
            if error:
                self._error_count += 1
            if not error:
                self._total_latency_ms += latency_ms
                self._total_input_tokens += input_tokens
                self._total_output_tokens += output_tokens
            self._provider_counts[provider] = self._provider_counts.get(provider, 0) + 1
            self._feature_counts[feature] = self._feature_counts.get(feature, 0) + 1
            self._model_counts[model] = self._model_counts.get(model, 0) + 1
            self._history.append(_Execution(
                feature=feature, provider=provider, model=model,
                latency_ms=latency_ms, input_tokens=input_tokens,
                output_tokens=output_tokens, from_cache=from_cache,
                fallback_to_cloud=fallback_to_cloud, error=error,
            ))

    def get_stats(self) -> dict:
        with self._lock:
            served = self._total_requests - self._fallback_count - self._error_count
            avg_latency = (
                self._total_latency_ms / max(1, served)
                if served > 0 else 0.0
            )
            total = self._total_requests
            cache_rate = (self._cache_hits / total * 100) if total else 0.0
            fallback_rate = (self._fallback_count / total * 100) if total else 0.0
            cost_saved = served * _COST_PER_SAVED_CLOUD_REQUEST_USD

            top_features = sorted(
                self._feature_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
            top_models = sorted(
                self._model_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]

            history = [
                {
                    "feature": e.feature,
                    "provider": e.provider,
                    "model": e.model,
                    "latency_ms": e.latency_ms,
                    "from_cache": e.from_cache,
                    "fallback": e.fallback_to_cloud,
                    "error": e.error,
                    "timestamp": e.timestamp,
                }
                for e in reversed(self._history)
            ]

            return {
                "total_requests": total,
                "requests_served_locally": served,
                "cache_hits": self._cache_hits,
                "cache_hit_rate_pct": round(cache_rate, 1),
                "fallback_to_cloud_count": self._fallback_count,
                "fallback_rate_pct": round(fallback_rate, 1),
                "error_count": self._error_count,
                "avg_latency_ms": round(avg_latency, 1),
                "total_input_tokens": self._total_input_tokens,
                "total_output_tokens": self._total_output_tokens,
                "estimated_cost_saved_usd": round(cost_saved, 4),
                "provider_breakdown": dict(self._provider_counts),
                "top_features": [{"feature": f, "count": c} for f, c in top_features],
                "top_models": [{"model": m, "count": c} for m, c in top_models],
                "recent_history": history[:20],
            }

    def reset(self) -> None:
        with self._lock:
            self._reset()


_telemetry: LocalAITelemetry | None = None
_telemetry_lock = threading.Lock()


def get_telemetry() -> LocalAITelemetry:
    global _telemetry
    if _telemetry is None:
        with _telemetry_lock:
            if _telemetry is None:
                _telemetry = LocalAITelemetry()
    return _telemetry


def reset_telemetry() -> None:
    get_telemetry().reset()
