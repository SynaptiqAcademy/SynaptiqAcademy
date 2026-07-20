"""Comprehensive tests for the Local AI Engine subsystem.

All tests are self-contained — no network, no running models, no API keys.
Provider HTTP calls are mocked via unittest.mock.

Run with:
    cd backend && python -m pytest tests/test_local_ai.py -v
"""
from __future__ import annotations

import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Config ───────────────────────────────────────────────────────────────────

class TestLocalAIConfig:
    def test_defaults(self):
        from services.local_ai.config import LocalAIConfig
        cfg = LocalAIConfig()
        assert cfg.ollama_base_url == "http://localhost:11434"
        assert cfg.default_provider == "ollama"
        assert cfg.max_context_tokens == 4096
        assert cfg.cache_ttl_seconds == 300.0
        assert cfg.max_retries == 1

    def test_from_env(self, monkeypatch):
        from services.local_ai.config import LocalAIConfig
        monkeypatch.setenv("LOCAL_AI_OLLAMA_URL", "http://myserver:11434")
        monkeypatch.setenv("LOCAL_AI_MAX_CONTEXT", "8192")
        monkeypatch.setenv("LOCAL_AI_TEMPERATURE", "0.7")
        cfg = LocalAIConfig.from_env()
        assert cfg.ollama_base_url == "http://myserver:11434"
        assert cfg.max_context_tokens == 8192
        assert cfg.temperature == pytest.approx(0.7)

    def test_from_env_defaults_when_empty(self, monkeypatch):
        from services.local_ai.config import LocalAIConfig
        monkeypatch.setenv("LOCAL_AI_MAX_CONTEXT", "")
        cfg = LocalAIConfig.from_env()
        assert cfg.max_context_tokens == 4096


# ── Token Estimator ──────────────────────────────────────────────────────────

class TestTokenEstimator:
    def test_estimate_short(self):
        from services.local_ai.utils.token_estimator import estimate_tokens
        assert estimate_tokens("hello") >= 1

    def test_estimate_longer(self):
        from services.local_ai.utils.token_estimator import estimate_tokens
        text = "word " * 100  # 500 chars
        est = estimate_tokens(text)
        assert 100 < est < 200  # ~125 tokens

    def test_estimate_per_family(self):
        from services.local_ai.utils.token_estimator import estimate_tokens
        text = "a" * 400
        qwen = estimate_tokens(text, "qwen")
        llama = estimate_tokens(text, "llama")
        # Qwen uses fewer chars/token (denser tokenizer)
        assert qwen >= llama

    def test_estimate_request_tokens(self):
        from services.local_ai.utils.token_estimator import estimate_request_tokens
        system = "You are an assistant."
        messages = [{"role": "user", "content": "Hello, how are you?"}]
        tokens = estimate_request_tokens(system, messages)
        assert tokens > 0

    def test_fits_context_window_true(self):
        from services.local_ai.utils.token_estimator import fits_context_window
        system = "System."
        messages = [{"role": "user", "content": "Hi"}]
        assert fits_context_window(system, messages, max_context_tokens=4096)

    def test_fits_context_window_false(self):
        from services.local_ai.utils.token_estimator import fits_context_window
        system = "S"
        messages = [{"role": "user", "content": "x" * 20000}]
        assert not fits_context_window(system, messages, max_context_tokens=1024)

    def test_truncation_budget(self):
        from services.local_ai.utils.token_estimator import truncation_budget
        budget = truncation_budget(max_context_tokens=4096, system="Short system.", reserved_output_tokens=512)
        assert budget > 3000


# ── Prompt Optimizer ─────────────────────────────────────────────────────────

