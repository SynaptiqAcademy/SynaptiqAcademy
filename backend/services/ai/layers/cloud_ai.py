"""Layer 3 — Premium Cloud AI.

Executes against the configured cloud provider chain with per-provider retry
and exponential back-off. Falls back through the chain automatically on failure.

Fallback policy:
  - If ALL real providers fail and NO real providers are configured → MockProvider (dev mode).
  - If ALL real providers fail but at least one IS configured → return a real error response.
    Demo/mock content must never reach users when a real API key is present.
"""
from __future__ import annotations

import asyncio
import logging
import time

from services.ai.engine.config import AIEngineConfig
from services.ai.engine.registry import FeatureMeta
from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer
from services.ai.providers.base import AIProvider

logger = logging.getLogger("synaptiq.ai.layers.cloud")

# Substrings (lower-cased) that indicate a billing / quota failure.
# These are non-retryable — retrying won't fix a zero-credit account.
_BILLING_ERROR_SIGNALS = (
    "credit balance is too low",
    "insufficient_quota",
    "billing_not_active",
    "insufficient credits",
    "you exceeded your current quota",
    "account is not active",
    "payment required",
)

# HTTP status codes that indicate billing / auth problems (no point retrying).
# 429 (rate limit) is intentionally excluded — it is transient and should be retried with backoff.
_NO_RETRY_STATUS_CODES = {400, 401, 403}


def _is_billing_or_auth_error(exc: Exception) -> bool:
    """True when the exception signals a non-retryable billing / auth failure."""
    msg = str(exc).lower()
    if any(sig in msg for sig in _BILLING_ERROR_SIGNALS):
        return True
    # Some SDK wrappers expose status_code directly
    code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    return code in _NO_RETRY_STATUS_CODES


