"""
Enterprise AI Gateway — Cost Ledger.

The single source of truth for all AI cost tracking.

Responsibilities:
  - Token → USD → Credit conversion (1 credit ≈ $0.001)
  - Per-request cost calculation by provider + model
  - MongoDB ai_costs collection write (async, non-blocking)
  - ARA mission used_credits increment (FIXES the audit finding)
  - Budget ceiling enforcement (pre-execution check)

Provider prices live in services/ai/pricing.py (configurable via
AI_PROVIDER_PRICING_JSON) — this module no longer keeps its own table.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from repo.shim import make_db_proxy

logger = logging.getLogger("gateway.cost_ledger")

USD_PER_CREDIT = 0.001  # internal cost unit for ARA missions — NOT customer AI credits


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> tuple[float, float]:
    """Return (cost_usd, cost_credits). Prices come from services/ai/pricing.py."""
    from services.ai.pricing import estimate_cost_usd
    cost_usd = estimate_cost_usd(model, input_tokens, output_tokens,
                                 cache_read_tokens, cache_write_tokens)
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