class TestPromptOptimizer:
    def test_compress_whitespace(self):
        from services.local_ai.utils.prompt_optimizer import compress_system_prompt
        result = compress_system_prompt("  Hello  \n\n\n  World  ")
        assert "  " not in result
        assert "\n\n\n" not in result

    def test_deduplicate_instructions(self):
        from services.local_ai.utils.prompt_optimizer import deduplicate_instructions
        result = deduplicate_instructions("Be concise. Be accurate. Be concise.")
        assert result.count("Be concise") == 1

    def test_trim_messages_to_budget(self):
        from services.local_ai.utils.prompt_optimizer import trim_messages_to_budget
        messages = [
            {"role": "user", "content": "x" * 500},
            {"role": "assistant", "content": "y" * 500},
            {"role": "user", "content": "short"},
        ]
        trimmed = trim_messages_to_budget(messages, budget_tokens=100, preserve_last_n=1)
        # Last message must be preserved
        assert trimmed[-1]["content"] == "short"

    def test_optimize_prompt_returns_tuple(self):
        from services.local_ai.utils.prompt_optimizer import optimize_prompt
        sys_prompt, msgs = optimize_prompt(
            "You are an assistant.",
            [{"role": "user", "content": "Test"}],
            max_context_tokens=4096,
        )
        assert isinstance(sys_prompt, str)
        assert isinstance(msgs, list)

    def test_build_academic_system_prompt(self):
        from services.local_ai.utils.prompt_optimizer import build_academic_system_prompt
        p = build_academic_system_prompt("summarization")
        assert "academic" in p.lower()
        assert "summarization" in p.lower()

    def test_build_academic_system_prompt_language(self):
        from services.local_ai.utils.prompt_optimizer import build_academic_system_prompt
        p = build_academic_system_prompt("translation", language="French")
        assert "French" in p


# ── Response Cache ────────────────────────────────────────────────────────────

class TestResponseCache:
    def test_cache_miss(self):
        from services.local_ai.cache.response_cache import LocalResponseCache
        c = LocalResponseCache(ttl_seconds=60)
        assert c.get("nonexistent_key") is None

    def test_cache_set_get(self):
        from services.local_ai.cache.response_cache import LocalResponseCache
        c = LocalResponseCache(ttl_seconds=60)
        c.set("k1", "hello world")
        assert c.get("k1") == "hello world"

    def test_cache_expiry(self):
        import time
        from services.local_ai.cache.response_cache import LocalResponseCache
        c = LocalResponseCache(ttl_seconds=0.05)  # 50ms TTL
        c.set("k2", "value")
        time.sleep(0.1)
        assert c.get("k2") is None

    def test_cache_max_size_eviction(self):
        from services.local_ai.cache.response_cache import LocalResponseCache
        c = LocalResponseCache(ttl_seconds=60, max_size=3)
        c.set("a", "1")
        c.set("b", "2")
        c.set("c", "3")
        c.set("d", "4")  # evicts "a" (LRU)
        assert c.get("a") is None
        assert c.get("d") == "4"

    def test_cache_clear(self):
        from services.local_ai.cache.response_cache import LocalResponseCache
        c = LocalResponseCache(ttl_seconds=60)
        c.set("a", "1")
        c.set("b", "2")
        count = c.clear()
        assert count == 2
        assert c.get("a") is None

    def test_is_cacheable(self):
        from services.local_ai.cache.response_cache import is_cacheable
        assert is_cacheable("grammar_correction")
        assert is_cacheable("translation")
        assert not is_cacheable("research_brainstorming")
        assert not is_cacheable("local_chat")

    def test_make_cache_key_deterministic(self):
        from services.local_ai.cache.response_cache import make_cache_key
        k1 = make_cache_key("f", "system", [{"role": "user", "content": "hi"}])
        k2 = make_cache_key("f", "system", [{"role": "user", "content": "hi"}])
        assert k1 == k2

    def test_make_cache_key_different(self):
        from services.local_ai.cache.response_cache import make_cache_key
        k1 = make_cache_key("f", "system", [{"role": "user", "content": "hi"}])
        k2 = make_cache_key("f", "system", [{"role": "user", "content": "bye"}])
        assert k1 != k2

    def test_cache_stats_hit_rate(self):
        from services.local_ai.cache.response_cache import LocalResponseCache
        c = LocalResponseCache(ttl_seconds=60)
        c.set("k", "v")
        c.get("k")  # hit
        c.get("missing")  # miss
        stats = c.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_pct"] == 50.0


# ── Provider Base: family/size detection ─────────────────────────────────────

