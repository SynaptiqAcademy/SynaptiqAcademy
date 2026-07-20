"""Synaptiq AI Operating System — Phase XXIII.

Main AI OS router. Provides conversational AI with memory, context awareness,
action execution, and proactive insights.

All endpoints require authentication. Service imports are wrapped in try/except
so the router is available even when the service layer is being built.

Routes
------
POST   /api/ai-os/conversations                        — create conversation
GET    /api/ai-os/conversations                        — list conversations
GET    /api/ai-os/conversations/{conv_id}              — get conversation + messages
PATCH  /api/ai-os/conversations/{conv_id}              — update metadata
DELETE /api/ai-os/conversations/{conv_id}              — soft-delete (archive)

POST   /api/ai-os/conversations/{conv_id}/messages     — send message (main AI endpoint)

GET    /api/ai-os/memory                               — list active memory items
POST   /api/ai-os/memory                               — save memory item
DELETE /api/ai-os/memory/{memory_id}                   — delete one memory item
DELETE /api/ai-os/memory                               — delete ALL memory (GDPR)

POST   /api/ai-os/actions/execute                      — execute platform action
GET    /api/ai-os/actions                              — list recent actions
GET    /api/ai-os/actions/available                    — available action types

GET    /api/ai-os/context                              — current cached context summary
POST   /api/ai-os/context/refresh                      — force-refresh context cache

GET    /api/ai-os/insights                             — proactive AI insights

GET    /api/ai-os/agents                               — available agent descriptions
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from plans_catalogue import CREDIT_COSTS
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.ai_os")

# ── Service imports — graceful degradation ────────────────────────────────────

try:
    from services.synaptiq_ai.context_engine import (
        get_or_refresh_context,
        build_user_context,
    )
    _context_engine_available = True
except ImportError as _e:
    logger.warning("context_engine unavailable: %s", _e)
    _context_engine_available = False

try:
    from services.synaptiq_ai.orchestrator import route_and_respond, detect_agent
    _orchestrator_available = True
except ImportError as _e:
    logger.warning("orchestrator unavailable: %s", _e)
    _orchestrator_available = False

try:
    from services.synaptiq_ai.memory_service import (
        get_user_memory,
        save_memory,
        delete_memory,
        clear_all_memory,
        extract_memory_from_response,
    )
    _memory_service_available = True
except ImportError as _e:
    logger.warning("memory_service unavailable: %s", _e)
    _memory_service_available = False

try:
    from services.synaptiq_ai.action_executor import (
        execute_action,
        log_action,
        AVAILABLE_ACTIONS,
    )
    _action_executor_available = True
except ImportError as _e:
    logger.warning("action_executor unavailable: %s", _e)
    _action_executor_available = False
    AVAILABLE_ACTIONS = {}

try:
    from services.synaptiq_ai.insights_engine import generate_insights
    _insights_engine_available = True
except ImportError as _e:
    logger.warning("insights_engine unavailable: %s", _e)
    _insights_engine_available = False

try:
    from services.credits_service import consume_credits
    _credits_available = True
except ImportError as _e:
    logger.warning("credits_service unavailable: %s", _e)
    _credits_available = False

# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/ai-os", tags=["synaptiq-ai"])

# ── Constants ─────────────────────────────────────────────────────────────────

_AI_MESSAGE_COST = CREDIT_COSTS.get("ai_chat_message", 2)
_RATE_LIMIT_PER_HOUR = 50
_HISTORY_WINDOW = 20
_LAST_MESSAGES_LIMIT = 100

_VALID_MEMORY_TYPES = {
    "research_goal",
    "publication_goal",
    "target_journal",
    "target_conference",
    "target_grant",
    "preferred_method",
    "career_goal",
    "teaching_goal",
    "collaboration_preference",
    "general",
}

_AGENTS = [
    {
        "type": "research",
        "name": "Research Copilot",
        "description": (
            "Research idea generation, gap discovery, methodology advice, "
            "literature mapping, and hypothesis refinement."
        ),
    },
    {
        "type": "publication",
        "name": "Manuscript Copilot",
        "description": (
            "Manuscript analysis, writing assistance, journal targeting, "
            "reviewer simulation, and revision planning."
        ),
    },
    {
        "type": "grant",
        "name": "Grant Copilot",
        "description": (
            "Grant discovery, proposal drafting, budget planning, "
            "eligibility checking, and deadline tracking."
        ),
    },
    {
        "type": "teaching",
        "name": "Teaching Copilot",
        "description": (
            "Curriculum design, lesson planning, student engagement, "
            "assessment creation, and teaching analytics."
        ),
    },
    {
        "type": "collaboration",
        "name": "Collaboration Copilot",
        "description": (
            "Collaboration partner discovery, team formation, conflict resolution, "
            "and co-authorship guidance."
        ),
    },
    {
        "type": "analytics",
        "name": "Analytics Copilot",
        "description": (
            "Research impact analysis, citation trends, reputation insights, "
            "benchmarking, and performance forecasting."
        ),
    },
    {
        "type": "general",
        "name": "General Assistant",
        "description": (
            "General-purpose academic assistant for any research-related question "
            "not covered by specialist copilots."
        ),
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _ser(doc: dict | None) -> dict:
    """Recursively convert ObjectId / datetime to JSON-safe types."""
    if not doc:
        return {}
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _ser(v)
        elif isinstance(v, list):
            out[k] = [
                _ser(i) if isinstance(i, dict)
                else str(i) if isinstance(i, ObjectId)
                else i.isoformat() if isinstance(i, datetime)
                else i
                for i in v
            ]
        else:
            out[k] = v
    return out


def _ser_list(docs: list[dict]) -> list[dict]:
    return [_ser(d) for d in docs]


def _doc_id(doc: dict) -> str:
    return str(doc["_id"])


async def _get_conversation(conv_id: str, user_id: str, db) -> dict:
    """Load a conversation, verify ownership. Raises 404/403."""
    try:
        oid = ObjectId(conv_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv = await db.ai_conversations.find_one({"_id": oid})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return conv


async def _build_context_safe(user_id: str, db, force_refresh: bool = False) -> dict:
    """Load context with full fallback to empty dict."""
    if not _context_engine_available:
        return {}
    try:
        return await get_or_refresh_context(user_id, db, force_refresh=force_refresh)
    except Exception as exc:
        logger.warning("Context engine error for user %s: %s", user_id, exc)
        return {}


async def _build_context_summary(user_id: str, db, force_refresh: bool = False) -> dict:
    """Return a lean summary for the /context endpoint."""
    ctx = await _build_context_safe(user_id, db, force_refresh)
    computed_at = ctx.get("computed_at")
    age_minutes: float = 0.0
    if computed_at:
        if isinstance(computed_at, str):
            try:
                computed_at = datetime.fromisoformat(computed_at)
            except ValueError:
                computed_at = None
        if computed_at:
            delta = _now() - computed_at.replace(tzinfo=timezone.utc) if computed_at.tzinfo is None else _now() - computed_at
            age_minutes = round(delta.total_seconds() / 60, 1)

    return {
        "summary": ctx.get("summary", ""),
        "manuscript_count": ctx.get("manuscript_count", 0),
        "project_count": ctx.get("project_count", 0),
        "collaboration_count": ctx.get("collaboration_count", 0),
        "reputation_score": ctx.get("reputation_score", 0.0),
        "impact_score": ctx.get("impact_score", 0),
        "memory_items": ctx.get("memory_items", 0),
        "context_age_minutes": age_minutes,
    }


async def _upsert_usage_analytics(
    user_id: str,
    agent_type: str,
    tokens_used: int,
    db,
) -> None:
    """Increment daily usage analytics (upsert by user_id + date + agent_type)."""
    date_str = _now().strftime("%Y-%m-%d")
    try:
        await db.ai_usage_analytics.update_one(
            {"user_id": user_id, "date": date_str, "agent_type": agent_type},
            {
                "$inc": {
                    "message_count": 1,
                    "tokens_used": tokens_used,
                },
                "$setOnInsert": {"created_at": _now_iso()},
                "$set": {"updated_at": _now_iso()},
            },
            upsert=True,
        )
    except Exception as exc:
        logger.warning("Usage analytics upsert failed: %s", exc)


# ── Request / Response Models ─────────────────────────────────────────────────


class CreateConversationBody(BaseModel):
    title: Optional[str] = None
    agent_type: Optional[str] = None


class UpdateConversationBody(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None
    tags: Optional[list[str]] = None


class SendMessageBody(BaseModel):
    message: str
    agent_type: Optional[str] = None
    force_context_refresh: bool = False


class SaveMemoryBody(BaseModel):
    memory_type: str
    content: str


class ExecuteActionBody(BaseModel):
    action_type: str
    params: dict
    conv_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/conversations")
async def create_conversation(
    body: CreateConversationBody,
    user: dict = Depends(get_current_user),
):
    """Create a new AI conversation."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]
    now = _now_iso()

    doc = {
        "user_id": user_id,
        "title": (body.title or "New Conversation").strip(),
        "agent_type": body.agent_type,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
        "pinned": False,
        "tags": [],
        "archived": False,
    }
    result = await db.ai_conversations.insert_one(doc)
    doc["_id"] = result.inserted_id
    serialized = _ser(doc)
    # Frontend expects "id" (not "_id") to match the list endpoint schema
    serialized["id"] = serialized.get("_id") or str(result.inserted_id)
    logger.debug("CONVERSATION_CREATED id=%s user=%s", serialized["id"], user_id)
    return serialized


