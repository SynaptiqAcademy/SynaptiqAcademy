"""AI Health Service.

Aggregates liveness probes from all registered providers and reports
the overall platform AI status. Called by GET /api/ai/health.

Health checks are lightweight by default: for cloud providers they check
key presence and package installation without making a real API call.
Deep probes (which make live API calls) are triggered only when
deep=True, gated by a configurable cooldown to limit spend.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from services.ai.engine.config import AIEngineConfig
from services.ai.engine.types import AISystemHealth, ProviderHealth
from services.ai.providers.base import AIProvider

logger = logging.getLogger("synaptiq.ai.health")

_DEEP_PROBE_COOLDOWN_SECONDS = 300
_last_deep_probe: float = 0.0
_cached_deep_result: list[ProviderHealth] | None = None


class AIHealthService:
    """Aggregates provider health into a single system-level status snapshot."""

    def __init__(
        self,
        providers: dict[str, AIProvider],
        config: AIEngineConfig,
    ) -> None:
        self._providers = providers
        self._config = config

    async def get_status(self, deep: bool = False) -> AISystemHealth:
        """Return aggregate AI system health.

        Args:
            deep: When True, makes live API calls to each provider to measure
                  real latency and confirm authentication. Subject to a 5-minute
                  cooldown to prevent accidental spend.
        """
        provider_healths = await self._probe_providers(deep=deep)

        available = [h for h in provider_healths if h.available and h.name != "mock"]
        mock_h = next((h for h in provider_healths if h.name == "mock"), None)

        if available:
            status = "ok"
        elif mock_h and mock_h.available:
            status = "degraded"
        else:
            status = "unavailable"

        active_layer = "cloud"
        if self._config.enable_local_layer:
            local_h = next((h for h in provider_healths if h.name == "local"), None)
            if local_h and local_h.available:
                active_layer = "local"

        return AISystemHealth(
            status=status,
            providers=provider_healths,
            active_layer=active_layer,
            cache_enabled=self._config.cache.enabled,
            rule_layer_enabled=self._config.enable_rule_layer,
            local_layer_enabled=self._config.enable_local_layer,
            budget_remaining_day_usd=(
                self._config.budget.daily_limit_usd if self._config.budget.daily_limit_usd else None
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _probe_providers(self, deep: bool) -> list[ProviderHealth]:
        global _last_deep_probe, _cached_deep_result

        if deep:
            now = time.monotonic()
            if (
                _cached_deep_result is not None
                and now - _last_deep_probe < _DEEP_PROBE_COOLDOWN_SECONDS
            ):
                logger.debug("health: returning cached deep probe (cooldown active)")
                return _cached_deep_result

            tasks = {
                name: asyncio.create_task(provider.health())
                for name, provider in self._providers.items()
            }
            results: list[ProviderHealth] = []
            for name, task in tasks.items():
                try:
                    results.append(await asyncio.wait_for(task, timeout=12.0))
                except Exception as exc:
                    results.append(ProviderHealth(name=name, available=False, error=str(exc)[:200]))

            _last_deep_probe = time.monotonic()
            _cached_deep_result = results
            return results

        return [self._shallow_probe(name) for name in self._providers]

    def _shallow_probe(self, name: str) -> ProviderHealth:
        """Structural check — no network calls, no API spend."""
        if name == "mock":
            return ProviderHealth(name="mock", available=True, latency_ms=0, models=["mock-v1"])

        if name == "local":
            enabled = self._config.enable_local_layer
            return ProviderHealth(
                name="local",
                available=enabled,
                error=None if enabled else "Local AI layer not enabled (AI_LOCAL_ENABLED=1)",
                models=[self._config.providers["local"].default_model] if enabled else [],
            )

        pc = self._config.providers.get(name)
        if pc is None:
            return ProviderHealth(name=name, available=False, error="Provider not configured")

        if not pc.api_key:
            return ProviderHealth(
                name=name,
                available=False,
                error=f"{name.upper()}_API_KEY not configured",
            )

        pkg_name = "anthropic" if name == "anthropic" else "openai"
        try:
            __import__(pkg_name)
        except ImportError:
            return ProviderHealth(
                name=name,
                available=False,
                error=f"{pkg_name} package not installed",
            )

        return ProviderHealth(
            name=name,
            available=True,
            models=[pc.default_model] + pc.fallback_models,
        )