class TestProviderBase:
    def test_detect_family_llama(self):
        from services.local_ai.providers.base import detect_model_family
        assert detect_model_family("llama3.2:latest") == "llama"

    def test_detect_family_qwen(self):
        from services.local_ai.providers.base import detect_model_family
        assert detect_model_family("qwen2.5:7b") == "qwen"

    def test_detect_family_mistral(self):
        from services.local_ai.providers.base import detect_model_family
        assert detect_model_family("mistral:7b-instruct") == "mistral"

    def test_detect_family_gemma(self):
        from services.local_ai.providers.base import detect_model_family
        assert detect_model_family("gemma2:9b") == "gemma"

    def test_detect_family_deepseek(self):
        from services.local_ai.providers.base import detect_model_family
        assert detect_model_family("deepseek-r1:8b") == "deepseek"

    def test_detect_family_unknown(self):
        from services.local_ai.providers.base import detect_model_family
        assert detect_model_family("unknown-model") == "other"

    def test_detect_param_size(self):
        from services.local_ai.providers.base import detect_parameter_size
        assert detect_parameter_size("llama3.2:3b") == "3B"
        assert detect_parameter_size("qwen2.5:7b") == "7B"
        assert detect_parameter_size("llama3:70b") == "70B"

    def test_detect_param_size_float(self):
        from services.local_ai.providers.base import detect_parameter_size
        assert detect_parameter_size("phi-3.5:3.8b") == "3.8B"

    def test_detect_param_size_none(self):
        from services.local_ai.providers.base import detect_parameter_size
        assert detect_parameter_size("some-model") == ""

    def test_model_info_ram_estimate(self):
        from services.local_ai.providers.base import LocalModelInfo
        m = LocalModelInfo(
            model_id="llama3:7b", provider="ollama", display_name="llama3:7b",
            family="llama", parameter_size="7B", context_window=8192,
        )
        assert m.ram_estimate_gb == 5.0

    def test_model_info_ram_unknown(self):
        from services.local_ai.providers.base import LocalModelInfo
        m = LocalModelInfo(
            model_id="unknown", provider="ollama", display_name="unknown",
            family="other", parameter_size="", context_window=0,
        )
        assert m.ram_estimate_gb == 0.0


# ── Model Registry ────────────────────────────────────────────────────────────

class TestModelRegistry:
    def _make_model(self, model_id, provider="ollama", family="llama", param_size="7B"):
        from services.local_ai.providers.base import LocalModelInfo
        return LocalModelInfo(
            model_id=model_id, provider=provider, display_name=model_id,
            family=family, parameter_size=param_size, context_window=8192,
        )

    def test_refresh_empty(self):
        from services.local_ai.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        result = asyncio.run(reg.refresh([]))
        assert result == 0

    def test_refresh_with_mock_provider(self):
        from services.local_ai.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        provider = MagicMock()
        provider.provider_name = "ollama"
        provider.list_models = AsyncMock(return_value=[
            self._make_model("llama3:7b"),
            self._make_model("qwen2.5:3b", family="qwen", param_size="3B"),
        ])
        count = asyncio.run(reg.refresh([provider]))
        assert count == 2

    def test_get_best_model_family_preference(self):
        from services.local_ai.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        provider = MagicMock()
        provider.provider_name = "ollama"
        provider.list_models = AsyncMock(return_value=[
            self._make_model("llama3:7b", family="llama"),
            self._make_model("qwen2.5:7b", family="qwen"),
        ])
        asyncio.run(reg.refresh([provider]))
        best = reg.get_best_model(family_preference=["qwen", "llama"])
        assert best is not None
        assert best.info.family == "qwen"

    def test_enable_disable_model(self):
        from services.local_ai.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        provider = MagicMock()
        provider.provider_name = "ollama"
        provider.list_models = AsyncMock(return_value=[self._make_model("llama3:7b")])
        asyncio.run(reg.refresh([provider]))
        key = "ollama::llama3:7b"
        assert reg.disable(key) is True
        assert reg.get(key).enabled is False
        assert reg.enable(key) is True
        assert reg.get(key).enabled is True

    def test_disable_nonexistent(self):
        from services.local_ai.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        assert reg.disable("nonexistent::model") is False

    def test_list_enabled(self):
        from services.local_ai.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        provider = MagicMock()
        provider.provider_name = "ollama"
        provider.list_models = AsyncMock(return_value=[
            self._make_model("llama3:7b"),
            self._make_model("qwen2:3b", family="qwen", param_size="3B"),
        ])
        asyncio.run(reg.refresh([provider]))
        reg.disable("ollama::llama3:7b")
        enabled = reg.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].info.model_id == "qwen2:3b"

    def test_record_response_updates_latency(self):
        from services.local_ai.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        provider = MagicMock()
        provider.provider_name = "ollama"
        provider.list_models = AsyncMock(return_value=[self._make_model("llama3:7b")])
        asyncio.run(reg.refresh([provider]))
        reg.record_response("ollama::llama3:7b", 250.0)
        m = reg.get("ollama::llama3:7b")
        assert m.avg_latency_ms == pytest.approx(250.0)
        assert m.request_count == 1


