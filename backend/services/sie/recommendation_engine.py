"""
SIE Recommendation Engine — continuously recommends actions, tools, and opportunities.
Rule-based cross-module intelligence, no LLM required.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Optional

_CATEGORIES = [
    "research_ideas", "collaborations", "grants", "journals",
    "conferences", "career_actions", "ai_tools", "publication_improvements",
    "training", "datasets",
]

_AI_TOOLS = [
    {"title": "Literature Review", "description": "Map the latest publications in your field.", "url": "/literature-review"},
    {"title": "Research Gap Finder", "description": "Identify unexplored research opportunities.", "url": "/research-gap-finder"},
    {"title": "Manuscript Review", "description": "Get AI feedback on your manuscript before submission.", "url": "/manuscript-review"},
    {"title": "Statistical Review", "description": "Verify your statistical methodology.", "url": "/statistical-review"},
    {"title": "Publishing Intelligence", "description": "Find the best journal for your paper.", "url": "/publishing-intelligence"},
    {"title": "Grant Hub", "description": "Find and manage grant opportunities.", "url": "/grant-hub"},
    {"title": "Collaboration Intelligence", "description": "Find ideal research collaborators.", "url": "/collaboration-intelligence"},
]

_TRAINING = [
    {"title": "Research Data Management", "description": "Learn best practices for FAIR data."},
    {"title": "Grant Writing Masterclass", "description": "Improve your grant application success rate."},
    {"title": "Open Access Publishing", "description": "Maximise the reach of your research."},
    {"title": "Academic Writing for Impact", "description": "Write clearer, more cited papers."},
    {"title": "Research Ethics & Integrity", "description": "Strengthen your academic integrity score."},
]


def _rec(category: str, title: str, description: str, priority: int, action_url: str = "", data: dict = None) -> dict:
    return {
        "category": category,
        "title": title,
        "description": description,
        "priority": priority,
        "action_url": action_url,
        "data": data or {},
        "dismissed": False,
        "rating": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def generate_recommendations(user_id: str, db) -> list:
    pubs, grants, collabs, goals, memory, missions = await asyncio.gather(
        db.publications.find({"user_id": user_id}).to_list(20),
        db.grant_applications.find({"user_id": user_id}).to_list(20),
        db.collaborations.count_documents({"user_id": user_id}),
        db.sie_goals.count_documents({"user_id": user_id, "status": "active"}),
        db.sie_memory.find_one({"user_id": user_id}),
        db.sie_missions.count_documents({"user_id": user_id, "status": "pending"}),
    )

    recs = []

    # Publication recommendations
    total_pubs = len(pubs)
    if total_pubs == 0:
        recs.append(_rec("ai_tools", "Start your first manuscript", "Use Synaptiq Manuscript Review to write and refine your first paper.", 5, "/manuscript-review"))
    elif total_pubs < 3:
        recs.append(_rec("publication_improvements", "Increase publication velocity", "You have few publications. Consider planning 2 more manuscripts this year.", 4, "/sie/planning"))

    q1_pubs = [p for p in pubs if p.get("quartile") in ("Q1", "Q2")]
    if total_pubs > 0 and len(q1_pubs) < total_pubs * 0.3:
        recs.append(_rec("publication_improvements", "Target higher-impact journals", "Less than 30% of your publications are in Q1/Q2 journals. Use Publishing Intelligence.", 4, "/publishing-intelligence"))

    # Grant recommendations
    approved = [g for g in grants if g.get("status") == "approved"]
    if len(approved) == 0:
        recs.append(_rec("grants", "Apply for your first competitive grant", "No approved grants detected. Visit Grant Hub to find suitable opportunities.", 4, "/grant-hub"))
    if len(grants) > 0 and len(approved) / len(grants) < 0.3:
        recs.append(_rec("grants", "Improve grant success rate", "Your grant success rate is below 30%. Use Synaptiq Grant Hub for strategic guidance.", 3, "/grant-hub"))

    # Collaboration recommendations
    if collabs == 0:
        recs.append(_rec("collaborations", "Start your first collaboration", "No collaborations found. Use Collaboration Intelligence to find compatible researchers.", 4, "/collaboration-intelligence"))
    elif collabs < 3:
        recs.append(_rec("collaborations", "Expand your research network", "Building more collaborations increases citation impact and grant success.", 3, "/collaboration-intelligence"))

    # Goal recommendations
    if goals == 0:
        recs.append(_rec("career_actions", "Define your research goals", "You have no active goals. Set long-term goals to unlock AI planning.", 5, "/sie/goals"))

    if missions == 0 and goals > 0:
        recs.append(_rec("research_ideas", "Generate your first research mission", "You have goals but no missions. Generate missions to start making progress.", 5, "/sie/missions"))

    # AI tools recommendations
    for tool in _AI_TOOLS[:3]:
        recs.append(_rec("ai_tools", tool["title"], tool["description"], 2, tool["url"]))

    # Training recommendations
    for t in _TRAINING[:2]:
        recs.append(_rec("training", t["title"], t["description"], 1))

    # Memory-driven (interests)
    if memory:
        interests = memory.get("research_interests", [])
        if interests:
            recs.append(_rec("research_ideas", f"Explore new directions in {interests[0]}", f"Your primary interest is {interests[0]}. Use the Research Gap Finder to identify new angles.", 3, "/research-gap-finder"))

    # Sort by priority
    recs.sort(key=lambda r: -r["priority"])

    # Persist
    await db.sie_recommendations.delete_many({"user_id": user_id, "dismissed": False})
    if recs:
        docs = [{"user_id": user_id, **r} for r in recs]
        await db.sie_recommendations.insert_many(docs)

    return recs[:20]


async def get_recommendations(user_id: str, db, category: Optional[str] = None) -> list:
    q: dict = {"user_id": user_id, "dismissed": False}
    if category:
        q["category"] = category
    cursor = db.sie_recommendations.find(q).sort("priority", -1)
    docs = await cursor.to_list(50)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return docs


async def dismiss_recommendation(user_id: str, rec_id: str, db) -> bool:
    r = await db.sie_recommendations.update_one(
        {"_id": ObjectId(rec_id), "user_id": user_id},
        {"$set": {"dismissed": True}},
    )
    return r.modified_count > 0


async def rate_recommendation(user_id: str, rec_id: str, rating: int, db) -> bool:
    r = await db.sie_recommendations.update_one(
        {"_id": ObjectId(rec_id), "user_id": user_id},
        {"$set": {"rating": max(1, min(5, rating))}},
    )
    return r.modified_count > 0
