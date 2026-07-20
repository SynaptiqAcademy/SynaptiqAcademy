"""Academic Copilot — API Router (Phase XI).

User routes:   /api/copilot/*
Admin routes:  /api/admin/copilot/*

Credit costs (from plans_catalogue.CREDIT_COSTS):
  copilot_chat      → 3
  copilot_dashboard → 2
  copilot_roadmap   → 5
  copilot_suggestions → 1
"""
from __future__ import annotations

import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from plans_catalogue import CREDIT_COSTS
from services.copilot import get_copilot_engine
from services.copilot.intent_classifier import classify_intents
from services.copilot.models import RoadmapType
from services.copilot.workflow_planner import describe_plan, plan_workflow
from services.credits_service import consume_credits, refund_credits
from services.permissions import require_feature, is_super_admin
from repo.shim import make_db_proxy

logger = logging.getLogger("synaptiq.api.copilot")

router = APIRouter(prefix="/api/copilot", tags=["academic-copilot"])
admin_router = APIRouter(prefix="/api/admin/copilot", tags=["admin-copilot"])

CREDIT_CHAT        = CREDIT_COSTS.get("copilot_chat", 3)
CREDIT_DASHBOARD   = CREDIT_COSTS.get("copilot_dashboard", 2)
CREDIT_ROADMAP     = CREDIT_COSTS.get("copilot_roadmap", 5)
CREDIT_SUGGESTIONS = CREDIT_COSTS.get("copilot_suggestions", 1)


# ── Pydantic request models ───────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)
    conversation_history: list[dict] = Field(default_factory=list)
    entity_kind: Optional[str] = None   # "workspace" | "project" | "manuscript"
    entity_id: Optional[str] = None

    class Config:
        extra = "ignore"


class RoadmapRequest(BaseModel):
    roadmap_type: str = "research"
    topic: Optional[str] = None
    journal: Optional[str] = None
    funder: Optional[str] = None
    career_stage: Optional[str] = None
    use_ai: bool = True

    class Config:
        extra = "ignore"


class MemoryWriteRequest(BaseModel):
    memory_type: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1, max_length=500)


class WorkflowPlanRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


# ── User routes ───────────────────────────────────────────────────────────────