# ── Local Router ──────────────────────────────────────────────────────────────

class TestLocalRouter:
    def _build_registry_with_model(self, model_id="llama3:7b", family="llama"):
        from services.local_ai.models.model_registry import ModelRegistry
        from services.local_ai.providers.base import LocalModelInfo
        reg = ModelRegistry()
        provider = MagicMock()
        provider.provider_name = "ollama"
        m = LocalModelInfo(
            model_id=model_id, provider="ollama", display_name=model_id,
            family=family, parameter_size="7B", context_window=8192,
        )
        provider.list_models = AsyncMock(return_value=[m])
        asyncio.run(reg.refresh([provider]))
        return reg, provider

    def test_select_returns_provider_and_model(self):
        from services.local_ai.router.local_router import LocalRouter
        reg, provider = self._build_registry_with_model("llama3:7b", "llama")
        router = LocalRouter()
        result = router.select(
            feature="summarization",
            context_tokens=100,
            registry=reg,
            providers={"ollama": provider},
        )
        assert result is not None
        p, model_id = result
        assert model_id == "llama3:7b"

    def test_select_empty_registry(self):
        from services.local_ai.models.model_registry import ModelRegistry
        from services.local_ai.router.local_router import LocalRouter
        router = LocalRouter()
        reg = ModelRegistry()
        result = router.select("summarization", 100, reg, {})
        assert result is None

    def test_select_preferred_model(self):
        from services.local_ai.router.local_router import LocalRouter
        reg, provider = self._build_registry_with_model("llama3:7b", "llama")
        router = LocalRouter()
        result = router.select(
            feature="summarization",
            context_tokens=100,
            registry=reg,
            providers={"ollama": provider},
            preferred_model="llama3:7b",
        )
        assert result is not None
        _, model_id = result
        assert model_id == "llama3:7b"

    def test_select_filters_by_context_window(self):
        from services.local_ai.models.model_registry import ModelRegistry
        from services.local_ai.providers.base import LocalModelInfo
        from services.local_ai.router.local_router import LocalRouter
        reg = ModelRegistry()
        provider = MagicMock()
        provider.provider_name = "ollama"
        # Small context model
        m = LocalModelInfo(
            model_id="small:7b", provider="ollama", display_name="small:7b",
            family="llama", parameter_size="7B", context_window=512,
        )
        provider.list_models = AsyncMock(return_value=[m])
        asyncio.run(reg.refresh([provider]))
        router = LocalRouter()
        result = router.select(
            feature="summarization",
            context_tokens=1024,  # exceeds model's 512 context
            registry=reg,
            providers={"ollama": provider},
        )
        assert result is None  # model doesn't have enough context


# ── Telemetry ─────────────────────────────────────────────────────────────────

