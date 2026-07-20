"""
Cost Analytics — Phase XXXV.6

Tracks AI and platform costs across every dimension:
  user, workspace, institution, provider, model, mission, agent, prompt

Every AI call should call record_cost(). The tracker stores records in
MongoDB `obs_cost` and supports arbitrary breakdowns for the dashboard.

Usage:
    from obs.cost import get_cost_tracker
    await get_cost_tracker().record(
        cost_usd=0.0042,
        provider="openai",
        model="gpt-4o",
        tokens_in=1200,
        tokens_out=400,
        user_id="u123",
        mission_id="m456",
    )
    breakdown = await get_cost_tracker().breakdown("provider")
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_COL = "obs_cost"

# Valid breakdown dimensions
DIMENSIONS = ("user_id", "workspace_id", "institution", "provider",
              "model", "mission_id", "agent_name", "prompt_key", "job_type")


@dataclass
class CostRecord:
    record_id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:    str = field(default_factory=lambda: datetime.utcnow().isoformat())
    cost_usd:     float = 0.0
    provider:     str | None = None
    model:        str | None = None
    tokens_in:    int = 0
    tokens_out:   int = 0
    user_id:      str | None = None
    workspace_id: str | None = None
    institution:  str | None = None
    mission_id:   str | None = None
    agent_name:   str | None = None
    prompt_key:   str | None = None
    job_type:     str | None = None
    trace_id:     str | None = None
    operation:    str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != 0}


class CostTracker:

    def __init__(self, db: Any) -> None:
        self._db     = db
        self._lock   = threading.Lock()
        # In-memory running totals (fast reads for dashboard)
        self._total_usd:    float = 0.0
        self._total_tokens: int   = 0
        self._by_provider:  dict[str, float] = {}
        self._by_model:     dict[str, float] = {}
        self._by_user:      dict[str, float] = {}

    async def record(
        self,
        cost_usd:     float = 0.0,
        provider:     str | None = None,
        model:        str | None = None,
        tokens_in:    int = 0,
        tokens_out:   int = 0,
        user_id:      str | None = None,
        workspace_id: str | None = None,
        institution:  str | None = None,
        mission_id:   str | None = None,
        agent_name:   str | None = None,
        prompt_key:   str | None = None,
        job_type:     str | None = None,
        trace_id:     str | None = None,
        operation:    str | None = None,
    ) -> None:
        rec = CostRecord(
            cost_usd=cost_usd, provider=provider, model=model,
            tokens_in=tokens_in, tokens_out=tokens_out, user_id=user_id,
            workspace_id=workspace_id, institution=institution,
            mission_id=mission_id, agent_name=agent_name,
            prompt_key=prompt_key, job_type=job_type,
            trace_id=trace_id, operation=operation,
        )
        # Update in-memory totals (thread-safe)
        with self._lock:
            self._total_usd    += cost_usd
            self._total_tokens += tokens_in + tokens_out
            if provider:
                self._by_provider[provider] = self._by_provider.get(provider, 0.0) + cost_usd
            if model:
                self._by_model[model] = self._by_model.get(model, 0.0) + cost_usd
            if user_id:
                self._by_user[user_id] = self._by_user.get(user_id, 0.0) + cost_usd
        # Persist to MongoDB (best-effort)
        try:
            await self._db[_COL].insert_one(rec.to_dict())
        except Exception as exc:
            logger.debug("CostTracker.record error: %s", exc)

    def totals(self) -> dict:
        with self._lock:
            return {
                "total_usd":    round(self._total_usd, 6),
                "total_tokens": self._total_tokens,
                "by_provider":  dict(self._by_provider),
                "by_model":     dict(self._by_model),
                "top_users":    sorted(self._by_user.items(), key=lambda x: -x[1])[:10],
            }

    async def breakdown(
        self,
        dimension:  str = "provider",
        from_ts:    str | None = None,
        to_ts:      str | None = None,
        user_id:    str | None = None,
        limit:      int = 50,
    ) -> list[dict]:
        if dimension not in DIMENSIONS:
            return []
        try:
            match_stage: dict = {}
            if from_ts or to_ts:
                ts: dict = {}
                if from_ts: ts["$gte"] = from_ts
                if to_ts:   ts["$lte"] = to_ts
                match_stage["timestamp"] = ts
            if user_id:
                match_stage["user_id"] = user_id
            pipeline: list = []
            if match_stage:
                pipeline.append({"$match": match_stage})
            pipeline += [
                {"$group": {
                    "_id":        f"${dimension}",
                    "total_usd":  {"$sum": "$cost_usd"},
                    "total_tokens": {"$sum": {"$add": ["$tokens_in", "$tokens_out"]}},
                    "count":      {"$sum": 1},
                }},
                {"$sort": {"total_usd": -1}},
                {"$limit": limit},
            ]
            cursor = await self._db[_COL].aggregate(pipeline)
            docs   = await cursor.to_list(limit)
            return [
                {
                    dimension:      d["_id"],
                    "total_usd":    round(d["total_usd"], 6),
                    "total_tokens": d["total_tokens"],
                    "count":        d["count"],
                }
                for d in docs
            ]
        except Exception as exc:
            logger.debug("CostTracker.breakdown error: %s", exc)
            return []

    async def recent(self, limit: int = 20) -> list[dict]:
        try:
            return await self._db[_COL].find(
                {}, {"_id": 0}
            ).sort("timestamp", -1).limit(limit).to_list(limit)
        except Exception:
            return []

    async def ensure_indexes(self) -> None:
        try:
            await self._db[_COL].create_index("timestamp")
            await self._db[_COL].create_index("user_id")
            await self._db[_COL].create_index("provider")
            await self._db[_COL].create_index("mission_id")
        except Exception as exc:
            logger.debug("CostTracker.ensure_indexes: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_tracker: CostTracker | None = None


def init_cost(db: Any) -> CostTracker:
    global _tracker
    _tracker = CostTracker(db)
    return _tracker


def get_cost_tracker() -> CostTracker | None:
    return _tracker
