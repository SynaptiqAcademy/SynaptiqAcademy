"""
Trust Badge System

13 badge types, each with award criteria, metadata and audit trail.
Badges are awarded automatically based on verified data.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId

log = logging.getLogger("synaptiq.trust.badges")

BADGE_CATALOGUE: dict[str, dict] = {
    "verified_researcher": {
        "label": "Verified Researcher",
        "description": "Academic research identity verified.",
        "icon": "shield-check",
        "color": "#0F2847",
        "level": "standard",
        "expiry_days": 365,
    },
    "verified_institution": {
        "label": "Verified Institution",
        "description": "Institutional affiliation verified.",
        "icon": "building-2",
        "color": "#0369A1",
        "level": "standard",
        "expiry_days": 365,
    },
    "verified_reviewer": {
        "label": "Verified Reviewer",
        "description": "Peer review activity verified (3+ reviews).",
        "icon": "clipboard-check",
        "color": "#059669",
        "level": "standard",
        "expiry_days": 365,
    },
    "verified_author": {
        "label": "Verified Author",
        "description": "At least one publication verified.",
        "icon": "book-open",
        "color": "#7C3AED",
        "level": "standard",
        "expiry_days": 1825,
    },
    "verified_grant_holder": {
        "label": "Verified Grant Holder",
        "description": "Grant participation verified.",
        "icon": "badge-dollar-sign",
        "color": "#D97706",
        "level": "premium",
        "expiry_days": 365,
    },
    "verified_conference_speaker": {
        "label": "Verified Conference Speaker",
        "description": "Conference speaker role verified.",
        "icon": "mic-2",
        "color": "#DC2626",
        "level": "standard",
        "expiry_days": 1825,
    },
    "verified_editor": {
        "label": "Verified Editor",
        "description": "Editorial board membership verified.",
        "icon": "pen-line",
        "color": "#0891B2",
        "level": "premium",
        "expiry_days": 365,
    },
    "verified_professor": {
        "label": "Verified Professor",
        "description": "Professor position and affiliation verified.",
        "icon": "graduation-cap",
        "color": "#0F2847",
        "level": "premium",
        "expiry_days": 730,
    },
    "verified_phd_candidate": {
        "label": "Verified PhD Candidate",
        "description": "PhD candidacy and institution verified.",
        "icon": "award",
        "color": "#7C3AED",
        "level": "standard",
        "expiry_days": 365,
    },
    "verified_laboratory": {
        "label": "Verified Laboratory",
        "description": "Laboratory membership verified.",
        "icon": "flask-conical",
        "color": "#059669",
        "level": "standard",
        "expiry_days": 365,
    },
    "verified_project_leader": {
        "label": "Verified Project Leader",
        "description": "Research project leadership verified.",
        "icon": "folder-open",
        "color": "#D97706",
        "level": "premium",
        "expiry_days": 365,
    },
    "verified_mentor": {
        "label": "Verified Mentor",
        "description": "Academic mentorship and teaching verified.",
        "icon": "users-2",
        "color": "#0369A1",
        "level": "standard",
        "expiry_days": 365,
    },
    "verified_educator": {
        "label": "Verified Educator",
        "description": "Teaching portfolio verified (5+ lessons).",
        "icon": "graduation-cap",
        "color": "#DC2626",
        "level": "premium",
        "expiry_days": 365,
    },
}


async def evaluate_badges(user_id: str, db) -> list[dict]:
    """
    Evaluate which badges a user qualifies for based on their trust verifications.
    Returns list of awarded badge dicts.
    """
    now = datetime.now(timezone.utc)

    # Load all verified verifications for this user
    cursor = db.trust_verifications.find({
        "user_id": user_id, "status": "verified"
    })
    verifications = await cursor.to_list(length=200)
    v_types = {v["verification_type"] for v in verifications}

    # Load review count, lesson count, project count
    rev_count, lesson_count, proj_count = await asyncio.gather(
        db.reviews.count_documents({"reviewer_id": user_id}),
        db.teaching_lessons.count_documents({"creator_id": user_id}),
        db.projects.count_documents({"owner_id": user_id}),
    )

    user = await db.users.find_one({"_id": _safe_oid(user_id)}) or {}
    position = (user.get("position") or "").lower()

    earned: list[str] = []

    if "researcher_identity" in v_types:
        earned.append("verified_researcher")
    if "institution_affiliation" in v_types:
        earned.append("verified_institution")
    if "reviewer_activity" in v_types and rev_count >= 3:
        earned.append("verified_reviewer")
    if "publication" in v_types or "doi" in v_types:
        earned.append("verified_author")
    if "grant_participation" in v_types:
        earned.append("verified_grant_holder")
    if "conference_speaker" in v_types:
        earned.append("verified_conference_speaker")
    if "editorial_board_membership" in v_types:
        earned.append("verified_editor")
    if "academic_position" in v_types and "professor" in position:
        earned.append("verified_professor")
    if "academic_position" in v_types and "phd" in position:
        earned.append("verified_phd_candidate")
    if "laboratory_membership" in v_types:
        earned.append("verified_laboratory")
    if "research_project" in v_types and proj_count >= 1:
        earned.append("verified_project_leader")
    if "teaching_experience" in v_types:
        earned.append("verified_mentor")
    if "teaching_experience" in v_types and lesson_count >= 5:
        earned.append("verified_educator")

    # Upsert earned badges in trust_badges
    result_badges = []
    for badge_key in set(earned):
        defn = BADGE_CATALOGUE.get(badge_key, {})
        expiry = now + timedelta(days=defn.get("expiry_days", 365))
        badge_doc = {
            "user_id":    user_id,
            "badge_key":  badge_key,
            "label":      defn.get("label", badge_key),
            "description":defn.get("description", ""),
            "icon":       defn.get("icon", "shield"),
            "color":      defn.get("color", "#0F2847"),
            "level":      defn.get("level", "standard"),
            "issued_at":  now,
            "expires_at": expiry,
            "status":     "active",
        }
        existing = await db.trust_badges.find_one({"user_id": user_id, "badge_key": badge_key})
        if existing:
            await db.trust_badges.update_one(
                {"_id": existing["_id"]},
                {"$set": {"expires_at": expiry, "status": "active", "updated_at": now}},
            )
            badge_doc["_id"] = str(existing["_id"])
        else:
            ins = await db.trust_badges.insert_one(badge_doc)
            badge_doc["_id"] = str(ins.inserted_id)
            # Audit new badge
            await db.trust_audit.insert_one({
                "user_id": user_id,
                "event":   "badge_awarded",
                "badge":   badge_key,
                "created_at": now,
            })
        result_badges.append(badge_doc)

    return result_badges


async def get_user_badges(user_id: str, db) -> list[dict]:
    cursor = db.trust_badges.find({"user_id": user_id, "status": "active"})
    badges = await cursor.to_list(length=50)
    return [_ser(b) for b in badges]


def _ser(doc: dict) -> dict:
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _safe_oid(s: str):
    try:
        return ObjectId(s)
    except Exception:
        return s
