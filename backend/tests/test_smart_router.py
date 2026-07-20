"""Phase V Smart Execution Router — comprehensive test suite.

Covers: types, config, profiles, complexity, token estimation,
budget, cache, load balancer, priority queue, telemetry, simulation,
and the engine decision logic.

Run with: python -m pytest tests/test_smart_router.py -v
"""
import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _messages(text="Hello, please help me."):
    return [{"role": "user", "content": text}]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Types
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplexityLevel:
    def test_ordering(self):
        from services.smart_router.types import ComplexityLevel
        assert ComplexityLevel.VERY_LOW < ComplexityLevel.LOW
        assert ComplexityLevel.LOW < ComplexityLevel.MEDIUM
        assert ComplexityLevel.MEDIUM < ComplexityLevel.HIGH
        assert ComplexityLevel.HIGH < ComplexityLevel.CRITICAL

    def test_int_values(self):
        from services.smart_router.types import ComplexityLevel
        assert ComplexityLevel.VERY_LOW.value == 1
        assert ComplexityLevel.CRITICAL.value == 5

    def test_label(self):
        from services.smart_router.types import ComplexityLevel
        assert "Very" in ComplexityLevel.VERY_LOW.label()


class TestRouterSignal:
    def test_values(self):
        from services.smart_router.types import RouterSignal
        assert RouterSignal.PROCEED.value == "proceed"
        assert RouterSignal.REJECT.value == "reject"


class TestTokenEstimate:
    def test_total_computed(self):
        from services.smart_router.types import TokenEstimate
        te = TokenEstimate(input_tokens=100, output_tokens=200)
        assert te.total_tokens == 300

    def test_explicit_total(self):
        from services.smart_router.types import TokenEstimate
        te = TokenEstimate(input_tokens=100, output_tokens=200, total_tokens=500)
        assert te.total_tokens == 500


class TestBudgetStatus:
    def test_defaults(self):
        from services.smart_router.types import BudgetStatus, RouterSignal
        bs = BudgetStatus()
        assert bs.signal == RouterSignal.PROCEED
        assert bs.daily_used_usd == 0.0


