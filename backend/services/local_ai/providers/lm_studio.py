"""LM Studio provider — OpenAI-compatible API served by LM Studio."""
from __future__ import annotations

import logging
import time
from typing import AsyncIterator

import httpx

from .base import (
    LocalAIProvider,
    LocalModelInfo,
    LocalProviderHealth,
    detect_model_family,
    detect_parameter_size,
)

logger = logging.getLogger("synaptiq.local_ai.providers.lm_studio")


class LMStudioProvider(LocalAIProvider):
    """Provider for LM Studio (https://lmstudio.ai)."""

    def __init__(self, base_url: str = "http://localhost:1234") -> None:
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "lm_studio"

    @property
    def base_url(self) -> str:
        return self._base_url

    def _api_base(self) -> str:
        return f"{self._base_url}/v1"

    def _client(self, timeout: float = 30.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._api_base(), timeout=timeout)

    async def list_models(self) -> list[LocalModelInfo]:
        try:
            async with self._client(timeout=10.0) as c:
                r = await c.get("/models")
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            logger.debug("lm_studio list_models error: %s", exc)
            return []

        models: list[LocalModelInfo] = []
        for m in data.get("data", []):
            model_id: str = m.get("id", "")
            family = detect_model_family(model_id)
            param_size = detect_parameter_size(model_id)
            models.append(LocalModelInfo(
                model_id=model_id,
                provider="lm_studio",
                display_name=model_id,
                family=family,
                parameter_size=param_size,
                context_window=int(m.get("max_context_length", 0)),
                available=True,
            ))
        return models

    async def chat(
        self,
        model: str,
        messages: list[dict],
        system: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> tuple[str, int, int]:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        start = time.monotonic()
        async with self._client(timeout=timeout) as c:
            r = await c.post("/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()

        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        logger.debug(
            "lm_studio.chat model=%s input=%d output=%d latency_ms=%d",
            model, input_tokens, output_tokens, int((time.monotonic() - start) * 1000),
        )
        return text, input_tokens, output_tokens

    async def stream_chat(
        self,
        model: str,
        messages: list[dict],
        system: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> AsyncIterator[str]:
        import json as _json
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        async with self._client(timeout=timeout) as c:
            async with c.stream("POST", "/chat/completions", json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload_str = line[6:]
                    if payload_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(payload_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue

    async def health_check(self) -> LocalProviderHealth:
        try:
            start = time.monotonic()
            async with self._client(timeout=5.0) as c:
                r = await c.get("/models")
                r.raise_for_status()
            latency_ms = int((time.monotonic() - start) * 1000)
            models = await self.list_models()
            return LocalProviderHealth(
                provider_name="lm_studio",
                available=True,
                latency_ms=latency_ms,
                models=models,
            )
        except Exception as exc:
            return LocalProviderHealth(
                provider_name="lm_studio",
                available=False,
                error=str(exc)[:300],
            )
