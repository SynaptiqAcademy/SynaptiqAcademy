"""LocalProvider — runs against any OpenAI-compatible local AI endpoint.

Compatible with Ollama, vLLM, LM Studio, Jan, and any server that exposes
the OpenAI Chat Completions API at a configurable base URL.

Enabled via environment:
  AI_LOCAL_ENABLED=1
  AI_LOCAL_URL=http://localhost:11434/v1   (Ollama default)
  AI_LOCAL_MODEL=llama3.2
"""
from __future__ import annotations

import logging
import threading
import time
from typing import AsyncIterator

from services.ai.engine.config import ProviderConfig
from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer, ProviderHealth
from services.ai.providers.base import AIProvider

logger = logging.getLogger("synaptiq.ai.providers.local")


class LocalProvider(AIProvider):
    """HTTP client to an OpenAI-compatible local AI endpoint (Ollama / vLLM)."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "local"

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    import openai as _openai
                    base_url = self._config.base_url or "http://localhost:11434/v1"
                    if not base_url.endswith("/v1"):
                        base_url = base_url.rstrip("/") + "/v1"
                    self._client = _openai.AsyncOpenAI(
                        api_key="local",
                        base_url=base_url,
                    )
                    logger.info("LocalProvider: client initialised at %s", base_url)
        return self._client

    def _resolve_model(self, request: AIRequest) -> str:
        return request.model or self._config.default_model or "llama3.2"

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
            "local.generate model=%s input_tokens=%d output_tokens=%d latency_ms=%d",
            model, input_tokens, output_tokens, latency_ms,
        )

        return AIResponse(
            text=text,
            layer=ExecutionLayer.LOCAL,
            provider="local",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=0.0,
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
        if not self._config.enabled:
            return ProviderHealth(
                name="local",
                available=False,
                error="Local AI layer not enabled (set AI_LOCAL_ENABLED=1)",
            )
        try:
            client = self._get_client()
            start = time.monotonic()
            models_page = await client.models.list()
            latency_ms = int((time.monotonic() - start) * 1000)
            model_ids = [m.id for m in models_page.data] if models_page.data else []
            return ProviderHealth(
                name="local",
                available=True,
                latency_ms=latency_ms,
                models=model_ids[:10],
            )
        except Exception as exc:
            return ProviderHealth(
                name="local",
                available=False,
                error=str(exc)[:300],
            )

    def estimate_tokens(self, messages: list[dict]) -> int:
        return sum(len(str(m.get("content", ""))) for m in messages) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def validate(self) -> bool:
        h = await self.health()
        return h.available