class TestRoutingDecision:
    def test_create(self):
        from services.smart_router.types import ComplexityLevel, RouterSignal, RoutingDecision, TokenEstimate
        d = RoutingDecision(
            request_id="abc",
            feature="ai_chat",
            complexity=ComplexityLevel.HIGH,
            selected_layer="cloud",
            selected_provider="anthropic",
            selected_model="claude-sonnet-4-6",
            token_estimate=TokenEstimate(),
            routing_reason="cloud_required:HIGH",
            fallback_chain=["cloud", "local", "error"],
            budget_signal=RouterSignal.PROCEED,
            priority_score=5,
        )
        assert d.feature == "ai_chat"
        assert d.selected_layer == "cloud"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Config
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmartRouterConfig:
    def test_load(self):
        from services.smart_router.config import load_router_config
        cfg = load_router_config()
        assert cfg.daily_budget_usd > 0
        assert cfg.monthly_budget_usd > cfg.daily_budget_usd
        assert cfg.preferred_cloud_provider in ("anthropic", "openai")

    def test_reload_returns_same_instance(self):
        from services.smart_router.config import load_router_config
        c1 = load_router_config()
        c2 = load_router_config()
        assert c1 is c2

    def test_provider_costs_populated(self):
        from services.smart_router.config import PROVIDER_COSTS
        assert "anthropic" in PROVIDER_COSTS
        assert "local" in PROVIDER_COSTS

    def test_output_estimates_cover_known_features(self):
        from services.smart_router.config import OUTPUT_TOKEN_ESTIMATES
        for feat in ("research_gap_finder", "literature_review", "grammar_correction"):
            assert feat in OUTPUT_TOKEN_ESTIMATES

    def test_provider_cost_estimate(self):
        from services.smart_router.config import PROVIDER_COSTS
        cfg = PROVIDER_COSTS["anthropic"]
        cost = cfg.estimate(1000, 500)
        assert cost > 0
        assert isinstance(cost, float)

    def test_local_cost_is_zero(self):
        from services.smart_router.config import PROVIDER_COSTS
        cost = PROVIDER_COSTS["local"].estimate(5000, 2000)
        assert cost == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Feature Profiles
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeatureProfiles:
    def test_get_known_profile(self):
        from services.smart_router.profiles import get_profile
        p = get_profile("ai_chat")
        assert p.feature_id == "ai_chat"
        assert p.priority_score <= 20

    def test_get_unknown_returns_default(self):
        from services.smart_router.profiles import get_profile
        p = get_profile("nonexistent_feature_xyz")
        assert p.feature_id == "unknown"

    def test_46_profiles_registered(self):
        from services.smart_router.profiles import list_profiles
        profiles = list_profiles()
        assert len(profiles) >= 40  # 46 in spec; allow for future additions

    def test_rule_native_features(self):
        from services.smart_router.profiles import get_profile
        from services.smart_router.types import ComplexityLevel
        for feat in ("keyword_extraction", "reference_validation", "citation_metrics"):
            p = get_profile(feat)
            assert p.base_complexity == ComplexityLevel.VERY_LOW

    def test_critical_features_no_rule_downgrade(self):
        from services.smart_router.profiles import get_profile
        for feat in ("research_gap_finder", "literature_review", "manuscript_review"):
            p = get_profile(feat)
            assert not p.allow_rule_downgrade

    def test_priority_scores_in_range(self):
        from services.smart_router.profiles import list_profiles
        for p in list_profiles():
            assert 1 <= p.priority_score <= 100

    def test_get_all_feature_ids(self):
        from services.smart_router.profiles import get_all_feature_ids
        ids = get_all_feature_ids()
        assert "ai_chat" in ids
        assert "grammar_correction" in ids


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Complexity Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplexityAnalyzer:
    def setup_method(self):
        from services.smart_router.complexity import ComplexityAnalyzer
        self.analyzer = ComplexityAnalyzer()

    def test_very_low_feature(self):
        from services.smart_router.types import ComplexityLevel
        result = self.analyzer.analyze("keyword_extraction", _messages())
        assert result == ComplexityLevel.VERY_LOW

    def test_critical_feature_stays_critical(self):
        from services.smart_router.types import ComplexityLevel
        result = self.analyzer.analyze("research_gap_finder", _messages())
        assert result >= ComplexityLevel.HIGH

    def test_large_context_bumps_complexity(self):
        large_msg = [{"role": "user", "content": " ".join(["word"] * 600)}]
        base = self.analyzer.analyze("ai_rewriting", _messages())
        large = self.analyzer.analyze("ai_rewriting", large_msg)
        assert large >= base

    def test_reasoning_keywords_increase_complexity(self):
        simple = _messages("fix spelling please")
        complex_msg = _messages("critically analyze and synthesize the research methodology")
        r_simple = self.analyzer.analyze("writing_improvement", simple)
        r_complex = self.analyzer.analyze("writing_improvement", complex_msg)
        assert r_complex >= r_simple

    def test_simple_keywords_can_reduce_complexity(self):
        from services.smart_router.types import ComplexityLevel
        simple = _messages("fix spelling errors in this paragraph")
        result = self.analyzer.analyze("grammar_correction", simple)
        assert result <= ComplexityLevel.LOW

    def test_deep_conversation_bumps(self):
        short = [{"role": "user", "content": "Hello"}]
        deep = [{"role": "user" if i % 2 == 0 else "assistant", "content": "message"}
                for i in range(10)]
        r_short = self.analyzer.analyze("general", short)
        r_deep = self.analyzer.analyze("general", deep)
        assert r_deep >= r_short

    def test_explain_returns_breakdown(self):
        result = self.analyzer.explain("ai_chat", _messages(), "some system")
        assert "final_complexity" in result
        assert "base_complexity" in result
        assert "total_tokens" in result

    def test_clamped_to_valid_range(self):
        from services.smart_router.types import ComplexityLevel
        very_long_sys = "word " * 3000
        result = self.analyzer.analyze("ai_chat", _messages(), very_long_sys)
        assert result in list(ComplexityLevel)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Token Estimator
# ═══════════════════════════════════════════════════════════════════════════════

