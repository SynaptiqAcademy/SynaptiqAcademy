"""AI Engine configuration — fully driven by environment variables.

Every tunable is exposed here and nowhere else. No AI code should call
os.environ directly; instead it reads from an AIEngineConfig instance
obtained via load_config().
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    name: str
    enabled: bool = True
    api_key: str = ""
    base_url: str | None = None
    default_model: str = ""
    fallback_models: list[str] = field(default_factory=list)
    timeout_seconds: float = 60.0
    max_retries: int = 2


@dataclass
class BudgetConfig:
    """Spending guards. 0.0 = unlimited for that window."""

    daily_limit_usd: float = 0.0
    monthly_limit_usd: float = 0.0
    hourly_limit_usd: float = 0.0

    @classmethod
    def from_env(cls) -> "BudgetConfig":
        return cls(
            daily_limit_usd=float(os.environ.get("AI_DAILY_BUDGET_USD", "0") or "0"),
            monthly_limit_usd=float(os.environ.get("AI_MONTHLY_BUDGET_USD", "0") or "0"),
            hourly_limit_usd=float(os.environ.get("AI_HOURLY_BUDGET_USD", "0") or "0"),
        )


@dataclass
class CacheConfig:
    enabled: bool = False
    ttl_seconds: int = 3600

    @classmethod
    def from_env(cls) -> "CacheConfig":
        return cls(
            enabled=os.environ.get("AI_CACHE_ENABLED", "0") == "1",
            ttl_seconds=int(os.environ.get("AI_CACHE_TTL_SECONDS", "3600") or "3600"),
        )


@dataclass
class AIEngineConfig:
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    preferred_cloud_provider: str = "anthropic"
    fallback_cloud_providers: list[str] = field(default_factory=list)
    enable_local_layer: bool = False
    enable_rule_layer: bool = True
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)

    @classmethod
    def from_env(cls) -> "AIEngineConfig":
        preferred = os.environ.get("AI_MATCHING_PROVIDER", "anthropic")
        fallback = ["openai"] if preferred == "anthropic" else ["anthropic"]

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        local_enabled = os.environ.get("AI_LOCAL_ENABLED", "0") == "1"

        providers: dict[str, ProviderConfig] = {
            "anthropic": ProviderConfig(
                name="anthropic",
                enabled=bool(anthropic_key),
                api_key=anthropic_key,
                default_model=os.environ.get("AI_MATCHING_MODEL", "claude-sonnet-4-6"),
                fallback_models=["claude-haiku-4-5-20251001"],
                timeout_seconds=float(os.environ.get("AI_ANTHROPIC_TIMEOUT", "60") or "60"),
                max_retries=int(os.environ.get("AI_ANTHROPIC_RETRIES", "2") or "2"),
            ),
            "openai": ProviderConfig(
                name="openai",
                enabled=bool(openai_key),
                api_key=openai_key,
                default_model=os.environ.get("AI_OPENAI_MODEL", "gpt-4o-mini"),
                fallback_models=["gpt-3.5-turbo"],
                timeout_seconds=float(os.environ.get("AI_OPENAI_TIMEOUT", "60") or "60"),
                max_retries=int(os.environ.get("AI_OPENAI_RETRIES", "2") or "2"),
            ),
            "local": ProviderConfig(
                name="local",
                enabled=local_enabled,
                base_url=os.environ.get("AI_LOCAL_URL", "http://localhost:11434"),
                default_model=os.environ.get("AI_LOCAL_MODEL", "llama3.2"),
                timeout_seconds=float(os.environ.get("AI_LOCAL_TIMEOUT", "120") or "120"),
                max_retries=1,
            ),
            "mock": ProviderConfig(
                name="mock",
                enabled=True,
                default_model="mock-v1",
            ),
        }

        return cls(
            providers=providers,
            preferred_cloud_provider=preferred,
            fallback_cloud_providers=fallback,
            enable_local_layer=local_enabled,
            enable_rule_layer=os.environ.get("AI_RULE_LAYER_ENABLED", "1") == "1",
            budget=BudgetConfig.from_env(),
            cache=CacheConfig.from_env(),
        )


_config: AIEngineConfig | None = None


def load_config() -> AIEngineConfig:
    """Return the process-level AI engine config, built once from env vars."""
    global _config
    if _config is None:
        _config = AIEngineConfig.from_env()
    return _config


def reload_config() -> AIEngineConfig:
    """Force a fresh config read from env vars (useful after tests patch env)."""
    global _config
    _config = AIEngineConfig.from_env()
    return _config
