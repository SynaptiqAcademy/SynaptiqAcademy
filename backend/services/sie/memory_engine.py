"""
SIE Memory Engine — persistent AI memory per user.
Stores research interests, writing style, preferences, career goals.
Memory grows more complete over time as the user interacts with Synaptiq.
"""
from datetime import datetime, timezone

_DEFAULT_MEMORY = {
    "research_interests": [],
    "writing_style": "academic",
    "preferred_journals": [],
    "methodologies": [],
    "stats_methods": [],
    "collaborator_preferences": [],
    "ongoing_projects": [],
    "ai_preferences": {"verbosity": "medium", "focus": "research"},
    "teaching_interests": [],
    "career_goals": [],
    "target_positions": [],
    "preferred_conferences": [],
    "grant_agencies": [],
    "language": "en",
    "notes": "",
}


async def get_memory(user_id: str, db) -> dict:
    doc = await db.sie_memory.find_one({"user_id": user_id})
    if not doc:
        mem = {
            **_DEFAULT_MEMORY,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc),
            "events": [],
        }
        await db.sie_memory.insert_one(mem)
        mem.pop("_id", None)
        return mem
    doc.pop("_id", None)
    return doc


async def update_memory(user_id: str, updates: dict, db) -> dict:
    safe = {k: v for k, v in updates.items() if k not in ("user_id", "_id", "events")}
    safe["last_updated"] = datetime.now(timezone.utc)
    await db.sie_memory.update_one(
        {"user_id": user_id},
        {"$set": safe},
        upsert=True,
    )
    return await get_memory(user_id, db)


async def add_memory_event(user_id: str, event_type: str, data: dict, db) -> None:
    event = {"type": event_type, "data": data, "ts": datetime.now(timezone.utc).isoformat()}
    await db.sie_memory.update_one(
        {"user_id": user_id},
        {
            "$push": {"events": {"$each": [event], "$slice": -200}},
            "$set": {"last_updated": datetime.now(timezone.utc)},
        },
        upsert=True,
    )


async def enrich_memory_from_platform(user_id: str, db) -> None:
    """Auto-populates memory fields from existing platform data."""
    pubs = await db.publications.find({"user_id": user_id}).to_list(50)
    grants = await db.grant_applications.find({"user_id": user_id}).to_list(20)

    inferred_journals = list({p.get("journal") for p in pubs if p.get("journal")})[:10]
    inferred_agencies = list({g.get("funder") for g in grants if g.get("funder")})[:10]

    updates: dict = {}
    if inferred_journals:
        updates["preferred_journals"] = inferred_journals
    if inferred_agencies:
        updates["grant_agencies"] = inferred_agencies

    if updates:
        await update_memory(user_id, updates, db)