class TestLocalAITelemetry:
    def setup_method(self):
        from services.local_ai.telemetry import get_telemetry
        get_telemetry().reset()

    def test_record_and_stats(self):
        from services.local_ai.telemetry import get_telemetry
        t = get_telemetry()
        t.record("summarization", "ollama", "llama3:7b", latency_ms=250,
                 input_tokens=100, output_tokens=150)
        stats = t.get_stats()
        assert stats["total_requests"] == 1
        assert stats["requests_served_locally"] == 1
        assert stats["avg_latency_ms"] == pytest.approx(250.0)

    def test_cache_hit_rate(self):
        from services.local_ai.telemetry import get_telemetry
        t = get_telemetry()
        t.record("translation", "cache", "cache", latency_ms=1, from_cache=True)
        t.record("translation", "ollama", "llama3:7b", latency_ms=300)
        stats = t.get_stats()
        assert stats["cache_hit_rate_pct"] == 50.0

    def test_fallback_tracking(self):
        from services.local_ai.telemetry import get_telemetry
        t = get_telemetry()
        t.record("local_chat", "none", "none", latency_ms=0,
                 fallback_to_cloud=True, error=True)
        stats = t.get_stats()
        assert stats["fallback_to_cloud_count"] == 1

    def test_cost_savings(self):
        from services.local_ai.telemetry import get_telemetry, _COST_PER_SAVED_CLOUD_REQUEST_USD
        t = get_telemetry()
        for _ in range(10):
            t.record("summarization", "ollama", "llama3:7b", latency_ms=200)
        stats = t.get_stats()
        assert stats["estimated_cost_saved_usd"] == pytest.approx(
            10 * _COST_PER_SAVED_CLOUD_REQUEST_USD, abs=0.001
        )

    def test_top_features(self):
        from services.local_ai.telemetry import get_telemetry
        t = get_telemetry()
        for _ in range(5):
            t.record("grammar_correction", "ollama", "llama3:7b", latency_ms=100)
        t.record("translation", "ollama", "llama3:7b", latency_ms=150)
        stats = t.get_stats()
        assert stats["top_features"][0]["feature"] == "grammar_correction"

    def test_reset(self):
        from services.local_ai.telemetry import get_telemetry
        t = get_telemetry()
        t.record("x", "y", "z", latency_ms=1)
        t.reset()
        stats = t.get_stats()
        assert stats["total_requests"] == 0

    def test_provider_breakdown(self):
        from services.local_ai.telemetry import get_telemetry
        t = get_telemetry()
        t.record("f1", "ollama", "m1", latency_ms=100)
        t.record("f2", "vllm", "m2", latency_ms=200)
        stats = t.get_stats()
        assert "ollama" in stats["provider_breakdown"]
        assert "vllm" in stats["provider_breakdown"]


# ── LocalAIEngine (mocked providers) ─────────────────────────────────────────

class TestLocalAIEngine:
    def _make_engine_with_mock_provider(self):
        """Create a LocalAIEngine with a mocked Ollama provider that always succeeds."""
        from services.local_ai.config import LocalAIConfig
        from services.local_ai.engine import LocalAIEngine
        from services.local_ai.providers.base import LocalModelInfo, LocalProviderHealth

        engine = LocalAIEngine(LocalAIConfig())

        # Mock the provider registry's discover + the ollama provider's methods
        mock_model = LocalModelInfo(
            model_id="llama3:7b", provider="ollama", display_name="llama3:7b",
            family="llama", parameter_size="7B", context_window=8192,
        )
        mock_health = LocalProviderHealth(
            provider_name="ollama", available=True, latency_ms=50, models=[mock_model]
        )
        ollama = engine._provider_registry._providers["ollama"]
        ollama.list_models = AsyncMock(return_value=[mock_model])
        ollama.health_check = AsyncMock(return_value=mock_health)
        ollama.chat = AsyncMock(return_value=("Test response from local model.", 50, 30))
        return engine

    def test_generate_success(self):
        from services.local_ai.engine import LocalGenerateRequest
        from services.local_ai.telemetry import get_telemetry
        get_telemetry().reset()

        engine = self._make_engine_with_mock_provider()

        async def _run():
            return await engine.generate(LocalGenerateRequest(
                system="You are helpful.",
                messages=[{"role": "user", "content": "Summarize this."}],
                feature="summarization",
            ))

        result = asyncio.run(_run())
        assert result.succeeded
        assert "Test response" in result.text
        assert result.provider == "ollama"
        assert result.model == "llama3:7b"
        assert result.latency_ms >= 0

    def test_generate_cache_hit(self):
        from services.local_ai.engine import LocalGenerateRequest
        engine = self._make_engine_with_mock_provider()

        req = LocalGenerateRequest(
            system="System",
            messages=[{"role": "user", "content": "Grammar check this."}],
            feature="grammar_correction",
        )

        async def _run():
            r1 = await engine.generate(req)
            r2 = await engine.generate(req)
            return r1, r2

        r1, r2 = asyncio.run(_run())
        assert r1.succeeded
        assert r2.from_cache is True
        assert r2.provider == "cache"

    def test_generate_no_models(self):
        from services.local_ai.config import LocalAIConfig
        from services.local_ai.engine import LocalAIEngine, LocalGenerateRequest
        from services.local_ai.providers.base import LocalProviderHealth

        engine = LocalAIEngine(LocalAIConfig())

        # All providers return not-available
        for p in engine._provider_registry._providers.values():
            p.health_check = AsyncMock(return_value=LocalProviderHealth(
                provider_name=p.provider_name, available=False, error="unreachable"
            ))
            p.list_models = AsyncMock(return_value=[])

        async def _run():
            with pytest.raises(Exception):
                await engine.generate(LocalGenerateRequest(
                    system="S",
                    messages=[{"role": "user", "content": "Hello"}],
                    feature="summarization",
                ))

        asyncio.run(_run())

    def test_telemetry_populated_after_generate(self):
        from services.local_ai.engine import LocalGenerateRequest
        from services.local_ai.telemetry import get_telemetry
        get_telemetry().reset()

        engine = self._make_engine_with_mock_provider()

        async def _run():
            await engine.generate(LocalGenerateRequest(
                system="S",
                messages=[{"role": "user", "content": "Hello"}],
                feature="writing_improvement",
            ))

        asyncio.run(_run())
        stats = get_telemetry().get_stats()
        assert stats["total_requests"] >= 1

    def test_batch_generate(self):
        from services.local_ai.engine import LocalGenerateRequest
        engine = self._make_engine_with_mock_provider()

        requests = [
            LocalGenerateRequest(
                system="System",
                messages=[{"role": "user", "content": f"Request {i}"}],
                feature="writing_improvement",
            )
            for i in range(3)
        ]

        async def _run():
            return await engine.generate_batch(requests)

        results = asyncio.run(_run())
        assert len(results) == 3
        assert all(r.succeeded for r in results)

    def test_health_returns_structure(self):
        engine = self._make_engine_with_mock_provider()

        async def _run():
            return await engine.health()

        h = asyncio.run(_run())
        assert "providers" in h
        assert "models" in h
        assert "system" in h
        assert "cache" in h