@router.post("/chat")
async def copilot_chat(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Main Academic Copilot chat endpoint.

    Automatically classifies intent, dispatches intelligence engines (quick-scan),
    synthesises results with an AI expert panel, and returns a structured response.
    """
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    await require_feature(user, "ai_chat")

    ok, balance = await consume_credits(user_id, CREDIT_CHAT, "copilot_chat", db)
    if not ok:
        raise HTTPException(402, detail={"error": "Insufficient credits", "required": CREDIT_CHAT, "balance": balance})

    try:
        engine = await get_copilot_engine()
        response = await engine.process_message(
            user_id=user_id,
            message=req.message,
            conversation_history=req.conversation_history,
            db=db,
        )
        return response.to_dict()
    except Exception as exc:
        await refund_credits(user_id, CREDIT_CHAT, "copilot_chat_refund", db)
        logger.error("copilot_chat error user=%s err=%s", user_id, exc)
        raise HTTPException(500, "Copilot encountered an error. Credits refunded.")


@router.post("/workflow/plan")
async def plan_workflow_preview(
    req: WorkflowPlanRequest,
    user: dict = Depends(get_current_user),
):
    """Preview the workflow the Copilot would execute for a given message (0 credits)."""
    intents = classify_intents(req.message)
    workflow = plan_workflow(req.message, intents, {})
    return {
        "message": req.message,
        "intents": [i.to_dict() for i in intents],
        "workflow": workflow.to_dict(),
        "description": describe_plan(workflow),
    }


@router.get("/dashboard")
async def get_dashboard(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return the personalised Academic Dashboard for the current user."""
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    ok, balance = await consume_credits(user_id, CREDIT_DASHBOARD, "copilot_dashboard", db)
    if not ok:
        raise HTTPException(402, detail={"error": "Insufficient credits", "required": CREDIT_DASHBOARD, "balance": balance})
    try:
        engine = await get_copilot_engine()
        dash = await engine.get_dashboard(user_id, db)
        return dash.to_dict()
    except Exception as exc:
        await refund_credits(user_id, CREDIT_DASHBOARD, "copilot_dashboard_refund", db)
        logger.error("copilot_dashboard error: %s", exc)
        raise HTTPException(500, "Dashboard generation failed. Credits refunded.")


@router.get("/suggestions")
async def get_suggestions(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return proactive suggestions based on user context."""
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    ok, balance = await consume_credits(user_id, CREDIT_SUGGESTIONS, "copilot_suggestions", db)
    if not ok:
        raise HTTPException(402, detail={"error": "Insufficient credits", "required": CREDIT_SUGGESTIONS, "balance": balance})
    engine = await get_copilot_engine()
    suggestions = await engine.get_suggestions(user_id, db)
    return {"suggestions": suggestions, "count": len(suggestions)}


@router.post("/roadmap")
async def generate_roadmap(
    req: RoadmapRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Generate a personalised academic roadmap (research / publication / grant / career / conference)."""
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    ok, balance = await consume_credits(user_id, CREDIT_ROADMAP, "copilot_roadmap", db)
    if not ok:
        raise HTTPException(402, detail={"error": "Insufficient credits", "required": CREDIT_ROADMAP, "balance": balance})

    try:
        roadmap_type_str = req.roadmap_type.lower()
        try:
            roadmap_type = RoadmapType(roadmap_type_str)
        except ValueError:
            roadmap_type = RoadmapType.RESEARCH

        params = {
            "topic": req.topic,
            "journal": req.journal,
            "funder": req.funder,
            "career_stage": req.career_stage,
        }
        engine = await get_copilot_engine()
        roadmap = await engine.build_academic_roadmap(
            user_id=user_id,
            roadmap_type=roadmap_type,
            params=params,
            db=db,
            use_ai=req.use_ai,
        )
        return roadmap.to_dict()
    except Exception as exc:
        await refund_credits(user_id, CREDIT_ROADMAP, "copilot_roadmap_refund", db)
        logger.error("roadmap generation error: %s", exc)
        raise HTTPException(500, "Roadmap generation failed. Credits refunded.")


@router.get("/memory")
async def get_memory(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return all active memory items for the current user."""
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    engine = await get_copilot_engine()
    items = await engine.get_memory(user_id, db)
    return {"memory": items, "count": len(items)}


@router.post("/memory")
async def save_memory(
    req: MemoryWriteRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Save a new memory item (research goal, target journal, preferred method, etc.)."""
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    engine = await get_copilot_engine()
    result = await engine.save_memory(user_id, req.memory_type, req.content, db)
    return {"saved": True, "item": result}


@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Deactivate a memory item (soft delete)."""
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    engine = await get_copilot_engine()
    deleted = await engine.delete_memory(user_id, memory_id, db)
    if not deleted:
        raise HTTPException(404, "Memory item not found or already removed.")
    return {"deleted": True, "memory_id": memory_id}


@router.get("/history")
async def get_history(
    limit: int = 50,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return conversation history with the Academic Copilot."""
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    if limit > 200:
        limit = 200
    engine = await get_copilot_engine()
    messages = await engine.get_history(user_id, db, limit=limit)
    return {"messages": messages, "count": len(messages)}


@router.get("/capabilities")
async def get_capabilities():
    """Return what the Academic Copilot can do — no auth required."""
    return {
        "name": "Synaptiq Academic Copilot",
        "version": "1.0",
        "description": (
            "The Academic Copilot orchestrates all Synaptiq intelligence engines "
            "to provide a seamless, proactive, explainable research experience."
        ),
        "personas": [
            "Researcher", "University Professor", "Journal Editor",
            "Peer Reviewer", "Statistician", "Research Supervisor",
            "Grant Consultant", "Academic Writing Coach",
            "Methodology Expert", "Career Mentor",
        ],
        "intelligence_engines": [
            {"id": "manuscript",  "name": "Manuscript Intelligence",  "description": "Writing quality, structure, scientific rigour, literature coverage."},
            {"id": "literature",  "name": "Literature Review Intelligence", "description": "Systematic search, synthesis, recency analysis."},
            {"id": "gap",         "name": "Research Gap Intelligence",  "description": "Identify underexplored areas and research opportunities."},
            {"id": "statistical", "name": "Statistical Intelligence",   "description": "Design, sampling, assumption checking, effect sizes."},
        ],
        "roadmap_types": [t.value for t in RoadmapType],
        "credit_costs": {
            "chat": CREDIT_CHAT,
            "dashboard": CREDIT_DASHBOARD,
            "roadmap": CREDIT_ROADMAP,
            "suggestions": CREDIT_SUGGESTIONS,
        },
        "endpoints": {
            "chat":        "POST /api/copilot/chat",
            "workflow":    "POST /api/copilot/workflow/plan",
            "dashboard":   "GET  /api/copilot/dashboard",
            "suggestions": "GET  /api/copilot/suggestions",
            "roadmap":     "POST /api/copilot/roadmap",
            "memory":      "GET/POST/DELETE /api/copilot/memory",
            "history":     "GET  /api/copilot/history",
        },
    }


# ── Admin routes ──────────────────────────────────────────────────────────────

@admin_router.get("/overview")
async def admin_overview(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    if not await is_super_admin(user):
        raise HTTPException(403)
    engine = await get_copilot_engine()
    stats = engine.get_telemetry()

    conversation_count = await db.copilot_conversations.count_documents({})
    roadmap_count = await db.copilot_roadmaps.count_documents({}) if hasattr(db, "copilot_roadmaps") else 0

    return {
        "telemetry": stats,
        "conversation_count": conversation_count,
        "roadmap_count": roadmap_count,
    }


@admin_router.get("/telemetry")
async def admin_telemetry(user: dict = Depends(get_current_user)):
    if not await is_super_admin(user):
        raise HTTPException(403)
    engine = await get_copilot_engine()
    return engine.get_telemetry()


@admin_router.post("/telemetry/reset")
async def admin_telemetry_reset(user: dict = Depends(get_current_user)):
    if not await is_super_admin(user):
        raise HTTPException(403)
    from services.copilot import reset_copilot_engine
    reset_copilot_engine()
    return {"reset": True}
