"""
Enterprise AI Gateway — Observability Layer.

Every gateway request is logged with:
  - request_id (UUID, traceable end-to-end)
  - feature / plugin / prompt_id
  - user_id, mission_id, workspace_id
  - provider, model, tokens, latency, cost
  - validation status and any warnings
  - success/failure and fallback details

Dual channel (matching pattern from services/ai/request_logger.py):
  1. Python structured logger — synchronous, zero latency impact
  2. MongoDB gateway_logs — async fire-and-forget

The gateway_logs collection powers a unified AI observability dashboard
and is the single source of cross-feature analytics.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from .schemas import GatewayRequest, GatewayResponse

logger = logging.getLogger("gateway.observability")


class GatewayObservability:

    async def log(self, request: GatewayRequest, response: GatewayResponse, db) -> None:
        self._log_structured(request, response)
        self._emit_metrics(request, response)
        if db is not None:
            asyncio.create_task(self._persist(request, response, db))

    def _emit_metrics(self, request: GatewayRequest, response: GatewayResponse) -> None:
        """Route gateway telemetry to the Enterprise Observability Platform."""
        try:
            from obs.metrics import (
                get_metrics,
                M_AI_REQUESTS, M_AI_LATENCY,
                M_AI_TOKENS_IN, M_AI_TOKENS_OUT,
                M_AI_COST, M_AI_CACHE_HITS,
            )
            m = get_metrics()
            tags = {
                "provider": response.provider or "unknown",
                "feature":  response.feature  or "unknown",
            }
            m.inc(M_AI_REQUESTS, tags=tags)
            m.observe(M_AI_LATENCY, float(response.latency_ms), tags={"provider": response.provider or "unknown"})
            if response.tokens_in:
                m.inc(M_AI_TOKENS_IN,  float(response.tokens_in),  tags={"provider": response.provider or "unknown"})
            if response.tokens_out:
                m.inc(M_AI_TOKENS_OUT, float(response.tokens_out), tags={"provider": response.provider or "unknown"})
            if response.cost_usd:
                m.inc(M_AI_COST, response.cost_usd, tags={"provider": response.provider or "unknown"})
            if response.from_cache:
                m.inc(M_AI_CACHE_HITS, tags={"provider": response.provider or "unknown"})
        except Exception:
            pass  # telemetry must never crash the gateway

    def _log_structured(self, request: GatewayRequest, response: GatewayResponse) -> None:
        logger.info(
            "GATEWAY_REQUEST "
            "id=%s feature=%s plugin=%s prompt=%s "
            "provider=%s model=%s "
            "tokens_in=%d tokens_out=%d latency_ms=%d "
            "cost_credits=%.4f cost_usd=%.6f "
            "validation=%s cache=%s fallback=%s "
            "user=%s mission=%s workspace=%s",
            response.request_id,
            response.feature,
            response.plugin_name or "-",
            request.prompt_id or "-",
            response.provider,
            response.model,
            response.tokens_in,
            response.tokens_out,
            response.latency_ms,
            response.cost_credits,
            response.cost_usd,
            response.validation_status,
            response.from_cache,
            response.fallback_reason or "-",
            request.user_id or "-",
            request.mission_id or "-",
            request.workspace_id or "-",
        )

    async def _persist(
        self, request: GatewayRequest, response: GatewayResponse, db
    ) -> None:
        try:
            await db["gateway_logs"].insert_one({
                "request_id":        response.request_id,
                "feature":           response.feature,
                "plugin_name":       response.plugin_name,
                "prompt_id":         request.prompt_id,
                "user_id":           request.user_id,
                "mission_id":        request.mission_id,
                "workspace_id":      request.workspace_id,
                "institution_id":    request.institution_id,
                "provider":          response.provider,
                "model":             response.model,
                "tokens_in":         response.tokens_in,
                "tokens_out":        response.tokens_out,
                "latency_ms":        response.latency_ms,
                "cost_credits":      response.cost_credits,
                "cost_usd":          response.cost_usd,
                "from_cache":        response.from_cache,
                "fallback_reason":   response.fallback_reason,
                "validation_status": response.validation_status,
                "validation_warnings": response.validation.warnings,
                "fabrication_flags": response.validation.fabrication_flags,
                "confidence":        response.confidence,
                "warnings":          response.warnings,
                "timestamp":         datetime.now(timezone.utc),
            })
        except Exception as exc:
            logger.warning("GatewayObservability._persist failed (non-blocking): %s", exc)

        # Also record in Enterprise Cost Tracker
        try:
            from obs.cost import get_cost_tracker
            tracker = get_cost_tracker()
            if tracker:
                await tracker.record(
                    cost_usd=response.cost_usd,
                    provider=response.provider,
                    model=response.model,
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    user_id=request.user_id,
                    mission_id=request.mission_id,
                    workspace_id=request.workspace_id,
                    institution=request.institution_id,
                    operation=f"gateway.{response.feature or 'unknown'}",
                )
        except Exception:
            pass
