"""Core data types for the Smart Execution Router."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComplexityLevel(int, Enum):
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5

    def label(self) -> str:
        return self.name.replace("_", " ").title()


class RouterSignal(str, Enum):
    PROCEED = "proceed"
    DOWNGRADE = "downgrade"   # move to cheaper layer
    THROTTLE = "throttle"     # add delay / queue
    REJECT = "reject"         # budget exhausted


class ProviderAvailability(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class TokenEstimate:
    input_tokens: int = 0
    context_tokens: int = 0         # RAG context tokens
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    provider: str = ""
    model: str = ""

    def __post_init__(self) -> None:
        if not self.total_tokens:
            self.total_tokens = self.input_tokens + self.context_tokens + self.output_tokens


@dataclass
class BudgetStatus:
    signal: RouterSignal = RouterSignal.PROCEED
    daily_used_usd: float = 0.0
    daily_limit_usd: float = 0.0
    monthly_used_usd: float = 0.0
    monthly_limit_usd: float = 0.0
    remaining_daily_usd: float = 0.0
    remaining_monthly_usd: float = 0.0
    utilization_pct: float = 0.0
    recommended_layer: str | None = None   # if downgrade suggested


@dataclass
class RoutingDecision:
    request_id: str
    feature: str
    complexity: ComplexityLevel
    selected_layer: str             # "rule" | "local" | "cloud"
    selected_provider: str | None
    selected_model: str | None
    token_estimate: TokenEstimate
    routing_reason: str
    fallback_chain: list[str]
    budget_signal: RouterSignal
    priority_score: int             # 1 (highest) – 100 (lowest)
    from_cache: bool = False
    queue_time_ms: int = 0
    decision_latency_ms: int = 0
    user_id: str = ""
    workspace_id: str | None = None


@dataclass
class ExecutionRecord:
    """Filled in after execution completes."""
    routing_decision: RoutingDecision
    actual_layer: str
    actual_provider: str
    actual_model: str
    actual_input_tokens: int = 0
    actual_output_tokens: int = 0
    actual_cost_usd: float = 0.0
    latency_ms: int = 0
    fallback_used: bool = False
    fallback_reason: str = ""
    from_cache: bool = False
    error: str = ""


@dataclass
class ProviderLoad:
    provider: str
    concurrent_requests: int = 0
    queue_depth: int = 0
    availability: ProviderAvailability = ProviderAvailability.AVAILABLE
    avg_latency_ms: float = 0.0


@dataclass
class SimulationResult:
    n_users: int
    duration_minutes: int
    estimated_requests: int
    layer_distribution: dict[str, int]          # layer → count
    estimated_cloud_cost_usd: float
    estimated_savings_vs_cloud_usd: float
    estimated_gpu_hours: float
    estimated_local_requests: int
    estimated_rule_requests: int
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    recommended_gpu_count: int
    recommended_local_model_replicas: int
    cost_breakdown: dict[str, float]
    warnings: list[str] = field(default_factory=list)
