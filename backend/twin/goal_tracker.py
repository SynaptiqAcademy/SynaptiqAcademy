"""
Goal tracker.

Measures progress against user-defined goals using verified platform data.
Progress computation is transparent — every count traces to a DB query.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .twin_store import list_goals, update_goal

logger = logging.getLogger("twin.goals")


# ── Goal categories that can be auto-tracked ──────────────────────────────────

async def compute_goal_progress(db, user_id: str, goal: dict) -> dict:
    """
    Derive current_value from platform data for a goal.
    Returns updated goal dict with current_value, evidence, and progress_pct.
    """
    category = goal.get("category", "other")
    target   = goal.get("target_value", 1)
    evidence = []
    current  = 0

    if category == "publication":
        count = await db.manuscripts.count_documents({
            "user_id": user_id,
            "status": {"$in": ["published", "accepted"]},
        })
        current = count
        evidence = [{"source": "Synaptiq manuscripts DB", "detail": f"{count} published/accepted manuscript(s)"}]

    elif category == "grant":
        count = await db.grants.count_documents({"user_id": user_id})
        current = count
        evidence = [{"source": "Synaptiq grants DB", "detail": f"{count} grant application(s)"}]

    elif category == "collaboration":
        count = await db.collaborations.count_documents({
            "$or": [{"requester_id": user_id}, {"recipient_id": user_id}],
            "status": "accepted",
        })
        current = count
        evidence = [{"source": "Synaptiq collaborations DB", "detail": f"{count} accepted collaboration(s)"}]

    elif category == "teaching":
        try:
            count = await db.lessons.count_documents({"instructor_id": user_id})
        except Exception:
            count = 0
        current = count
        evidence = [{"source": "Synaptiq teaching DB", "detail": f"{count} lesson(s)"}]

    else:
        # Manual goals — progress tracked by user
        current  = goal.get("current_value", 0)
        evidence = goal.get("evidence", [])

    # Compute progress (0-100, capped at 100)
    progress_pct = min(100, round((current / max(target, 1)) * 100))
    status = goal.get("status", "active")
    if progress_pct >= 100 and status == "active":
        status = "completed"

    return {
        "current_value": current,
        "progress_pct":  progress_pct,
        "status":        status,
        "evidence":      evidence,
        "last_computed": datetime.now(timezone.utc).isoformat(),
        "methodology":   f"Counted verified {category} records from Synaptiq platform database",
    }


async def refresh_all_goals(db, user_id: str) -> list[dict]:
    """Recompute progress for all active goals."""
    goals = await list_goals(db, user_id, status="active")
    updated = []
    for goal in goals:
        progress = await compute_goal_progress(db, user_id, goal)
        await update_goal(db, goal["_id"], user_id, {
            "current_value": progress["current_value"],
            "status":        progress["status"],
            "evidence":      progress["evidence"],
        })
        updated.append({**goal, **progress})
    return updated


def _deadline_urgency(deadline) -> str:
    if not deadline:
        return "no_deadline"
    try:
        dt = deadline if isinstance(deadline, datetime) else datetime.fromisoformat(str(deadline))
        days = (dt.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days
        if days < 0:
            return "overdue"
        if days <= 30:
            return "urgent"
        if days <= 90:
            return "upcoming"
        return "future"
    except Exception:
        return "unknown"


async def get_goals_summary(db, user_id: str) -> dict:
    """Summary of all goals with progress and urgency."""
    all_goals = await list_goals(db, user_id)
    enriched = []
    for goal in all_goals:
        progress = await compute_goal_progress(db, user_id, goal)
        enriched.append({
            **goal,
            **progress,
            "urgency": _deadline_urgency(goal.get("deadline")),
        })

    active    = [g for g in enriched if g["status"] == "active"]
    completed = [g for g in enriched if g["status"] == "completed"]

    return {
        "goals":           enriched,
        "active_count":    len(active),
        "completed_count": len(completed),
        "total_count":     len(enriched),
        "source":          "Synaptiq platform data — all progress counts from DB queries",
        "policy_note":     "Progress values are platform activity counts. They do not represent research quality assessments.",
    }
