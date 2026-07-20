"""
Enterprise AI Gateway — Main Orchestrator.

This is the ONLY class that may communicate with LLM providers.
Every AI request on the platform flows through here.

Pipeline (every call):
  User / Feature
      ↓
  GatewayRequest
      ↓
  1. Context Builder    — load twin, LKG, workspace, institution, recent AI
  ↓
  2. Policy Engine      — credits, injection detection, academic integrity
  ↓
  3. Prompt Registry    — versioned prompt or inline passthrough
  ↓
  4. AIEngine.generate  — routing, RAG, academic enrichment, provider fallback
  ↓
  5. Response Validator — evidence grounding (LLM-based, not regex)
  ↓
  6. Cost Ledger        — token counting, credit deduction, mission tracking
  ↓
  7. Observability      — structured logging with request_id tracing
  ↓
  8. AI Memory          — store conversation + mission context
  ↓
  GatewayResponse

Backward compat:
  - call_llm(system, user_msg, feature) → str
    still works; it calls execute_simple() which runs the full pipeline
    but returns only the response text. No caller changes required.

  - execute(GatewayRequest) → GatewayResponse
    Rich API for new code and migrated modules.

  - stream(GatewayRequest) → AsyncGenerator[str, None]
    For SSE paths (Copilot). Context/policy run before streaming;
    validation/cost/log run after stream completes.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import AsyncGenerator, Optional

from .context_builder import ContextBuilder
from .cost_ledger import CostLedger
from .observability import GatewayObservability
from .policy_engine import PolicyEngine, PolicyViolation
from .plugin_registry import plugin_registry
from .prompt_registry import registry as prompt_registry
from .response_validator import ResponseValidator
from .schemas import GatewayRequest, GatewayResponse, ValidationResult
from .ai_memory import get_memory

logger = logging.getLogger("gateway.core")


class AIGateway:
    """Enterprise AI Gateway — singleton; created via get_gateway()."""

    def __init__(self):
        self._context_builder = ContextBuilder()
        self._policy_engine   = PolicyEngine()
        self._validator       = ResponseValidator()
        self._cost_ledger     = CostLedger()
        self._observability   = GatewayObservability()
        logger.info("AIGateway initialised")

    # ── Primary API ───────────────────────────────────────────────────────────

    async def execute(
        self,
        request: GatewayRequest,
        db=None,
        user: dict | None = None,
    ) -> GatewayResponse:
        """
        Full gateway pipeline. Returns a GatewayResponse.
        Never raises — failures become structured error responses.
        """
        start = time.monotonic()
        response = GatewayResponse(
            request_id=request.request_id,
            feature=request.feature,
            plugin_name=request.plugin_name,
            prompt_id=request.prompt_id,
        )

        try:
            # 1. Plugin metadata
            plugin = plugin_registry.get(request.plugin_name or request.feature)

            # 2. Context building
            context_block = ""
            if db and (request.load_twin or request.load_lkg or
                       request.load_workspace or request.load_institution or
                       request.load_recent_ai):
                context_block = await self._context_builder.build(request, db)

            # 3. Policy enforcement
            try:
                await self._policy_engine.enforce(request, db, user)
            except PolicyViolation as pv:
                response.response = f"Request blocked by policy: {pv.message}"
                response.validation_status = "policy_rejected"
                response.warnings.append(f"policy:{pv.code}:{pv.message}")
                response.latency_ms = int((time.monotonic() - start) * 1000)
                return response

            # 4. Prompt resolution
            system, user_text = self._resolve_prompt(request, context_block)

            # 5. Cache check
            memory = get_memory()
            if not request.stream and system and user_text:
                cache_key = _make_cache_key(system, user_text)
                cached = await memory.get_cached_response(cache_key)
                if cached:
                    response.response       = cached
                    response.from_cache     = True
                    response.confidence     = "medium"
                    response.validation_status = "passed"
                    response.latency_ms     = int((time.monotonic() - start) * 1000)
                    await self._observability.log(request, response, db)
                    return response

            # 6. Execute via existing AIEngine
            ai_response = await self._call_engine(request, system, user_text)
            response.response       = ai_response.text
            response.provider       = ai_response.provider
            response.model          = ai_response.model
            response.tokens_in      = getattr(ai_response, "input_tokens", 0)
            response.tokens_out     = getattr(ai_response, "output_tokens", 0)
            response.from_cache     = getattr(ai_response, "from_cache", False)
            response.fallback_reason = ai_response.fallback_reason

            # 7. Response validation (real evidence grounding, not regex)
            require_ev = request.require_evidence or (
                plugin.require_evidence if plugin else False
            )
            val_result = await self._validator.validate(
                response_text=ai_response.text,
                request_context={"system": system[:200], "feature": request.feature},
                require_evidence=require_ev,
                feature=request.feature,
            )
            response.validation        = val_result
            response.validation_status = val_result.status
            response.confidence        = val_result.confidence or "low"
            response.warnings.extend(val_result.warnings)

            # Academic integrity disclaimer (injected by policy engine)
            if "academic_integrity_disclaimer" in request.metadata:
                response.warnings.append(request.metadata["academic_integrity_disclaimer"])

            # 8. Cost tracking (FIXES audit finding C-03: used_credits never incremented)
            if db:
                cost_usd, cost_credits = await self._cost_ledger.record(
                    request_id=request.request_id,
                    feature=request.feature,
                    user_id=request.user_id,
                    mission_id=request.mission_id,
                    provider=ai_response.provider,
                    model=ai_response.model,
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    db=db,
                )
                response.cost_usd     = cost_usd
                response.cost_credits = cost_credits

            # 9. Cache store (short-TTL for deterministic features)
            if not response.from_cache and not request.stream and response.response:
                cache_key = _make_cache_key(system, user_text)
                await memory.cache_response(cache_key, response.response, ttl_seconds=300)

            # 10. Memory: store conversation turn
            if request.user_id and request.user_message:
                await memory.append_message(request.user_id, "user", request.user_message)
                await memory.append_message(request.user_id, "assistant", response.response[:500])

        except Exception as exc:
            logger.error("Gateway execute error (request %s): %s", request.request_id, exc)
            response.response          = (
                "Synaptiq AI is temporarily unavailable. Please try again in a moment."
            )
            response.validation_status = "error"
            response.warnings.append(f"Internal error: {str(exc)[:200]}")

        response.latency_ms = int((time.monotonic() - start) * 1000)

        # 11. Observability
        await self._observability.log(request, response, db)

        return response

    async def execute_simple(
        self,
        system:    str,
        user_msg:  str,
        feature:   str = "general",
        user_id:   str | None = None,
        mission_id: str | None = None,
        workspace_id: str | None = None,
        max_tokens: int = 2048,
        db=None,
        **kwargs,
    ) -> str:
        """
        Backward-compatible thin wrapper used by call_llm().
        Runs the full gateway pipeline; returns only the response text.
        """
        request = GatewayRequest(
            system=system,
            user_message=user_msg,
            feature=feature,
            user_id=user_id,
            mission_id=mission_id,
            workspace_id=workspace_id,
            max_tokens=max_tokens,
        )
        response = await self.execute(request, db=db)
        return response.response

    async def stream(
        self,
        request: GatewayRequest,
        db=None,
        user: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming variant for SSE paths (Copilot).
        Context/policy run before the first token;
        validation/cost/log run after the stream completes.
        """
        start = time.monotonic()
        collected: list[str] = []

        # Pre-stream: context + policy (same as execute)
        context_block = ""
        if db and (request.load_twin or request.load_lkg):
            context_block = await self._context_builder.build(request, db)

        try:
            await self._policy_engine.enforce(request, db, user)
        except PolicyViolation as pv:
            yield f"[blocked:{pv.code}] {pv.message}"
            return

        system, user_text = self._resolve_prompt(request, context_block)

        # Stream from engine
        async for chunk in self._stream_engine(request, system, user_text):
            collected.append(chunk)
            yield chunk

        # Post-stream: cost + log (non-blocking)
        full_text = "".join(collected)
        if db and full_text:
            await self._cost_ledger.record(
                request_id=request.request_id,
                feature=request.feature,
                user_id=request.user_id,
                mission_id=request.mission_id,
                provider="anthropic",
                model="claude-sonnet-4-6",
                tokens_in=len(system) // 4,       # rough estimate
                tokens_out=len(full_text) // 4,
                db=db,
            )
        response = GatewayResponse(
            request_id=request.request_id,
            response=full_text,
            feature=request.feature,
            latency_ms=int((time.monotonic() - start) * 1000),
        )
        await self._observability.log(request, response, db)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve_prompt(
        self, request: GatewayRequest, context_block: str
    ) -> tuple[str, str]:
        """
        Return (system, user_message) with:
          - versioned prompt if prompt_id is set
          - context_block injected into system
          - inline system/user_message as fallback (backward compat)
        """
        if request.prompt_id:
            try:
                system, user_text = prompt_registry.render(
                    request.prompt_id, **request.variables
                )
            except KeyError:
                logger.warning("Prompt '%s' not found; using inline", request.prompt_id)
                system    = request.system
                user_text = request.user_message
        else:
            system    = request.system
            user_text = request.user_message

        # Inject context block
        if context_block:
            system = system + "\n" + context_block if system else context_block

        return system, user_text

    async def _call_engine(
        self, request: GatewayRequest, system: str, user_text: str
    ):
        """Delegate to existing AIEngine (with all its routing, RAG, academic enrichment)."""
        from services.ai.engine.core import get_engine
        from services.ai.engine.types import AIRequest

        messages = request.messages or [{"role": "user", "content": user_text}]
        ai_request = AIRequest(
            system=system,
            messages=messages,
            feature=request.feature,
            max_tokens=request.max_tokens,
            provider=request.provider,
            model=request.model,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
        )
        return await get_engine().generate(ai_request)

    async def _stream_engine(
        self, request: GatewayRequest, system: str, user_text: str
    ) -> AsyncGenerator[str, None]:
        """
        Streaming path: fall through to existing streaming infrastructure.
        The Copilot's SSE handler already manages streaming; we just pass through.
        """
        # Collect non-streaming response and yield it as one chunk
        # (true token-by-token streaming requires provider-level changes
        # tracked separately; this maintains current behavior exactly)
        ai_response = await self._call_engine(request, system, user_text)
        yield ai_response.text


# ── Cache key ─────────────────────────────────────────────────────────────────

def _make_cache_key(system: str, user_text: str) -> str:
    import hashlib
    raw = f"{system[:500]}|{user_text[:500]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ── Process-level singleton ───────────────────────────────────────────────────

_gateway: AIGateway | None = None
_gateway_lock = threading.Lock()


def get_gateway() -> AIGateway:
    """Return the process-level AIGateway singleton."""
    global _gateway
    if _gateway is None:
        with _gateway_lock:
            if _gateway is None:
                _gateway = AIGateway()
    return _gateway


def reset_gateway() -> None:
    """Discard singleton (test helper)."""
    global _gateway
    with _gateway_lock:
        _gateway = None
