"""Local AI Engine — main orchestrator for all local inference requests.

Responsibilities:
  • Provider & model selection via LocalRouter
  • Prompt optimization before inference
  • Response caching for deterministic features
  • Async request queue + parallel execution + timeout management
  • Automatic retry → model fallback → cloud escalation signal
  • Thread-safe telemetry recording
  • Streaming support
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import AsyncIterator

from services.local_ai.cache.response_cache import (
    LocalResponseCache,
    is_cacheable,
    make_cache_key,
)
from services.local_ai.config import LocalAIConfig, load_local_config
from services.local_ai.health.health_monitor import HealthMonitor, SystemResourceHealth
from services.local_ai.models.model_registry import ModelRegistry
from services.local_ai.providers.base import LocalAIProvider
from services.local_ai.registry.provider_registry import ProviderRegistry
from services.local_ai.router.local_router import LocalRouter
from services.local_ai.telemetry import get_telemetry
from services.local_ai.utils.prompt_optimizer import optimize_prompt
from services.local_ai.utils.token_estimator import estimate_request_tokens

logger = logging.getLogger("synaptiq.local_ai.engine")


@dataclass
class LocalGenerateRequest:
    system: str
    messages: list[dict]
    feature: str = "general"
    max_tokens: int = 1024
    temperature: float = 0.3
    model: str | None = None        # None → auto-select
    user_id: str | None = None
    workspace_id: str | None = None
    subscription_tier: str | None = None


@dataclass
class LocalAIResponse:
    text: str
    provider: str
    model: str
    feature: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    from_cache: bool = False
    fallback_reason: str | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


class _LocalAIUnavailableError(RuntimeError):
    """Raised when no local provider/model is available — triggers cloud escalation."""


class LocalAIEngine:
    """Main Local AI orchestrator — process-level singleton."""

    def __init__(self, config: LocalAIConfig) -> None:
        self._config = config
        self._provider_registry = ProviderRegistry(config)
        self._model_registry = ModelRegistry()
        self._router = LocalRouter()
        self._cache = LocalResponseCache(
            ttl_seconds=config.cache_ttl_seconds,
            max_size=config.cache_max_size,
        )
        self._health_monitor = HealthMonitor()
        self._semaphore = asyncio.Semaphore(config.max_parallel_requests)
        self._initialised = False
        self._init_lock = asyncio.Lock()

    async def _ensure_initialised(self) -> None:
        if self._initialised:
            return
        async with self._init_lock:
            if self._initialised:
                return
            logger.info("local_ai: initialising provider discovery …")
            available = await self._provider_registry.discover()
            if available:
                await self._model_registry.refresh(
                    [self._provider_registry.get(n) for n in available
                     if self._provider_registry.get(n)]
                )
                logger.info(
                    "local_ai: discovered providers=%s models=%d",
                    available, self._model_registry.count(),
                )
            else:
                logger.info("local_ai: no local providers reachable")
            self._initialised = True

    async def generate(self, request: LocalGenerateRequest) -> LocalAIResponse:
        """Generate a response. Never raises — returns error payload on failure."""
        await self._ensure_initialised()
        start = time.monotonic()

        # ── Cache lookup ──────────────────────────────────────────────────────
        if is_cacheable(request.feature):
            cache_key = make_cache_key(request.feature, request.system, request.messages)
            cached = self._cache.get(cache_key)
            if cached is not None:
                latency = int((time.monotonic() - start) * 1000)
                get_telemetry().record(
                    feature=request.feature, provider="cache", model="cache",
                    latency_ms=latency, from_cache=True,
                )
                return LocalAIResponse(
                    text=cached, provider="cache", model="cache",
                    feature=request.feature, latency_ms=latency, from_cache=True,
                )

        async with self._semaphore:
            return await self._execute_with_retry(request, start)

    async def _execute_with_retry(
        self, request: LocalGenerateRequest, start: float
    ) -> LocalAIResponse:
        context_tokens = estimate_request_tokens(request.system, request.messages)
        result = await self._try_execute(request, context_tokens)
        if result.succeeded:
            return result

        # Retry once with a different model if available
        if self._config.max_retries >= 1:
            await asyncio.sleep(self._config.retry_delay_seconds)
            result2 = await self._try_execute(
                request, context_tokens,
                exclude_model=result.model,
            )
            if result2.succeeded:
                result2.fallback_reason = f"retry after first model failed: {result.error}"
                return result2

        # All local attempts failed — signal for cloud escalation
        latency = int((time.monotonic() - start) * 1000)
        get_telemetry().record(
            feature=request.feature, provider="none", model="none",
            latency_ms=latency, error=True, fallback_to_cloud=True,
        )
        raise _LocalAIUnavailableError(result.error or "all local attempts failed")

    async def _try_execute(
        self,
        request: LocalGenerateRequest,
        context_tokens: int,
        exclude_model: str | None = None,
    ) -> LocalAIResponse:
        providers = self._provider_registry.all()
        preferred = request.model if request.model != exclude_model else None
        selected = self._router.select(
            feature=request.feature,
            context_tokens=context_tokens,
            registry=self._model_registry,
            providers=providers,
            preferred_model=preferred or self._config.preferred_model,
        )
        if selected is None:
            return LocalAIResponse(
                text="", provider="none", model="none",
                feature=request.feature, error="no_model_available",
            )

        provider, model_id = selected
        model_key = f"{provider.provider_name}::{model_id}"
        opt_system, opt_messages = optimize_prompt(
            request.system,
            request.messages,
            self._config.max_context_tokens,
            reserved_output_tokens=min(request.max_tokens, 512),
        )
        max_tokens = min(request.max_tokens, self._config.max_output_tokens)
        start = time.monotonic()

        try:
            text, inp, out = await asyncio.wait_for(
                provider.chat(
                    model=model_id,
                    messages=opt_messages,
                    system=opt_system,
                    max_tokens=max_tokens,
                    temperature=request.temperature or self._config.temperature,
                    timeout=self._config.timeout_seconds,
                ),
                timeout=self._config.timeout_seconds + 5,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            latency = int((time.monotonic() - start) * 1000)
            self._model_registry.record_response(model_key, latency, error=True)
            get_telemetry().record(
                feature=request.feature, provider=provider.provider_name, model=model_id,
                latency_ms=latency, error=True,
            )
            logger.warning("local_ai: %s/%s failed: %s", provider.provider_name, model_id, exc)
            return LocalAIResponse(
                text="", provider=provider.provider_name, model=model_id,
                feature=request.feature, error=str(exc)[:200],
            )

        latency = int((time.monotonic() - start) * 1000)
        self._model_registry.record_response(model_key, latency)
        get_telemetry().record(
            feature=request.feature, provider=provider.provider_name, model=model_id,
            latency_ms=latency, input_tokens=inp, output_tokens=out,
        )

        # Store in cache if eligible
        if is_cacheable(request.feature) and text:
            cache_key = make_cache_key(request.feature, request.system, request.messages)
            self._cache.set(cache_key, text)

        return LocalAIResponse(
            text=text,
            provider=provider.provider_name,
            model=model_id,
            feature=request.feature,
            input_tokens=inp,
            output_tokens=out,
            latency_ms=latency,
        )

    async def stream_generate(self, request: LocalGenerateRequest) -> AsyncIterator[str]:
        """Stream tokens. Falls back to non-streaming generate on error."""
        await self._ensure_initialised()
        context_tokens = estimate_request_tokens(request.system, request.messages)
        providers = self._provider_registry.all()
        selected = self._router.select(
            feature=request.feature,
            context_tokens=context_tokens,
            registry=self._model_registry,
            providers=providers,
            preferred_model=request.model or self._config.preferred_model,
        )
        if selected is None:
            yield "[Local AI unavailable]"
            return

        provider, model_id = selected
        opt_system, opt_messages = optimize_prompt(
            request.system, request.messages, self._config.max_context_tokens,
        )
        try:
            async for chunk in provider.stream_chat(
                model=model_id,
                messages=opt_messages,
                system=opt_system,
                max_tokens=min(request.max_tokens, self._config.max_output_tokens),
                temperature=request.temperature or self._config.temperature,
                timeout=self._config.timeout_seconds,
            ):
                yield chunk
        except Exception as exc:
            logger.warning("stream_generate error: %s", exc)
            result = await self.generate(request)
            yield result.text

    async def generate_batch(
        self,
        requests: list[LocalGenerateRequest],
    ) -> list[LocalAIResponse]:
        """Execute multiple requests concurrently."""
        return list(await asyncio.gather(*(self.generate(r) for r in requests)))

    async def health(self) -> dict:
        await self._ensure_initialised()
        provider_health = await self._provider_registry.health_all()
        system_health = await self._health_monitor.get_system_health()
        return {
            "providers": [h.to_dict() for h in provider_health],
            "models": {
                "total": self._model_registry.count(),
                "enabled": len(self._model_registry.list_enabled()),
            },
            "system": system_health.to_dict(),
            "cache": self._cache.stats(),
        }

    async def refresh_models(self) -> int:
        available = await self._provider_registry.discover()
        count = await self._model_registry.refresh(
            [self._provider_registry.get(n) for n in available
             if self._provider_registry.get(n)]
        )
        return count

    async def list_models(self):
        await self._ensure_initialised()
        return self._model_registry.list_all()

    def telemetry(self) -> dict:
        return get_telemetry().get_stats()

    def cache_stats(self) -> dict:
        return self._cache.stats()

    def clear_cache(self) -> int:
        return self._cache.clear()

    def enable_model(self, key: str) -> bool:
        return self._model_registry.enable(key)

    def disable_model(self, key: str) -> bool:
        return self._model_registry.disable(key)


# ── Singleton ────────────────────────────────────────────────────────────────

_engine: LocalAIEngine | None = None
_engine_lock = threading.Lock()


def get_local_engine() -> LocalAIEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = LocalAIEngine(load_local_config())
    return _engine


def reset_local_engine() -> None:
    global _engine
    with _engine_lock:
        _engine = None