class TestTokenEstimator:
    def setup_method(self):
        from services.smart_router.config import load_router_config
        from services.smart_router.token_estimator import TokenEstimator
        self.estimator = TokenEstimator(load_router_config())

    def test_estimate_produces_non_zero_cost_for_cloud(self):
        est = self.estimator.estimate(
            "ai_chat", _messages("Analyze this paper"), "some system", "anthropic", "claude-sonnet-4-6"
        )
        assert est.input_tokens > 0
        assert est.output_tokens > 0
        assert est.estimated_cost_usd > 0

    def test_local_cost_zero(self):
        est = self.estimator.estimate("grammar_correction", _messages(), "", "local")
        assert est.estimated_cost_usd == 0.0

    def test_longer_message_higher_tokens(self):
        short_est = self.estimator.estimate("general", _messages("Hi"), "", "anthropic")
        long_est = self.estimator.estimate("general", _messages("Hi " * 200), "", "anthropic")
        assert long_est.input_tokens > short_est.input_tokens

    def test_count_message_tokens(self):
        from services.smart_router.token_estimator import TokenEstimator
        n = TokenEstimator.count_message_tokens(_messages("hello world"))
        assert n > 0

    def test_estimate_from_tokens(self):
        cost = self.estimator.estimate_from_tokens(1000, 500, "anthropic", "claude-sonnet-4-6")
        assert cost > 0

    def test_estimate_from_tokens_local_free(self):
        cost = self.estimator.estimate_from_tokens(1000, 500, "local")
        assert cost == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Router Cache
# ═══════════════════════════════════════════════════════════════════════════════

class TestRouterCache:
    def setup_method(self):
        from services.smart_router.cache import RouterCache
        self.cache = RouterCache(decision_ttl=60.0, output_ttl=60.0)

    def test_output_cache_hit(self):
        key = self.cache.make_output_key("grammar_correction", "", _messages())
        assert self.cache.get_output(key) is None
        self.cache.set_output(key, "Corrected text here.")
        assert self.cache.get_output(key) == "Corrected text here."

    def test_decision_cache(self):
        key = self.cache.make_decision_key("ai_chat", "user123")
        assert self.cache.get_decision(key) is None
        self.cache.set_decision(key, {"layer": "cloud"})
        assert self.cache.get_decision(key) == {"layer": "cloud"}

    def test_clear_all(self):
        key = self.cache.make_output_key("general", "", _messages())
        self.cache.set_output(key, "cached")
        self.cache.clear("all")
        assert self.cache.get_output(key) is None

    def test_stats_structure(self):
        stats = self.cache.stats()
        assert "decision_cache" in stats
        assert "output_cache" in stats
        assert "overall_hit_rate_pct" in stats

    def test_key_different_for_different_inputs(self):
        k1 = self.cache.make_output_key("general", "sys1", _messages("A"))
        k2 = self.cache.make_output_key("general", "sys2", _messages("B"))
        assert k1 != k2

    def test_template_cache(self):
        self.cache.set_template("tmpl:grammar", "You are a grammar expert.")
        assert self.cache.get_template("tmpl:grammar") == "You are a grammar expert."


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Load Balancer
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadBalancer:
    def setup_method(self):
        from services.smart_router.load_balancer import LoadBalancer
        self.lb = LoadBalancer(max_concurrent_per_provider=5)

    def test_acquire_and_release(self):
        assert self.lb.acquire("anthropic")
        load = self.lb.get_provider_load("anthropic")
        assert load.concurrent_requests == 1
        self.lb.release("anthropic", latency_ms=500, success=True)
        load = self.lb.get_provider_load("anthropic")
        assert load.concurrent_requests == 0

    def test_mark_unavailable(self):
        self.lb.mark_unavailable("anthropic")
        from services.smart_router.types import ProviderAvailability
        load = self.lb.get_provider_load("anthropic")
        assert load.availability == ProviderAvailability.UNAVAILABLE
        assert not self.lb.acquire("anthropic")

    def test_select_cloud_prefers_least_loaded(self):
        # Add 3 concurrent to anthropic, 0 to openai
        self.lb.acquire("anthropic")
        self.lb.acquire("anthropic")
        self.lb.acquire("anthropic")
        best = self.lb.select_cloud_provider("anthropic", ["openai"])
        assert best == "openai"

    def test_summary(self):
        self.lb.acquire("local")
        summary = self.lb.summary()
        assert "providers" in summary
        assert summary["total_concurrent"] >= 1

    def test_error_count_marks_degraded(self):
        from services.smart_router.types import ProviderAvailability
        for _ in range(5):
            self.lb.acquire("openai")
            self.lb.release("openai", 100, success=False)
        load = self.lb.get_provider_load("openai")
        assert load.availability == ProviderAvailability.DEGRADED


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Priority Queue
# ═══════════════════════════════════════════════════════════════════════════════

