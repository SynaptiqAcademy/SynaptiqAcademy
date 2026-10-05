"""AI provider pricing, cost-aware model routing and cost guards — one module.

Replaces three hardcoded, mutually inconsistent price tables (Anthropic
provider, gateway cost ledger, smart-router config). Everything here is
overridable from the environment without a code change:

  AI_PROVIDER_PRICING_JSON  '{"claude-sonnet-4-6": {"input": 3, "output": 15,
                               "cache_read": 0.3, "cache_write": 3.75}}'
                             USD per 1M tokens; merged over the defaults.
  AI_MODEL_SIMPLE           model for simple operations (default: Haiku 4.5)
  AI_MODEL_STANDARD         model for standard operations (default: feature default)
  AI_MODEL_ADVANCED         model for advanced operations (default: feature default)
  AI_COST_GUARDS_JSON       overrides for COST_GUARDS below (per tier).

The default prices are list prices as understood when this was written and
MUST be verified against Anthropic's current pricing page before relying on
cost reports — set AI_PROVIDER_PRICING_JSON in production.
Internal cost data is never exposed to ordinary users.
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger("synaptiq.ai.pricing")

# USD per 1M tokens.
_DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5":  {"input": 1.00, "output": 5.00,  "cache_read": 0.10, "cache_write": 1.25},
    "claude-sonnet-4":   {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4":     {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_write": 18.75},
    "gpt-4o-mini":       {"input": 0.15, "output": 0.60,  "cache_read": 0.075, "cache_write": 0.15},
    "gpt-4o":            {"input": 2.50, "output": 10.00, "cache_read": 1.25, "cache_write": 2.50},
    "o1-mini":           {"input": 3.00, "output": 12.00, "cache_read": 1.50, "cache_write": 3.00},
    "o1":                {"input": 15.00, "output": 60.00, "cache_read": 7.50, "cache_write": 15.00},
    "local":             {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0},
    "mock":              {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0},
    "rule_engine":       {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0},
    "none":              {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0},
}
# Unknown model: assume a Sonnet-class price so costs are never under-reported.
_FALLBACK = {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75}


def _load_pricing() -> dict[str, dict[str, float]]:
    table = {k: dict(v) for k, v in _DEFAULT_PRICING.items()}
    raw = os.environ.get("AI_PROVIDER_PRICING_JSON", "").strip()
    if raw:
        try:
            for model, rates in json.loads(raw).items():
                base = dict(table.get(model, _FALLBACK))
                base.update({k: float(v) for k, v in rates.items()
                             if k in ("input", "output", "cache_read", "cache_write")})
                table[model] = base
        except (ValueError, TypeError, AttributeError) as exc:
            logger.error("AI_PROVIDER_PRICING_JSON invalid (%s) — using defaults", exc)
    return table


PRICING = _load_pricing()


def rates_for(model: str) -> dict[str, float]:
    """Longest-prefix match so dated ids (claude-haiku-4-5-20251001) resolve."""
    model = model or ""
    best = None
    for prefix in PRICING:
        if model.startswith(prefix) and (best is None or len(prefix) > len(best)):
            best = prefix
    return PRICING[best] if best else _FALLBACK


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int,
                      cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> float:
    """Provider cost. `input_tokens` excludes cached tokens (Anthropic usage
    reports cache reads/writes separately)."""
    r = rates_for(model)
    cost = (
        (input_tokens or 0) * r["input"]
        + (output_tokens or 0) * r["output"]
        + (cache_read_tokens or 0) * r["cache_read"]
        + (cache_write_tokens or 0) * r["cache_write"]
    ) / 1_000_000
    return round(cost, 8)


# ───────────────────────── model routing ─────────────────────────

def model_for_tier(model_tier: str | None) -> str | None:
    """Model for an operation's tier, or None to keep the feature default."""
    if model_tier == "simple":
        return os.environ.get("AI_MODEL_SIMPLE", "claude-haiku-4-5-20251001") or None
    if model_tier == "standard":
        return os.environ.get("AI_MODEL_STANDARD") or None
    if model_tier == "advanced":
        return os.environ.get("AI_MODEL_ADVANCED") or None
    return None


# ───────────────────────── cost guards ─────────────────────────

# Credits are the economic control; these are runaway/abuse backstops.
# Token limits are per provider call; cost limits in USD.
_DEFAULT_GUARDS: dict[str, dict[str, float]] = {
    "PRO": {
        "max_input_tokens": 60_000,
        "max_output_tokens": 4_096,
        "max_cost_per_request_usd": 0.75,
        "daily_cost_limit_usd": 3.00,
        "monthly_cost_limit_usd": 15.00,
    },
    "PRO_ADVANCED": {
        "max_input_tokens": 150_000,     # extended context
        "max_output_tokens": 8_192,
        "max_cost_per_request_usd": 2.00,
        "daily_cost_limit_usd": 8.00,
        "monthly_cost_limit_usd": 45.00,
    },
}
# Requests with no paying user attached (system jobs, internal tools).
_DEFAULT_GUARDS["SYSTEM"] = dict(_DEFAULT_GUARDS["PRO_ADVANCED"])


def _load_guards() -> dict[str, dict[str, float]]:
    guards = {k: dict(v) for k, v in _DEFAULT_GUARDS.items()}
    raw = os.environ.get("AI_COST_GUARDS_JSON", "").strip()
    if raw:
        try:
            for tier, vals in json.loads(raw).items():
                if tier in guards:
                    guards[tier].update({k: float(v) for k, v in vals.items() if k in guards[tier]})
        except (ValueError, TypeError, AttributeError) as exc:
            logger.error("AI_COST_GUARDS_JSON invalid (%s) — using defaults", exc)
    return guards


COST_GUARDS = _load_guards()


def guards_for(tier: str | None) -> dict[str, float]:
    return COST_GUARDS.get(tier or "SYSTEM", COST_GUARDS["SYSTEM"])


def estimate_tokens(text: str) -> int:
    """Conservative ~4 chars/token estimate (no tokenizer dependency)."""
    return (len(text or "") + 3) // 4
