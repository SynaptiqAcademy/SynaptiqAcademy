"""
MissionRepository — bounded-context repository for ARA missions.

Wraps all mission data access.  The ara/ package still has mission_store.py
for engine-internal use (mark_queued, mark_running, heartbeat update, etc.)
because those operations happen inside the worker, which has no HTTP context.
This repository is for router/service-layer access (create, list, get, cancel).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .base           import BaseRepository, NotFoundError, PermissionError, _serialize
from .cache          import SHORT_TTL
from .events         import RepoEvent
from .security_context import SecurityContext
from .specs          import QuerySpec, Specs


class MissionRepository(BaseRepository):
    collection   = "ara_missions"
    event_prefix = "mission"
    cache_ttl    = SHORT_TTL  # missions mutate frequently

    # ── Scoping ───────────────────────────────────────────────────────────────

    def _scope_query(self, filters: dict) -> dict:
        """Researchers see only their own missions. Admins see all."""
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    # ── Named query methods ───────────────────────────────────────────────────

    async def list_missions(
        self,
        *,
        status: str | list | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict]:
        spec = Specs.active()
        if status:
            spec = spec.and_(Specs.by_status(status))
        spec = spec.with_sort(("created_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_mission(self, mission_id: str) -> dict | None:
        return await self.find_one(doc_id=mission_id)

    async def create_mission(self, data: dict) -> dict:
        return await self.create(data)

    async def cancel_mission(self, mission_id: str) -> dict:
        mission = await self.find_one(doc_id=mission_id, bypass_cache=True)
        if not mission:
            raise NotFoundError(f"Mission {mission_id} not found")

        terminal = {"completed", "failed", "cancelled", "archived"}
        if mission.get("status") in terminal:
            raise ValueError(f"Mission is already {mission['status']}")

        return await self.update(mission_id, {"status": "cancelled"})

    async def get_active_count(self) -> int:
        from ara.models import ACTIVE_STATUSES
        spec = QuerySpec({"status": {"$in": list(ACTIVE_STATUSES)}})
        return await self.count(spec)

    async def pending_approval(self) -> list[dict]:
        return await self.find_many(Specs.pending_approval())

    # ── Step-level access ─────────────────────────────────────────────────────

    async def get_step_result(self, mission_id: str, step_id: str) -> dict | None:
        mission = await self.get_mission(mission_id)
        if not mission:
            return None
        for step in mission.get("steps", []):
            if step.get("id") == step_id or step.get("step_id") == step_id:
                return step
        return None

    # ── Analytics (admin) ─────────────────────────────────────────────────────

    async def status_distribution(self) -> dict[str, int]:
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        results = await self.raw_aggregate(pipeline)
        return {r["_id"]: r["count"] for r in results if r["_id"]}
