"""Academic Copilot — Main Orchestrator (Phase XI).

CopilotEngine coordinates all subsystems:
  intent_classifier → workflow_planner → context_aggregator →
  engine_dispatcher → ai_copilot → response_composer

Singleton via get_copilot_engine() / reset_copilot_engine().
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from bson import ObjectId

from .ai_copilot import generate_copilot_response
from .context_aggregator import build_copilot_context, extract_scan_content
from .dashboard_builder import build_dashboard
from .engine_dispatcher import dispatch_engines
from .intent_classifier import classify_intents
from .models import (
    AcademicRoadmap, CopilotDashboard, CopilotResponse,
    CopilotWorkflow, RoadmapType, WorkflowStatus,
)
from .proactive_advisor import generate_suggestions
from .response_composer import compose
from .roadmap_builder import build_roadmap
from .telemetry import get_copilot_telemetry
from .workflow_planner import describe_plan, plan_workflow

logger = logging.getLogger("synaptiq.copilot.engine")

# Max characters to pass to engine scans from a single message
_MAX_SCAN_CHARS = 10_000


class CopilotEngine:

    # ── Memory extraction (delegates to existing synaptiq_ai service) ─────────

    async def _maybe_extract_memory(self, user_id: str, message: str, db) -> None:
        try:
            from services.synaptiq_ai.memory_service import extract_and_save_memory
            await extract_and_save_memory(user_id, message, db)
        except Exception as exc:
            logger.debug("memory extraction skipped: %s", exc)

    # ── Core: process a chat message ──────────────────────────────────────────

    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_history: list[dict],
        db,
    ) -> CopilotResponse:
        t0 = time.perf_counter()
        telemetry = get_copilot_telemetry()
        error = False

        try:
            # 1. Classify intents
            intents = classify_intents(message)

            # 2. Build workflow plan (for transparency, not full execution in chat)
            context = await build_copilot_context(user_id, db)
            workflow = plan_workflow(message, intents, context)
            workflow.status = WorkflowStatus.RUNNING

            # 3. Determine which engines to invoke
            required_engines = list({
                eng
                for intent in intents
                for eng in intent.requires_engines
            })

            # 4. Dispatch engines on best available content
            engine_results: dict = {}
            if required_engines:
                scan_content = extract_scan_content(message, context, _MAX_SCAN_CHARS)
                if scan_content.strip():
                    engine_results = await dispatch_engines(required_engines, scan_content, context)

            # 5. Generate AI response
            ai_text, tokens = await generate_copilot_response(
                user_message=message,
                conversation_history=conversation_history,
                context=context,
                intents=intents,
                engine_results=engine_results,
            )

            # 6. Proactive suggestions (lightweight, always run)
            suggestions = generate_suggestions(context)[:3]

            # 7. Mark workflow complete
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now(timezone.utc)

            # 8. Compose response
            elapsed_ms = (time.perf_counter() - t0) * 1000
            response = compose(
                user_id=user_id,
                ai_text=ai_text,
                intents=intents,
                engine_results=engine_results,
                context=context,
                workflow=workflow,
                suggestions=suggestions,
                tokens_used=tokens,
                latency_ms=elapsed_ms,
            )

            # 9. Persist conversation
            await self._persist_message(user_id, message, ai_text, db)

            # 10. Extract and save memory
            await self._maybe_extract_memory(user_id, message, db)

            # 11. Telemetry
            telemetry.record_chat(
                primary_intent=intents[0].intent_type.value if intents else "general_chat",
                agent_type=response.agent_type,
                engines_invoked=list(engine_results.keys()),
                latency_ms=elapsed_ms,
            )

            return response

        except Exception as exc:
            error = True
            logger.error("copilot.process_message failed: %s", exc)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            telemetry.record_chat("error", "general", [], elapsed_ms, error=True)
            raise

    # ── Dashboard ─────────────────────────────────────────────────────────────

    async def get_dashboard(self, user_id: str, db) -> CopilotDashboard:
        telemetry = get_copilot_telemetry()
        dash = await build_dashboard(user_id, db)
        telemetry.record_dashboard()
        return dash

    # ── Proactive suggestions ─────────────────────────────────────────────────

    async def get_suggestions(self, user_id: str, db) -> list[dict]:
        context = await build_copilot_context(user_id, db, include_manuscripts=False)
        suggestions = generate_suggestions(context)
        return [s.to_dict() for s in suggestions]

    # ── Roadmap builder ───────────────────────────────────────────────────────

    async def build_academic_roadmap(
        self,
        user_id: str,
        roadmap_type: RoadmapType,
        params: dict,
        db,
        use_ai: bool = True,
    ) -> AcademicRoadmap:
        telemetry = get_copilot_telemetry()
        context = await build_copilot_context(user_id, db, include_manuscripts=False)
        roadmap = await build_roadmap(roadmap_type, context, params, use_ai=use_ai)
        await self._persist_roadmap(user_id, roadmap, db)
        telemetry.record_roadmap()
        return roadmap

    # ── Memory operations (delegate to existing service) ─────────────────────

    async def get_memory(self, user_id: str, db) -> list[dict]:
        try:
            from services.synaptiq_ai.memory_service import get_user_memory
            return await get_user_memory(user_id, db)
        except Exception as exc:
            logger.warning("get_memory failed: %s", exc)
            return []

    async def save_memory(self, user_id: str, memory_type: str, content: str, db) -> dict:
        try:
            from services.synaptiq_ai.memory_service import save_memory_item
            return await save_memory_item(user_id, memory_type, content, db)
        except Exception as exc:
            logger.error("save_memory failed: %s", exc)
            raise

    async def delete_memory(self, user_id: str, memory_id: str, db) -> bool:
        try:
            from bson import ObjectId
            result = await db.ai_memory.update_one(
                {"_id": ObjectId(memory_id), "user_id": user_id},
                {"$set": {"is_active": False}},
            )
            return result.modified_count > 0
        except Exception as exc:
            logger.error("delete_memory failed: %s", exc)
            return False

    # ── Conversation history ──────────────────────────────────────────────────

    async def get_history(self, user_id: str, db, limit: int = 50) -> list[dict]:
        try:
            cursor = db.copilot_conversations.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(limit)
            docs = await cursor.to_list(limit)
            return [
                {
                    "id": str(d["_id"]),
                    "role": d.get("role", "user"),
                    "content": d.get("content", ""),
                    "created_at": str(d.get("created_at", "")),
                    "intents": d.get("intents", []),
                    "agent_type": d.get("agent_type", ""),
                }
                for d in reversed(docs)
            ]
        except Exception as exc:
            logger.warning("get_history failed: %s", exc)
            return []

    # ── Telemetry (admin) ─────────────────────────────────────────────────────

    def get_telemetry(self) -> dict:
        return get_copilot_telemetry().get_stats()

    # ── Persistence helpers ───────────────────────────────────────────────────

    async def _persist_message(
        self, user_id: str, user_msg: str, ai_text: str, db
    ) -> None:
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            await db.copilot_conversations.insert_many([
                {"user_id": user_id, "role": "user",
                 "content": user_msg[:4000], "created_at": now},
                {"user_id": user_id, "role": "assistant",
                 "content": ai_text[:8000], "created_at": now},
            ])
        except Exception as exc:
            logger.debug("message persistence failed: %s", exc)

    async def _persist_roadmap(
        self, user_id: str, roadmap: AcademicRoadmap, db
    ) -> None:
        try:
            doc = roadmap.to_dict()
            doc["user_id"] = user_id
            await db.copilot_roadmaps.replace_one(
                {"roadmap_id": roadmap.roadmap_id},
                doc,
                upsert=True,
            )
        except Exception as exc:
            logger.debug("roadmap persistence failed: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine_instance: CopilotEngine | None = None
_engine_lock = asyncio.Lock()


async def get_copilot_engine() -> CopilotEngine:
    global _engine_instance
    if _engine_instance is None:
        async with _engine_lock:
            if _engine_instance is None:
                _engine_instance = CopilotEngine()
                logger.info("CopilotEngine initialised")
    return _engine_instance


def reset_copilot_engine() -> None:
    global _engine_instance
    _engine_instance = None
    get_copilot_telemetry().reset()
