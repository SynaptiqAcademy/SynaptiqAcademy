"""Structured AI request logger.

Every AI request is logged in two channels:
  1. Python structured logger — synchronous, zero latency impact, always works.
  2. MongoDB ai_requests collection — async fire-and-forget, does not block the
     caller. Failures are silently swallowed to ensure logging never crashes a request.

The MongoDB record powers the admin AI center dashboard and cost analytics.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from services.ai.engine.types import AIRequest, AIResponse
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.ai.request_logger")


class AIRequestLogger:
    """Dual-channel logger: structured Python log + async MongoDB write."""

    async def log(self, request: AIRequest, response: AIResponse) -> None:
        self._log_structured(request, response)
        # Capture the billing attribution now (request context), persist later.
        try:
            from services.credits_service import current_reservation
            billing = dict(current_reservation() or {})
        except Exception:
            billing = {}
        asyncio.create_task(self._persist(request, response, billing))

    def _log_structured(self, request: AIRequest, response: AIResponse) -> None:
        logger.info(
            "AI_REQUEST "
            "feature=%s layer=%s provider=%s model=%s "
            "input_tokens=%d output_tokens=%d latency_ms=%d "
            "cost_usd=%.6f cache=%s fallback=%s user=%s",
            request.feature,
            response.layer.value,
            response.provider,
            response.model,
            response.input_tokens,
            response.output_tokens,
            response.latency_ms,
            response.cost_usd,
            response.from_cache,
            response.fallback_reason or "-",
            request.user_id or "-",
        )

    async def _persist(self, request: AIRequest, response: AIResponse, billing: dict | None = None) -> None:
        try:
            from obs.metrics import get_metrics, M_AI_REQUESTS, M_AI_LATENCY, M_AI_TOKENS_IN, M_AI_TOKENS_OUT, M_AI_COST
            m = get_metrics()
            tags = {"provider": response.provider or "unknown", "feature": request.feature or "unknown"}
            m.inc(M_AI_REQUESTS, tags=tags)
            m.observe(M_AI_LATENCY, float(response.latency_ms), tags=tags)
            m.inc(M_AI_TOKENS_IN, float(response.input_tokens), tags=tags)
            m.inc(M_AI_TOKENS_OUT, float(response.output_tokens), tags=tags)
            m.observe(M_AI_COST, response.cost_usd, tags=tags)
        except Exception:
            pass

        try:
            from db import get_db
            db = get_db()
            db = DBProxy(db, SecurityContext.system())

            billing = billing or {}
            failed = response.provider in ("error_fallback", "budget_manager", "emergency_fallback")
            await db.ai_requests.insert_one(
                {
                    # Per-request cost telemetry (internal only — never
                    # returned to ordinary users).
                    "user_id": billing.get("user_id") or request.user_id,
                    "plan_code": billing.get("plan_code"),
                    "operation": billing.get("operation"),
                    "action": billing.get("action"),
                    "reservation_id": billing.get("id"),
                    "credits_charged": billing.get("credits", 0),
                    "billed": bool(billing),
                    "status": "failed" if failed else "succeeded",
                    "cache_read_tokens": getattr(response, "cache_read_tokens", 0),
                    "cache_write_tokens": getattr(response, "cache_write_tokens", 0),
                    "feature": request.feature,
                    "layer": response.layer.value,
                    "provider": response.provider,
                    "model": response.model,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "latency_ms": response.latency_ms,
                    "cost_usd": response.cost_usd,
                    "from_cache": response.from_cache,
                    "fallback_reason": response.fallback_reason,
                    "workspace_id": request.workspace_id,
                    "subscription_tier": request.subscription_tier,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as exc:
            logger.warning("AI request log persistence failed: %s", exc)
