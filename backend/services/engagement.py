"""Engagement scoring + platform analytics.

Engagement classification (5 tiers):
  power     — daily-active, multiple projects/workspaces, high AI usage, paid plan
  healthy   — weekly-active, regular usage
  inactive  — last 14-30d
  at_risk   — last 30-60d
  dormant   — > 60d since activity

Scoring inputs (all from MongoDB):
  - session_events count (last 30d)
  - active minutes (last 30d, from session_end events)
  - projects + workspaces owned
  - collaborations count
  - AI usage (credit_transactions where kind='consume' in last 30d)
  - subscription_status
  - qualified referrals count
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Literal

from bson import ObjectId

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext


Tier = Literal["power", "healthy", "inactive", "at_risk", "dormant"]


def _ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _score_to_tier(*, days_since_active: int, score: int) -> Tier:
    if days_since_active > 60: return "dormant"
    if days_since_active > 30: return "at_risk"
    if days_since_active > 14: return "inactive"
    if score >= 80: return "power"
    return "healthy"


async def compute_engagement(user_id: str) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff_30 = _ago_iso(30)
    # Last activity
    last_event = await db.session_events.find_one({"user_id": user_id},
                                                   sort=[("created_at", -1)])
    last_iso = (last_event or {}).get("created_at")
    if last_iso:
        try:
            days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_iso)).days
        except Exception:
            days_since = 999
    else:
        days_since = 999

    sessions = await db.session_events.count_documents(
        {"user_id": user_id, "event": "session_start", "created_at": {"$gte": cutoff_30}}
    )
    minutes_agg = await db.session_events.aggregate([
        {"$match": {"user_id": user_id, "event": "session_end", "created_at": {"$gte": cutoff_30}}},
        {"$group": {"_id": None, "minutes": {"$sum": "$duration_minutes"}}},
    ]).to_list(1)
    minutes = int((minutes_agg[0]["minutes"] if minutes_agg else 0))
    projects = await db.projects.count_documents({"owner_id": user_id})
    workspaces = await db.workspaces.count_documents({"owner_id": user_id})
    collabs = await db.collaborations.count_documents({"owner_id": user_id})
    ai_agg = await db.credit_transactions.aggregate([
        {"$match": {"user_id": user_id, "kind": "consume", "created_at": {"$gte": cutoff_30}}},
        {"$group": {"_id": None, "credits": {"$sum": "$amount"}}},
    ]).to_list(1)
    ai_credits = int((ai_agg[0]["credits"] if ai_agg else 0))
    qualified_refs = await db.referrals.count_documents(
        {"referrer_id": user_id, "status": {"$in": ["qualified", "rewarded"]}}
    )
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    sub_status = (user or {}).get("subscription_status") or "inactive"
    plan = (user or {}).get("plan_code") or "free"
    paid = plan != "free" and sub_status in ("active", "trialing")

    # Simple weighted scoring
    score = 0
    score += min(sessions, 30) * 1          # max 30
    score += min(minutes // 5, 20)           # max 20 (100 minutes capped)
    score += min(projects, 5) * 2            # max 10
    score += min(workspaces, 5) * 2          # max 10
    score += min(collabs, 5) * 2             # max 10
    score += min(ai_credits // 25, 10)        # max 10
    score += 5 if paid else 0
    score += min(qualified_refs, 3) * 2      # max 6
    score = min(score, 100)

    tier = _score_to_tier(days_since_active=days_since, score=score)
    result = {
        "user_id": user_id,
        "tier": tier,
        "score": score,
        "days_since_active": days_since,
        "metrics": {
            "sessions_30d": sessions,
            "minutes_30d": minutes,
            "projects": projects,
            "workspaces": workspaces,
            "collaborations": collabs,
            "ai_credits_30d": ai_credits,
            "qualified_referrals": qualified_refs,
            "paid": paid,
        },
    }
    # Persist precomputed score to user document so the overview endpoint
    # can read without looping (scalability fix for /engagement overview).
    try:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "engagement_tier": tier,
                "engagement_score": score,
                "engagement_computed_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
    except Exception:
        pass
    return result


async def platform_analytics() -> dict:
    """Daily / Weekly / Monthly active users + feature/page heatmaps + retention."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = datetime.now(timezone.utc)
    d1 = _ago_iso(1); d7 = _ago_iso(7); d30 = _ago_iso(30)

    async def _unique(start: str) -> int:
        agg = await db.session_events.aggregate([
            {"$match": {"event": "session_start", "created_at": {"$gte": start}}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "n"},
        ]).to_list(1)
        return int(agg[0]["n"]) if agg else 0

    dau = await _unique(d1)
    wau = await _unique(d7)
    mau = await _unique(d30)

    # Average session duration (last 30d)
    dur_agg = await db.session_events.aggregate([
        {"$match": {"event": "session_end", "created_at": {"$gte": d30}}},
        {"$group": {"_id": None, "avg_min": {"$avg": "$duration_minutes"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    avg_session_min = round((dur_agg[0]["avg_min"] if dur_agg else 0) or 0, 2)
    sessions_30d = int((dur_agg[0]["n"] if dur_agg else 0))

    # Top pages (page_view events)
    top_pages = await db.session_events.aggregate([
        {"$match": {"event": "page_view", "created_at": {"$gte": d30}}},
        {"$group": {"_id": "$path", "views": {"$sum": 1}}},
        {"$sort": {"views": -1}},
        {"$limit": 10},
    ]).to_list(10)

    # Feature usage (from credit_transactions)
    feat = await db.credit_transactions.aggregate([
        {"$match": {"kind": "consume", "created_at": {"$gte": d30}, "amount": {"$gt": 0}}},
        {"$group": {"_id": "$action", "uses": {"$sum": 1}, "credits": {"$sum": "$amount"}}},
        {"$sort": {"credits": -1}},
        {"$limit": 15},
    ]).to_list(15)

    # Most active users
    top_users = await db.session_events.aggregate([
        {"$match": {"event": "session_start", "created_at": {"$gte": d30}}},
        {"$group": {"_id": "$user_id", "sessions": {"$sum": 1}}},
        {"$sort": {"sessions": -1}},
        {"$limit": 10},
    ]).to_list(10)

    # Most active institutions
    top_inst = await db.users.aggregate([
        {"$match": {"institution_id": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$institution_id", "users": {"$sum": 1}}},
        {"$sort": {"users": -1}},
        {"$limit": 10},
    ]).to_list(10)

    # Referral performance
    ref_total = await db.referrals.count_documents({})
    ref_qualified = await db.referrals.count_documents({"status": {"$in": ["qualified", "rewarded"]}})

    # Retention proxy: % of users created >30d ago who are still active in last 7d
    older = await db.users.count_documents({"created_at": {"$lte": _ago_iso(30)}})
    retained_pipe = await db.session_events.aggregate([
        {"$match": {"event": "session_start", "created_at": {"$gte": d7}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "n"},
    ]).to_list(1)
    retained_recent = int((retained_pipe[0]["n"] if retained_pipe else 0))
    retention_rate = round((retained_recent / max(older, 1)) * 100, 2)

    return {
        "active_users": {"dau": dau, "wau": wau, "mau": mau},
        "sessions": {"sessions_30d": sessions_30d, "avg_session_minutes": avg_session_min},
        "top_pages": [{"path": p["_id"], "views": p["views"]} for p in top_pages],
        "feature_usage": [{"action": f["_id"], "uses": f["uses"], "credits": f["credits"]} for f in feat],
        "top_users": [{"user_id": u["_id"], "sessions": u["sessions"]} for u in top_users],
        "top_institutions": [{"institution_id": i["_id"], "users": i["users"]} for i in top_inst],
        "referrals": {"total": ref_total, "qualified": ref_qualified},
        "retention_pct": retention_rate,
        "generated_at": now.isoformat(),
    }