# ── Provider: Ollama (mocked HTTP) ────────────────────────────────────────────

class TestOllamaProvider:
    def test_list_models_parses_response(self):
        from services.local_ai.providers.ollama import OllamaProvider
        provider = OllamaProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:7b", "size": 4000000000, "details": {}},
                {"name": "qwen2.5:3b", "size": 2000000000, "details": {}},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        async def _run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client
                return await provider.list_models()

        models = asyncio.run(_run())
        assert len(models) == 2
        assert models[0].model_id == "llama3:7b"
        assert models[0].family == "llama"
        assert models[1].model_id == "qwen2.5:3b"
        assert models[1].family == "qwen"

    def test_health_check_unavailable(self):
        from services.local_ai.providers.ollama import OllamaProvider
        provider = OllamaProvider("http://unreachable:11434")

        async def _run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
                mock_client_cls.return_value = mock_client
                return await provider.health_check()

        health = asyncio.run(_run())
        assert not health.available
        assert "Connection refused" in health.error


# ── Provider Registry ─────────────────────────────────────────────────────────

class TestProviderRegistry:
    def test_build_providers(self):
        from services.local_ai.config import LocalAIConfig
        from services.local_ai.registry.provider_registry import ProviderRegistry
        reg = ProviderRegistry(LocalAIConfig())
        providers = reg.all()
        assert "ollama" in providers
        assert "vllm" in providers
        assert "lm_studio" in providers

    def test_discover_returns_empty_when_all_down(self):
        from services.local_ai.config import LocalAIConfig
        from services.local_ai.providers.base import LocalProviderHealth
        from services.local_ai.registry.provider_registry import ProviderRegistry

        reg = ProviderRegistry(LocalAIConfig())
        for p in reg._providers.values():
            p.health_check = AsyncMock(return_value=LocalProviderHealth(
                provider_name=p.provider_name, available=False, error="down"
            ))

        available = asyncio.run(reg.discover())
        assert available == []

    def test_preferred_returns_none_when_all_down(self):
        from services.local_ai.config import LocalAIConfig
        from services.local_ai.providers.base import LocalProviderHealth
        from services.local_ai.registry.provider_registry import ProviderRegistry

        reg = ProviderRegistry(LocalAIConfig())
        for p in reg._providers.values():
            p.health_check = AsyncMock(return_value=LocalProviderHealth(
                provider_name=p.provider_name, available=False, error="down"
            ))
        asyncio.run(reg.discover())
        assert reg.preferred() is None

    def test_openai_compatible_provider_created_when_url_set(self):
        from services.local_ai.config import LocalAIConfig
        from services.local_ai.providers.openai_compatible import OpenAICompatibleProvider
        from services.local_ai.registry.provider_registry import ProviderRegistry

        cfg = LocalAIConfig(openai_compatible_base_url="http://custom:5000")
        reg = ProviderRegistry(cfg)
        assert "openai_compatible" in reg.all()
        assert isinstance(reg.get("openai_compatible"), OpenAICompatibleProvider)

    def test_no_openai_compatible_when_url_empty(self):
        from services.local_ai.config import LocalAIConfig
        from services.local_ai.registry.provider_registry import ProviderRegistry

        cfg = LocalAIConfig(openai_compatible_base_url="")
        reg = ProviderRegistry(cfg)
        assert "openai_compatible" not in reg.all()


