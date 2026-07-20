"""LoadBalancer — tracks concurrent requests across providers and local models."""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import NamedTuple

from services.smart_router.types import ProviderAvailability, ProviderLoad

_LATENCY_WINDOW = 100   # keep last N latency samples per provider


class _ProviderState:
    def __init__(self, name: str, max_concurrent: int) -> None:
        self.name = name
        self.max_concurrent = max_concurrent
        self.concurrent = 0
        self.queue_depth = 0
        self.availability = ProviderAvailability.AVAILABLE
        self.error_count = 0
        self.total_requests = 0
        self.latencies: deque[float] = deque(maxlen=_LATENCY_WINDOW)
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        with self._lock:
            if self.availability == ProviderAvailability.UNAVAILABLE:
                return False
            self.concurrent += 1
            self.total_requests += 1
            return True

    def release(self, latency_ms: float, success: bool) -> None:
        with self._lock:
            self.concurrent = max(0, self.concurrent - 1)
            self.latencies.append(latency_ms)
            if not success:
                self.error_count += 1
                if self.error_count >= 5:
                    self.availability = ProviderAvailability.DEGRADED
            else:
                self.error_count = max(0, self.error_count - 1)
                if self.error_count == 0:
                    self.availability = ProviderAvailability.AVAILABLE

    def mark_unavailable(self) -> None:
        with self._lock:
            self.availability = ProviderAvailability.UNAVAILABLE

    def mark_available(self) -> None:
        with self._lock:
            self.availability = ProviderAvailability.AVAILABLE
            self.error_count = 0

    def avg_latency_ms(self) -> float:
        with self._lock:
            if not self.latencies:
                return 0.0
            return sum(self.latencies) / len(self.latencies)

    def load_ratio(self) -> float:
        """0.0=idle, 1.0=at max capacity."""
        with self._lock:
            return self.concurrent / self.max_concurrent if self.max_concurrent > 0 else 1.0

    def to_load_info(self) -> ProviderLoad:
        with self._lock:
            avg_ms = round(sum(self.latencies) / len(self.latencies), 1) if self.latencies else 0.0
            return ProviderLoad(
                provider=self.name,
                concurrent_requests=self.concurrent,
                queue_depth=self.queue_depth,
                availability=self.availability,
                avg_latency_ms=avg_ms,
            )


_CLOUD_PROVIDERS = ["anthropic", "openai"]
_LOCAL_PROVIDERS = ["local", "ollama", "vllm", "lm_studio"]


class LoadBalancer:
    """Routes requests to the provider with the most capacity."""

    def __init__(self, max_concurrent_per_provider: int = 20) -> None:
        self._max = max_concurrent_per_provider
        self._states: dict[str, _ProviderState] = {}
        self._lock = threading.Lock()

    def _get_state(self, provider: str) -> _ProviderState:
        with self._lock:
            if provider not in self._states:
                self._states[provider] = _ProviderState(provider, self._max)
            return self._states[provider]

    def acquire(self, provider: str) -> bool:
        return self._get_state(provider).acquire()

    def release(self, provider: str, latency_ms: float, success: bool) -> None:
        self._get_state(provider).release(latency_ms, success)

    def mark_unavailable(self, provider: str) -> None:
        self._get_state(provider).mark_unavailable()

    def mark_available(self, provider: str) -> None:
        self._get_state(provider).mark_available()

    def select_cloud_provider(self, preferred: str, fallbacks: list[str]) -> str | None:
        """Return the least-loaded available cloud provider."""
        candidates = [preferred] + [f for f in fallbacks if f != preferred and f != "local"]
        best: str | None = None
        best_load = 2.0
        for name in candidates:
            state = self._get_state(name)
            if state.availability == ProviderAvailability.UNAVAILABLE:
                continue
            lr = state.load_ratio()
            if lr < best_load:
                best_load = lr
                best = name
        return best

    def local_is_available(self) -> bool:
        state = self._get_state("local")
        return state.availability != ProviderAvailability.UNAVAILABLE and state.load_ratio() < 0.95

    def get_all_load(self) -> list[ProviderLoad]:
        with self._lock:
            return [s.to_load_info() for s in self._states.values()]

    def get_provider_load(self, provider: str) -> ProviderLoad:
        return self._get_state(provider).to_load_info()

    def summary(self) -> dict:
        loads = self.get_all_load()
        return {
            "providers": [
                {
                    "name": l.provider,
                    "concurrent": l.concurrent_requests,
                    "availability": l.availability.value,
                    "avg_latency_ms": l.avg_latency_ms,
                }
                for l in loads
            ],
            "total_concurrent": sum(l.concurrent_requests for l in loads),
        }
