"""Provider registry — auto-discovers available local AI providers."""
from __future__ import annotations

import asyncio
import logging

from services.local_ai.config import LocalAIConfig
from services.local_ai.providers.base import LocalAIProvider, LocalProviderHealth
from services.local_ai.providers.lm_studio import LMStudioProvider
from services.local_ai.providers.ollama import OllamaProvider
from services.local_ai.providers.openai_compatible import OpenAICompatibleProvider
from services.local_ai.providers.vllm import VLLMProvider

logger = logging.getLogger("synaptiq.local_ai.registry")


class ProviderRegistry:
    """Manages all local AI providers. Supports runtime enable/disable."""

    def __init__(self, config: LocalAIConfig) -> None:
        self._config = config
        self._providers: dict[str, LocalAIProvider] = {}
        self._available: dict[str, bool] = {}
        self._build_providers()

    def _build_providers(self) -> None:
        self._providers = {
            "ollama": OllamaProvider(self._config.ollama_base_url),
            "vllm": VLLMProvider(self._config.vllm_base_url),
            "lm_studio": LMStudioProvider(self._config.lm_studio_base_url),
        }
        if self._config.openai_compatible_base_url:
            self._providers["openai_compatible"] = OpenAICompatibleProvider(
                base_url=self._config.openai_compatible_base_url,
                api_key=self._config.openai_compatible_api_key,
            )
        # All start as unknown
        self._available = {name: False for name in self._providers}

    async def discover(self) -> list[str]:
        """Probe all providers concurrently and update availability."""
        timeout = self._config.discovery_timeout_seconds

        async def _probe(name: str, provider: LocalAIProvider) -> tuple[str, bool]:
            try:
                h = await asyncio.wait_for(provider.health_check(), timeout=timeout)
                return name, h.available
            except Exception:
                return name, False

        results = await asyncio.gather(
            *(_probe(n, p) for n, p in self._providers.items()),
            return_exceptions=False,
        )
        available_names: list[str] = []
        for name, ok in results:
            self._available[name] = ok
            if ok:
                available_names.append(name)
                logger.info("local_ai: provider '%s' available", name)
            else:
                logger.debug("local_ai: provider '%s' not reachable", name)

        return available_names

    def get(self, name: str) -> LocalAIProvider | None:
        return self._providers.get(name)

    def get_available(self, name: str) -> LocalAIProvider | None:
        if self._available.get(name):
            return self._providers.get(name)
        return None

    def list_available(self) -> list[LocalAIProvider]:
        return [p for n, p in self._providers.items() if self._available.get(n)]

    def preferred(self) -> LocalAIProvider | None:
        """Return the configured default provider if available, else first available."""
        default = self._config.default_provider
        p = self.get_available(default)
        if p:
            return p
        # Try in priority order
        for name in ("ollama", "lm_studio", "vllm", "openai_compatible"):
            p = self.get_available(name)
            if p:
                return p
        return None

    def all(self) -> dict[str, LocalAIProvider]:
        return dict(self._providers)

    def availability(self) -> dict[str, bool]:
        return dict(self._available)

    async def health_all(self) -> list[LocalProviderHealth]:
        results = await asyncio.gather(
            *(p.health_check() for p in self._providers.values()),
            return_exceptions=False,
        )
        for h in results:
            self._available[h.provider_name] = h.available
        return list(results)
