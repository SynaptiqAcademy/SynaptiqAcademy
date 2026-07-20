"""
SIE Agenda Engine — generates daily and weekly AI-driven agendas.
Combines goals, missions, deadlines, and platform activity into a prioritised schedule.
"""
import asyncio
from datetime import datetime, timezone, timedelta, date

_WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


async def _active_goals(user_id: str, db) -> list:
    cursor = db.sie_goals.find({"user_id": user_id, "status": "active"}).sort("priority", -1)
    return await cursor.to_list(10)


async def _pending_missions(user_id: str, db, limit: int = 10) -> list:
    cursor = db.sie_missions.find(
        {"user_id": user_id, "status": {"$in": ["pending", "in_progress"]}}
    ).sort([("priority", -1), ("due_date", 1)]).limit(limit)
    return await cursor.to_list(limit)


async def _upcoming_deadlines(user_id: str, db) -> list:
    horizon = datetime.now(timezone.utc) + timedelta(days=14)
    cursor = db.sie_goals.find({
        "user_id": user_id,
        "status": "active",
        "deadline": {"$lte": horizon.isoformat()},
    }).sort("deadline", 1)
    return await cursor.to_list(5)


async def _recent_publications(user_id: str, db) -> list:
    cursor = db.publications.find({"user_id": user_id}).sort("year", -1).limit(3)
    return await cursor.to_list(3)


def _priority_item(category: str, title: str, description: str, priority: int, action_url: str = "") -> dict:
    return {"category": category, "title": title, "description": description, "priority": priority, "action_url": action_url}


async def generate_daily_agenda(user_id: str, db) -> dict:
    goals, missions, deadlines, pubs = await asyncio.gather(
        _active_goals(user_id, db),
        _pending_missions(user_id, db, 10),
        _upcoming_deadlines(user_id, db),
        _recent_publications(user_id, db),
    )

    today = datetime.now(timezone.utc)
    items = []

    # High-priority missions first
    for m in missions[:5]:
        items.append(_priority_item(
            "mission",
            m.get("title", "Mission"),
            f"Est. {m.get('estimated_hours', 2)}h · Difficulty: {m.get('difficulty', 3)}/5",
            m.get("priority", 3),
            "/sie/missions",
        ))

    # Deadline warnings
    for g in deadlines:
        deadline_str = g.get("deadline", "")
        items.append(_priority_item(
            "deadline",
            f"Deadline approaching: {g.get('title', 'Goal')}",
            f"Progress: {g.get('progress', 0)}% · Due: {deadline_str[:10] if deadline_str else 'unknown'}",
            5,
            "/sie/goals",
        ))

    # AI recommendations
    if len(pubs) == 0:
        items.append(_priority_item("recommendation", "Start your publication journey", "You have no publications yet. Use Synaptiq to generate a research roadmap.", 4, "/sie/planning"))

    # Goal progress nudges
    for g in goals[:3]:
        if g.get("progress", 0) < 10:
            items.append(_priority_item("goal", f"Activate goal: {g.get('title', '')}", "This goal has not started. Generate missions to make progress.", 3, "/sie/goals"))

    # Sort by priority descending
    items.sort(key=lambda x: -x["priority"])

    recommendations = [
        "Check Synaptiq Literature Review for new papers in your area.",
        "Review pending collaboration requests in your network.",
        "Update your Trust Score with any new verifications.",
    ]

    agenda = {
        "user_id": user_id,
        "date": today.strftime("%Y-%m-%d"),
        "weekday": _WEEKDAY[today.weekday()],
        "priorities": items[:8],
        "active_goals": len(goals),
        "pending_missions": len(missions),
        "upcoming_deadlines": len(deadlines),
        "ai_recommendations": recommendations,
        "generated_at": today.isoformat(),
    }
    await db.sie_daily_agenda.replace_one(
        {"user_id": user_id, "date": agenda["date"]},
        {**agenda},
        upsert=True,
    )
    return agenda


async def get_daily_agenda(user_id: str, db) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cached = await db.sie_daily_agenda.find_one({"user_id": user_id, "date": today})
    if cached:
        cached.pop("_id", None)
        return cached
    return await generate_daily_agenda(user_id, db)


async def generate_weekly_plan(user_id: str, db) -> dict:
    goals, missions = await asyncio.gather(
        _active_goals(user_id, db),
        _pending_missions(user_id, db, 20),
    )

    today = datetime.now(timezone.utc)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Distribute missions across weekdays
    days = []
    mission_pool = list(missions)
    for i in range(5):  # Mon-Fri
        day_date = week_start + timedelta(days=i)
        day_missions = mission_pool[i * 2:(i * 2) + 2]
        total_hours = sum(m.get("estimated_hours", 2) for m in day_missions)
        days.append({
            "weekday": _WEEKDAY[i],
            "date": day_date.strftime("%Y-%m-%d"),
            "missions": [{"title": m.get("title"), "hours": m.get("estimated_hours", 2), "type": m.get("type", "other")} for m in day_missions],
            "total_hours": round(total_hours, 1),
        })

    completed_this_week = await db.sie_missions.count_documents({
        "user_id": user_id,
        "status": "completed",
        "updated_at": {"$gte": week_start},
    })

    total_hours_week = sum(m.get("estimated_hours", 2) for m in missions[:10])

    plan = {
        "user_id": user_id,
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "days": days,
        "weekly_goals": [g.get("title") for g in goals[:5]],
        "total_missions": len(missions),
        "completed_this_week": completed_this_week,
        "estimated_hours_total": round(total_hours_week, 1),
        "ai_focus": "Focus on high-priority missions. Review goal progress at week end.",
        "generated_at": today.isoformat(),
    }
    await db.sie_weekly_plan.replace_one(
        {"user_id": user_id, "week_start": plan["week_start"]},
        {**plan},
        upsert=True,
    )
    return plan


async def get_weekly_plan(user_id: str, db) -> dict:
    today = datetime.now(timezone.utc)
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    cached = await db.sie_weekly_plan.find_one({"user_id": user_id, "week_start": week_start})
    if cached:
        cached.pop("_id", None)
        return cached
    return await generate_weekly_plan(user_id, db)
