"""Layer 2 — Local AI.

Routes requests to the LocalAIEngine (services/local_ai/) which supports
Ollama, vLLM, LM Studio, and any OpenAI-compatible local endpoint.

Activated when AI_LOCAL_ENABLED=1 and the feature does not require cloud-grade
reasoning (requires_reasoning=False in the feature registry).

Fallback chain: LocalAIEngine → LocalProvider (legacy) → raise (triggers cloud)
"""
from __future__ import annotations

import logging
import time

from services.ai.engine.registry import FeatureMeta
from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer
from services.ai.providers.base import AIProvider

logger = logging.getLogger("synaptiq.ai.layers.local")


class LocalAILayer:
    """Orchestration wrapper — delegates to LocalAIEngine, falls back to LocalProvider."""

    def __init__(self, provider: AIProvider | None) -> None:
        self._legacy_provider = provider

    async def generate(self, request: AIRequest, meta: FeatureMeta) -> AIResponse:
        start = time.monotonic()

        # ── Path 1: new LocalAIEngine ─────────────────────────────────────────
        try:
            from services.local_ai.engine import (
                LocalGenerateRequest,
                _LocalAIUnavailableError,
                get_local_engine,
            )
            engine = get_local_engine()
            local_request = LocalGenerateRequest(
                system=request.system,
                messages=request.messages,
                feature=request.feature,
                max_tokens=request.max_tokens,
                model=request.model,
                user_id=request.user_id,
                workspace_id=request.workspace_id,
                subscription_tier=request.subscription_tier,
            )
            result = await engine.generate(local_request)
            if result.succeeded:
                latency_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "local_ai.generate feature=%s provider=%s model=%s cache=%s latency_ms=%d",
                    request.feature, result.provider, result.model, result.from_cache, latency_ms,
                )
                return AIResponse(
                    text=result.text,
                    layer=ExecutionLayer.LOCAL,
                    provider=result.provider,
                    model=result.model,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    latency_ms=latency_ms,
                    from_cache=result.from_cache,
                    cost_usd=0.0,
                )
            # engine returned an error payload — try legacy fallback
            raise RuntimeError(result.error or "local engine returned empty response")

        except ImportError:
            pass  # LocalAIEngine not importable — fall through to legacy
        except Exception as exc:
            logger.debug("local_ai_engine failed: %s — trying legacy provider", exc)

        # ── Path 2: legacy LocalProvider (OpenAI-compatible single endpoint) ──
        if self._legacy_provider is not None:
            if meta.preferred_model:
                from dataclasses import replace
                request = replace(request, model=request.model or meta.preferred_model)
            logger.info(
                "local_ai.generate feature=%s → legacy provider model=%s",
                request.feature, request.model,
            )
            return await self._legacy_provider.generate(request)

        raise RuntimeError(
            "Local AI layer requested but neither LocalAIEngine nor LocalProvider is available. "
            "Set AI_LOCAL_ENABLED=1 and configure at least one local AI provider."
        )
