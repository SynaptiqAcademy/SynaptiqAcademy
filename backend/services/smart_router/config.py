"""SmartRouterConfig — all settings from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ProviderCostConfig:
    """Cost per million tokens (USD)."""
    name: str
    input_per_m: float
    output_per_m: float

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens / 1_000_000 * self.input_per_m
                + output_tokens / 1_000_000 * self.output_per_m)


# Current provider cost tables (2025 pricing)
PROVIDER_COSTS: dict[str, ProviderCostConfig] = {
    "claude-sonnet-4-6":           ProviderCostConfig("claude-sonnet-4-6",          3.00, 15.00),
    "claude-haiku-4-5-20251001":   ProviderCostConfig("claude-haiku-4-5-20251001",  0.80,  4.00),
    "claude-opus-4-8":             ProviderCostConfig("claude-opus-4-8",            15.00, 75.00),
    "gpt-4o":                      ProviderCostConfig("gpt-4o",                      2.50, 10.00),
    "gpt-4o-mini":                 ProviderCostConfig("gpt-4o-mini",                 0.15,  0.60),
    "anthropic":                   ProviderCostConfig("anthropic",                   3.00, 15.00),
    "openai":                      ProviderCostConfig("openai",                      2.50, 10.00),
    "local":                       ProviderCostConfig("local",                       0.00,  0.00),
    "rule_engine":                 ProviderCostConfig("rule_engine",                 0.00,  0.00),
}

# Default output token estimates per feature complexity
OUTPUT_TOKEN_ESTIMATES: dict[str, int] = {
    "title_generation": 60,
    "subtitle_generation": 60,
    "email_drafting": 200,
    "bullet_points": 250,
    "keyword_extraction": 100,
    "grammar_correction": 500,
    "translation": 600,
    "paraphrasing": 500,
    "academic_tone": 600,
    "outline_generation": 400,
    "plain_language_explanation": 400,
    "teaching_simplification": 500,
    "teaching_explanation": 600,
    "local_chat": 400,
    "summarization": 600,
    "academic_proofreading": 800,
    "writing_improvement": 800,
    "abstract_generator": 600,
    "research_brainstorming": 800,
    "teaching_assistant": 600,
    "ai_rewriting": 800,
    "research_design_advisor": 1200,
    "grant_gap_detection": 1200,
    "teaching_assessment_generation": 1500,
    "teaching_lesson_generation": 2000,
    "ai_assistant": 1000,
    "ai_chat": 1200,
    "journal_matching": 800,
    "conference_matching": 800,
    "grant_matching": 800,
    "reviewer_matching": 800,
    "marketplace_matching": 800,
    "recommendation_engine": 1000,
    "admin_copilot": 400,
    "statistical_review": 2000,
    "manuscript_review": 2500,
    "collaboration_intelligence": 2500,
    "research_design_advisor": 1500,
    "research_gap_finder": 3000,
    "literature_review": 3500,
    "general": 800,
    # Rule engine — no output tokens
    "profile_completion": 0,
    "reference_validation": 0,
    "alert_generation": 0,
    "citation_metrics": 0,
    "research_stats": 0,
    "profile_report": 0,
}


@dataclass
class SmartRouterConfig:
    # ── Enable / disable ─────────────────────────────────────────────────────
    enabled: bool = True

    # ── Cloud provider selection ───────────────────────────────────────────────
    preferred_cloud_provider: str = "anthropic"
    cloud_provider_fallbacks: list = field(default_factory=lambda: ["anthropic", "openai"])

    # ── Budget limits (USD) ───────────────────────────────────────────────────
    daily_budget_usd: float = 50.0
    weekly_budget_usd: float = 300.0
    monthly_budget_usd: float = 1000.0
    per_request_max_usd: float = 0.50

    # ── Budget alert thresholds (%) ───────────────────────────────────────────
    budget_alert_pct: float = 80.0       # log warning
    budget_throttle_pct: float = 90.0    # downgrade to LOCAL
    budget_reject_pct: float = 98.0      # reject cloud requests

    # ── Queue settings ────────────────────────────────────────────────────────
    max_queue_size: int = 1000
    max_queue_wait_ms: int = 10000       # 10s
    worker_concurrency: int = 50
    request_timeout_ms: int = 120000     # 2 min

    # ── Retry ─────────────────────────────────────────────────────────────────
    max_retries: int = 2
    retry_delay_ms: int = 500

    # ── Cache TTLs ─────────────────────────────────────────────────────────────
    decision_cache_ttl_s: float = 300.0   # 5 min
    output_cache_ttl_s: float = 3600.0    # 1 hr
    template_cache_ttl_s: float = 86400.0  # 24 hr

    # ── Load balancing ────────────────────────────────────────────────────────
    max_concurrent_per_provider: int = 20
    provider_timeout_ms: int = 30000

    # ── Context size thresholds (tokens) for complexity bump ──────────────────
    large_context_threshold: int = 2000
    very_large_context_threshold: int = 6000
    message_depth_threshold: int = 5      # messages before +1 complexity

    # ── Observability ─────────────────────────────────────────────────────────
    audit_enabled: bool = True
    audit_log_retention_days: int = 30

    @classmethod
    def from_env(cls) -> "SmartRouterConfig":
        def _f(k: str, default: float) -> float:
            return float(os.environ.get(k, str(default)) or str(default))
        def _i(k: str, default: int) -> int:
            return int(os.environ.get(k, str(default)) or str(default))
        def _b(k: str, default: bool) -> bool:
            return os.environ.get(k, "1" if default else "0") == "1"
        return cls(
            enabled=_b("SMART_ROUTER_ENABLED", True),
            preferred_cloud_provider=os.environ.get("SMART_ROUTER_PREFERRED_PROVIDER", "anthropic"),
            daily_budget_usd=_f("SMART_ROUTER_DAILY_BUDGET_USD", 50.0),
            weekly_budget_usd=_f("SMART_ROUTER_WEEKLY_BUDGET_USD", 300.0),
            monthly_budget_usd=_f("SMART_ROUTER_MONTHLY_BUDGET_USD", 1000.0),
            per_request_max_usd=_f("SMART_ROUTER_PER_REQUEST_MAX_USD", 0.50),
            budget_alert_pct=_f("SMART_ROUTER_BUDGET_ALERT_PCT", 80.0),
            budget_throttle_pct=_f("SMART_ROUTER_BUDGET_THROTTLE_PCT", 90.0),
            budget_reject_pct=_f("SMART_ROUTER_BUDGET_REJECT_PCT", 98.0),
            max_queue_size=_i("SMART_ROUTER_MAX_QUEUE_SIZE", 1000),
            max_queue_wait_ms=_i("SMART_ROUTER_MAX_QUEUE_WAIT_MS", 10000),
            worker_concurrency=_i("SMART_ROUTER_CONCURRENCY", 50),
            max_retries=_i("SMART_ROUTER_MAX_RETRIES", 2),
            audit_enabled=_b("SMART_ROUTER_AUDIT_LOG", True),
        )


_config: SmartRouterConfig | None = None


def load_router_config() -> SmartRouterConfig:
    global _config
    if _config is None:
        _config = SmartRouterConfig.from_env()
    return _config


def reload_router_config() -> SmartRouterConfig:
    global _config
    _config = SmartRouterConfig.from_env()
    return _config