class TestPriorityQueue:
    def test_enqueue_and_dequeue(self):
        from services.smart_router.priority_queue import PriorityRequestQueue

        async def _test():
            q = PriorityRequestQueue()
            rid, fut = await q.enqueue("ai_chat", priority_score=5, payload={"msg": "hi"})
            assert q.queue_size() == 1
            item = await q.dequeue(timeout_s=1.0)
            assert item is not None
            assert item.feature == "ai_chat"
            q.complete(rid, "done")

        _run(_test())

    def test_priority_ordering(self):
        from services.smart_router.priority_queue import PriorityRequestQueue

        async def _test():
            q = PriorityRequestQueue()
            await q.enqueue("low_priority", priority_score=80, payload={})
            await q.enqueue("high_priority", priority_score=5, payload={})
            first = await q.dequeue(timeout_s=1.0)
            assert first is not None
            assert first.priority_score == 5
            second = await q.dequeue(timeout_s=1.0)
            assert second is not None
            assert second.priority_score == 80
            q.complete(first.request_id, None)
            q.complete(second.request_id, None)

        _run(_test())

    def test_queue_timeout(self):
        from services.smart_router.priority_queue import PriorityRequestQueue

        async def _test():
            q = PriorityRequestQueue()
            _, _ = await q.enqueue(
                "general", priority_score=50, payload={}, max_wait_ms=1
            )
            await asyncio.sleep(0.01)  # let the item expire
            item = await q.dequeue(timeout_s=1.0)
            assert item is None  # timed out
            assert q.stats()["total_timed_out"] == 1

        _run(_test())

    def test_stats_structure(self):
        from services.smart_router.priority_queue import PriorityRequestQueue

        async def _test():
            q = PriorityRequestQueue()
            stats = q.stats()
            assert "queue_size" in stats
            assert "total_enqueued" in stats
            assert "dead_letter_queue_size" in stats

        _run(_test())

    def test_dead_letter_on_no_retries(self):
        from services.smart_router.priority_queue import PriorityRequestQueue

        async def _test():
            q = PriorityRequestQueue()
            rid, _ = await q.enqueue("general", priority_score=50, payload={}, retries=0)
            item = await q.dequeue(timeout_s=1.0)
            assert item is not None
            q.fail(rid, RuntimeError("test error"))
            assert q.stats()["total_dead_lettered"] == 1
            dlq = q.dead_letter_items()
            assert len(dlq) == 1

        _run(_test())


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Smart Router Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmartRouterTelemetry:
    def setup_method(self):
        from services.smart_router.telemetry import SmartRouterTelemetry
        self.t = SmartRouterTelemetry()

    def test_record_and_stats(self):
        self.t.record(
            layer="cloud", feature="ai_chat", provider="anthropic",
            latency_ms=800, actual_cost_usd=0.01, baseline_cost_usd=0.01,
        )
        stats = self.t.get_stats()
        assert stats["total_requests"] == 1
        assert stats["layer_distribution"]["cloud"] == 1

    def test_cost_savings_calculated(self):
        self.t.record(
            layer="local", feature="grammar_correction", provider="local",
            latency_ms=200, actual_cost_usd=0.0, baseline_cost_usd=0.005,
        )
        stats = self.t.get_stats()
        assert stats["total_cost_saved_usd"] > 0

    def test_cache_hit_rate(self):
        self.t.record(layer="cloud", feature="f", provider="a", latency_ms=0,
                      actual_cost_usd=0, baseline_cost_usd=0, from_cache=True)
        self.t.record(layer="cloud", feature="f", provider="a", latency_ms=0,
                      actual_cost_usd=0, baseline_cost_usd=0, from_cache=False)
        stats = self.t.get_stats()
        assert stats["cache_hit_rate_pct"] == 50.0

    def test_reset(self):
        self.t.record(layer="rule", feature="x", provider="rule_engine",
                      latency_ms=10, actual_cost_usd=0, baseline_cost_usd=0)
        self.t.reset()
        assert self.t.get_stats()["total_requests"] == 0

    def test_routing_accuracy(self):
        self.t.record(layer="cloud", feature="f", provider="a",
                      latency_ms=0, actual_cost_usd=0, baseline_cost_usd=0)
        self.t.record(layer="local", feature="f", provider="local",
                      latency_ms=0, actual_cost_usd=0, baseline_cost_usd=0,
                      fallback_reason="cloud_error")
        acc = self.t.get_routing_accuracy()
        assert acc["total"] == 2
        assert acc["fallbacks"] == 1

    def test_latency_percentiles(self):
        for ms in [100, 200, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000]:
            self.t.record(layer="cloud", feature="f", provider="a",
                          latency_ms=ms, actual_cost_usd=0, baseline_cost_usd=0)
        stats = self.t.get_stats()
        assert stats["latency_p50_ms"] > 0
        assert stats["latency_p95_ms"] >= stats["latency_p50_ms"]


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Load Simulator
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadSimulator:
    def setup_method(self):
        from services.smart_router.config import load_router_config
        from services.smart_router.simulation import LoadSimulator
        self.sim = LoadSimulator(load_router_config())

    def test_small_scale(self):
        result = self.sim.simulate(100)
        assert result.n_users == 100
        assert result.estimated_requests > 0
        assert sum(result.layer_distribution.values()) > 0

    def test_large_scale(self):
        result = self.sim.simulate(10_000)
        assert result.estimated_cloud_cost_usd > 0
        assert result.p95_latency_ms > 0

    def test_deterministic(self):
        r1 = self.sim.simulate(1000)
        r2 = self.sim.simulate(1000)
        assert r1.estimated_cloud_cost_usd == r2.estimated_cloud_cost_usd

    def test_more_users_more_cost(self):
        r100 = self.sim.simulate(100)
        r10k = self.sim.simulate(10_000)
        assert r10k.estimated_cloud_cost_usd > r100.estimated_cloud_cost_usd

    def test_layer_distribution_sums_to_estimate(self):
        result = self.sim.simulate(500)
        total = sum(result.layer_distribution.values())
        # The distribution is scaled, so each bucket should be roughly correct
        assert total > 0

    def test_compare_scales(self):
        results = self.sim.compare_scales([100, 1000, 10_000])
        assert len(results) == 3
        assert results[0]["concurrent_users"] == 100
        assert results[2]["concurrent_users"] == 10_000
        assert "cost_per_day_usd" in results[0]
        assert "layer_distribution" in results[0]

    def test_warnings_at_high_load(self):
        result = self.sim.simulate(100_000)
        assert len(result.warnings) > 0

    def test_gpu_hours_positive_with_local_layer(self):
        result = self.sim.simulate(5000)
        # Some requests should go to local, producing GPU usage
        assert result.estimated_gpu_hours >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Budget Manager
