"""Admin AI Center — Phase XXIII.

Platform-wide analytics and operational visibility for the Synaptiq AI Operating
System. All endpoints require admin or super_admin role.

Routes
------
GET  /api/admin/ai/stats               — platform-wide AI OS statistics
GET  /api/admin/ai/top-users           — top users by AI usage
GET  /api/admin/ai/agent-performance   — per-agent statistics
GET  /api/admin/ai/actions-log         — recent AI actions log
GET  /api/admin/ai/memory-stats        — memory usage statistics
GET  /api/admin/ai/conversations       — recent conversations (anonymized)
GET  /api/admin/ai/cost-analytics      — estimated cost analytics
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

logger = logging.getLogger("synaptiq.admin_ai_center")

router = APIRouter(prefix="/api/admin/ai", tags=["admin-ai"])

# Rough Claude Sonnet pricing: $3 per 1M tokens (output) — used for estimates
_COST_PER_TOKEN_USD = 0.000003


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require_admin(user: dict) -> None:
    zt_check(user, "admin", "admin")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _days_ago_iso(days: int) -> str:
    return (_now() - timedelta(days=days)).isoformat()


def _date_str(days_back: int = 0) -> str:
    return (_now() - timedelta(days=days_back)).strftime("%Y-%m-%d")


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


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/admin/ai/stats
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/stats")
async def platform_ai_stats(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
):
    """Platform-wide AI OS statistics aggregated from ai_usage_analytics."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    since_date = _date_str(days)

    # ── Totals from ai_usage_analytics ───────────────────────────────────────
    totals_pipeline = [
        {"$match": {"date": {"$gte": since_date}}},
        {
            "$group": {
                "_id": None,
                "total_messages": {"$sum": "$message_count"},
                "total_tokens": {"$sum": "$tokens_used"},
                "total_actions": {"$sum": "$actions_count"},
                "unique_users": {"$addToSet": "$user_id"},
            }
        },
    ]
    totals_result = await db.ai_usage_analytics.aggregate(totals_pipeline).to_list(1)
    totals = totals_result[0] if totals_result else {}

    total_messages: int = totals.get("total_messages", 0) or 0
    total_tokens: int = totals.get("total_tokens", 0) or 0
    total_actions: int = totals.get("total_actions", 0) or 0
    active_users: int = len(totals.get("unique_users", []))

    avg_messages_per_user: float = round(total_messages / active_users, 2) if active_users else 0.0

    # ── Total conversations ────────────────────────────────────────────────────
    since_iso = _days_ago_iso(days)
    total_conversations = await db.ai_conversations.count_documents(
        {"created_at": {"$gte": since_iso}}
    )

    # ── By agent type ─────────────────────────────────────────────────────────
    agent_pipeline = [
        {"$match": {"date": {"$gte": since_date}}},
        {
            "$group": {
                "_id": "$agent_type",
                "message_count": {"$sum": "$message_count"},
            }
        },
        {"$sort": {"message_count": -1}},
    ]
    agent_results = await db.ai_usage_analytics.aggregate(agent_pipeline).to_list(50)

    by_agent_type = []
    for row in agent_results:
        count = row.get("message_count", 0) or 0
        pct = round(count / total_messages * 100, 1) if total_messages else 0.0
        by_agent_type.append({
            "agent_type": row.get("_id") or "unknown",
            "message_count": count,
            "pct": pct,
        })

    # ── Daily activity (last N days) ──────────────────────────────────────────
    daily_pipeline = [
        {"$match": {"date": {"$gte": since_date}}},
        {
            "$group": {
                "_id": "$date",
                "messages": {"$sum": "$message_count"},
                "users": {"$addToSet": "$user_id"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    daily_results = await db.ai_usage_analytics.aggregate(daily_pipeline).to_list(400)
    daily_activity = [
        {
            "date": row["_id"],
            "messages": row.get("messages", 0) or 0,
            "users": len(row.get("users", [])),
        }
        for row in daily_results
    ]

    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_tokens_used": total_tokens,
        "total_actions_executed": total_actions,
        "active_users": active_users,
        "avg_messages_per_user": avg_messages_per_user,
        "by_agent_type": by_agent_type,
        "daily_activity": daily_activity,
        "generated_at": _now_iso(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/admin/ai/top-users
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/top-users")
async def top_users_by_ai_usage(
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
):
    """Top users by AI usage, joined with user profile data."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    since_date = _date_str(days)

    pipeline = [
        {"$match": {"date": {"$gte": since_date}}},
        {
            "$group": {
                "_id": "$user_id",
                "total_messages": {"$sum": "$message_count"},
                "total_tokens": {"$sum": "$tokens_used"},
                "total_actions": {"$sum": "$actions_count"},
                "days_active": {"$addToSet": "$date"},
            }
        },
        {"$sort": {"total_messages": -1}},
        {"$limit": limit},
    ]

    results = await db.ai_usage_analytics.aggregate(pipeline).to_list(limit)

    # Enrich with user details
    enriched = []
    for row in results:
        uid = row.get("_id")
        user_doc: dict = {}
        if uid:
            try:
                u = await db.users.find_one(
                    {"_id": ObjectId(uid)},
                    {"first_name": 1, "last_name": 1, "email": 1, "institution": 1},
                )
                if u:
                    user_doc = {
                        "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
                        "email": u.get("email", ""),
                        "institution": u.get("institution", ""),
                    }
            except Exception:
                pass

        enriched.append({
            "user_id": uid,
            **user_doc,
            "total_messages": row.get("total_messages", 0) or 0,
            "total_tokens": row.get("total_tokens", 0) or 0,
            "total_actions": row.get("total_actions", 0) or 0,
            "days_active": len(row.get("days_active", [])),
        })

    return enriched


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/admin/ai/agent-performance
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/agent-performance")
async def agent_performance(user: dict = Depends(get_current_user)):
    """Per-agent statistics: message counts, token usage, avg response length."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    pipeline = [
        {"$match": {"role": "assistant"}},
        {
            "$group": {
                "_id": "$agent_type",
                "message_count": {"$sum": 1},
                "total_tokens": {"$sum": "$tokens_used"},
                "avg_tokens": {"$avg": "$tokens_used"},
                "total_content_length": {
                    "$sum": {"$strLenCP": {"$ifNull": ["$content", ""]}}
                },
                "avg_content_length": {
                    "$avg": {"$strLenCP": {"$ifNull": ["$content", ""]}}
                },
            }
        },
        {"$sort": {"message_count": -1}},
    ]

    results = await db.ai_messages.aggregate(pipeline).to_list(50)

    return [
        {
            "agent_type": row.get("_id") or "unknown",
            "message_count": row.get("message_count", 0) or 0,
            "total_tokens": row.get("total_tokens", 0) or 0,
            "avg_tokens_per_response": round(row.get("avg_tokens", 0) or 0, 1),
            "avg_response_length_chars": round(row.get("avg_content_length", 0) or 0, 0),
        }
        for row in results
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/admin/ai/actions-log
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/actions-log")
async def actions_log(
    limit: int = Query(100, ge=1, le=500),
    action_type: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """Recent AI actions, joined with user display names."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    filt: dict = {}
    if action_type:
        filt["action_type"] = action_type

    cursor = db.ai_actions.find(filt).sort("created_at", -1).limit(limit)
    actions = await cursor.to_list(limit)

    enriched = []
    for action in actions:
        uid = action.get("user_id")
        user_name = ""
        if uid:
            try:
                u = await db.users.find_one(
                    {"_id": ObjectId(uid)},
                    {"first_name": 1, "last_name": 1, "email": 1},
                )
                if u:
                    user_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("email", "")
            except Exception:
                pass

        doc = _ser(action)
        doc["user_name"] = user_name
        enriched.append(doc)

    return enriched


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/admin/ai/memory-stats
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/memory-stats")
async def memory_stats(user: dict = Depends(get_current_user)):
    """Memory usage statistics: totals, type distribution, active users."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    total_items = await db.ai_memory.count_documents({"is_active": True})

    # Distribution by memory_type
    type_pipeline = [
        {"$match": {"is_active": True}},
        {
            "$group": {
                "_id": "$memory_type",
                "count": {"$sum": 1},
                "unique_users": {"$addToSet": "$user_id"},
            }
        },
        {"$sort": {"count": -1}},
    ]
    type_results = await db.ai_memory.aggregate(type_pipeline).to_list(50)

    by_type = [
        {
            "memory_type": row.get("_id") or "unknown",
            "count": row.get("count", 0),
            "unique_users": len(row.get("unique_users", [])),
        }
        for row in type_results
    ]

    # Users with at least one active memory item
    users_pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "total"},
    ]
    users_result = await db.ai_memory.aggregate(users_pipeline).to_list(1)
    users_with_memory = users_result[0].get("total", 0) if users_result else 0

    return {
        "total_memory_items": total_items,
        "users_with_memory": users_with_memory,
        "by_memory_type": by_type,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/admin/ai/conversations
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/conversations")
async def admin_conversations(
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    """
    Recent conversations — anonymized admin view.
    Returns count, agent_type, message_count only. No message content.
    """
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    cursor = db.ai_conversations.find({}).sort("created_at", -1).limit(limit)
    conversations = await cursor.to_list(limit)

    return [
        {
            "id": str(conv["_id"]),
            "agent_type": conv.get("agent_type"),
            "message_count": conv.get("message_count", 0),
            "archived": conv.get("archived", False),
            "pinned": conv.get("pinned", False),
            "created_at": conv.get("created_at"),
            "updated_at": conv.get("updated_at"),
        }
        for conv in conversations
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/admin/ai/cost-analytics
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/cost-analytics")
async def cost_analytics(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
):
    """Estimated cost analytics based on token usage."""
    _require_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    since_date = _date_str(days)

    # Total tokens
    totals_pipeline = [
        {"$match": {"date": {"$gte": since_date}}},
        {
            "$group": {
                "_id": None,
                "total_tokens": {"$sum": "$tokens_used"},
                "total_messages": {"$sum": "$message_count"},
            }
        },
    ]
    totals_result = await db.ai_usage_analytics.aggregate(totals_pipeline).to_list(1)
    totals = totals_result[0] if totals_result else {}

    total_tokens: int = totals.get("total_tokens", 0) or 0
    total_messages: int = totals.get("total_messages", 0) or 0
    estimated_cost_usd: float = round(total_tokens * _COST_PER_TOKEN_USD, 4)

    # Cost by date
    daily_pipeline = [
        {"$match": {"date": {"$gte": since_date}}},
        {
            "$group": {
                "_id": "$date",
                "tokens": {"$sum": "$tokens_used"},
                "messages": {"$sum": "$message_count"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    daily_results = await db.ai_usage_analytics.aggregate(daily_pipeline).to_list(400)
    cost_by_date = [
        {
            "date": row["_id"],
            "tokens": row.get("tokens", 0) or 0,
            "messages": row.get("messages", 0) or 0,
            "estimated_cost_usd": round((row.get("tokens", 0) or 0) * _COST_PER_TOKEN_USD, 4),
        }
        for row in daily_results
    ]

    # Cost by agent type
    agent_pipeline = [
        {"$match": {"date": {"$gte": since_date}}},
        {
            "$group": {
                "_id": "$agent_type",
                "tokens": {"$sum": "$tokens_used"},
                "messages": {"$sum": "$message_count"},
            }
        },
        {"$sort": {"tokens": -1}},
    ]
    agent_results = await db.ai_usage_analytics.aggregate(agent_pipeline).to_list(50)
    cost_by_agent = [
        {
            "agent_type": row.get("_id") or "unknown",
            "tokens": row.get("tokens", 0) or 0,
            "messages": row.get("messages", 0) or 0,
            "estimated_cost_usd": round((row.get("tokens", 0) or 0) * _COST_PER_TOKEN_USD, 4),
        }
        for row in agent_results
    ]

    return {
        "period_days": days,
        "total_tokens": total_tokens,
        "total_messages": total_messages,
        "estimated_cost_usd": estimated_cost_usd,
        "cost_per_token_usd": _COST_PER_TOKEN_USD,
        "cost_by_date": cost_by_date,
        "cost_by_agent_type": cost_by_agent,
        "generated_at": _now_iso(),
    }
