"""AnthropicProvider — production implementation using the Anthropic SDK.

Client is initialised lazily and reused across calls (shares the underlying
httpx connection pool). Thread-safe double-checked locking guards initialisation.
Token usage is read from the response and propagated to AIResponse for cost tracking.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import AsyncIterator

from services.ai.engine.config import ProviderConfig
from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer, ProviderHealth
from services.ai.pricing import estimate_cost_usd
from services.ai.providers.base import AIProvider

logger = logging.getLogger("synaptiq.ai.providers.anthropic")

# Prompt caching: a system prompt at least this long is sent as a cacheable
# block. Anthropic only caches prompts above a model-specific minimum
# (1024 tokens for Sonnet/Opus, 2048 for Haiku); shorter ones are simply not
# cached, so the threshold only avoids pointless cache_control on tiny prompts.
# Savings are measurable via cache_read_tokens in ai_requests telemetry.
_CACHE_MIN_CHARS = int(os.environ.get("AI_PROMPT_CACHE_MIN_CHARS", "4096"))


def _prompt_caching_enabled() -> bool:
    return os.environ.get("AI_PROMPT_CACHING", "1").lower() not in ("0", "false", "no")


def _system_param(system: str):
    if system and _prompt_caching_enabled() and len(system) >= _CACHE_MIN_CHARS:
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    return system


class AnthropicProvider(AIProvider):
    """Wraps AsyncAnthropic with lazy init, usage tracking, and health probing."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "anthropic"

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    import anthropic as _anthropic
                    if not self._config.api_key:
                        raise ValueError("ANTHROPIC_API_KEY not configured")
                    self._client = _anthropic.AsyncAnthropic(
                        api_key=self._config.api_key,
                    )
                    logger.debug("AnthropicProvider: client initialised")
        return self._client

    def _resolve_model(self, request: AIRequest) -> str:
        return request.model or self._config.default_model or "claude-sonnet-4-6"

    async def generate(self, request: AIRequest) -> AIResponse:
        client = self._get_client()
        model = self._resolve_model(request)
        start = time.monotonic()

        resp = await client.messages.create(
            model=model,
            max_tokens=request.max_tokens,
            system=_system_param(request.system),
            messages=request.messages,
            timeout=self._config.timeout_seconds,
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        text = resp.content[0].text
        input_tokens = getattr(resp.usage, "input_tokens", 0) or 0
        output_tokens = getattr(resp.usage, "output_tokens", 0) or 0
        cache_read = getattr(resp.usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(resp.usage, "cache_creation_input_tokens", 0) or 0

        logger.info(
            "anthropic.generate model=%s input_tokens=%d output_tokens=%d "
            "cache_read=%d cache_write=%d latency_ms=%d",
            model, input_tokens, output_tokens, cache_read, cache_write, latency_ms,
        )

        return AIResponse(
            text=text,
            layer=ExecutionLayer.CLOUD,
            provider="anthropic",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=estimate_cost_usd(model, input_tokens, output_tokens, cache_read, cache_write),
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        client = self._get_client()
        model = self._resolve_model(request)
        async with client.messages.stream(
            model=model,
            max_tokens=request.max_tokens,
            system=_system_param(request.system),
            messages=request.messages,
            timeout=self._config.timeout_seconds,
        ) as s:
            async for chunk in s.text_stream:
                yield chunk

    async def health(self) -> ProviderHealth:
        if not self._config.api_key:
            return ProviderHealth(
                name="anthropic",
                available=False,
                error="ANTHROPIC_API_KEY not configured",
            )
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return ProviderHealth(
                name="anthropic",
                available=False,
                error="anthropic package not installed",
            )
        try:
            client = self._get_client()
            start = time.monotonic()
            await asyncio.wait_for(
                client.messages.create(
                    model=self._config.default_model or "claude-haiku-4-5-20251001",
                    max_tokens=1,
                    system="Health check.",
                    messages=[{"role": "user", "content": "ping"}],
                ),
                timeout=10.0,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderHealth(
                name="anthropic",
                available=True,
                latency_ms=latency_ms,
                models=[self._config.default_model] + self._config.fallback_models,
            )
        except Exception as exc:
            return ProviderHealth(
                name="anthropic",
                available=False,
                error=str(exc)[:300],
            )

    def estimate_tokens(self, messages: list[dict]) -> int:
        return sum(len(str(m.get("content", ""))) for m in messages) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return estimate_cost_usd(self._config.default_model or "", input_tokens, output_tokens)

    async def validate(self) -> bool:
        h = await self.health()
        return h.available
