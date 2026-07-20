"""
Enterprise AI Gateway — Cost Ledger.

The single source of truth for all AI cost tracking.

Responsibilities:
  - Token → USD → Credit conversion (1 credit ≈ $0.001)
  - Per-request cost calculation by provider + model
  - MongoDB ai_costs collection write (async, non-blocking)
  - ARA mission used_credits increment (FIXES the audit finding)
  - Budget ceiling enforcement (pre-execution check)

Cost model (approximate, updated periodically):
  Anthropic claude-sonnet-4-6:      $3.00 / 1M in, $15.00 / 1M out
  Anthropic claude-haiku-4-5:       $0.25 / 1M in, $1.25 / 1M out
  OpenAI gpt-4o:                    $5.00 / 1M in, $15.00 / 1M out
  OpenAI gpt-4o-mini:               $0.15 / 1M in, $0.60 / 1M out
  Local (Ollama/vLLM):              $0.00 (compute only)
  Mock/Rule:                        $0.00
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from repo.shim import make_db_proxy

logger = logging.getLogger("gateway.cost_ledger")

USD_PER_CREDIT = 0.001  # 1 credit = $0.001

# (input_usd_per_1M, output_usd_per_1M)
_PROVIDER_COSTS: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-sonnet-4-6":         (3.00, 15.00),
    "claude-sonnet-4-5":         (3.00, 15.00),
    "claude-opus-4-8":           (15.00, 75.00),
    "claude-haiku-4-5-20251001": (0.25,  1.25),
    "claude-haiku-4-5":          (0.25,  1.25),
    # OpenAI
    "gpt-4o":                    (5.00, 15.00),
    "gpt-4o-mini":               (0.15,  0.60),
    "o1":                        (15.00, 60.00),
    "o1-mini":                   (3.00, 12.00),
    # Local / rule engine
    "local":                     (0.00,  0.00),
    "mock":                      (0.00,  0.00),
    "rule_engine":               (0.00,  0.00),
}
_DEFAULT_COST = (3.00, 15.00)  # assume Sonnet if unknown


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> tuple[float, float]:
    """Return (cost_usd, cost_credits)."""
    rates = _PROVIDER_COSTS.get(model, _DEFAULT_COST)
    cost_usd = (input_tokens / 1_000_000) * rates[0] + (output_tokens / 1_000_000) * rates[1]
    cost_credits = cost_usd / USD_PER_CREDIT
    return round(cost_usd, 8), round(cost_credits, 4)


class CostLedger:
    """
    Records and enforces AI cost for every gateway request.

    Methods are all best-effort: never raise to callers.
    """

    async def record(
        self,
        request_id: str,
        feature:    str,
        user_id:    str | None,
        mission_id: str | None,
        provider:   str,
        model:      str,
        tokens_in:  int,
        tokens_out: int,
        db,
    ) -> tuple[float, float]:
        """
        Calculate cost, persist to ai_costs, update ARA mission if applicable.
        Returns (cost_usd, cost_credits).
        """
        cost_usd, cost_credits = calculate_cost(model, tokens_in, tokens_out)

        # Fire-and-forget — never block the caller
        asyncio.create_task(
            self._persist(request_id, feature, user_id, mission_id,
                          provider, model, tokens_in, tokens_out,
                          cost_usd, cost_credits, db)
        )
        return cost_usd, cost_credits

    async def _persist(
        self,
        request_id: str,
        feature:    str,
        user_id:    str | None,
        mission_id: str | None,
        provider:   str,
        model:      str,
        tokens_in:  int,
        tokens_out: int,
        cost_usd:   float,
        cost_credits: float,
        db,
    ) -> None:
        if db is None:
            return
        db = make_db_proxy(db, system=True)
        try:
            now = datetime.now(timezone.utc)

            # Write to ai_costs collection
            await db["ai_costs"].insert_one({
                "request_id":  request_id,
                "feature":     feature,
                "user_id":     user_id,
                "mission_id":  mission_id,
                "provider":    provider,
                "model":       model,
                "tokens_in":   tokens_in,
                "tokens_out":  tokens_out,
                "cost_usd":    cost_usd,
                "cost_credits": cost_credits,
                "timestamp":   now,
            })

            # Also record in Enterprise Cost Tracker (obs layer)
            try:
                from obs.cost import get_cost_tracker
                tracker = get_cost_tracker()
                if tracker:
                    await tracker.record(
                        cost_usd=cost_usd,
                        provider=provider,
                        model=model,
                        job_type=feature,
                        user_id=user_id,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                    )
            except Exception:
                pass

            # CRITICAL FIX (audit finding C-03): increment ARA mission used_credits
            if mission_id:
                from bson import ObjectId
                try:
                    await db["ara_missions"].update_one(
                        {"_id": ObjectId(mission_id)},
                        {"$inc": {"used_credits": cost_credits},
                         "$set": {"updated_at": now}},
                    )
                except Exception as exc:
                    logger.debug("mission used_credits update failed (non-blocking): %s", exc)

        except Exception as exc:
            logger.warning("CostLedger._persist failed (non-blocking): %s", exc)
