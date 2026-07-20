"""Unit tests for the Hybrid AI Engine architecture.

Runs entirely in-process against MockProvider — no network calls, no DB.
Execute with:
    cd backend && python -m pytest tests/test_ai_engine.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── helpers ─────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


# ══════════════════════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════════════════════

class TestAIEngineConfig:
    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("AI_MATCHING_PROVIDER", "anthropic")

        from services.ai.engine.config import AIEngineConfig, reload_config
        cfg = reload_config()

        assert cfg.preferred_cloud_provider == "anthropic"
        assert cfg.enable_rule_layer is True
        assert cfg.enable_local_layer is False
        assert "anthropic" in cfg.providers
        assert "openai" in cfg.providers
        assert "mock" in cfg.providers

    def test_anthropic_enabled_when_key_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from services.ai.engine.config import reload_config
        cfg = reload_config()
        assert cfg.providers["anthropic"].enabled is True
        assert cfg.providers["anthropic"].api_key == "sk-ant-test"

    def test_openai_disabled_when_no_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from services.ai.engine.config import reload_config
        cfg = reload_config()
        assert cfg.providers["openai"].enabled is False

    def test_budget_defaults_unlimited(self, monkeypatch):
        monkeypatch.delenv("AI_DAILY_BUDGET_USD", raising=False)
        from services.ai.engine.config import reload_config
        cfg = reload_config()
        assert cfg.budget.daily_limit_usd == 0.0

    def test_custom_budget(self, monkeypatch):
        monkeypatch.setenv("AI_DAILY_BUDGET_USD", "25.50")
        from services.ai.engine.config import reload_config
        cfg = reload_config()
        assert cfg.budget.daily_limit_usd == 25.50

    def test_mock_always_enabled(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from services.ai.engine.config import reload_config
        cfg = reload_config()
        assert cfg.providers["mock"].enabled is True


# ══════════════════════════════════════════════════════════════════════════════
# Feature Registry
# ══════════════════════════════════════════════════════════════════════════════

class TestFeatureRegistry:
    def test_all_required_features_present(self):
        from services.ai.engine.registry import get_all_feature_ids
        ids = get_all_feature_ids()
        required = [
            "research_gap_finder", "literature_review", "manuscript_review",
            "statistical_review", "research_design_advisor", "abstract_generator",
            "ai_rewriting", "collaboration_intelligence", "ai_assistant",
            "ai_chat", "journal_matching", "conference_matching", "grant_matching",
            "reviewer_matching", "teaching_lesson_generation",
            "teaching_assessment_generation", "teaching_assistant",
            "grant_gap_detection", "marketplace_matching", "admin_copilot",
            "recommendation_engine", "general",
        ]
        for feat in required:
            assert feat in ids, f"Feature '{feat}' missing from registry"

    def test_unknown_feature_falls_back_to_general(self):
        from services.ai.engine.registry import get_feature_meta
        meta = get_feature_meta("nonexistent_feature_xyz")
        assert meta.feature_id == "general"

    def test_admin_copilot_uses_haiku(self):
        from services.ai.engine.registry import get_feature_meta
        meta = get_feature_meta("admin_copilot")
        assert meta.preferred_model == "claude-haiku-4-5-20251001"

    def test_ai_chat_is_critical(self):
        from services.ai.engine.registry import get_feature_meta
        meta = get_feature_meta("ai_chat")
        assert meta.priority == "critical"
        assert meta.requires_reasoning is True

    def test_abstract_generator_no_reasoning(self):
        from services.ai.engine.registry import get_feature_meta
        meta = get_feature_meta("abstract_generator")
        assert meta.requires_reasoning is False

    def test_all_features_have_fallback_layers(self):
        from services.ai.engine.registry import list_features
        for feat in list_features():
            assert len(feat.fallback_layers) >= 1, (
                f"{feat.feature_id} has no fallback layers"
            )

    def test_all_cloud_features_use_valid_providers(self):
        from services.ai.engine.registry import list_features
        from services.ai.engine.types import ExecutionLayer
        valid_providers = {"anthropic", "openai", "local", "mock"}
        for feat in list_features():
            if feat.preferred_layer == ExecutionLayer.CLOUD:
                assert feat.preferred_provider in valid_providers, (
                    f"{feat.feature_id} has unknown provider '{feat.preferred_provider}'"
                )


# ══════════════════════════════════════════════════════════════════════════════
# MockProvider
# ══════════════════════════════════════════════════════════════════════════════

class TestMockProvider:
    def test_generate_returns_response(self):
        from services.ai.engine.types import AIRequest
        from services.ai.providers.mock_provider import MockProvider
        provider = MockProvider()
        request = AIRequest(
            system="test system",
            messages=[{"role": "user", "content": "hello"}],
            feature="general",
        )
        response = run(provider.generate(request))
        assert isinstance(response.text, str)
        assert len(response.text) > 10
        assert response.provider == "mock"
        assert response.cost_usd == 0.0

    def test_generate_uses_feature_template(self):
        from services.ai.engine.types import AIRequest
        from services.ai.providers.mock_provider import MockProvider
        provider = MockProvider()
        request = AIRequest(
            system="",
            messages=[{"role": "user", "content": "find gaps"}],
            feature="research_gap_finder",
        )
        response = run(provider.generate(request))
        assert "Research Gap" in response.text

    def test_health_always_available(self):
        from services.ai.providers.mock_provider import MockProvider
        h = run(MockProvider().health())
        assert h.available is True
        assert h.latency_ms == 0

    def test_estimate_cost_is_zero(self):
        from services.ai.providers.mock_provider import MockProvider
        assert MockProvider().estimate_cost(100_000, 50_000) == 0.0

    def test_validate_returns_true(self):
        from services.ai.providers.mock_provider import MockProvider
        assert run(MockProvider().validate()) is True

    def test_stream_yields_chunks(self):
        from services.ai.engine.types import AIRequest
        from services.ai.providers.mock_provider import MockProvider

        async def collect():
            request = AIRequest(
                system="",
                messages=[{"role": "user", "content": "test"}],
                feature="general",
            )
            chunks = []
            async for chunk in MockProvider().stream(request):
                chunks.append(chunk)
            return chunks

        chunks = run(collect())
        assert len(chunks) > 0
        assert "".join(chunks).strip()


# ══════════════════════════════════════════════════════════════════════════════
# HybridExecutionRouter
# ══════════════════════════════════════════════════════════════════════════════

class TestHybridExecutionRouter:
    def _make_config(self, local=False, rule=True):
        from services.ai.engine.config import AIEngineConfig, ProviderConfig
        return AIEngineConfig(
            providers={
                "anthropic": ProviderConfig(name="anthropic", enabled=True, api_key="test"),
                "openai": ProviderConfig(name="openai", enabled=False),
                "mock": ProviderConfig(name="mock", enabled=True),
                "local": ProviderConfig(name="local", enabled=local),
            },
            preferred_cloud_provider="anthropic",
            fallback_cloud_providers=["openai"],
            enable_local_layer=local,
            enable_rule_layer=rule,
        )

    def test_cloud_features_route_to_cloud(self):
        from services.ai.engine.router import HybridExecutionRouter
        from services.ai.engine.types import AIRequest, ExecutionLayer
        router = HybridExecutionRouter()
        config = self._make_config()
        request = AIRequest(system="", messages=[], feature="research_gap_finder")
        assert router.route(request, config) == ExecutionLayer.CLOUD

    def test_explicit_local_provider_routes_to_local(self):
        from services.ai.engine.router import HybridExecutionRouter
        from services.ai.engine.types import AIRequest, ExecutionLayer
        router = HybridExecutionRouter()
        config = self._make_config(local=True)
        request = AIRequest(system="", messages=[], feature="ai_chat", provider="local")
        assert router.route(request, config) == ExecutionLayer.LOCAL

    def test_local_layer_disabled_routes_to_cloud(self):
        from services.ai.engine.router import HybridExecutionRouter
        from services.ai.engine.types import AIRequest, ExecutionLayer
        router = HybridExecutionRouter()
        config = self._make_config(local=False)
        request = AIRequest(system="", messages=[], feature="abstract_generator")
        assert router.route(request, config) == ExecutionLayer.CLOUD

    def test_fallback_skips_failed_layer(self):
        from services.ai.engine.router import HybridExecutionRouter
        from services.ai.engine.types import AIRequest, ExecutionLayer
        router = HybridExecutionRouter()
        config = self._make_config()
        request = AIRequest(system="", messages=[], feature="research_gap_finder")
        fallback = router.route_fallback(ExecutionLayer.CLOUD, request, config)
        assert fallback != ExecutionLayer.CLOUD

    def test_fallback_chain_exhausted_returns_none(self):
        from services.ai.engine.config import AIEngineConfig, ProviderConfig
        from services.ai.engine.router import HybridExecutionRouter
        from services.ai.engine.types import AIRequest, ExecutionLayer
        router = HybridExecutionRouter()
        config = AIEngineConfig(
            providers={},
            enable_local_layer=False,
            enable_rule_layer=False,
        )
        request = AIRequest(system="", messages=[], feature="admin_copilot")
        result = router.route_fallback(ExecutionLayer.RULE, request, config)
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# AIEngine (integration — all mock)
# ══════════════════════════════════════════════════════════════════════════════

class TestAIEngine:
    def _build_mock_engine(self):
        from services.ai.engine.config import AIEngineConfig, ProviderConfig
        from services.ai.engine.core import AIEngine
        config = AIEngineConfig(
            providers={
                "anthropic": ProviderConfig(name="anthropic", enabled=False, api_key=""),
                "openai": ProviderConfig(name="openai", enabled=False, api_key=""),
                "local": ProviderConfig(name="local", enabled=False),
                "mock": ProviderConfig(name="mock", enabled=True, default_model="mock-v1"),
            },
            preferred_cloud_provider="anthropic",
            fallback_cloud_providers=[],
            enable_local_layer=False,
            enable_rule_layer=True,
        )
        return AIEngine(config)

    def test_generate_returns_text(self):
        from services.ai.engine.types import AIRequest
        engine = self._build_mock_engine()
        request = AIRequest(
            system="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Hello"}],
            feature="general",
        )
        response = run(engine.generate(request))
        assert isinstance(response.text, str)
        assert len(response.text) > 0

    def test_generate_uses_feature_from_registry(self):
        from services.ai.engine.types import AIRequest
        engine = self._build_mock_engine()
        request = AIRequest(
            system="",
            messages=[{"role": "user", "content": "analyze"}],
            feature="literature_review",
        )
        response = run(engine.generate(request))
        assert response.text  # non-empty

    def test_generate_never_raises(self):
        from services.ai.engine.types import AIRequest
        engine = self._build_mock_engine()
        request = AIRequest(
            system="",
            messages=[{"role": "user", "content": "test"}],
            feature="unknown_feature_that_does_not_exist",
        )
        response = run(engine.generate(request))
        assert isinstance(response.text, str)

    def test_health_returns_system_health(self):
        engine = self._build_mock_engine()
        h = run(engine.health())
        assert h.status in ("ok", "degraded", "unavailable")
        assert isinstance(h.providers, list)
        assert len(h.providers) > 0

    def test_health_mock_is_degraded_not_unavailable(self):
        engine = self._build_mock_engine()
        h = run(engine.health())
        assert h.status != "unavailable"


# ══════════════════════════════════════════════════════════════════════════════
# call_llm backward-compatibility shim
# ══════════════════════════════════════════════════════════════════════════════

class TestCallLLMShim:
    def test_signature_unchanged(self):
        import inspect
        from services.ai.llm import call_llm
        sig = inspect.signature(call_llm)
        params = list(sig.parameters.keys())
        assert "system" in params
        assert "user_msg" in params
        assert "provider" in params
        assert "model" in params
        assert "messages" in params
        assert "max_tokens" in params
        assert "feature" in params

    def test_returns_string(self, monkeypatch):
        from services.ai.engine.core import reset_engine
        reset_engine()
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from services.ai.engine.config import reload_config
        reload_config()
        reset_engine()

        from services.ai.llm import call_llm
        result = run(call_llm(system="Be helpful.", user_msg="Hi"))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_multi_turn_messages(self, monkeypatch):
        from services.ai.engine.core import reset_engine
        reset_engine()
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from services.ai.engine.config import reload_config
        reload_config()
        reset_engine()

        from services.ai.llm import call_llm
        msgs = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
        ]
        result = run(call_llm(system="Be helpful.", messages=msgs))
        assert isinstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
# AnthropicProvider pricing
# ══════════════════════════════════════════════════════════════════════════════

class TestAnthropicProviderPricing:
    def test_haiku_cheaper_than_sonnet(self):
        from services.ai.engine.config import ProviderConfig
        from services.ai.providers.anthropic_provider import AnthropicProvider

        sonnet = AnthropicProvider(ProviderConfig(
            name="anthropic", api_key="x", default_model="claude-sonnet-4-6"
        ))
        haiku = AnthropicProvider(ProviderConfig(
            name="anthropic", api_key="x", default_model="claude-haiku-4-5-20251001"
        ))
        cost_sonnet = sonnet.estimate_cost(10_000, 5_000)
        cost_haiku = haiku.estimate_cost(10_000, 5_000)
        assert cost_haiku < cost_sonnet

    def test_cost_is_positive(self):
        from services.ai.engine.config import ProviderConfig
        from services.ai.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(ProviderConfig(name="anthropic", api_key="x"))
        assert provider.estimate_cost(1000, 500) > 0

    def test_zero_tokens_zero_cost(self):
        from services.ai.engine.config import ProviderConfig
        from services.ai.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(ProviderConfig(name="anthropic", api_key="x"))
        assert provider.estimate_cost(0, 0) == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# AIHealthService
# ══════════════════════════════════════════════════════════════════════════════

class TestAIHealthService:
    def _build_service(self, anthropic_key="", openai_key=""):
        from services.ai.engine.config import AIEngineConfig, ProviderConfig
        from services.ai.health import AIHealthService
        from services.ai.providers.mock_provider import MockProvider
        config = AIEngineConfig(
            providers={
                "anthropic": ProviderConfig(
                    name="anthropic", enabled=bool(anthropic_key),
                    api_key=anthropic_key, default_model="claude-sonnet-4-6",
                    fallback_models=["claude-haiku-4-5-20251001"],
                ),
                "openai": ProviderConfig(
                    name="openai", enabled=bool(openai_key), api_key=openai_key,
                    default_model="gpt-4o-mini",
                ),
                "mock": ProviderConfig(name="mock", enabled=True),
            },
            preferred_cloud_provider="anthropic",
        )
        providers = {"mock": MockProvider(config.providers["mock"])}
        return AIHealthService(providers, config)

    def test_no_keys_status_degraded(self):
        svc = self._build_service()
        health = run(svc.get_status())
        assert health.status in ("degraded", "unavailable")

    def test_timestamp_present(self):
        svc = self._build_service()
        health = run(svc.get_status())
        assert health.timestamp

    def test_to_dict_serialises(self):
        svc = self._build_service()
        health = run(svc.get_status())
        d = health.to_dict()
        assert "status" in d
        assert "providers" in d
        assert isinstance(d["providers"], list)

    def test_cache_enabled_reflected(self):
        from services.ai.engine.config import AIEngineConfig, CacheConfig, ProviderConfig
        from services.ai.health import AIHealthService
        from services.ai.providers.mock_provider import MockProvider
        config = AIEngineConfig(
            providers={"mock": ProviderConfig(name="mock", enabled=True)},
            cache=CacheConfig(enabled=True, ttl_seconds=300),
        )
        svc = AIHealthService({"mock": MockProvider()}, config)
        health = run(svc.get_status())
        assert health.cache_enabled is True


# ══════════════════════════════════════════════════════════════════════════════
# CloudAILayer
# ══════════════════════════════════════════════════════════════════════════════

class TestCloudAILayer:
    def test_falls_through_to_mock_when_no_real_providers(self):
        from services.ai.engine.config import AIEngineConfig, ProviderConfig
        from services.ai.engine.registry import get_feature_meta
        from services.ai.engine.types import AIRequest
        from services.ai.layers.cloud_ai import CloudAILayer
        from services.ai.providers.mock_provider import MockProvider

        config = AIEngineConfig(
            providers={
                "anthropic": ProviderConfig(name="anthropic", enabled=False),
                "mock": ProviderConfig(name="mock", enabled=True),
            },
            preferred_cloud_provider="anthropic",
            fallback_cloud_providers=[],
        )
        providers = {"mock": MockProvider()}
        layer = CloudAILayer(providers, config)
        meta = get_feature_meta("general")
        request = AIRequest(system="", messages=[{"role": "user", "content": "hi"}])
        response = run(layer.generate(request, meta))
        assert response.provider == "mock"

    def test_uses_feature_preferred_model(self):
        from services.ai.engine.config import AIEngineConfig, ProviderConfig
        from services.ai.engine.registry import get_feature_meta
        from services.ai.engine.types import AIRequest
        from services.ai.layers.cloud_ai import CloudAILayer
        from services.ai.providers.mock_provider import MockProvider

        config = AIEngineConfig(
            providers={"mock": ProviderConfig(name="mock", enabled=True)},
            preferred_cloud_provider="anthropic",
        )
        providers = {"mock": MockProvider()}
        layer = CloudAILayer(providers, config)
        meta = get_feature_meta("admin_copilot")
        request = AIRequest(system="", messages=[{"role": "user", "content": "briefing"}])
        response = run(layer.generate(request, meta))
        assert response.text