class CloudAILayer:
    """Ordered provider chain with retry, fallback, and mock safety net."""

    def __init__(
        self,
        providers: dict[str, AIProvider],
        config: AIEngineConfig,
    ) -> None:
        self._providers = providers
        self._config = config

    def _real_providers_configured(self) -> list[str]:
        """Return names of providers that have a real API key enabled."""
        return [
            name for name, provider in self._providers.items()
            if name != "mock" and provider is not None
        ]

    def _provider_chain(self, request: AIRequest, meta: FeatureMeta) -> list[str]:
        """Return ordered list of provider names to attempt.

        Priority (highest to lowest):
          1. Explicit request.provider override — respect it, no further fallback.
          2. Engine's preferred_cloud_provider (AI_MATCHING_PROVIDER env var).
             This overrides the feature registry so operators can switch providers
             without touching code.
          3. Feature registry's preferred_provider (e.g. "anthropic" by default).
          4. Engine's fallback_cloud_providers.
          5. "mock" — always last; only used as fallback when no real key is set.
        """
        if request.provider and request.provider in self._providers:
            return [request.provider]

        chain: list[str] = []
        # Engine-level setting takes precedence over feature-level defaults
        candidates = [
            self._config.preferred_cloud_provider,   # env var — operator authority
            meta.preferred_provider,                 # feature registry default
            *self._config.fallback_cloud_providers,  # explicit fallback list
        ]
        seen: set[str] = set()
        for name in candidates:
            if name and name not in seen and name in self._providers:
                pc = self._config.providers.get(name)
                if pc and pc.enabled:
                    chain.append(name)
                    seen.add(name)

        if "mock" not in chain:
            chain.append("mock")
        return chain

    @staticmethod
    def _truncate_messages(request: AIRequest) -> AIRequest:
        """Trim message history when total chars would exceed ~180k tokens.

        Keeps the first (system-seed) message and the most-recent tail so the
        model always has current context. Only fires on extreme inputs.
        """
        from dataclasses import replace as _replace

        _CHAR_LIMIT = 720_000  # ~180k tokens at 4 chars/token — conservative safety net
        if not request.messages:
            return request
        total = sum(len(str(m.get("content", ""))) for m in request.messages)
        if total <= _CHAR_LIMIT:
            return request

        # Retain the first message (often a seed/system turn) + trim from oldest
        msgs = list(request.messages)
        while len(msgs) > 1 and sum(len(str(m.get("content", ""))) for m in msgs) > _CHAR_LIMIT:
            msgs.pop(1)  # drop the second-oldest, preserving first + recent tail
        logger.warning(
            "cloud.generate context truncated: original=%d msgs → %d msgs (total_chars was >%d)",
            len(request.messages), len(msgs), _CHAR_LIMIT,
        )
        return _replace(request, messages=msgs)

    async def generate(self, request: AIRequest, meta: FeatureMeta) -> AIResponse:
        from dataclasses import replace

        request = self._truncate_messages(request)
        chain = self._provider_chain(request, meta)
        real_tried: list[str] = []
        last_exc: Exception | None = None
        last_exc_str: str = ""

        for provider_name in chain:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue

            # When we reach "mock" and real providers were tried (and failed),
            # return a proper error response instead of the demo template.
            if provider_name == "mock" and real_tried:
                logger.error(
                    "cloud.generate: all real providers failed for feature=%s — "
                    "returning error response (real providers tried: %s)",
                    request.feature, real_tried,
                )
                return self._provider_error_response(request, real_tried, last_exc_str)

            pc = self._config.providers.get(provider_name)
            max_retries = pc.max_retries if pc else 0

            # Resolve the model: prefer explicit request model, then feature preferred,
            # then provider default (handled inside the provider itself).
            effective_model = request.model or meta.preferred_model
            effective_request = (
                replace(request, model=effective_model) if effective_model else request
            )

            for attempt in range(max_retries + 1):
                try:
                    response = await provider.generate(effective_request)
                    if last_exc is not None:
                        response.fallback_reason = (
                            f"fell back to {provider_name}: {str(last_exc)[:120]}"
                        )
                    logger.info(
                        "cloud.generate ok provider=%s model=%s feature=%s",
                        provider_name, response.model, request.feature,
                    )
                    return response
                except Exception as exc:
                    last_exc = exc
                    last_exc_str = str(exc)
                    is_billing = _is_billing_or_auth_error(exc)
                    logger.warning(
                        "cloud.generate failed provider=%s attempt=%d/%d feature=%s "
                        "billing_error=%s: %s",
                        provider_name, attempt + 1, max_retries + 1,
                        request.feature, is_billing, exc,
                    )
                    if is_billing:
                        # Billing/auth errors are non-retryable — move on immediately
                        break
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)

            real_tried.append(provider_name)

        # Unreachable: the loop above always returns or the error path fires before mock
        raise RuntimeError(
            f"Cloud AI layer exhausted all providers; last error: {last_exc}"
        )

    @staticmethod
    def _provider_error_response(
        request: AIRequest,
        providers_tried: list[str],
        error_detail: str,
    ) -> AIResponse:
        """Return a user-facing error response when all real providers failed."""
        # Surface a billing hint when we can detect it
        hint = ""
        if any(sig in error_detail.lower() for sig in _BILLING_ERROR_SIGNALS):
            hint = (
                "\n\n**Likely cause:** The AI provider account has insufficient credits. "
                "Please top up your account at the provider's billing page and restart the server."
            )
        elif "401" in error_detail or "authentication" in error_detail.lower():
            hint = (
                "\n\n**Likely cause:** Invalid API key. "
                "Check `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in `backend/.env`."
            )

        provider_list = ", ".join(providers_tried)
        text = (
            f"**Synaptiq AI is temporarily unavailable.**\n\n"
            f"The AI service encountered an error connecting to its provider "
            f"({provider_list})."
            f"{hint}\n\n"
            "_Please try again in a moment. If the issue persists, contact support._"
        )

        return AIResponse(
            text=text,
            layer=ExecutionLayer.CLOUD,
            provider="error_fallback",
            model="none",
            latency_ms=0,
            cost_usd=0.0,
            fallback_reason=f"all real providers failed ({provider_list}): {error_detail[:200]}",
        )