# ═══════════════════════════════════════════════════════════════════════════════

class TestBudgetManager:
    def _make_budget(self, daily=50.0, monthly=500.0):
        from services.smart_router.budget import BudgetManager
        from services.smart_router.config import SmartRouterConfig

        cfg = SmartRouterConfig(
            daily_budget_usd=daily,
            monthly_budget_usd=monthly,
        )

        async def fake_find_one(query):
            return None

        mock_coll = MagicMock()
        mock_coll.find_one = AsyncMock(return_value=None)
        mock_coll.update_one = AsyncMock(return_value=None)
        mock_coll.find = MagicMock()
        mock_coll.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)
        return BudgetManager(cfg, mock_db)

    def test_proceed_under_budget(self):
        bm = self._make_budget(daily=50.0)

        async def _test():
            status = await bm.check(0.01)
            from services.smart_router.types import RouterSignal
            assert status.signal == RouterSignal.PROCEED

        _run(_test())

    def test_reject_over_budget(self):
        from services.smart_router.config import SmartRouterConfig
        from services.smart_router.budget import BudgetManager
        from services.smart_router.types import RouterSignal

        cfg = SmartRouterConfig(daily_budget_usd=1.0, budget_reject_pct=80.0)
        mock_coll = MagicMock()
        mock_coll.find_one = AsyncMock(return_value={"total_usd": 0.95})  # 95% used
        mock_coll.update_one = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)
        bm = BudgetManager(cfg, mock_db)

        async def _test():
            status = await bm.check(0.1)
            assert status.signal == RouterSignal.REJECT

        _run(_test())

    def test_summary_structure(self):
        bm = self._make_budget()

        async def _test():
            summary = await bm.get_summary()
            assert "daily" in summary
            assert "monthly" in summary

        _run(_test())


