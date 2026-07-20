"""Teaching Analytics — Phase 9.

Dedicated analytics module for the Teaching Hub. All metrics are derived
exclusively from real platform collections — no mock data, no hardcoded values.

Endpoints (all require authentication):
  GET /api/teaching-analytics/overview       — summary stats across all teaching activity
  GET /api/teaching-analytics/lessons        — lesson creation & growth trends
  GET /api/teaching-analytics/assessments    — assessment analytics
  GET /api/teaching-analytics/workspaces     — workspace analytics + health scores
  GET /api/teaching-analytics/collaboration  — collaboration analytics
  GET /api/teaching-analytics/ai-usage       — AI assistant usage analytics
  GET /api/teaching-analytics/portfolio      — portfolio analytics
  GET /api/teaching-analytics/reputation     — reputation integration (Phase 7)
  GET /api/teaching-analytics/productivity   — productivity score + suggestions
  GET /api/teaching-analytics/insights       — auto-generated growth insights
  GET /api/teaching-analytics/admin/overview — platform-wide analytics (super admin only)
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger("synaptiq.teaching_analytics")
router = APIRouter(prefix="/api/teaching-analytics", tags=["teaching-analytics"])

# ── In-memory cache (5-minute TTL — safe for single-process deployments) ──────
_CACHE: dict[str, tuple[float, object]] = {}
_TTL = 300  # seconds

def _cached(key: str) -> object | None:
    entry = _CACHE.get(key)
    return entry[1] if entry and time.monotonic() - entry[0] < _TTL else None

def _cache_put(key: str, data: object) -> object:
    _CACHE[key] = (time.monotonic(), data)
    return data

# ── Period helpers ─────────────────────────────────────────────────────────────
PERIOD_DAYS: dict[str, int] = {"today": 1, "7d": 7, "30d": 30, "90d": 90}

def _cutoff(period: str) -> str | None:
    d = PERIOD_DAYS.get(period)
    return None if d is None else (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()

def _df(cutoff: str | None) -> dict:
    return {"created_at": {"$gte": cutoff}} if cutoff else {}

# ── Scoring helpers ────────────────────────────────────────────────────────────
def _sat(x: float, scale: float) -> float:
    """Log-saturation: approaches 1.0 as x grows. Prevents gaming."""
    return 1.0 - math.exp(-max(x, 0) / max(scale, 0.001))

def _ws_health(activity_30d: int, member_count: int, comments_30d: int, content_count: int) -> int:
    a = 40 * _sat(activity_30d, 8)
    m = 30 * _sat(max(member_count - 1, 0), 4)
    c = 20 * _sat(comments_30d, 6)
    n = 10 * _sat(content_count, 4)
    return min(100, round(a + m + c + n))

def _health_label(score: int) -> str:
    if score >= 80: return "Excellent"
    if score >= 60: return "Healthy"
    if score >= 40: return "Needs Attention"
    return "Inactive"

def _productivity_score(
    lessons: int, assessments: int, ws_activity: int,
    invites: int, versions: int, comments: int,
    ai_sessions: int, portfolio: int,
) -> int:
    content = 35 * _sat(lessons + assessments * 0.8, 10)
    collab  = 25 * _sat(ws_activity * 0.5 + invites * 2, 15)
    depth   = 20 * _sat(versions + comments * 0.5, 8)
    growth  = 20 * _sat(ai_sessions * 0.5 + portfolio, 8)
    return min(100, round(content + collab + depth + growth))

# ── Admin guard ────────────────────────────────────────────────────────────────
async def _require_admin(user: dict = Depends(get_current_user)) -> dict:
    zt_check(user, "admin", "security")
    return user

# ── Aggregation helpers ────────────────────────────────────────────────────────
async def _trend(db, coll: str, match: dict) -> list[dict]:
    cursor = db[coll].aggregate([
        {"$match": match},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ])
    return [{"date": r["_id"], "count": r["count"]} async for r in cursor]

async def _group_dist(db, coll: str, match: dict, field: str, limit: int = 12) -> list[dict]:
    cursor = db[coll].aggregate([
        {"$match": match},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ])
    return [{"label": r["_id"] or "Other", "count": r["count"]} async for r in cursor]


# ══════════════════════════════════════════════════════════════════════════════
# 1. Overview
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/overview")
async def overview(
    period: str = Query("30d", pattern="^(today|7d|30d|90d|all)$"),
    user: dict = Depends(get_current_user),
):
    uid = user["id"]
    cache_key = f"ta:overview:{uid}:{period}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut = _cutoff(period)
    period_filter = _df(cut)

    ws_all    = {"$or": [{"owner_id": uid}, {"member_ids": uid}]}
    ws_period = {**ws_all, **period_filter} if period_filter else ws_all

    (
        lessons_total, lessons_period,
        assess_total, assess_period,
        ws_total, ws_period_count,
        portfolio_total, portfolio_period,
        ai_total, ai_period,
        invites_total, invites_period,
        collab_total, collab_period,
    ) = await asyncio.gather(
        db.teaching_lessons.count_documents({"owner_id": uid}),
        db.teaching_lessons.count_documents({"owner_id": uid, **period_filter}),
        db.teaching_assessments.count_documents({"owner_id": uid}),
        db.teaching_assessments.count_documents({"owner_id": uid, **period_filter}),
        db.teaching_workspaces.count_documents(ws_all),
        db.teaching_workspaces.count_documents(ws_period),
        db.teaching_portfolio_items.count_documents({"owner_id": uid}),
        db.teaching_portfolio_items.count_documents({"owner_id": uid, **period_filter}),
        db.teaching_chat_messages.count_documents({"owner_id": uid, "role": "user"}),
        db.teaching_chat_messages.count_documents({"owner_id": uid, "role": "user", **period_filter}),
        db.teaching_workspace_invitations.count_documents({"inviter_id": uid}),
        db.teaching_workspace_invitations.count_documents({"inviter_id": uid, **period_filter}),
        db.collaborations.count_documents({"members": uid}),
        db.collaborations.count_documents({"members": uid, **period_filter}),
    )

    rep = await db.reputation_scores.find_one(
        {"user_id": uid}, {"teaching_score": 1, "community_score": 1, "overall": 1}
    )

    result = {
        "period": period,
        "totals": {
            "lessons":         lessons_total,
            "assessments":     assess_total,
            "workspaces":      ws_total,
            "portfolio_items": portfolio_total,
            "ai_sessions":     ai_total,
            "collaborations":  collab_total,
            "invitations":     invites_total,
        },
        "period_counts": {
            "lessons":         lessons_period,
            "assessments":     assess_period,
            "workspaces":      ws_period_count,
            "portfolio_items": portfolio_period,
            "ai_sessions":     ai_period,
            "collaborations":  collab_period,
            "invitations":     invites_period,
        },
        "reputation": {
            "teaching_score":  round(rep.get("teaching_score", 0)) if rep else 0,
            "community_score": round(rep.get("community_score", 0)) if rep else 0,
            "overall":         round(rep.get("overall", 0)) if rep else 0,
        },
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Lessons
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/lessons")
async def lesson_analytics(
    period: str = Query("30d", pattern="^(today|7d|30d|90d|all)$"),
    user: dict = Depends(get_current_user),
):
    uid = user["id"]
    cache_key = f"ta:lessons:{uid}:{period}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut = _cutoff(period)
    pf = _df(cut)
    own = {"owner_id": uid}
    own_p = {**own, **pf}

    (
        created, versions_count, collab_edited, restored,
    ) = await asyncio.gather(
        db.teaching_lessons.count_documents(own_p),
        db.teaching_lesson_versions.count_documents({"author_id": uid, **pf}),
        db.teaching_lessons.count_documents({
            "owner_id": uid,
            "updated_by": {"$exists": True, "$ne": uid},
            **({"updated_at": {"$gte": cut}} if cut else {}),
        }),
        db.teaching_workspace_activity.count_documents(
            {"actor_id": uid, "kind": "lesson_restored", **pf}
        ),
    )

    updated_count = await db.teaching_lessons.count_documents(
        {"owner_id": uid, **({"updated_at": {"$gte": cut}} if cut else {})}
    )

    trend_data  = await _trend(db, "teaching_lessons", own_p if pf else own)
    by_subject  = await _group_dist(db, "teaching_lessons", own, "subject")
    by_level    = await _group_dist(db, "teaching_lessons", own, "level")
    by_status   = await _group_dist(db, "teaching_lessons", own, "status")

    result = {
        "period": period,
        "created": created,
        "updated": updated_count,
        "collab_edited": collab_edited,
        "versions_saved": versions_count,
        "restored": restored,
        "trend": trend_data,
        "by_subject": by_subject,
        "by_level": by_level,
        "by_status": by_status,
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Assessments
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/assessments")
async def assessment_analytics(
    period: str = Query("30d", pattern="^(today|7d|30d|90d|all)$"),
    user: dict = Depends(get_current_user),
):
    uid = user["id"]
    cache_key = f"ta:assessments:{uid}:{period}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut = _cutoff(period)
    pf  = _df(cut)
    own = {"owner_id": uid}
    own_p = {**own, **pf}

    (
        created, versions_count, rubrics_count,
    ) = await asyncio.gather(
        db.teaching_assessments.count_documents(own_p),
        db.teaching_assessment_versions.count_documents({"author_id": uid, **pf}),
        db.teaching_assessments.count_documents({"owner_id": uid, "assessment_type": "rubric"}),
    )

    collab_edited = await db.teaching_assessments.count_documents({
        "owner_id": uid,
        "updated_by": {"$exists": True, "$ne": uid},
        **({"updated_at": {"$gte": cut}} if cut else {}),
    })

    q_result = [r async for r in db.teaching_assessments.aggregate([
        {"$match": own},
        {"$project": {"q_count": {"$size": {"$ifNull": ["$questions", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$q_count"}}},
    ])]
    total_questions = q_result[0]["total"] if q_result else 0

    trend_data  = await _trend(db, "teaching_assessments", own_p if pf else own)
    by_type     = await _group_dist(db, "teaching_assessments", own, "assessment_type")
    by_subject  = await _group_dist(db, "teaching_assessments", own, "subject")
    by_level    = await _group_dist(db, "teaching_assessments", own, "level")

    result = {
        "period": period,
        "created": created,
        "versions_saved": versions_count,
        "collab_edited": collab_edited,
        "total_questions": total_questions,
        "rubrics_created": rubrics_count,
        "trend": trend_data,
        "by_type": by_type,
        "by_subject": by_subject,
        "by_level": by_level,
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Workspaces
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/workspaces")
async def workspace_analytics(
    period: str = Query("30d", pattern="^(today|7d|30d|90d|all)$"),
    user: dict = Depends(get_current_user),
):
    uid = user["id"]
    cache_key = f"ta:workspaces:{uid}:{period}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut    = _cutoff(period)
    cut30  = _cutoff("30d")
    pf     = _df(cut)

    ws_list = await db.teaching_workspaces.find(
        {"$or": [{"owner_id": uid}, {"member_ids": uid}]}
    ).to_list(200)
    ws_ids = [str(ws["_id"]) for ws in ws_list]

    # Batch-aggregate activity and comments per workspace (30d for health)
    act_by_ws: dict[str, int] = {}
    cmt_by_ws: dict[str, int] = {}
    if ws_ids:
        act_pipe = [
            {"$match": {"workspace_id": {"$in": ws_ids}, "created_at": {"$gte": cut30}}},
            {"$group": {"_id": "$workspace_id", "count": {"$sum": 1}}},
        ]
        cmt_pipe = [
            {"$match": {"workspace_id": {"$in": ws_ids}, "created_at": {"$gte": cut30}}},
            {"$group": {"_id": "$workspace_id", "count": {"$sum": 1}}},
        ]
        async for r in db.teaching_workspace_activity.aggregate(act_pipe):
            act_by_ws[r["_id"]] = r["count"]
        async for r in db.teaching_workspace_comments.aggregate(cmt_pipe):
            cmt_by_ws[r["_id"]] = r["count"]

    (
        created_period,
        invites_sent, invites_accepted,
        comments_period, version_events,
    ) = await asyncio.gather(
        db.teaching_workspaces.count_documents({"owner_id": uid, **pf}),
        db.teaching_workspace_invitations.count_documents({"inviter_id": uid, **pf}),
        db.teaching_workspace_invitations.count_documents({"inviter_id": uid, "status": "accepted", **pf}),
        db.teaching_workspace_comments.count_documents({"author_id": uid, **pf}),
        db.teaching_workspace_activity.count_documents({
            "actor_id": uid,
            "kind": {"$in": ["lesson_restored", "assessment_restored"]},
            **pf,
        }),
    )

    role_dist: dict[str, int] = {}
    workspace_health: list[dict] = []
    for ws in ws_list:
        ws_id = str(ws["_id"])
        if ws.get("owner_id") == uid:
            for mid, role in (ws.get("member_roles") or {}).items():
                if mid != uid:
                    role_dist[role] = role_dist.get(role, 0) + 1
        member_count  = len(ws.get("member_ids") or []) + 1
        content_count = len(ws.get("linked_lesson_ids") or []) + len(ws.get("linked_assessment_ids") or [])
        health = _ws_health(
            act_by_ws.get(ws_id, 0),
            member_count,
            cmt_by_ws.get(ws_id, 0),
            content_count,
        )
        workspace_health.append({
            "id": ws_id,
            "title": ws.get("title", ""),
            "health_score": health,
            "health_label": _health_label(health),
            "member_count": member_count,
            "activity_30d": act_by_ws.get(ws_id, 0),
            "comments_30d": cmt_by_ws.get(ws_id, 0),
            "lessons": len(ws.get("linked_lesson_ids") or []),
            "assessments": len(ws.get("linked_assessment_ids") or []),
            "status": ws.get("status", "active"),
            "my_role": (ws.get("member_roles") or {}).get(uid, "workspace_owner" if ws.get("owner_id") == uid else "observer"),
        })
    workspace_health.sort(key=lambda x: x["health_score"], reverse=True)

    result = {
        "period": period,
        "total_workspaces": len(ws_list),
        "created": created_period,
        "invites_sent": invites_sent,
        "invites_accepted": invites_accepted,
        "comments": comments_period,
        "version_events": version_events,
        "role_distribution": [{"role": k, "count": v} for k, v in role_dist.items()],
        "workspace_health": workspace_health[:20],
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Collaboration
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/collaboration")
async def collaboration_analytics(
    period: str = Query("30d", pattern="^(today|7d|30d|90d|all)$"),
    user: dict = Depends(get_current_user),
):
    uid = user["id"]
    cache_key = f"ta:collab:{uid}:{period}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut = _cutoff(period)
    pf  = _df(cut)

    (
        collab_total, collab_period,
        inv_sent, inv_accepted, inv_declined,
    ) = await asyncio.gather(
        db.collaborations.count_documents({"members": uid}),
        db.collaborations.count_documents({"members": uid, **pf}),
        db.teaching_workspace_invitations.count_documents({"inviter_id": uid, **pf}),
        db.teaching_workspace_invitations.count_documents({"inviter_id": uid, "status": "accepted", **pf}),
        db.teaching_workspace_invitations.count_documents({"inviter_id": uid, "status": "declined", **pf}),
    )

    # Top contributors to workspaces this user owns
    owned_ws_ids = [str(ws["_id"]) async for ws in db.teaching_workspaces.find({"owner_id": uid}, {"_id": 1})]
    contributor_dist: list[dict] = []
    if owned_ws_ids:
        contrib_pipe = [
            {"$match": {"workspace_id": {"$in": owned_ws_ids}, **pf}},
            {"$group": {
                "_id":       "$actor_id",
                "actor_name": {"$first": "$actor_name"},
                "count":     {"$sum": 1},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        contributor_dist = [
            {"name": r.get("actor_name") or "Unknown", "contributions": r["count"]}
            async for r in db.teaching_workspace_activity.aggregate(contrib_pipe)
        ]

    by_collab_type = await _group_dist(db, "collaborations", {"members": uid}, "collab_type")

    result = {
        "period": period,
        "collaborations": collab_period,
        "collaborations_total": collab_total,
        "invites_sent": inv_sent,
        "invites_accepted": inv_accepted,
        "invites_declined": inv_declined,
        "acceptance_rate": round(inv_accepted / inv_sent * 100) if inv_sent else 0,
        "top_contributors": contributor_dist,
        "by_collab_type": by_collab_type,
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 6. AI Usage
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/ai-usage")
async def ai_usage_analytics(
    period: str = Query("30d", pattern="^(today|7d|30d|90d|all)$"),
    user: dict = Depends(get_current_user),
):
    uid = user["id"]
    cache_key = f"ta:ai:{uid}:{period}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut = _cutoff(period)
    pf  = _df(cut)

    (
        total_messages, period_messages,
        lesson_gen_total, lesson_gen_period,
        assess_gen_total, assess_gen_period,
    ) = await asyncio.gather(
        db.teaching_chat_messages.count_documents({"owner_id": uid, "role": "user"}),
        db.teaching_chat_messages.count_documents({"owner_id": uid, "role": "user", **pf}),
        db.teaching_lessons.count_documents({"owner_id": uid, "generated": True}),
        db.teaching_lessons.count_documents({"owner_id": uid, "generated": True, **pf}),
        db.teaching_assessments.count_documents({"owner_id": uid, "generated": True}),
        db.teaching_assessments.count_documents({"owner_id": uid, "generated": True, **pf}),
    )

    trend_data = await _trend(
        db, "teaching_chat_messages",
        {"owner_id": uid, "role": "user", **pf} if pf else {"owner_id": uid, "role": "user"},
    )

    # Per-workspace message distribution
    ws_dist_pipe = [
        {"$match": {"owner_id": uid, "role": "user", **pf}},
        {"$group": {"_id": "$workspace_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    ws_ids_with_counts: list[tuple[str, int]] = [
        (r["_id"], r["count"]) async for r in db.teaching_chat_messages.aggregate(ws_dist_pipe)
    ]
    ws_titles: dict[str, str] = {}
    if ws_ids_with_counts:
        from bson import ObjectId
        def _try_oid(s):
            try: return ObjectId(s)
            except Exception: return None
        oids = [o for s, _ in ws_ids_with_counts if (o := _try_oid(s))]
        if oids:
            async for ws in db.teaching_workspaces.find({"_id": {"$in": oids}}, {"title": 1}):
                ws_titles[str(ws["_id"])] = ws.get("title", "")
    by_workspace = [
        {"workspace": ws_titles.get(ws_id) or ws_id or "Unknown", "messages": cnt}
        for ws_id, cnt in ws_ids_with_counts
    ]

    result = {
        "period": period,
        "total_messages": total_messages,
        "period_messages": period_messages,
        "credits_consumed": period_messages * 2,
        "lesson_plans_generated": lesson_gen_period,
        "lesson_plans_generated_total": lesson_gen_total,
        "assessments_generated": assess_gen_period,
        "assessments_generated_total": assess_gen_total,
        "trend": trend_data,
        "by_workspace": by_workspace,
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Portfolio
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/portfolio")
async def portfolio_analytics(
    period: str = Query("30d", pattern="^(today|7d|30d|90d|all)$"),
    user: dict = Depends(get_current_user),
):
    uid = user["id"]
    cache_key = f"ta:portfolio:{uid}:{period}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut = _cutoff(period)
    pf  = _df(cut)
    own = {"owner_id": uid}

    (total_items, period_items, featured_count) = await asyncio.gather(
        db.teaching_portfolio_items.count_documents(own),
        db.teaching_portfolio_items.count_documents({**own, **pf}),
        db.teaching_portfolio_items.count_documents({**own, "featured": True}),
    )

    trend_data = await _trend(db, "teaching_portfolio_items", {**own, **pf} if pf else own)
    by_type    = await _group_dist(db, "teaching_portfolio_items", own, "item_type")

    IDEAL_TYPES = {"lesson", "course", "assessment", "achievement", "reflection", "publication"}
    present_types = {r["label"] for r in by_type if r["count"] > 0}
    completeness = round(len(present_types & IDEAL_TYPES) / len(IDEAL_TYPES) * 100)

    timeline = [
        {
            "title":    d.get("title", ""),
            "type":     d.get("item_type", ""),
            "date":     d.get("date", ""),
            "featured": d.get("featured", False),
        }
        async for d in db.teaching_portfolio_items.find(
            own, {"title": 1, "item_type": 1, "date": 1, "featured": 1}
        ).sort("date", -1).limit(10)
    ]

    result = {
        "period": period,
        "total_items": total_items,
        "period_items": period_items,
        "featured_items": featured_count,
        "completeness_score": completeness,
        "trend": trend_data,
        "by_type": by_type,
        "timeline": timeline,
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 8. Reputation
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/reputation")
async def reputation_analytics(user: dict = Depends(get_current_user)):
    uid = user["id"]
    cache_key = f"ta:reputation:{uid}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    rep        = await db.reputation_scores.find_one({"user_id": uid})
    badges_doc = await db.reputation_badges.find_one({"user_id": uid})

    if not rep:
        return _cache_put(cache_key, {
            "overall": 0, "teaching_score": 0, "community_score": 0, "research_score": 0,
            "badges": [], "badge_count": 0, "computed_at": None,
        })

    badges              = badges_doc.get("badges", []) if badges_doc else []
    teaching_badges     = [b for b in badges if b.get("category") == "teaching"]
    community_badges    = [b for b in badges if b.get("category") == "community"]
    research_badges     = [b for b in badges if b.get("category") == "research"]

    result = {
        "overall":               round(rep.get("overall", 0)),
        "teaching_score":        round(rep.get("teaching_score", 0)),
        "community_score":       round(rep.get("community_score", 0)),
        "research_score":        round(rep.get("research_score", 0)),
        "badge_count":           len(badges),
        "teaching_badge_count":  len(teaching_badges),
        "community_badge_count": len(community_badges),
        "research_badge_count":  len(research_badges),
        "badges":                badges[:12],
        "computed_at":           rep.get("computed_at"),
        "dimension_weights":     rep.get("dimension_weights", {}),
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 9. Productivity
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/productivity")
async def productivity_analytics(user: dict = Depends(get_current_user)):
    uid = user["id"]
    cache_key = f"ta:productivity:{uid}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut30 = _cutoff("30d")
    cut7  = _cutoff("7d")
    cut8w = (datetime.now(timezone.utc) - timedelta(weeks=8)).isoformat()

    pf30 = _df(cut30)
    pf7  = _df(cut7)

    (
        lessons_30, assess_30, portfolio_30, ai_30,
        ws_act_30, invites_30, versions_30, comments_30,
        lessons_7, assess_7,
    ) = await asyncio.gather(
        db.teaching_lessons.count_documents({"owner_id": uid, **pf30}),
        db.teaching_assessments.count_documents({"owner_id": uid, **pf30}),
        db.teaching_portfolio_items.count_documents({"owner_id": uid, **pf30}),
        db.teaching_chat_messages.count_documents({"owner_id": uid, "role": "user", **pf30}),
        db.teaching_workspace_activity.count_documents({"actor_id": uid, **pf30}),
        db.teaching_workspace_invitations.count_documents({"inviter_id": uid, **pf30}),
        db.teaching_lesson_versions.count_documents({"author_id": uid, **pf30}),
        db.teaching_workspace_comments.count_documents({"author_id": uid, **pf30}),
        db.teaching_lessons.count_documents({"owner_id": uid, **pf7}),
        db.teaching_assessments.count_documents({"owner_id": uid, **pf7}),
    )

    score = _productivity_score(
        lessons=lessons_30, assessments=assess_30, ws_activity=ws_act_30,
        invites=invites_30, versions=versions_30, comments=comments_30,
        ai_sessions=ai_30, portfolio=portfolio_30,
    )

    # Weekly trend: lessons + assessments per week (last 8 weeks)
    weekly_pipe = [
        {"$match": {"owner_id": uid, "created_at": {"$gte": cut8w}}},
        {"$addFields": {"day": {"$substr": ["$created_at", 0, 10]}}},
        {"$group": {
            "_id": {"$subtract": [
                {"$toLong": {"$dateFromString": {"dateString": "$day"}}},
                {"$mod": [
                    {"$subtract": [
                        {"$toLong": {"$dateFromString": {"dateString": "$day"}}},
                        {"$toLong": {"date": datetime(2024, 1, 1, tzinfo=timezone.utc)}},
                    ]},
                    604800000,
                ]},
            ]},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]

    suggestions: list[str] = []
    if lessons_30 == 0 and assess_30 == 0:
        suggestions.append("Start by creating a lesson plan to begin building your teaching activity.")
    if assess_30 == 0 and lessons_30 > 0:
        suggestions.append("You have lessons but no assessments — adding assessments completes the learning cycle.")
    if portfolio_30 == 0:
        suggestions.append("Add a portfolio item to document your teaching achievements this period.")
    if ai_30 == 0:
        suggestions.append("Try the AI Teaching Assistant to accelerate lesson and assessment design.")
    if invites_30 == 0 and ws_act_30 == 0:
        suggestions.append("Inviting a colleague to a teaching workspace can significantly boost collaboration impact.")
    if not suggestions:
        suggestions.append("Keep up the strong teaching activity — your productivity reflects consistent engagement.")

    result = {
        "productivity_score": score,
        "score_label": (
            "Excellent" if score >= 80 else
            "Good"      if score >= 60 else
            "Building"  if score >= 40 else
            "Getting Started"
        ),
        "components": {
            "content_creation": {"lessons": lessons_30, "assessments": assess_30},
            "collaboration":    {"workspace_activity": ws_act_30, "invitations": invites_30},
            "depth":            {"versions": versions_30, "comments": comments_30},
            "engagement":       {"ai_sessions": ai_30, "portfolio_items": portfolio_30},
        },
        "this_week": lessons_7 + assess_7,
        "suggestions": suggestions[:3],
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 10. Insights
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/insights")
async def growth_insights(user: dict = Depends(get_current_user)):
    uid = user["id"]
    cache_key = f"ta:insights:{uid}"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cut_now   = _cutoff("30d")
    cut_prior = _cutoff("90d")   # 90d-30d = prior 30d window

    (
        lessons_now, lessons_prior,
        assess_now, assess_prior,
        ai_now, ai_prior,
        portfolio_total,
        collab_total, ws_total,
    ) = await asyncio.gather(
        db.teaching_lessons.count_documents({"owner_id": uid, "created_at": {"$gte": cut_now}}),
        db.teaching_lessons.count_documents({"owner_id": uid, "created_at": {"$gte": cut_prior, "$lt": cut_now}}),
        db.teaching_assessments.count_documents({"owner_id": uid, "created_at": {"$gte": cut_now}}),
        db.teaching_assessments.count_documents({"owner_id": uid, "created_at": {"$gte": cut_prior, "$lt": cut_now}}),
        db.teaching_chat_messages.count_documents({"owner_id": uid, "role": "user", "created_at": {"$gte": cut_now}}),
        db.teaching_chat_messages.count_documents({"owner_id": uid, "role": "user", "created_at": {"$gte": cut_prior, "$lt": cut_now}}),
        db.teaching_portfolio_items.count_documents({"owner_id": uid}),
        db.collaborations.count_documents({"members": uid}),
        db.teaching_workspaces.count_documents({"$or": [{"owner_id": uid}, {"member_ids": uid}]}),
    )

    insights: list[dict] = []

    # Teaching activity growth
    if lessons_prior > 0 and lessons_now > lessons_prior:
        pct = round((lessons_now - lessons_prior) / lessons_prior * 100)
        if pct >= 10:
            insights.append({"type": "growth", "text": f"Teaching activity increased {pct}% over the last 30 days compared to the prior period.", "metric": "lessons"})
    elif lessons_now > 0 and lessons_prior == 0:
        insights.append({"type": "growth", "text": f"You created {lessons_now} lesson{'s' if lessons_now > 1 else ''} in the last 30 days — a strong start.", "metric": "lessons"})

    # Fastest growing activity
    growth_map = {
        "lesson creation":     lessons_now - lessons_prior,
        "assessment creation": assess_now  - assess_prior,
        "AI assistant usage":  ai_now      - ai_prior,
    }
    top_activity = max(growth_map, key=lambda k: growth_map[k])
    if growth_map[top_activity] > 0:
        insights.append({"type": "trend", "text": f"{top_activity.capitalize()} is your fastest growing teaching activity this period.", "metric": top_activity})

    # Portfolio completeness nudge
    if portfolio_total < 3:
        missing = 3 - portfolio_total
        insights.append({"type": "suggestion", "text": f"Adding {missing} more portfolio item{'s' if missing > 1 else ''} would improve your Teaching Reputation score.", "metric": "portfolio"})
    elif portfolio_total >= 5:
        insights.append({"type": "achievement", "text": f"Your portfolio has {portfolio_total} items — a well-documented teaching record.", "metric": "portfolio"})

    # Collaboration strength
    if collab_total >= 3:
        insights.append({"type": "strength", "text": f"You are involved in {collab_total} collaborations — your collaboration rate is above average.", "metric": "collaboration"})

    # AI adoption
    if ai_now > 10:
        insights.append({"type": "strength", "text": f"You had {ai_now} AI Teaching Assistant sessions this period — excellent AI adoption.", "metric": "ai"})
    elif ai_now == 0 and (lessons_now > 0 or assess_now > 0):
        insights.append({"type": "suggestion", "text": "Using the AI Teaching Assistant can help you design richer lessons and assessments faster.", "metric": "ai"})

    # Assessment coverage gap
    if lessons_now > 2 and assess_now == 0:
        insights.append({"type": "gap", "text": "You created lessons but no assessments this period — assessments complete the learning cycle.", "metric": "assessments"})

    # Workspace creation nudge
    if ws_total == 0:
        insights.append({"type": "suggestion", "text": "Creating a Teaching Workspace enables collaborative course design with a built-in AI teaching assistant.", "metric": "workspaces"})

    result = {
        "insights": insights[:6],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return _cache_put(cache_key, result)


# ══════════════════════════════════════════════════════════════════════════════
# 11. Admin Overview
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/admin/overview")
async def admin_overview(admin: dict = Depends(_require_admin)):
    cache_key = "ta:admin:overview"
    if (hit := _cached(cache_key)):
        return hit

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cut30 = _cutoff("30d")

    (
        total_lessons, total_assessments, total_workspaces,
        total_portfolio, total_ai_messages,
        lessons_30d, assessments_30d, ai_30d,
    ) = await asyncio.gather(
        db.teaching_lessons.count_documents({}),
        db.teaching_assessments.count_documents({}),
        db.teaching_workspaces.count_documents({}),
        db.teaching_portfolio_items.count_documents({}),
        db.teaching_chat_messages.count_documents({"role": "user"}),
        db.teaching_lessons.count_documents({"created_at": {"$gte": cut30}}),
        db.teaching_assessments.count_documents({"created_at": {"$gte": cut30}}),
        db.teaching_chat_messages.count_documents({"role": "user", "created_at": {"$gte": cut30}}),
    )

    active_educators = await db.teaching_lessons.distinct("owner_id")

    # Top educators by lesson count
    top_pipe = [
        {"$group": {"_id": "$owner_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 15},
    ]
    top_raw = [r async for r in db.teaching_lessons.aggregate(top_pipe)]
    uids = [r["_id"] for r in top_raw]
    user_map: dict[str, dict] = {}
    if uids:
        async for u in db.users.find({"_id": {"$in": [__import__('bson').ObjectId(i) if len(i) == 24 else i for i in uids]}}, {"full_name": 1, "institution": 1}):
            user_map[str(u["_id"])] = u
    top_educators = [
        {
            "id":          r["_id"],
            "name":        user_map.get(r["_id"], {}).get("full_name", "—"),
            "institution": user_map.get(r["_id"], {}).get("institution", ""),
            "lessons":     r["count"],
        }
        for r in top_raw
    ]

    subject_dist  = await _group_dist(db, "teaching_lessons",     {}, "subject",         15)
    level_dist    = await _group_dist(db, "teaching_lessons",     {}, "level",            10)
    assess_types  = await _group_dist(db, "teaching_assessments", {}, "assessment_type",  10)
    ws_act_trend  = await _trend(db, "teaching_workspace_activity", {"created_at": {"$gte": cut30}})

    result = {
        "platform_totals": {
            "active_educators": len(active_educators),
            "lessons":          total_lessons,
            "assessments":      total_assessments,
            "workspaces":       total_workspaces,
            "portfolio_items":  total_portfolio,
            "ai_messages":      total_ai_messages,
        },
        "last_30d": {
            "lessons":     lessons_30d,
            "assessments": assessments_30d,
            "ai_messages": ai_30d,
        },
        "top_educators":              top_educators,
        "subject_distribution":       subject_dist,
        "level_distribution":         level_dist,
        "assessment_type_distribution": assess_types,
        "workspace_activity_trend":   ws_act_trend,
    }
    return _cache_put(cache_key, result)
