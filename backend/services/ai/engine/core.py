"""AIEngine — central intelligence coordinator for the Synaptiq platform.

Every AI request flows through here:

  AI Feature
      ↓
  AIEngine.generate(AIRequest)
      ↓
  HybridExecutionRouter  →  ExecutionLayer
      ↓
  Layer (Rule | Local | Cloud)
      ↓
  Provider (Anthropic | OpenAI | Local | Mock)
      ↓
  AIResponse
      ↓
  AIRequestLogger (async, non-blocking)
      ↓
  caller receives AIResponse.text

The engine is a process-level singleton created via get_engine(). All state
(clients, config) lives in the engine and its subordinate objects.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time

from services.ai.engine.config import AIEngineConfig, load_config
from services.ai.engine.registry import get_feature_meta
from services.ai.engine.router import HybridExecutionRouter
from services.ai.engine.types import AIRequest, AIResponse, AISystemHealth, ExecutionLayer
from services.ai.health import AIHealthService
from services.ai.layers.cloud_ai import CloudAILayer
from services.ai.layers.local_ai import LocalAILayer
from services.ai.layers.rule_engine import RuleEngineLayer
from services.ai.providers import build_provider_registry
from services.ai.request_logger import AIRequestLogger

logger = logging.getLogger("synaptiq.ai.engine")


class AIEngine:
    """Orchestrates routing, execution, fallback, logging, and health reporting."""

    def __init__(self, config: AIEngineConfig) -> None:
        self._config = config
        self._router = HybridExecutionRouter()
        self._logger = AIRequestLogger()

        providers = build_provider_registry(config)
        self._providers = providers

        self._rule_layer = RuleEngineLayer()
        self._local_layer = LocalAILayer(providers.get("local"))
        self._cloud_layer = CloudAILayer(providers, config)
        self._health_service = AIHealthService(providers, config)

        logger.info(
            "AIEngine initialised — preferred=%s local=%s rule=%s providers=%s",
            config.preferred_cloud_provider,
            config.enable_local_layer,
            config.enable_rule_layer,
            list(providers.keys()),
        )

    async def generate(self, request: AIRequest) -> AIResponse:
        """Route and execute an AI request; never raises to callers."""
        start = time.monotonic()
        request = await self._rag_enrich(request)

        # Phase VI: Academic Intelligence Engine enriches the request with reasoning context
        request = await self._academic_enrich(request)

        # Phase V: Smart Router determines the optimal execution layer
        smart_decision = await self._smart_route(request)
        if smart_decision is not None and smart_decision.selected_layer == "error":
            from services.ai.engine.types import ExecutionLayer as _EL
            return AIResponse(
                text="AI request budget exhausted. Please try again later.",
                layer=_EL.RULE,
                provider="budget_manager",
                model="none",
                fallback_reason="budget_exhausted",
            )

        if smart_decision is not None and smart_decision.selected_layer not in ("", "cache"):
            try:
                from services.ai.engine.types import ExecutionLayer as _EL
                _LAYER_MAP = {"rule": _EL.RULE, "local": _EL.LOCAL, "cloud": _EL.CLOUD}
                layer = _LAYER_MAP.get(smart_decision.selected_layer, _EL.CLOUD)
            except Exception:
                layer = self._router.route(request, self._config)
        else:
            layer = self._router.route(request, self._config)

        response = await self._execute_with_fallback(request, layer)

        # Phase VI: Academic post-processing (validation + quality + memory update)
        response = await self._academic_post_process(request, response)

        response.latency_ms = int((time.monotonic() - start) * 1000)

        if smart_decision is not None:
            asyncio.create_task(self._smart_record(smart_decision, response))

        self._schedule_log(request, response)
        return response

    async def health(self, deep: bool = False) -> AISystemHealth:
        return await self._health_service.get_status(deep=deep)

    async def _execute_with_fallback(
        self,
        request: AIRequest,
        layer: ExecutionLayer,
    ) -> AIResponse:
        meta = get_feature_meta(request.feature)

        try:
            return await self._execute_layer(request, layer, meta)
        except Exception as primary_exc:
            logger.warning(
                "AIEngine: layer=%s failed feature=%s — seeking fallback. Error: %s",
                layer.value, request.feature, primary_exc,
            )
            fallback = self._router.route_fallback(layer, request, self._config)

            if fallback is not None:
                try:
                    response = await self._execute_layer(request, fallback, meta)
                    response.fallback_reason = (
                        f"fell back from {layer.value}: {str(primary_exc)[:120]}"
                    )
                    return response
                except Exception as fb_exc:
                    logger.error(
                        "AIEngine: fallback layer=%s also failed feature=%s: %s",
                        fallback.value, request.feature, fb_exc,
                    )

            mock = self._providers.get("mock")
            if mock is not None:
                response = await mock.generate(request)
                response.fallback_reason = f"all layers failed: {str(primary_exc)[:200]}"
                return response

            return AIResponse(
                text=(
                    "Synaptiq AI is temporarily unavailable. "
                    "Please try again in a moment."
                ),
                layer=ExecutionLayer.RULE,
                provider="emergency_fallback",
                model="none",
                fallback_reason=f"catastrophic failure: {str(primary_exc)[:200]}",
            )

    async def _execute_layer(
        self,
        request: AIRequest,
        layer: ExecutionLayer,
        meta,
    ) -> AIResponse:
        if layer == ExecutionLayer.RULE:
            return await self._rule_layer.generate(request)
        if layer == ExecutionLayer.LOCAL:
            return await self._local_layer.generate(request, meta)
        return await self._cloud_layer.generate(request, meta)

    async def _academic_enrich(self, request: AIRequest) -> AIRequest:
        """Inject academic reasoning context (best-effort; never raises)."""
        try:
            from services.academic.engine import get_academic_engine
            engine = await get_academic_engine()
            return await engine.enrich_request(request)
        except Exception:
            return request

    async def _academic_post_process(self, request: AIRequest, response: AIResponse) -> AIResponse:
        """Run academic validation + quality scoring after LLM response (best-effort)."""
        try:
            from services.academic.engine import get_academic_engine
            engine = await get_academic_engine()
            return await engine.post_process(request, response)
        except Exception:
            return response

    async def _smart_route(self, request: AIRequest):
        """Ask the SmartRouter for the optimal layer (best-effort; never raises)."""
        try:
            from services.smart_router.engine import get_smart_router_async
            router = await get_smart_router_async()
            return await router.decide(
                feature=request.feature,
                messages=request.messages,
                system_prompt=request.system or "",
                user_id=request.user_id or "",
                workspace_id=request.workspace_id,
                subscription_tier=getattr(request, "subscription_tier", "free"),
            )
        except Exception:
            return None

    async def _smart_record(self, decision, response: AIResponse) -> None:
        """Record actual execution results back into the SmartRouter (best-effort)."""
        try:
            from services.smart_router.engine import get_smart_router_async
            router = await get_smart_router_async()
            await router.record(
                decision=decision,
                response_text=response.text or "",
                actual_cost=0.0,         # actual cost tracking via billing layer
                actual_input_tokens=getattr(response, "input_tokens", 0),
                actual_output_tokens=getattr(response, "output_tokens", 0),
                actual_provider=response.provider or "",
                actual_model=response.model or "",
                actual_layer=response.layer.value if response.layer else "cloud",
                latency_ms=response.latency_ms,
                fallback_used=bool(response.fallback_reason),
                fallback_reason=response.fallback_reason or "",
                error="",
            )
        except Exception:
            pass

    async def _rag_enrich(self, request: AIRequest) -> AIRequest:
        """Inject retrieved document context into the system prompt (best-effort)."""
        try:
            from services.knowledge.engine import _RAG_FEATURES, get_knowledge_engine
            if request.feature not in _RAG_FEATURES:
                return request
            if not request.user_id:
                return request
            engine = await get_knowledge_engine()
            if not engine._config.rag_enabled:
                return request
            # Use the last user message as the query
            query = next(
                (m.get("content", "") for m in reversed(request.messages) if m.get("role") == "user"),
                "",
            )
            if not query or len(query) < 10:
                return request
            context, citations = await engine.build_context(
                query=query,
                user_id=request.user_id,
                workspace_id=request.workspace_id,
            )
            if context:
                request.system = request.system + "\n\n" + context if request.system else context
        except Exception:
            pass  # RAG enrichment is always best-effort; never blocks the request
        return request

    def _schedule_log(self, request: AIRequest, response: AIResponse) -> None:
        try:
            asyncio.create_task(self._logger.log(request, response))
        except RuntimeError:
            pass  # no running event loop (e.g. synchronous test context)


_engine: AIEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> AIEngine:
    """Return the process-level AIEngine singleton, creating it on first call."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AIEngine(load_config())
    return _engine


def reset_engine() -> None:
    """Discard the singleton (test helper — forces a fresh build on next get_engine())."""
    global _engine
    with _engine_lock:
        _engine = None