@router.get("/conversations")
async def list_conversations(
    archived: bool = Query(False),
    pinned: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """List user's conversations sorted by updated_at DESC."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    filt: dict = {"user_id": user_id, "archived": archived}
    if pinned is not None:
        filt["pinned"] = pinned

    cursor = db.ai_conversations.find(filt).sort("updated_at", -1).limit(limit)
    conversations = await cursor.to_list(limit)

    results = []
    for conv in conversations:
        conv_id_str = str(conv["_id"])

        # Fetch last assistant message preview
        last_msg = await db.ai_messages.find_one(
            {"conv_id": conv_id_str, "role": "assistant"},
            sort=[("created_at", -1)],
        )
        preview = ""
        if last_msg:
            content = last_msg.get("content", "")
            preview = content[:100]

        results.append({
            "id": conv_id_str,
            "title": conv.get("title"),
            "agent_type": conv.get("agent_type"),
            "message_count": conv.get("message_count", 0),
            "updated_at": conv.get("updated_at"),
            "pinned": conv.get("pinned", False),
            "archived": conv.get("archived", False),
            "last_message_preview": preview,
        })

    return results


@router.get("/conversations/{conv_id}")
async def get_conversation(
    conv_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a full conversation with its messages (last 100)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    logger.info("CONVERSATION_FETCH_REQUEST conv_id=%s user=%s", conv_id, user_id)
    conv = await _get_conversation(conv_id, user_id, db)
    logger.info("CONVERSATION_FOUND id=%s title=%r", conv_id, conv.get("title"))

    # Fetch last 100 messages
    cursor = (
        db.ai_messages.find({"conv_id": conv_id})
        .sort("created_at", 1)
        .limit(_LAST_MESSAGES_LIMIT)
    )
    raw_messages = await cursor.to_list(_LAST_MESSAGES_LIMIT)
    logger.info("MESSAGES_FOUND conv_id=%s count=%d", conv_id, len(raw_messages))

    messages = []
    for m in raw_messages:
        messages.append({
            "id": str(m["_id"]),
            "role": m.get("role"),
            "content": m.get("content"),
            "agent_type": m.get("agent_type"),
            "suggested_actions": m.get("suggested_actions", []),
            "sources": m.get("sources", []),
            "tokens_used": m.get("tokens_used", 0),
            "created_at": m["created_at"] if isinstance(m.get("created_at"), str) else (m["created_at"].isoformat() if isinstance(m.get("created_at"), datetime) else None),
        })

    conv_serialized = _ser(conv)
    # Ensure "id" is always present (frontend needs it; _ser only produces "_id")
    conv_serialized.setdefault("id", conv_id)
    logger.debug(
        "CONVERSATION_RETURNED id=%s messages=%d user=%s",
        conv_id, len(messages), user_id,
    )
    return {
        "conversation": conv_serialized,
        "messages": messages,
    }


@router.patch("/conversations/{conv_id}")
async def update_conversation(
    conv_id: str,
    body: UpdateConversationBody,
    user: dict = Depends(get_current_user),
):
    """Update conversation metadata (title, pinned, archived, tags)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    await _get_conversation(conv_id, user_id, db)

    updates: dict = {"updated_at": _now_iso()}
    if body.title is not None:
        updates["title"] = body.title.strip()
    if body.pinned is not None:
        updates["pinned"] = body.pinned
    if body.archived is not None:
        updates["archived"] = body.archived
    if body.tags is not None:
        updates["tags"] = body.tags

    await db.ai_conversations.update_one(
        {"_id": ObjectId(conv_id)},
        {"$set": updates},
    )

    updated = await db.ai_conversations.find_one({"_id": ObjectId(conv_id)})
    return _ser(updated)


@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: str,
    user: dict = Depends(get_current_user),
):
    """Soft-delete: mark conversation as archived (GDPR-safe)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    await _get_conversation(conv_id, user_id, db)

    await db.ai_conversations.update_one(
        {"_id": ObjectId(conv_id)},
        {"$set": {"archived": True, "updated_at": _now_iso()}},
    )
    return {"success": True, "message": "Conversation archived"}


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE ENDPOINT (main AI interaction)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/conversations/{conv_id}/messages")
async def send_message(
    conv_id: str,
    body: SendMessageBody,
    user: dict = Depends(get_current_user),
):
    """
    Main AI endpoint. Orchestrates context loading, routing, credit deduction,
    memory extraction, and usage logging.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    # 1. Verify conversation ownership
    conv = await _get_conversation(conv_id, user_id, db)

    # 2. Rate limit: max 50 messages/hour
    one_hour_ago = (_now() - timedelta(hours=1)).isoformat()
    recent_count = await db.ai_messages.count_documents({
        "user_id": user_id,
        "role": "user",
        "created_at": {"$gte": one_hour_ago},
    })
    if recent_count >= _RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {_RATE_LIMIT_PER_HOUR} messages per hour.",
        )

    # 3. Load user context
    context = await _build_context_safe(user_id, db, force_refresh=body.force_context_refresh)

    # 4. Load conversation history (last 20 messages for context window)
    history_cursor = (
        db.ai_messages.find({"conv_id": conv_id})
        .sort("created_at", -1)
        .limit(_HISTORY_WINDOW)
    )
    raw_history = await history_cursor.to_list(_HISTORY_WINDOW)
    history = [
        {"role": m.get("role"), "content": m.get("content")}
        for m in reversed(raw_history)
    ]

    # 5. Route and respond
    response: dict = {}
    if not _orchestrator_available:
        raise HTTPException(
            status_code=503,
            detail="AI orchestrator service is not available.",
        )
    try:
        response = await route_and_respond(
            body.message,
            history,
            context,
            db,
            agent_type=body.agent_type,
        )
    except Exception as exc:
        logger.error("Orchestrator error for user %s: %s", user_id, exc)
        # Fallback minimal response
        response = {
            "content": "I'm sorry, I encountered an issue processing your request. Please try again.",
            "agent_type": body.agent_type or "general",
            "suggested_actions": [],
            "sources": [],
            "tokens_used": 0,
        }

    response_content: str = response.get("response") or response.get("content", "")
    agent_type_used: str = response.get("agent_type") or body.agent_type or "general"
    suggested_actions: list = response.get("suggested_actions", [])
    sources: list = response.get("sources", [])
    tokens_used: int = response.get("tokens_used", 0)

    # 6. Deduct credits (never block AI response on credit failure)
    if _credits_available:
        try:
            await consume_credits(user_id, _AI_MESSAGE_COST, db, "ai_os_message")
        except Exception as exc:
            logger.warning("Credit deduction failed for user %s: %s", user_id, exc)

    now_str = _now_iso()

    # 7. Save user message
    user_msg_doc = {
        "conv_id": conv_id,
        "user_id": user_id,
        "role": "user",
        "content": body.message,
        "agent_type": agent_type_used,
        "suggested_actions": [],
        "sources": [],
        "tokens_used": 0,
        "created_at": now_str,
    }
    await db.ai_messages.insert_one(user_msg_doc)

    # 8. Save assistant response
    assistant_msg_doc = {
        "conv_id": conv_id,
        "user_id": user_id,
        "role": "assistant",
        "content": response_content,
        "agent_type": agent_type_used,
        "suggested_actions": suggested_actions,
        "sources": sources,
        "tokens_used": tokens_used,
        "created_at": _now_iso(),
    }
    asst_result = await db.ai_messages.insert_one(assistant_msg_doc)
    message_id = str(asst_result.inserted_id)

    # 9 & 10. Update conversation: increment count, update agent_type and timestamp.
    #          Auto-generate title on first message (message_count was 0).
    current_count: int = conv.get("message_count", 0)
    new_count = current_count + 1  # +1 pair (user+assistant counted as 1 exchange)

    conv_updates: dict = {
        "updated_at": _now_iso(),
        "message_count": new_count,
        "agent_type": agent_type_used,
    }

    new_title: Optional[str] = None
    if current_count == 0:
        msg = body.message
        auto_title = msg[:50].strip() + ("..." if len(msg) > 50 else "")
        conv_updates["title"] = auto_title
        new_title = auto_title

    await db.ai_conversations.update_one(
        {"_id": ObjectId(conv_id)},
        {"$set": conv_updates},
    )

    conversation_title = new_title or conv.get("title", "")

    # 11. Extract and auto-save memory hints (never blocks response)
    if _memory_service_available:
        try:
            memory_hints = await extract_memory_from_response(response_content, body.message)
            for hint in (memory_hints or []):
                if hint:
                    await save_memory(
                        user_id,
                        hint.get("memory_type", "general"),
                        hint.get("content", ""),
                        db,
                    )
        except Exception as exc:
            logger.warning("Memory extraction failed for user %s: %s", user_id, exc)

    # 12. Log usage analytics
    await _upsert_usage_analytics(user_id, agent_type_used, tokens_used, db)

    # 13. Return response
    return {
        "message_id": message_id,
        "response": response_content,
        "agent_type": agent_type_used,
        "suggested_actions": suggested_actions,
        "sources": sources,
        "tokens_used": tokens_used,
        "conversation_title": conversation_title,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/memory")
async def list_memory(user: dict = Depends(get_current_user)):
    """Return all active memory items for the authenticated user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    if not _memory_service_available:
        # Fallback: query directly
        cursor = db.ai_memory.find({"user_id": user_id, "is_active": True})
        items = await cursor.to_list(500)
        return [
            {
                "id": str(m["_id"]),
                "memory_type": m.get("memory_type"),
                "content": m.get("content"),
                "created_at": m.get("created_at"),
                "updated_at": m.get("updated_at"),
            }
            for m in items
        ]

    try:
        items = await get_user_memory(user_id, db)
        return items or []
    except Exception as exc:
        logger.error("get_user_memory failed: %s", exc)
        raise HTTPException(status_code=503, detail="Memory service unavailable")


@router.post("/memory")
async def create_memory(
    body: SaveMemoryBody,
    user: dict = Depends(get_current_user),
):
    """Manually save a memory item."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    if body.memory_type not in _VALID_MEMORY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid memory_type. Valid types: {sorted(_VALID_MEMORY_TYPES)}",
        )
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Content cannot be empty")

    if not _memory_service_available:
        # Fallback: insert directly
        now_str = _now_iso()
        doc = {
            "user_id": user_id,
            "memory_type": body.memory_type,
            "content": body.content.strip(),
            "is_active": True,
            "created_at": now_str,
            "updated_at": now_str,
        }
        result = await db.ai_memory.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _ser(doc)

    try:
        item = await save_memory(user_id, body.memory_type, body.content.strip(), db)
        return item
    except Exception as exc:
        logger.error("save_memory failed: %s", exc)
        raise HTTPException(status_code=503, detail="Memory service unavailable")


