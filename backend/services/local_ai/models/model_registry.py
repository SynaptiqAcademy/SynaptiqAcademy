"""Model registry — tracks all discovered models across all providers."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from services.local_ai.providers.base import LocalAIProvider, LocalModelInfo

logger = logging.getLogger("synaptiq.local_ai.models")

_FAMILY_QUALITY_RANK: dict[str, int] = {
    "qwen": 1, "llama": 2, "mistral": 3, "gemma": 4, "deepseek": 5,
    "phi": 6, "falcon": 7, "command": 8, "starcoder": 9, "other": 10,
}


@dataclass
class ManagedModel:
    info: LocalModelInfo
    enabled: bool = True
    avg_latency_ms: float = 0.0
    request_count: int = 0
    error_count: int = 0
    last_used: float = 0.0
    last_checked: float = field(default_factory=time.time)

    def record_response(self, latency_ms: float, error: bool = False) -> None:
        self.request_count += 1
        if error:
            self.error_count += 1
        else:
            alpha = 0.2
            self.avg_latency_ms = (
                latency_ms if self.avg_latency_ms == 0
                else alpha * latency_ms + (1 - alpha) * self.avg_latency_ms
            )
        self.last_used = time.time()

    def to_dict(self) -> dict:
        d = self.info.to_dict()
        d.update({
            "enabled": self.enabled,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "last_used": self.last_used,
            "last_checked": self.last_checked,
        })
        return d


class ModelRegistry:
    """Thread-safe registry of all discovered local models."""

    def __init__(self) -> None:
        self._models: dict[str, ManagedModel] = {}
        self._lock = threading.Lock()

    async def refresh(self, providers: list[LocalAIProvider]) -> int:
        """Re-discover models from all providers. Returns count of new/updated models."""
        seen: dict[str, ManagedModel] = {}
        for provider in providers:
            try:
                models = await provider.list_models()
                for m in models:
                    key = f"{provider.provider_name}::{m.model_id}"
                    existing = self._models.get(key)
                    managed = ManagedModel(
                        info=m,
                        enabled=existing.enabled if existing else True,
                        avg_latency_ms=existing.avg_latency_ms if existing else 0.0,
                        request_count=existing.request_count if existing else 0,
                        error_count=existing.error_count if existing else 0,
                        last_used=existing.last_used if existing else 0.0,
                    )
                    seen[key] = managed
            except Exception as exc:
                logger.warning("model_registry: refresh error for %s: %s", provider.provider_name, exc)

        with self._lock:
            self._models = seen
        logger.info("model_registry: discovered %d models", len(seen))
        return len(seen)

    def get_best_model(
        self,
        family_preference: list[str] | None = None,
        min_context_window: int = 0,
        exclude_providers: list[str] | None = None,
    ) -> ManagedModel | None:
        with self._lock:
            candidates = [
                m for m in self._models.values()
                if m.enabled
                and m.info.available
                and m.info.context_window >= min_context_window
                and (not exclude_providers or m.info.provider not in exclude_providers)
            ]

        if not candidates:
            return None

        preference = family_preference or []

        def _rank(m: ManagedModel) -> tuple[int, int, float]:
            # Lower is better
            family = m.info.family
            family_rank = (
                preference.index(family) if family in preference
                else len(preference) + _FAMILY_QUALITY_RANK.get(family, 99)
            )
            # Prefer smaller models (faster) when quality is equal
            size_map = {"1B": 1, "3B": 3, "7B": 7, "8B": 8, "13B": 13, "14B": 14}
            size_rank = size_map.get(m.info.parameter_size, 9)
            # Latency as tiebreaker (0 = never used = neutral)
            lat = m.avg_latency_ms if m.avg_latency_ms > 0 else 5000
            return (family_rank, size_rank, lat)

        return min(candidates, key=_rank)

    def get(self, key: str) -> ManagedModel | None:
        with self._lock:
            return self._models.get(key)

    def get_by_model_id(self, model_id: str) -> ManagedModel | None:
        with self._lock:
            for key, m in self._models.items():
                if m.info.model_id == model_id:
                    return m
        return None

    def enable(self, key: str) -> bool:
        with self._lock:
            if key in self._models:
                self._models[key].enabled = True
                return True
        return False

    def disable(self, key: str) -> bool:
        with self._lock:
            if key in self._models:
                self._models[key].enabled = False
                return True
        return False

    def record_response(self, key: str, latency_ms: float, error: bool = False) -> None:
        with self._lock:
            if key in self._models:
                self._models[key].record_response(latency_ms, error)

    def list_all(self) -> list[ManagedModel]:
        with self._lock:
            return list(self._models.values())

    def list_enabled(self) -> list[ManagedModel]:
        with self._lock:
            return [m for m in self._models.values() if m.enabled and m.info.available]

    def count(self) -> int:
        with self._lock:
            return len(self._models)
