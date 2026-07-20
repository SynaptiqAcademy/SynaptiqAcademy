"""Ollama provider — uses Ollama's native REST API."""
from __future__ import annotations

import json
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

logger = logging.getLogger("synaptiq.local_ai.providers.ollama")

_CONTEXT_WINDOW_DEFAULTS: dict[str, int] = {
    "llama": 8192,
    "qwen": 32768,
    "mistral": 32768,
    "gemma": 8192,
    "deepseek": 16384,
    "phi": 4096,
    "other": 4096,
}


class OllamaProvider(LocalAIProvider):
    """Provider for locally-running Ollama (https://ollama.ai)."""

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def base_url(self) -> str:
        return self._base_url

    def _client(self, timeout: float = 30.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    async def list_models(self) -> list[LocalModelInfo]:
        try:
            async with self._client(timeout=10.0) as c:
                r = await c.get("/api/tags")
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            logger.debug("ollama list_models error: %s", exc)
            return []

        models: list[LocalModelInfo] = []
        for m in data.get("models", []):
            raw_name: str = m.get("name", "")
            model_id = raw_name
            family = detect_model_family(model_id)
            param_size = detect_parameter_size(model_id)
            details = m.get("details", {})
            if not param_size:
                param_size = detect_parameter_size(details.get("parameter_size", ""))
            context_window = _CONTEXT_WINDOW_DEFAULTS.get(family, 4096)
            models.append(LocalModelInfo(
                model_id=model_id,
                provider="ollama",
                display_name=raw_name,
                family=family,
                parameter_size=param_size,
                context_window=context_window,
                available=True,
                size_bytes=int(m.get("size", 0)),
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
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        start = time.monotonic()
        async with self._client(timeout=timeout) as c:
            r = await c.post("/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        latency_ms = int((time.monotonic() - start) * 1000)
        text = data.get("message", {}).get("content", "")
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        logger.debug(
            "ollama.chat model=%s input_tokens=%d output_tokens=%d latency_ms=%d",
            model, prompt_eval_count, eval_count, latency_ms,
        )
        return text, prompt_eval_count, eval_count

    async def stream_chat(
        self,
        model: str,
        messages: list[dict],
        system: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        async with self._client(timeout=timeout) as c:
            async with c.stream("POST", "/api/chat", json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> LocalProviderHealth:
        try:
            start = time.monotonic()
            async with self._client(timeout=5.0) as c:
                r = await c.get("/api/tags")
                r.raise_for_status()
                data = r.json()
            latency_ms = int((time.monotonic() - start) * 1000)
            models = await self.list_models()
            version = ""
            try:
                async with self._client(timeout=3.0) as c:
                    vr = await c.get("/api/version")
                    version = vr.json().get("version", "")
            except Exception:
                pass
            return LocalProviderHealth(
                provider_name="ollama",
                available=True,
                latency_ms=latency_ms,
                models=models,
                version=version,
            )
        except Exception as exc:
            return LocalProviderHealth(
                provider_name="ollama",
                available=False,
                error=str(exc)[:300],
            )