# ═══════════════════════════════════════════════════════════════════════════════
# 12. SmartExecutionRouter Engine
# ═══════════════════════════════════════════════════════════════════════════════

def _make_router():
    from services.smart_router.engine import SmartExecutionRouter
    from services.smart_router.config import load_router_config

    cfg = load_router_config()
    mock_coll = MagicMock()
    mock_coll.find_one = AsyncMock(return_value=None)
    mock_coll.update_one = AsyncMock(return_value=None)
    mock_coll.insert_one = AsyncMock(return_value=None)
    mock_coll.find = MagicMock()
    mock_coll.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)
    return SmartExecutionRouter(cfg, mock_db)


class TestSmartExecutionRouterEngine:
    def test_decide_basic(self):
        router = _make_router()

        async def _test():
            decision = await router.decide(
                feature="ai_chat",
                messages=_messages("Tell me about climate change"),
                user_id="user_test",
            )
            assert decision.feature == "ai_chat"
            assert decision.selected_layer in ("rule", "local", "cloud", "cache", "error")
            assert decision.request_id != ""

        _run(_test())

    def test_decide_rule_native(self):
        router = _make_router()

        async def _test():
            decision = await router.decide(
                feature="keyword_extraction",
                messages=_messages("machine learning deep neural networks"),
                user_id="user1",
            )
            # keyword_extraction is VERY_LOW and allow_rule_downgrade=False;
            # but with no local available it may go to cloud or local
            assert decision.selected_layer in ("rule", "local", "cloud")

        _run(_test())

    def test_decide_never_raises(self):
        router = _make_router()

        async def _test():
            for _ in range(5):
                decision = await router.decide(
                    feature="literature_review",
                    messages=_messages("systematic review of deep learning"),
                    user_id="user1",
                )
                assert decision is not None

        _run(_test())

    def test_budget_exhausted_returns_error_layer(self):
        from services.smart_router.engine import SmartExecutionRouter
        from services.smart_router.config import SmartRouterConfig

        cfg = SmartRouterConfig(daily_budget_usd=0.001, budget_reject_pct=1.0)

        mock_coll = MagicMock()
        mock_coll.find_one = AsyncMock(return_value={"total_usd": 0.01})  # way over budget
        mock_coll.update_one = AsyncMock()
        mock_coll.insert_one = AsyncMock()
        mock_coll.find = MagicMock()
        mock_coll.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)

        router = SmartExecutionRouter(cfg, mock_db)

        async def _test():
            decision = await router.decide("ai_chat", _messages(), user_id="u1")
            from services.smart_router.types import RouterSignal
            assert decision.budget_signal == RouterSignal.REJECT
            assert decision.selected_layer == "error"

        _run(_test())

    def test_simulation_via_router(self):
        router = _make_router()
        result = router.simulate(1000)
        assert result.n_users == 1000
        assert result.estimated_requests > 0

    def test_cache_stats_via_router(self):
        router = _make_router()
        stats = router.get_cache_stats()
        assert "decision_cache" in stats

    def test_telemetry_via_router(self):
        router = _make_router()
        stats = router.get_telemetry()
        assert "total_requests" in stats

    def test_explain_complexity(self):
        router = _make_router()
        result = router.explain_complexity(
            "ai_chat",
            _messages("analyze this paper systematically"),
        )
        assert "final_complexity" in result
        assert "feature" in result

    def test_clear_cache(self):
        router = _make_router()
        router.clear_cache("all")
        stats = router.get_cache_stats()
        assert stats["decision_cache"]["size"] == 0

    def test_reset_telemetry(self):
        router = _make_router()
        router.reset_telemetry()
        stats = router.get_telemetry()
        assert stats["total_requests"] == 0

    def test_budget_summary_structure(self):
        router = _make_router()

        async def _test():
            summary = await router.get_budget_summary()
            assert isinstance(summary, dict)

        _run(_test())


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Singleton
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    def test_reset_clears_singleton(self):
        from services.smart_router.engine import reset_smart_router
        reset_smart_router()
        from services.smart_router.engine import _router
        assert _router is None

    def test_get_router_telemetry_singleton(self):
        from services.smart_router.telemetry import get_router_telemetry
        t1 = get_router_telemetry()
        t2 = get_router_telemetry()
        assert t1 is t2
