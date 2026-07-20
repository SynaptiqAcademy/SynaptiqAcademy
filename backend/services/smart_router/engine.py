"""SmartExecutionRouter — central AI routing engine for the Synaptiq platform.

Every AIEngine.generate() call passes through here after RAG enrichment.
The router decides which layer (rule/local/cloud) handles the request by
considering feature profile, complexity, budget, load, and cache state.

Integration point in AIEngine.generate():
    request = await self._rag_enrich(request)
    decision = await smart_router.decide(request)
    layer = ExecutionLayer[decision.selected_layer.upper()]
    response = await self._execute_with_fallback(request, layer)
    await smart_router.record(decision, response)
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any

from services.smart_router.budget import BudgetManager
from services.smart_router.cache import RouterCache
from services.smart_router.complexity import ComplexityAnalyzer
from services.smart_router.config import SmartRouterConfig, load_router_config
from services.smart_router.load_balancer import LoadBalancer
from services.smart_router.observability import RouterObservability
from services.smart_router.profiles import get_profile
from services.smart_router.simulation import LoadSimulator
from services.smart_router.telemetry import SmartRouterTelemetry, get_router_telemetry
from services.smart_router.token_estimator import TokenEstimator
from services.smart_router.types import (
    BudgetStatus,
    ComplexityLevel,
    ExecutionRecord,
    RouterSignal,
    RoutingDecision,
    SimulationResult,
    TokenEstimate,
)

logger = logging.getLogger("synaptiq.smart_router")


class SmartExecutionRouter:
    """Decides the optimal execution layer for every AI request."""

    def __init__(self, config: SmartRouterConfig, db: Any) -> None:
        self._config = config
        self._complexity = ComplexityAnalyzer(
            large_context_tokens=config.large_context_threshold,
            very_large_context_tokens=config.very_large_context_threshold,
        )
        self._estimator = TokenEstimator(config)
        self._budget = BudgetManager(config, db)
        self._cache = RouterCache(
            decision_ttl=float(config.decision_cache_ttl_s),
            output_ttl=float(config.output_cache_ttl_s),
        )
        self._balancer = LoadBalancer(max_concurrent_per_provider=config.max_concurrent_per_provider)
        self._telemetry = get_router_telemetry()
        self._observability = RouterObservability(db, audit_enabled=config.audit_enabled)
        self._simulator = LoadSimulator(config)

    async def decide(
        self,
        feature: str,
        messages: list[dict],
        system_prompt: str = "",
        user_id: str = "",
        workspace_id: str | None = None,
        subscription_tier: str = "free",
    ) -> RoutingDecision:
        """Return a RoutingDecision without executing. Always returns, never raises."""
        t0 = time.monotonic()
        request_id = str(uuid.uuid4())

        try:
            return await self._decide_inner(
                request_id=request_id,
                feature=feature,
                messages=messages,
                system_prompt=system_prompt,
                user_id=user_id,
                workspace_id=workspace_id,
                subscription_tier=subscription_tier,
                t0=t0,
            )
        except Exception as exc:
            logger.warning("SmartRouter.decide failed (fallback to cloud): %s", exc)
            return self._safe_cloud_decision(request_id, feature, user_id, t0)

    async def record(self, decision: RoutingDecision, response_text: str, actual_cost: float,
                     actual_input_tokens: int, actual_output_tokens: int,
                     actual_provider: str, actual_model: str, actual_layer: str,
                     latency_ms: int, fallback_used: bool = False,
                     fallback_reason: str = "", error: str = "") -> None:
        """Record execution results for telemetry and budget tracking."""
        try:
            record = ExecutionRecord(
                routing_decision=decision,
                actual_layer=actual_layer,
                actual_provider=actual_provider,
                actual_model=actual_model,
                actual_input_tokens=actual_input_tokens,
                actual_output_tokens=actual_output_tokens,
                actual_cost_usd=actual_cost,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                fallback_reason=fallback_reason,
                error=error,
            )
            await self._budget.record(
                actual_cost_usd=actual_cost,
                feature=decision.feature,
                layer=actual_layer,
                user_id=decision.user_id,
            )
            baseline_cost = self._estimator.estimate_from_tokens(
                decision.token_estimate.input_tokens,
                decision.token_estimate.output_tokens,
                "anthropic",
            )
            self._telemetry.record(
                layer=actual_layer,
                feature=decision.feature,
                provider=actual_provider,
                latency_ms=latency_ms,
                actual_cost_usd=actual_cost,
                baseline_cost_usd=baseline_cost,
                fallback_reason=fallback_reason,
                from_cache=decision.from_cache,
                budget_signal=decision.budget_signal.value,
                complexity=decision.complexity.name,
                input_tokens=actual_input_tokens,
                output_tokens=actual_output_tokens,
            )
            asyncio.create_task(self._observability.log_execution(record))

            # Cache deterministic outputs
            if actual_layer == "rule" and not error:
                out_key = self._cache.make_output_key(decision.feature, system_prompt="", messages=[])
                self._cache.set_output(out_key, response_text)
        except Exception as exc:
            logger.debug("SmartRouter.record error: %s", exc)

    def simulate(self, concurrent_users: int, duration_minutes: int = 60) -> SimulationResult:
        return self._simulator.simulate(concurrent_users, duration_minutes)

    def compare_scales(self, user_counts: list[int]) -> list[dict]:
        return self._simulator.compare_scales(user_counts)

    def get_telemetry(self) -> dict:
        return self._telemetry.get_stats()

    def get_cache_stats(self) -> dict:
        return self._cache.stats()

    def get_load_summary(self) -> dict:
        return self._balancer.summary()

    async def get_budget_summary(self) -> dict:
        return await self._budget.get_summary()

    async def get_budget_history(self, days: int = 7) -> list[dict]:
        return await self._budget.get_daily_breakdown(days)

    async def get_audit_log(self, limit: int = 100, feature: str | None = None) -> list[dict]:
        return await self._observability.get_recent_decisions(limit=limit, feature=feature)

    def explain_complexity(
        self,
        feature: str,
        messages: list[dict],
        system_prompt: str = "",
    ) -> dict:
        return self._complexity.explain(feature, messages, system_prompt)

    def clear_cache(self, level: str = "all") -> None:
        self._cache.clear(level)

    def reset_telemetry(self) -> None:
        self._telemetry.reset()

    # ── Internal routing logic ─────────────────────────────────────────────────

    async def _decide_inner(
        self,
        request_id: str,
        feature: str,
        messages: list[dict],
        system_prompt: str,
        user_id: str,
        workspace_id: str | None,
        subscription_tier: str,
        t0: float,
    ) -> RoutingDecision:
        profile = get_profile(feature)
        complexity = self._complexity.analyze(feature, messages, system_prompt)

        # ── Step 1: Check output cache for deterministic features ─────────────
        if profile.cacheable and complexity <= ComplexityLevel.LOW:
            out_key = self._cache.make_output_key(feature, system_prompt, messages)
            if self._cache.get_output(out_key) is not None:
                estimate = TokenEstimate(
                    input_tokens=0, output_tokens=0, estimated_cost_usd=0.0,
                    provider="cache", model="cache",
                )
                return RoutingDecision(
                    request_id=request_id,
                    feature=feature,
                    complexity=complexity,
                    selected_layer="cache",
                    selected_provider="cache",
                    selected_model=None,
                    token_estimate=estimate,
                    routing_reason="output_cache_hit",
                    fallback_chain=[],
                    budget_signal=RouterSignal.PROCEED,
                    priority_score=profile.priority_score,
                    from_cache=True,
                    decision_latency_ms=int((time.monotonic() - t0) * 1000),
                    user_id=user_id,
                    workspace_id=workspace_id,
                )

        # ── Step 2: Classify target layer from complexity and profile ─────────
        target_layer = self._classify_layer(complexity, profile, subscription_tier)

        # ── Step 3: Select provider for the layer ─────────────────────────────
        provider, model = self._select_provider(target_layer, profile)

        # ── Step 4: Estimate tokens and cost ──────────────────────────────────
        estimate = self._estimator.estimate(feature, messages, system_prompt, provider, model)

        # ── Step 5: Budget check ──────────────────────────────────────────────
        budget_status = await self._budget.check(estimate.estimated_cost_usd, user_id)

        if budget_status.signal == RouterSignal.REJECT:
            return RoutingDecision(
                request_id=request_id,
                feature=feature,
                complexity=complexity,
                selected_layer="error",
                selected_provider=None,
                selected_model=None,
                token_estimate=estimate,
                routing_reason="budget_exhausted",
                fallback_chain=[],
                budget_signal=budget_status.signal,
                priority_score=profile.priority_score,
                decision_latency_ms=int((time.monotonic() - t0) * 1000),
                user_id=user_id,
                workspace_id=workspace_id,
            )

        # If budget signals downgrade, try cheaper layer
        if budget_status.signal == RouterSignal.DOWNGRADE and target_layer == "cloud":
            if profile.allow_local_downgrade and self._balancer.local_is_available():
                target_layer = "local"
                provider, model = "local", None
                estimate = self._estimator.estimate(feature, messages, system_prompt, "local")

        # ── Step 6: Load-balance within the cloud tier ────────────────────────
        if target_layer == "cloud":
            best_provider = self._balancer.select_cloud_provider(
                preferred=self._config.preferred_cloud_provider,
                fallbacks=self._config.cloud_provider_fallbacks,
            )
            if best_provider:
                provider = best_provider
            else:
                # All cloud providers overloaded — try local
                if profile.allow_local_downgrade and self._balancer.local_is_available():
                    target_layer = "local"
                    provider, model = "local", None

        # ── Step 7: Build fallback chain ──────────────────────────────────────
        fallback_chain = self._build_fallback_chain(target_layer, profile)

        reason = self._build_reason(
            target_layer, complexity, budget_status, profile.allow_local_downgrade
        )

        asyncio.create_task(
            self._observability.log_decision(
                RoutingDecision(
                    request_id=request_id,
                    feature=feature,
                    complexity=complexity,
                    selected_layer=target_layer,
                    selected_provider=provider,
                    selected_model=model,
                    token_estimate=estimate,
                    routing_reason=reason,
                    fallback_chain=fallback_chain,
                    budget_signal=budget_status.signal,
                    priority_score=profile.priority_score,
                    decision_latency_ms=int((time.monotonic() - t0) * 1000),
                    user_id=user_id,
                    workspace_id=workspace_id,
                )
            )
        )

        return RoutingDecision(
            request_id=request_id,
            feature=feature,
            complexity=complexity,
            selected_layer=target_layer,
            selected_provider=provider,
            selected_model=model,
            token_estimate=estimate,
            routing_reason=reason,
            fallback_chain=fallback_chain,
            budget_signal=budget_status.signal,
            priority_score=profile.priority_score,
            decision_latency_ms=int((time.monotonic() - t0) * 1000),
            user_id=user_id,
            workspace_id=workspace_id,
        )

    def _classify_layer(self, complexity: ComplexityLevel, profile, tier: str) -> str:
        # Rule-native features
        if complexity == ComplexityLevel.VERY_LOW and profile.allow_rule_downgrade:
            return "rule"

        # Free tier forces downgrade where allowed
        if tier == "free" and profile.allow_local_downgrade and complexity <= ComplexityLevel.MEDIUM:
            if self._balancer.local_is_available():
                return "local"

        if complexity <= ComplexityLevel.LOW:
            if profile.allow_local_downgrade and self._balancer.local_is_available():
                return "local"
            if profile.allow_rule_downgrade:
                return "rule"

        if complexity == ComplexityLevel.MEDIUM:
            if profile.allow_local_downgrade and self._balancer.local_is_available():
                return "local"

        return "cloud"

    def _select_provider(self, layer: str, profile) -> tuple[str, str | None]:
        if layer == "rule":
            return "rule_engine", None
        if layer == "local":
            return "local", None
        provider = self._config.preferred_cloud_provider
        model_map = {
            "anthropic": "claude-sonnet-4-6",
            "openai": "gpt-4o",
        }
        return provider, model_map.get(provider)

    def _build_fallback_chain(self, selected_layer: str, profile) -> list[str]:
        chain = [selected_layer]
        if selected_layer == "cloud" and profile.allow_local_downgrade:
            chain.append("local")
        if selected_layer in ("cloud", "local") and profile.allow_rule_downgrade:
            chain.append("rule")
        chain.append("cache")
        chain.append("error")
        return chain

    def _build_reason(
        self,
        layer: str,
        complexity: ComplexityLevel,
        budget: BudgetStatus,
        can_local: bool,
    ) -> str:
        if budget.signal == RouterSignal.DOWNGRADE:
            return f"budget_downgrade:{budget.utilization_pct:.0f}%_used"
        if layer == "rule":
            return f"rule_native:{complexity.name}"
        if layer == "local":
            return f"local_sufficient:{complexity.name}"
        if layer == "cloud":
            return f"cloud_required:{complexity.name}"
        if layer == "cache":
            return "output_cache_hit"
        return "default_cloud"

    def _safe_cloud_decision(self, request_id: str, feature: str, user_id: str, t0: float) -> RoutingDecision:
        return RoutingDecision(
            request_id=request_id,
            feature=feature,
            complexity=ComplexityLevel.MEDIUM,
            selected_layer="cloud",
            selected_provider=self._config.preferred_cloud_provider,
            selected_model="claude-sonnet-4-6",
            token_estimate=TokenEstimate(provider="anthropic", model="claude-sonnet-4-6"),
            routing_reason="router_error_fallback",
            fallback_chain=["cloud", "local", "error"],
            budget_signal=RouterSignal.PROCEED,
            priority_score=50,
            decision_latency_ms=int((time.monotonic() - t0) * 1000),
            user_id=user_id,
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_router: SmartExecutionRouter | None = None
_router_lock = threading.Lock()


def get_smart_router(db: Any = None) -> SmartExecutionRouter:
    """Return or create the process-level SmartExecutionRouter singleton."""
    global _router
    if _router is None:
        with _router_lock:
            if _router is None:
                if db is None:
                    from db import get_db
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Called from within async context — db will be injected later
                            db = {}  # placeholder; will be replaced on first async use
                        else:
                            db = {}
                    except RuntimeError:
                        db = {}
                _router = SmartExecutionRouter(load_router_config(), db)
    return _router


async def get_smart_router_async() -> SmartExecutionRouter:
    """Async singleton factory that injects the real Motor DB."""
    global _router
    if _router is not None:
        return _router
    from db import get_db
    from repo.shim import make_db_proxy
    db = make_db_proxy(get_db(), system=True)
    with _router_lock:
        if _router is None:
            _router = SmartExecutionRouter(load_router_config(), db)
    return _router


def reset_smart_router() -> None:
    global _router
    with _router_lock:
        _router = None
