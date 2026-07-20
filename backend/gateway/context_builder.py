"""
Enterprise AI Gateway — Context Builder.

Lazily loads contextual information from platform services and injects
it into the AI request as a structured system-prompt block.

Context types (each opt-in via GatewayRequest flags):
  twin         — Digital Research Twin profile + working style + goals
  lkg          — Knowledge Graph: user node + top connections
  workspace    — Current workspace / project context
  institution  — Institution context + policies
  recent_ai    — Last N AI interactions for conversation continuity

Each loader is best-effort: never raises; returns empty string on failure.
Contexts are cached per request_id for the lifetime of one gateway call.
"""
from __future__ import annotations

import logging
from typing import Optional

from repo.shim import make_db_proxy
from .schemas import GatewayRequest

logger = logging.getLogger("gateway.context_builder")


class ContextBuilder:

    async def build(self, request: GatewayRequest, db) -> str:
        """
        Return a formatted context block to prepend to the system prompt.
        Only loads what the request flagged as needed.
        """
        db = make_db_proxy(db, system=True)
        parts: list[str] = []

        if request.load_twin and request.user_id:
            c = await self._load_twin(request.user_id, db)
            if c:
                parts.append(c)

        if request.load_lkg and request.user_id:
            c = await self._load_lkg(request.user_id, db)
            if c:
                parts.append(c)

        if request.load_workspace and request.workspace_id:
            c = await self._load_workspace(request.workspace_id, db)
            if c:
                parts.append(c)

        if request.load_institution and request.institution_id:
            c = await self._load_institution(request.institution_id, db)
            if c:
                parts.append(c)

        if request.load_recent_ai and request.user_id:
            c = await self._load_recent_ai(request.user_id, db)
            if c:
                parts.append(c)

        if not parts:
            return ""

        return (
            "\n\n=== RESEARCHER CONTEXT (derived from platform data) ===\n"
            + "\n\n".join(parts)
            + "\n=== END CONTEXT ===\n"
        )

    # ── Loaders (all best-effort) ─────────────────────────────────────────────

    async def _load_twin(self, user_id: str, db) -> str:
        try:
            from twin.twin_store import get_twin
            twin = await get_twin(db, user_id)
            if not twin:
                return ""
            profile = twin.get("profile", {})
            domains = profile.get("research_domains", [])[:5]
            career  = profile.get("career_stage", "unknown")
            return (
                f"[Twin Profile]\n"
                f"Career stage: {career}\n"
                f"Research domains: {', '.join(domains) or 'not specified'}\n"
                f"Active goals: {twin.get('goals_summary', 'none')}"
            )
        except Exception as exc:
            logger.debug("context_builder.twin failed: %s", exc)
            return ""

    async def _load_lkg(self, user_id: str, db) -> str:
        try:
            from lkg.unified import get_unified_graph
            node_id = f"researcher:internal:{user_id}"
            neighbors = await get_unified_graph().get_relationships(db, node_id, "out", None, limit=10)
            if not neighbors:
                return ""
            lines = [f"  - {n.get('to_id', '?')} ({n.get('type', '')})"
                     for n in neighbors]
            return "[Knowledge Graph]\nTop connections:\n" + "\n".join(lines)
        except Exception as exc:
            logger.debug("context_builder.lkg failed: %s", exc)
            return ""

    async def _load_workspace(self, workspace_id: str, db) -> str:
        try:
            from bson import ObjectId
            ws = await db["workspaces"].find_one(
                {"_id": ObjectId(workspace_id)},
                {"name": 1, "description": 1, "tags": 1},
            )
            if not ws:
                return ""
            return (
                f"[Workspace]\n"
                f"Name: {ws.get('name','')}\n"
                f"Description: {ws.get('description','')[:200]}"
            )
        except Exception as exc:
            logger.debug("context_builder.workspace failed: %s", exc)
            return ""

    async def _load_institution(self, institution_id: str, db) -> str:
        try:
            from bson import ObjectId
            inst = await db["institutions"].find_one(
                {"_id": ObjectId(institution_id)},
                {"name": 1, "ai_policy": 1},
            )
            if not inst:
                return ""
            policy = inst.get("ai_policy", "")
            return (
                f"[Institution]\n"
                f"Name: {inst.get('name','')}\n"
                + (f"AI Policy: {policy[:300]}" if policy else "")
            )
        except Exception as exc:
            logger.debug("context_builder.institution failed: %s", exc)
            return ""

    async def _load_recent_ai(self, user_id: str, db) -> str:
        try:
            recent = await db["ai_requests"].find(
                {"user_id": user_id},
                {"feature": 1, "timestamp": 1},
            ).sort("timestamp", -1).limit(3).to_list(3)
            if not recent:
                return ""
            lines = [f"  - {r.get('feature','?')} ({r.get('timestamp','')[:10]})"
                     for r in recent]
            return "[Recent AI Activity]\n" + "\n".join(lines)
        except Exception as exc:
            logger.debug("context_builder.recent_ai failed: %s", exc)
            return ""
