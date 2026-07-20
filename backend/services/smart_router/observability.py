"""RouterObservability — structured audit logging for every routing decision."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from services.smart_router.types import ExecutionRecord, RoutingDecision

logger = logging.getLogger("synaptiq.smart_router")

_COLL = "smart_router_audit"
_MAX_RETENTION_DAYS = 30


class RouterObservability:
    def __init__(self, db: Any, audit_enabled: bool = True) -> None:
        self._db = db
        self._audit_enabled = audit_enabled

    async def log_decision(self, decision: RoutingDecision, request_text: str = "") -> None:
        """Structured log entry for every routing decision."""
        entry = {
            "event": "routing_decision",
            "request_id": decision.request_id,
            "feature": decision.feature,
            "complexity": decision.complexity.name,
            "selected_layer": decision.selected_layer,
            "selected_provider": decision.selected_provider,
            "selected_model": decision.selected_model,
            "routing_reason": decision.routing_reason,
            "fallback_chain": decision.fallback_chain,
            "budget_signal": decision.budget_signal.value,
            "priority_score": decision.priority_score,
            "estimated_cost_usd": decision.token_estimate.estimated_cost_usd,
            "estimated_input_tokens": decision.token_estimate.input_tokens,
            "estimated_output_tokens": decision.token_estimate.output_tokens,
            "from_cache": decision.from_cache,
            "decision_latency_ms": decision.decision_latency_ms,
            "user_id": decision.user_id,
            "workspace_id": decision.workspace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "ROUTE feature=%s layer=%s provider=%s cost=%.4f reason=%s",
            decision.feature,
            decision.selected_layer,
            decision.selected_provider,
            decision.token_estimate.estimated_cost_usd,
            decision.routing_reason,
        )
        if self._audit_enabled:
            asyncio.create_task(self._persist(entry))

    async def log_execution(self, record: ExecutionRecord) -> None:
        """Structured log entry after execution completes."""
        d = record.routing_decision
        entry = {
            "event": "execution_complete",
            "request_id": d.request_id,
            "feature": d.feature,
            "actual_layer": record.actual_layer,
            "actual_provider": record.actual_provider,
            "actual_model": record.actual_model,
            "actual_cost_usd": record.actual_cost_usd,
            "actual_input_tokens": record.actual_input_tokens,
            "actual_output_tokens": record.actual_output_tokens,
            "latency_ms": record.latency_ms,
            "fallback_used": record.fallback_used,
            "fallback_reason": record.fallback_reason,
            "from_cache": record.from_cache,
            "error": record.error,
            "user_id": d.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if record.error:
            logger.warning(
                "EXEC_FAIL feature=%s provider=%s error=%s",
                d.feature, record.actual_provider, record.error[:200],
            )
        else:
            logger.info(
                "EXEC_OK feature=%s provider=%s cost=%.4f latency=%dms",
                d.feature, record.actual_provider, record.actual_cost_usd, record.latency_ms,
            )
        if self._audit_enabled:
            asyncio.create_task(self._persist(entry))

    async def get_recent_decisions(self, limit: int = 100, feature: str | None = None) -> list[dict]:
        try:
            query: dict = {}
            if feature:
                query["feature"] = feature
            docs = await self._db[_COLL].find(query).sort("timestamp", -1).limit(limit).to_list(length=limit)
            for d in docs:
                d.pop("_id", None)
            return docs
        except Exception as exc:
            logger.warning("Could not fetch audit log: %s", exc)
            return []

    async def _persist(self, entry: dict) -> None:
        try:
            await self._db[_COLL].insert_one(entry)
        except Exception as exc:
            logger.debug("Audit log persist failed: %s", exc)