@router.delete("/memory/{memory_id}")
async def delete_memory_item(
    memory_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a specific memory item (must belong to user)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    try:
        oid = ObjectId(memory_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Memory item not found")

    # Verify ownership
    item = await db.ai_memory.find_one({"_id": oid})
    if not item:
        raise HTTPException(status_code=404, detail="Memory item not found")
    if item.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not _memory_service_available:
        await db.ai_memory.update_one({"_id": oid}, {"$set": {"is_active": False}})
        return {"success": True, "deleted": memory_id}

    try:
        await delete_memory(user_id, memory_id, db)
        return {"success": True, "deleted": memory_id}
    except Exception as exc:
        logger.error("delete_memory failed: %s", exc)
        raise HTTPException(status_code=503, detail="Memory service unavailable")


@router.delete("/memory")
async def clear_memory(user: dict = Depends(get_current_user)):
    """GDPR: delete ALL memory items for the authenticated user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    if not _memory_service_available:
        result = await db.ai_memory.update_many(
            {"user_id": user_id, "is_active": True},
            {"$set": {"is_active": False, "updated_at": _now_iso()}},
        )
        return {"deleted_count": result.modified_count}

    try:
        result = await clear_all_memory(user_id, db)
        return result
    except Exception as exc:
        logger.error("clear_all_memory failed: %s", exc)
        raise HTTPException(status_code=503, detail="Memory service unavailable")


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/actions/execute")
async def execute_platform_action(
    body: ExecuteActionBody,
    user: dict = Depends(get_current_user),
):
    """Execute a platform action via the AI OS action executor."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    if not _action_executor_available:
        raise HTTPException(
            status_code=503,
            detail="Action executor service is not available.",
        )

    try:
        result = await execute_action(user_id, body.action_type, body.params, db)
    except Exception as exc:
        logger.error("execute_action failed for user %s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail=f"Action execution failed: {str(exc)[:200]}")

    action_id: str = ""
    try:
        action_id = await log_action(
            user_id=user_id,
            conv_id=body.conv_id,
            action_type=body.action_type,
            params=body.params,
            status=result.get("status", "completed"),
            result=result,
            confirmed=True,
            db=db,
        )
    except Exception as exc:
        logger.warning("log_action failed: %s", exc)

    return {
        "success": result.get("success", True),
        "action_type": body.action_type,
        "result": result,
        "message": result.get("message", "Action completed"),
        "action_id": action_id,
    }


@router.get("/actions/available")
async def list_available_actions(user: dict = Depends(get_current_user)):
    """Return list of available platform actions."""
    if not _action_executor_available:
        raise HTTPException(
            status_code=503,
            detail="Action executor service is not available.",
        )
    # AVAILABLE_ACTIONS is imported from action_executor (may be a dict or list)
    if isinstance(AVAILABLE_ACTIONS, dict):
        return [
            {"action_type": k, **v} if isinstance(v, dict) else {"action_type": k, "description": str(v)}
            for k, v in AVAILABLE_ACTIONS.items()
        ]
    return AVAILABLE_ACTIONS


@router.get("/actions")
async def list_actions(
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """List user's recent AI-executed actions."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    cursor = (
        db.ai_actions.find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    actions = await cursor.to_list(limit)
    return _ser_list(actions)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT & INSIGHTS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/context")
async def get_context(user: dict = Depends(get_current_user)):
    """Return the user's current cached context summary."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]
    return await _build_context_summary(user_id, db, force_refresh=False)


@router.post("/context/refresh")
async def refresh_context(user: dict = Depends(get_current_user)):
    """Force-refresh the user context cache and return the new summary."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]
    return await _build_context_summary(user_id, db, force_refresh=True)


@router.get("/insights")
async def get_insights(
    limit: int = Query(6, ge=1, le=20),
    user: dict = Depends(get_current_user),
):
    """Return proactive AI insights for the user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id: str = user["id"]

    if not _insights_engine_available:
        raise HTTPException(
            status_code=503,
            detail="Insights engine service is not available.",
        )

    try:
        insights = await generate_insights(user_id, db)
        return (insights or [])[:limit]
    except Exception as exc:
        logger.error("generate_insights failed for user %s: %s", user_id, exc)
        raise HTTPException(status_code=503, detail="Insights engine error")


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT INFO ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/agents")
async def list_agents(user: dict = Depends(get_current_user)):
    """Return the list of available AI agents and their descriptions."""
    return _AGENTS
