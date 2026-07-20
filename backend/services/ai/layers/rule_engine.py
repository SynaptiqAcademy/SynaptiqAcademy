"""Layer 1 — Rule-Based Intelligence.

Pure Python. No LLM. No network calls. No token usage.

Routes `call_llm(feature=...)` calls to the Rule Engine subsystem
(`services/rule_engine/`) when the feature can be handled deterministically.
Falls back to a structured placeholder for features that still require AI.
"""
from __future__ import annotations

import logging
import time

from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer

logger = logging.getLogger("synaptiq.ai.layers.rule_engine")

# Features that the Rule Engine can handle — mapped to the engine feature key
# and the data extraction function (takes AIRequest, returns dict for engine)
_RULE_FEATURES: dict[str, str] = {
    "profile_completion":    "profile_score",
    "keyword_extraction":    "extract_keywords",
    "reference_validation":  "validate_manuscript",
    "alert_generation":      "generate_alerts",
    "profile_report":        "profile_report",
    "citation_metrics":      "citation_analytics",
    "research_stats":        "statistics",
}

_FALLBACK_RESPONSE = (
    "**Synaptiq AI** — Service Temporarily Unavailable\n\n"
    "The AI service is currently unavailable. Your request has been received. "
    "Please try again in a few moments or contact support at admin@synaptiq.academy."
)


class RuleEngineLayer:
    """Handles AI requests using deterministic Python logic (zero LLM cost)."""

    async def generate(self, request: AIRequest) -> AIResponse:
        start = time.monotonic()
        text = self._resolve(request)
        latency_ms = int((time.monotonic() - start) * 1000)

        return AIResponse(
            text=text,
            layer=ExecutionLayer.RULE,
            provider="rule_engine",
            model="deterministic-v1",
            input_tokens=0,
            output_tokens=len(text) // 4,
            latency_ms=latency_ms,
            cost_usd=0.0,
        )

    def _resolve(self, request: AIRequest) -> str:
        engine_feature = _RULE_FEATURES.get(request.feature)
        if engine_feature:
            try:
                from services.rule_engine.engine import get_rule_engine
                data = _extract_data(request)
                engine = get_rule_engine()
                return engine.execute_text(engine_feature, data)
            except Exception as exc:
                logger.warning(
                    "rule_engine_layer feature=%s engine_error=%s — using fallback",
                    request.feature, exc,
                )

        return _FALLBACK_RESPONSE


def _extract_data(request: AIRequest) -> dict:
    """Extract structured data from an AIRequest for rule engine consumption.

    The user message is JSON when callers pass structured data; otherwise
    we return a minimal dict so handlers can gracefully degrade.
    """
    import json
    last_msg = ""
    for msg in reversed(request.messages or []):
        if msg.get("role") == "user":
            last_msg = msg.get("content") or ""
            break
    try:
        data = json.loads(last_msg)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return {"text": last_msg, "feature": request.feature}
