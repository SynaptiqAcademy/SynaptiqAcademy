"""
SIE Goal Engine — long-term academic goal management.
Goals track ambitions like "publish 3 Q1 papers", "obtain tenure", "secure Horizon funding".
AI evaluates each goal for risk, recommends actions, estimates completion.
"""
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

_GOAL_TYPES = [
    "publication", "grant", "career", "teaching", "collaboration",
    "citation", "degree", "trust", "reputation", "other",
]

_PRIORITY_LABELS = {1: "low", 2: "medium-low", 3: "medium", 4: "high", 5: "critical"}

_AI_RECOMMENDATIONS = {
    "publication": [
        "Identify 3 target journals aligned to your research area.",
        "Create a writing schedule: 2 hours per day dedicated to manuscript work.",
        "Use Synaptiq Literature Review to find relevant gaps before writing.",
        "Set a submission deadline 6 weeks from the manuscript draft completion.",
    ],
    "grant": [
        "Review eligibility criteria for each identified opportunity.",
        "Build a consortium of collaborators to strengthen the proposal.",
        "Allocate at least 8 weeks for proposal writing and internal review.",
        "Use Synaptiq Grant Planner to structure budget and deliverables.",
    ],
    "career": [
        "Document all research outputs systematically in your profile.",
        "Request peer reviews to build your academic reputation score.",
        "Identify a mentor currently holding your target position.",
        "Track promotion requirements for your institution.",
    ],
    "teaching": [
        "Use Synaptiq Teaching Hub to build a documented teaching portfolio.",
        "Collect student feedback to evidence teaching quality.",
        "Develop course materials that can be peer-reviewed.",
    ],
    "citation": [
        "Publish in open-access formats to maximize discoverability.",
        "Present at high-visibility conferences to reach broader audiences.",
        "Engage with your research community on academic social networks.",
    ],
    "collaboration": [
        "Use Synaptiq Collaboration Intelligence to find complementary researchers.",
        "Reach out to researchers who have cited your work.",
        "Propose a joint grant application to formalize collaborations.",
    ],
    "other": [
        "Break this goal into smaller measurable milestones.",
        "Set a quarterly review to assess progress.",
        "Use Synaptiq AI to generate a step-by-step plan.",
    ],
}


def _compute_risk(goal: dict) -> str:
    deadline = goal.get("deadline")
    progress = goal.get("progress", 0)
    if not deadline:
        return "medium"
    now = datetime.now(timezone.utc)
    if isinstance(deadline, str):
        try:
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except Exception:
            return "medium"
    days_left = (deadline - now).days
    if days_left < 30 and progress < 50:
        return "critical"
    if days_left < 90 and progress < 30:
        return "high"
    if days_left < 180 and progress < 20:
        return "medium"
    return "low"


def _estimate_completion(goal: dict) -> Optional[str]:
    progress = goal.get("progress", 0)
    deadline = goal.get("deadline")
    if progress == 0 or not deadline:
        return None
    now = datetime.now(timezone.utc)
    if isinstance(deadline, str):
        try:
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except Exception:
            return None
    total_days = (deadline - now).days
    if total_days <= 0:
        return "overdue"
    remaining_pct = 100 - progress
    days_per_pct = total_days / max(progress, 1)
    est_days = remaining_pct * days_per_pct
    est_date = datetime.now(timezone.utc)
    from datetime import timedelta
    est_date += timedelta(days=est_days)
    return est_date.strftime("%Y-%m-%d")


def _ser_goal(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id", ""))
    for k, v in doc.items():
        if hasattr(v, "isoformat"):
            doc[k] = v.isoformat()
    return doc


async def create_goal(user_id: str, data: dict, db) -> dict:
    goal_type = data.get("type", "other")
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "title": data.get("title", "Untitled Goal"),
        "description": data.get("description", ""),
        "type": goal_type if goal_type in _GOAL_TYPES else "other",
        "priority": max(1, min(5, int(data.get("priority", 3)))),
        "deadline": data.get("deadline"),
        "progress": 0,
        "status": "active",
        "dependencies": data.get("dependencies", []),
        "ai_recommendations": _AI_RECOMMENDATIONS.get(goal_type, _AI_RECOMMENDATIONS["other"]),
        "created_at": now,
        "updated_at": now,
    }
    doc["risk_level"] = _compute_risk(doc)
    doc["estimated_completion"] = _estimate_completion(doc)
    result = await db.sie_goals.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    for k, v in doc.items():
        if hasattr(v, "isoformat"):
            doc[k] = v.isoformat()
    return doc


async def get_goals(user_id: str, db, status: Optional[str] = None) -> list:
    q: dict = {"user_id": user_id}
    if status:
        q["status"] = status
    cursor = db.sie_goals.find(q).sort("priority", -1)
    docs = await cursor.to_list(100)
    return [_ser_goal(d) for d in docs]


async def update_goal(user_id: str, goal_id: str, updates: dict, db) -> Optional[dict]:
    allowed = {"title", "description", "type", "priority", "deadline", "progress", "status", "dependencies"}
    safe = {k: v for k, v in updates.items() if k in allowed}
    safe["updated_at"] = datetime.now(timezone.utc)

    doc = await db.sie_goals.find_one({"_id": ObjectId(goal_id), "user_id": user_id})
    if not doc:
        return None
    merged = {**doc, **safe}
    merged["risk_level"] = _compute_risk(merged)
    merged["estimated_completion"] = _estimate_completion(merged)
    merged["ai_recommendations"] = _AI_RECOMMENDATIONS.get(merged.get("type", "other"), _AI_RECOMMENDATIONS["other"])

    await db.sie_goals.update_one(
        {"_id": ObjectId(goal_id), "user_id": user_id},
        {"$set": {k: merged[k] for k in safe.keys()} | {"risk_level": merged["risk_level"], "estimated_completion": merged["estimated_completion"]}},
    )
    doc = await db.sie_goals.find_one({"_id": ObjectId(goal_id)})
    return _ser_goal(doc) if doc else None


async def delete_goal(user_id: str, goal_id: str, db) -> bool:
    r = await db.sie_goals.delete_one({"_id": ObjectId(goal_id), "user_id": user_id})
    return r.deleted_count > 0


async def evaluate_goal(user_id: str, goal_id: str, db) -> dict:
    doc = await db.sie_goals.find_one({"_id": ObjectId(goal_id), "user_id": user_id})
    if not doc:
        return {}
    pubs = await db.publications.count_documents({"user_id": user_id})
    grants = await db.grant_applications.count_documents({"user_id": user_id, "status": "approved"})
    risk = _compute_risk(doc)
    est = _estimate_completion(doc)
    blockers = []
    if doc.get("progress", 0) < 10 and doc.get("priority", 3) >= 4:
        blockers.append("Goal has not started. Assign a first mission to activate progress.")
    if risk in ("high", "critical"):
        blockers.append("Deadline pressure detected. Increase weekly effort immediately.")
    return {
        "goal_id": goal_id,
        "risk_level": risk,
        "estimated_completion": est,
        "blockers": blockers,
        "platform_context": {"total_publications": pubs, "approved_grants": grants},
        "recommendations": _AI_RECOMMENDATIONS.get(doc.get("type", "other"), _AI_RECOMMENDATIONS["other"]),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
