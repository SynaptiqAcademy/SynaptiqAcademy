"""Core data-transfer objects shared across every AI execution layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExecutionLayer(str, Enum):
    RULE = "rule"
    LOCAL = "local"
    CLOUD = "cloud"


class ProviderName(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"
    MOCK = "mock"


@dataclass
class AIRequest:
    """Normalised input to every AI execution path."""

    system: str
    messages: list[dict]
    feature: str = "general"
    max_tokens: int = 2048
    provider: str | None = None
    model: str | None = None
    user_id: str | None = None
    workspace_id: str | None = None
    subscription_tier: str | None = None


@dataclass
class AIResponse:
    """Normalised output from every AI execution path."""

    text: str
    layer: ExecutionLayer
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    from_cache: bool = False
    fallback_reason: str | None = None
    cost_usd: float = 0.0


@dataclass
class ProviderHealth:
    name: str
    available: bool
    latency_ms: int | None = None
    error: str | None = None
    models: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "available": self.available,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "models": self.models,
        }


@dataclass
class AISystemHealth:
    """Aggregate health snapshot returned by the health endpoint."""

    status: str
    providers: list[ProviderHealth] = field(default_factory=list)
    active_layer: str = "cloud"
    cache_enabled: bool = False
    rule_layer_enabled: bool = True
    local_layer_enabled: bool = False
    budget_remaining_day_usd: float | None = None
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "providers": [p.to_dict() for p in self.providers],
            "active_layer": self.active_layer,
            "cache_enabled": self.cache_enabled,
            "rule_layer_enabled": self.rule_layer_enabled,
            "local_layer_enabled": self.local_layer_enabled,
            "budget_remaining_day_usd": self.budget_remaining_day_usd,
            "timestamp": self.timestamp,
        }