# ── AI Engine registry has LOCAL features ────────────────────────────────────

class TestRegistryLocalFeatures:
    def test_local_features_registered(self):
        from services.ai.engine.registry import list_features
        from services.ai.engine.types import ExecutionLayer

        local_features = [f for f in list_features() if f.preferred_layer == ExecutionLayer.LOCAL]
        assert len(local_features) >= 15

    def test_summarization_is_local(self):
        from services.ai.engine.registry import get_feature_meta
        from services.ai.engine.types import ExecutionLayer

        meta = get_feature_meta("summarization")
        assert meta.preferred_layer == ExecutionLayer.LOCAL
        assert not meta.requires_reasoning
        assert meta.cost_sensitivity == "high"

    def test_local_features_have_cloud_fallback(self):
        from services.ai.engine.registry import list_features
        from services.ai.engine.types import ExecutionLayer

        for f in list_features():
            if f.preferred_layer == ExecutionLayer.LOCAL:
                assert ExecutionLayer.CLOUD in f.fallback_layers, (
                    f"{f.feature_id} missing CLOUD fallback"
                )

    def test_router_sends_summarization_to_local(self):
        from services.ai.engine.config import AIEngineConfig
        from services.ai.engine.router import HybridExecutionRouter
        from services.ai.engine.types import AIRequest, ExecutionLayer

        config = AIEngineConfig(enable_local_layer=True, enable_rule_layer=True)
        router = HybridExecutionRouter()
        request = AIRequest(
            system="S",
            messages=[{"role": "user", "content": "Summarize."}],
            feature="summarization",
        )
        layer = router.route(request, config)
        assert layer == ExecutionLayer.LOCAL

    def test_router_sends_research_gap_to_cloud(self):
        from services.ai.engine.config import AIEngineConfig
        from services.ai.engine.router import HybridExecutionRouter
        from services.ai.engine.types import AIRequest, ExecutionLayer

        config = AIEngineConfig(enable_local_layer=True, enable_rule_layer=True)
        router = HybridExecutionRouter()
        request = AIRequest(
            system="S",
            messages=[{"role": "user", "content": "Find gaps."}],
            feature="research_gap_finder",
        )
        layer = router.route(request, config)
        assert layer == ExecutionLayer.CLOUD

    def test_router_local_disabled_sends_to_cloud(self):
        from services.ai.engine.config import AIEngineConfig
        from services.ai.engine.router import HybridExecutionRouter
        from services.ai.engine.types import AIRequest, ExecutionLayer

        config = AIEngineConfig(enable_local_layer=False, enable_rule_layer=True)
        router = HybridExecutionRouter()
        request = AIRequest(
            system="S",
            messages=[{"role": "user", "content": "Summarize."}],
            feature="summarization",
        )
        layer = router.route(request, config)
        assert layer == ExecutionLayer.CLOUD


# ── Embedding service (mocked HTTP) ──────────────────────────────────────────

class TestEmbeddingService:
    def test_cosine_similarity_identical(self):
        from services.local_ai.embeddings.embedding_service import _cosine
        v = [1.0, 0.0, 0.0]
        assert _cosine(v, v) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        from services.local_ai.embeddings.embedding_service import _cosine
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert _cosine(a, b) == pytest.approx(0.0)

    def test_cosine_empty(self):
        from services.local_ai.embeddings.embedding_service import _cosine
        assert _cosine([], []) == 0.0

    def test_embed_single_mocked(self):
        from services.local_ai.embeddings.embedding_service import LocalEmbeddingService

        service = LocalEmbeddingService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_response.raise_for_status = MagicMock()

        async def _run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client
                return await service.embed_single("test text")

        vec = asyncio.run(_run())
        assert vec == pytest.approx([0.1, 0.2, 0.3])
