"""
SIE Mission Engine — converts objectives into discrete, actionable missions.
Missions are short-horizon tasks (days to weeks) derived from long-term goals.
"""
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

_MISSION_TYPES = [
    "literature_review", "data_collection", "writing", "submission",
    "revision", "conference", "grant_application", "collaboration",
    "analysis", "presentation", "teaching", "admin", "other",
]

_DIFFICULTY_LABELS = {1: "easy", 2: "moderate", 3: "challenging", 4: "hard", 5: "very_hard"}

_AUTO_MISSIONS = {
    "publication": [
        {"title": "Conduct targeted literature review", "type": "literature_review", "priority": 4, "difficulty": 3, "estimated_hours": 20},
        {"title": "Define research questions and methodology", "type": "writing", "priority": 5, "difficulty": 4, "estimated_hours": 10},
        {"title": "Draft manuscript introduction", "type": "writing", "priority": 4, "difficulty": 3, "estimated_hours": 8},
        {"title": "Select target journal", "type": "admin", "priority": 3, "difficulty": 2, "estimated_hours": 2},
        {"title": "Submit manuscript", "type": "submission", "priority": 5, "difficulty": 2, "estimated_hours": 4},
    ],
    "grant": [
        {"title": "Review grant call requirements", "type": "admin", "priority": 5, "difficulty": 2, "estimated_hours": 4},
        {"title": "Build consortium list", "type": "collaboration", "priority": 4, "difficulty": 3, "estimated_hours": 6},
        {"title": "Write project summary", "type": "writing", "priority": 4, "difficulty": 4, "estimated_hours": 12},
        {"title": "Complete budget planning", "type": "admin", "priority": 4, "difficulty": 3, "estimated_hours": 8},
        {"title": "Submit grant application", "type": "submission", "priority": 5, "difficulty": 2, "estimated_hours": 3},
    ],
    "career": [
        {"title": "Update academic CV", "type": "admin", "priority": 3, "difficulty": 2, "estimated_hours": 4},
        {"title": "Identify promotion requirements", "type": "admin", "priority": 4, "difficulty": 2, "estimated_hours": 3},
        {"title": "Identify a career mentor", "type": "collaboration", "priority": 3, "difficulty": 2, "estimated_hours": 2},
    ],
    "other": [
        {"title": "Define success criteria", "type": "admin", "priority": 3, "difficulty": 2, "estimated_hours": 2},
        {"title": "Create action plan", "type": "admin", "priority": 4, "difficulty": 2, "estimated_hours": 3},
    ],
}


def _ser(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id", ""))
    for k, v in doc.items():
        if hasattr(v, "isoformat"):
            doc[k] = v.isoformat()
    return doc


async def create_mission(user_id: str, data: dict, db) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "title": data.get("title", "Untitled Mission"),
        "description": data.get("description", ""),
        "type": data.get("type", "other"),
        "priority": max(1, min(5, int(data.get("priority", 3)))),
        "difficulty": max(1, min(5, int(data.get("difficulty", 3)))),
        "estimated_hours": float(data.get("estimated_hours", 4)),
        "goal_id": data.get("goal_id"),
        "completion": 0,
        "status": "pending",
        "dependencies": data.get("dependencies", []),
        "due_date": data.get("due_date"),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.sie_missions.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


async def get_missions(user_id: str, db, status: Optional[str] = None, goal_id: Optional[str] = None) -> list:
    q: dict = {"user_id": user_id}
    if status:
        q["status"] = status
    if goal_id:
        q["goal_id"] = goal_id
    cursor = db.sie_missions.find(q).sort([("priority", -1), ("created_at", -1)])
    docs = await cursor.to_list(200)
    return [_ser(d) for d in docs]


async def update_mission(user_id: str, mission_id: str, updates: dict, db) -> Optional[dict]:
    allowed = {"title", "description", "type", "priority", "difficulty", "estimated_hours", "completion", "status", "due_date"}
    safe = {k: v for k, v in updates.items() if k in allowed}
    if "completion" in safe:
        safe["completion"] = max(0, min(100, int(safe["completion"])))
        if safe["completion"] >= 100:
            safe["status"] = "completed"
    safe["updated_at"] = datetime.now(timezone.utc)
    r = await db.sie_missions.update_one(
        {"_id": ObjectId(mission_id), "user_id": user_id},
        {"$set": safe},
    )
    if r.matched_count == 0:
        return None
    doc = await db.sie_missions.find_one({"_id": ObjectId(mission_id)})
    return _ser(doc) if doc else None


async def complete_mission(user_id: str, mission_id: str, db) -> Optional[dict]:
    return await update_mission(user_id, mission_id, {"completion": 100, "status": "completed"}, db)


async def generate_missions_from_goal(user_id: str, goal_id: str, db) -> list:
    goal = await db.sie_goals.find_one({"_id": ObjectId(goal_id), "user_id": user_id})
    if not goal:
        return []
    goal_type = goal.get("type", "other")
    templates = _AUTO_MISSIONS.get(goal_type, _AUTO_MISSIONS["other"])
    created = []
    for tmpl in templates:
        existing = await db.sie_missions.find_one({"user_id": user_id, "goal_id": goal_id, "title": tmpl["title"]})
        if existing:
            continue
        doc = {**tmpl, "user_id": user_id, "goal_id": goal_id,
               "description": "", "completion": 0, "status": "pending",
               "dependencies": [], "due_date": None,
               "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
        result = await db.sie_missions.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        doc.pop("_id", None)
        created.append(doc)
    return created
