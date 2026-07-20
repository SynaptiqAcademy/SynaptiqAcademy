"""
MongoDB persistence for the Digital Research Twin.

One document per user in `digital_twins`.
Goals live in `twin_goals` (many per user).
Events live in `twin_events` (append-only event log).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId

logger = logging.getLogger("twin.store")

_TWIN_COLLECTION  = "digital_twins"
_GOALS_COLLECTION = "twin_goals"
_EVENTS_COLLECTION = "twin_events"


# ── Index setup ────────────────────────────────────────────────────────────────

async def ensure_indexes(db) -> None:
    await db[_TWIN_COLLECTION].create_index("user_id", unique=True)
    await db[_GOALS_COLLECTION].create_index("user_id")
    await db[_GOALS_COLLECTION].create_index([("user_id", 1), ("status", 1)])
    await db[_EVENTS_COLLECTION].create_index("user_id")
    await db[_EVENTS_COLLECTION].create_index([("user_id", 1), ("occurred_at", -1)])


# ── Twin document ──────────────────────────────────────────────────────────────

def _default_twin(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_id":      user_id,
        "version":      1,
        "created_at":   now,
        "last_sync":    None,

        # Derived intelligence — no raw user data stored here
        "profile": {
            "research_domains":      [],   # ResearchDomainEntry dicts
            "emerging_interests":    [],
            "methodological_expertise": [],
            "publication_themes":    [],
            "career_stage":          "unknown",
            "career_stage_evidence": [],
            "interdisciplinary_activity": None,
        },

        "working_style": {
            "observations":          [],   # WorkingStyleObservation dicts
            "last_analyzed":         None,
        },

        "activity_summary": {
            "manuscripts_count":     0,
            "projects_count":        0,
            "collaborations_count":  0,
            "grants_count":          0,
            "orcid_publications":    0,
            "teaching_lessons":      0,
            "last_computed":         None,
        },

        "ai_context": {
            "accepted_suggestion_types":  [],  # What kinds of AI suggestions this user accepts
            "rejected_suggestion_types":  [],
            "last_ai_interaction":        None,
        },

        "privacy": {
            "share_with_institution":      False,
            "personalization_enabled":     True,
            "excluded_manuscript_ids":     [],
            "excluded_project_ids":        [],
            "corrections":                 {},  # field → user override value
        },

        "explainability_log": [],  # Last N insight generations
    }


async def get_twin(db, user_id: str) -> dict:
    """Get twin or create a blank one."""
    doc = await db[_TWIN_COLLECTION].find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        blank = _default_twin(user_id)
        await db[_TWIN_COLLECTION].insert_one({**blank})
        return blank
    return doc


async def upsert_twin(db, user_id: str, updates: dict) -> None:
    """Apply partial updates to the twin document."""
    updates["version"] = updates.get("version", 1)
    await db[_TWIN_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": updates, "$inc": {"version": 1}},
        upsert=True,
    )


async def update_privacy(db, user_id: str, privacy_updates: dict) -> None:
    set_doc = {f"privacy.{k}": v for k, v in privacy_updates.items()}
    await db[_TWIN_COLLECTION].update_one({"user_id": user_id}, {"$set": set_doc})


async def add_correction(db, user_id: str, field: str, value: Any) -> None:
    """Store a user-supplied correction for a derived field."""
    await db[_TWIN_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": {f"privacy.corrections.{field}": {"value": value, "corrected_at": datetime.now(timezone.utc).isoformat()}}},
    )


async def reset_preferences(db, user_id: str) -> None:
    """Clear all learned AI interaction preferences."""
    await db[_TWIN_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": {
            "ai_context.accepted_suggestion_types": [],
            "ai_context.rejected_suggestion_types": [],
            "working_style.observations": [],
            "privacy.corrections": {},
        }},
    )


async def exclude_item(db, user_id: str, item_type: str, item_id: str) -> None:
    """Exclude a specific manuscript or project from twin analysis."""
    field_map = {
        "manuscript": "privacy.excluded_manuscript_ids",
        "project":    "privacy.excluded_project_ids",
    }
    field = field_map.get(item_type)
    if field:
        await db[_TWIN_COLLECTION].update_one(
            {"user_id": user_id},
            {"$addToSet": {field: item_id}},
        )


async def get_version_history(db, user_id: str, limit: int = 10) -> list[dict]:
    """Return recent twin event log (proxy for version history)."""
    events = await db[_EVENTS_COLLECTION].find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("occurred_at", -1).limit(limit).to_list(limit)
    return events


# ── Goals ──────────────────────────────────────────────────────────────────────

async def create_goal(db, user_id: str, goal: dict) -> str:
    goal["user_id"]    = user_id
    goal["created_at"] = datetime.now(timezone.utc)
    goal["updated_at"] = datetime.now(timezone.utc)
    goal.setdefault("status", "active")
    goal.setdefault("current_value", 0)
    result = await db[_GOALS_COLLECTION].insert_one(goal)
    return str(result.inserted_id)


async def list_goals(db, user_id: str, status: Optional[str] = None) -> list[dict]:
    q: dict = {"user_id": user_id}
    if status:
        q["status"] = status
    docs = await db[_GOALS_COLLECTION].find(q, {"_id": 1, **{k: 1 for k in [
        "title", "category", "target_value", "current_value", "unit",
        "deadline", "status", "evidence", "created_at", "updated_at",
    ]}}).sort("created_at", -1).to_list(50)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def update_goal(db, goal_id: str, user_id: str, updates: dict) -> bool:
    updates["updated_at"] = datetime.now(timezone.utc)
    result = await db[_GOALS_COLLECTION].update_one(
        {"_id": ObjectId(goal_id), "user_id": user_id},
        {"$set": updates},
    )
    return result.modified_count > 0


async def delete_goal(db, goal_id: str, user_id: str) -> bool:
    result = await db[_GOALS_COLLECTION].delete_one(
        {"_id": ObjectId(goal_id), "user_id": user_id}
    )
    return result.deleted_count > 0


# ── Event log ──────────────────────────────────────────────────────────────────

async def log_event(db, user_id: str, event_type: str, detail: str, evidence: Optional[list] = None) -> None:
    await db[_EVENTS_COLLECTION].insert_one({
        "user_id":     user_id,
        "event_type":  event_type,
        "detail":      detail,
        "evidence":    evidence or [],
        "occurred_at": datetime.now(timezone.utc),
    })


async def list_events(db, user_id: str, limit: int = 20) -> list[dict]:
    events = await db[_EVENTS_COLLECTION].find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("occurred_at", -1).limit(limit).to_list(limit)
    return events
