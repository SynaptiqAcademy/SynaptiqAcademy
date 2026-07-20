"""
Mission Observability — execution timeline, metrics and audit trail.

Tracks every state transition with duration, cost, tokens, and error detail.
Stored in ara_timeline collection (append-only, never overwritten).

This provides the raw data for:
  - The mission detail page execution timeline
  - Cost attribution per step and per mission
  - Performance analysis across missions
  - Error debugging and audit trails
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("ara.engine.observability")

_COLL = "ara_timeline"


class MissionObservability:

    async def record_execution_start(self, db, mission_id: str, worker_id: str) -> None:
        await self._insert(db, {
            "type":       "execution_start",
            "mission_id": mission_id,
            "worker_id":  worker_id,
        })
        try:
            from obs.metrics import get_metrics, M_MISSION_STARTED
            get_metrics().inc(M_MISSION_STARTED)
        except Exception:
            pass

    async def record_step_start(self, db, mission_id: str, step_id: str, agent: str = "") -> None:
        await self._insert(db, {
            "type":       "step_start",
            "mission_id": mission_id,
            "step_id":    step_id,
            "agent":      agent,
        })

    async def record_step_end(
        self,
        db,
        mission_id:   str,
        step_id:      str,
        duration_ms:  int,
        cost_credits: float = 0.0,
        tokens:       int   = 0,
        success:      bool  = True,
        error:        str | None = None,
        confidence:   str  = "low",
        agent:        str  = "",
    ) -> None:
        await self._insert(db, {
            "type":        "step_end",
            "mission_id":  mission_id,
            "step_id":     step_id,
            "agent":       agent,
            "duration_ms": duration_ms,
            "cost_credits": cost_credits,
            "tokens":       tokens,
            "success":      success,
            "error":        error,
            "confidence":   confidence,
        })
        try:
            from obs.metrics import get_metrics, M_MISSION_STEPS
            get_metrics().inc(M_MISSION_STEPS, tags={"success": str(success), "agent": agent or "unknown"})
        except Exception:
            pass

    async def record_mission_end(
        self,
        db,
        mission_id:        str,
        status:            str,
        total_duration_ms: int,
        total_cost:        float = 0.0,
        steps_completed:   int   = 0,
        steps_failed:      int   = 0,
    ) -> None:
        await self._insert(db, {
            "type":              "mission_end",
            "mission_id":        mission_id,
            "status":            status,
            "total_duration_ms": total_duration_ms,
            "total_cost_credits": total_cost,
            "steps_completed":   steps_completed,
            "steps_failed":      steps_failed,
        })
        try:
            from obs.metrics import get_metrics, M_MISSION_DONE, M_MISSION_FAILED, M_MISSION_LATENCY
            m = get_metrics()
            if status == "completed":
                m.inc(M_MISSION_DONE)
            else:
                m.inc(M_MISSION_FAILED)
            m.observe(M_MISSION_LATENCY, float(total_duration_ms))
        except Exception:
            pass

    async def get_timeline(self, db, mission_id: str) -> list[dict]:
        """Return full execution timeline ordered by timestamp."""
        try:
            docs = await db[_COLL].find(
                {"mission_id": mission_id}, {"_id": 0}
            ).sort("timestamp", 1).to_list(500)
            for d in docs:
                if isinstance(d.get("timestamp"), datetime):
                    d["timestamp"] = d["timestamp"].isoformat()
            return docs
        except Exception as exc:
            logger.debug("get_timeline failed: %s", exc)
            return []

    async def get_mission_metrics(self, db, mission_id: str) -> dict:
        """Aggregate cost and performance metrics for one mission."""
        try:
            pipeline = [
                {"$match": {"mission_id": mission_id, "type": "step_end"}},
                {"$group": {
                    "_id":            None,
                    "total_cost":     {"$sum": "$cost_credits"},
                    "total_tokens":   {"$sum": "$tokens"},
                    "total_duration": {"$sum": "$duration_ms"},
                    "steps_ok":       {"$sum": {"$cond": ["$success", 1, 0]}},
                    "steps_fail":     {"$sum": {"$cond": ["$success", 0, 1]}},
                }},
            ]
            result = await db[_COLL].aggregate(pipeline).to_list(1)
            if result:
                r = result[0]
                r.pop("_id", None)
                return r
        except Exception as exc:
            logger.debug("get_mission_metrics failed: %s", exc)
        return {}

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _insert(self, db, doc: dict) -> None:
        if db is None:
            return
        doc["timestamp"] = datetime.now(timezone.utc)
        asyncio.create_task(self._do_insert(db, doc))

    async def _do_insert(self, db, doc: dict) -> None:
        try:
            await db[_COLL].insert_one(doc)
        except Exception as exc:
            logger.debug("ara_timeline insert failed: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────────

_obs: MissionObservability | None = None


def get_observability() -> MissionObservability:
    global _obs
    if _obs is None:
        _obs = MissionObservability()
    return _obs
