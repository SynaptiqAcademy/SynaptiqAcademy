"""OpenAIProvider — production implementation using the OpenAI SDK.

Supports any OpenAI-compatible endpoint (including Azure OpenAI) via
base_url override. Client is lazy-initialised and reused.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import AsyncIterator

from services.ai.engine.config import ProviderConfig
from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer, ProviderHealth
from services.ai.providers.base import AIProvider

logger = logging.getLogger("synaptiq.ai.providers.openai")

_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o":       (5.0,  15.0),
    "gpt-4o-mini":  (0.15,  0.60),
    "gpt-4-turbo":  (10.0, 30.0),
    "gpt-3.5-turbo": (0.5,  1.5),
}
_DEFAULT_PRICING = (5.0, 15.0)


def _pricing(model: str) -> tuple[float, float]:
    for prefix, rates in _PRICING.items():
        if model.startswith(prefix):
            return rates
    return _DEFAULT_PRICING


class OpenAIProvider(AIProvider):
    """Wraps AsyncOpenAI with lazy init, usage tracking, and health probing."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "openai"

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    import openai as _openai
                    if not self._config.api_key:
                        raise ValueError("OPENAI_API_KEY not configured")
                    kwargs: dict = {"api_key": self._config.api_key}
                    if self._config.base_url:
                        kwargs["base_url"] = self._config.base_url
                    self._client = _openai.AsyncOpenAI(**kwargs)
                    logger.debug("OpenAIProvider: client initialised")
        return self._client

    def _resolve_model(self, request: AIRequest) -> str:
        return request.model or self._config.default_model or "gpt-4o-mini"

    async def generate(self, request: AIRequest) -> AIResponse:
        client = self._get_client()
        model = self._resolve_model(request)
        start = time.monotonic()

        full_messages = [{"role": "system", "content": request.system}] + request.messages
        resp = await client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=request.max_tokens,
            timeout=self._config.timeout_seconds,
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        text = resp.choices[0].message.content or ""
        input_tokens = getattr(resp.usage, "prompt_tokens", 0) if resp.usage else 0
        output_tokens = getattr(resp.usage, "completion_tokens", 0) if resp.usage else 0

        logger.info(
            "openai.generate model=%s input_tokens=%d output_tokens=%d latency_ms=%d",
            model, input_tokens, output_tokens, latency_ms,
        )

        return AIResponse(
            text=text,
            layer=ExecutionLayer.CLOUD,
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=self.estimate_cost(input_tokens, output_tokens),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        client = self._get_client()
        model = self._resolve_model(request)
        full_messages = [{"role": "system", "content": request.system}] + request.messages
        async with client.chat.completions.stream(
            model=model,
            messages=full_messages,
            max_tokens=request.max_tokens,
        ) as s:
            async for event in s:
                if event.choices and event.choices[0].delta.content:
                    yield event.choices[0].delta.content

    async def health(self) -> ProviderHealth:
        if not self._config.api_key:
            return ProviderHealth(
                name="openai",
                available=False,
                error="OPENAI_API_KEY not configured",
            )
        try:
            import openai  # noqa: F401
        except ImportError:
            return ProviderHealth(
                name="openai",
                available=False,
                error="openai package not installed",
            )
        try:
            client = self._get_client()
            start = time.monotonic()
            await client.models.list()
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderHealth(
                name="openai",
                available=True,
                latency_ms=latency_ms,
                models=[self._config.default_model] + self._config.fallback_models,
            )
        except Exception as exc:
            return ProviderHealth(
                name="openai",
                available=False,
                error=str(exc)[:300],
            )

    def estimate_tokens(self, messages: list[dict]) -> int:
        return sum(len(str(m.get("content", ""))) for m in messages) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        in_rate, out_rate = _pricing(self._config.default_model or "")
        return round((input_tokens * in_rate + output_tokens * out_rate) / 1_000_000, 6)

    async def validate(self) -> bool:
        h = await self.health()
        return h.available
