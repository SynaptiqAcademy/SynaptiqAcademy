"""
SIE Automation Engine — user-configurable monitoring automations.
Each automation defines a trigger type, schedule, and notification behaviour.
"""
from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional

_AUTOMATION_TYPES = [
    "monitor_journal",
    "monitor_grant",
    "monitor_citation",
    "monitor_collaborator",
    "deadline_reminder",
    "weekly_report",
    "goal_check",
    "recommendation_refresh",
]

_TYPE_DESCRIPTIONS = {
    "monitor_journal": "Alert when new papers appear in a target journal.",
    "monitor_grant": "Alert when a grant deadline is approaching.",
    "monitor_citation": "Alert when your papers receive new citations.",
    "monitor_collaborator": "Alert when a collaborator publishes new work.",
    "deadline_reminder": "Remind you of upcoming goal and mission deadlines.",
    "weekly_report": "Generate a weekly progress summary every Monday.",
    "goal_check": "Evaluate goal progress and generate recommendations daily.",
    "recommendation_refresh": "Refresh AI recommendations weekly.",
}

_SCHEDULE_OPTIONS = ["daily", "weekly", "monthly"]


def _ser(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id", ""))
    for k, v in doc.items():
        if hasattr(v, "isoformat"):
            doc[k] = v.isoformat()
    return doc


async def create_automation(user_id: str, data: dict, db) -> dict:
    automation_type = data.get("type", "deadline_reminder")
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "name": data.get("name", _TYPE_DESCRIPTIONS.get(automation_type, "Automation")),
        "type": automation_type if automation_type in _AUTOMATION_TYPES else "deadline_reminder",
        "description": _TYPE_DESCRIPTIONS.get(automation_type, ""),
        "config": data.get("config", {}),  # e.g. {"journal": "Nature", "threshold": 3}
        "schedule": data.get("schedule", "weekly") if data.get("schedule") in _SCHEDULE_OPTIONS else "weekly",
        "enabled": True,
        "last_run": None,
        "run_count": 0,
        "last_result": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.sie_automations.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


async def get_automations(user_id: str, db) -> list:
    cursor = db.sie_automations.find({"user_id": user_id}).sort("created_at", -1)
    docs = await cursor.to_list(100)
    return [_ser(d) for d in docs]


async def update_automation(user_id: str, automation_id: str, updates: dict, db) -> Optional[dict]:
    allowed = {"name", "config", "schedule", "enabled"}
    safe = {k: v for k, v in updates.items() if k in allowed}
    safe["updated_at"] = datetime.now(timezone.utc)
    r = await db.sie_automations.update_one(
        {"_id": ObjectId(automation_id), "user_id": user_id},
        {"$set": safe},
    )
    if r.matched_count == 0:
        return None
    doc = await db.sie_automations.find_one({"_id": ObjectId(automation_id)})
    return _ser(doc) if doc else None


async def delete_automation(user_id: str, automation_id: str, db) -> bool:
    r = await db.sie_automations.delete_one({"_id": ObjectId(automation_id), "user_id": user_id})
    return r.deleted_count > 0


async def run_automation(user_id: str, automation_id: str, db) -> dict:
    doc = await db.sie_automations.find_one({"_id": ObjectId(automation_id), "user_id": user_id})
    if not doc:
        return {"success": False, "error": "Automation not found"}

    automation_type = doc.get("type")
    result_data = {}

    if automation_type == "deadline_reminder":
        from datetime import timedelta
        horizon = datetime.now(timezone.utc) + timedelta(days=7)
        goals = await db.sie_goals.find({
            "user_id": user_id,
            "status": "active",
            "deadline": {"$lte": horizon.isoformat()},
        }).to_list(10)
        result_data = {"deadlines_found": len(goals), "goals": [g.get("title") for g in goals]}

    elif automation_type == "goal_check":
        goals = await db.sie_goals.count_documents({"user_id": user_id, "status": "active"})
        missions = await db.sie_missions.count_documents({"user_id": user_id, "status": "pending"})
        result_data = {"active_goals": goals, "pending_missions": missions}

    elif automation_type == "recommendation_refresh":
        from services.sie.recommendation_engine import generate_recommendations
        recs = await generate_recommendations(user_id, db)
        result_data = {"recommendations_generated": len(recs)}

    elif automation_type == "weekly_report":
        from services.sie.progress_engine import get_progress_overview
        progress = await get_progress_overview(user_id, db)
        result_data = {"report_generated": True, "summary": progress.get("summary", {})}

    else:
        result_data = {"message": f"Automation type {automation_type} executed."}

    now = datetime.now(timezone.utc)
    await db.sie_automations.update_one(
        {"_id": ObjectId(automation_id)},
        {"$set": {"last_run": now, "last_result": result_data}, "$inc": {"run_count": 1}},
    )
    return {"success": True, "automation_id": automation_id, "type": automation_type, "result": result_data, "ran_at": now.isoformat()}


async def seed_default_automations(user_id: str, db) -> None:
    existing = await db.sie_automations.count_documents({"user_id": user_id})
    if existing > 0:
        return
    defaults = [
        {"type": "deadline_reminder", "schedule": "daily", "name": "Deadline Reminders"},
        {"type": "goal_check",        "schedule": "daily", "name": "Daily Goal Check"},
        {"type": "weekly_report",     "schedule": "weekly", "name": "Weekly Progress Report"},
        {"type": "recommendation_refresh", "schedule": "weekly", "name": "Weekly Recommendations"},
    ]
    for d in defaults:
        await create_automation(user_id, d, db)
