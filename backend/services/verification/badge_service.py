"""Verification Badge Service — awards and retrieves verification badges.

Badges are awarded based on computed boolean flags from the verification profile.
No manual assignment, no fake badges. All criteria are evidence-based.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId

logger = logging.getLogger("synaptiq.verification.badges")

BADGE_DEFINITIONS: dict[str, str] = {
    "verified_email": "Email address verified",
    "verified_orcid": "ORCID profile linked and verified",
    "verified_institution": "Institutional affiliation verified",
    "verified_researcher": "Academic research activity verified",
    "verified_reviewer": "Peer review contributions verified",
    "verified_mentor": "Teaching and mentorship verified",
    "expert_verified": "Domain expertise verified",
    "trusted_researcher": "Trusted researcher status — level 7",
    "distinguished_scholar": "Distinguished Scholar — elite platform status",
    "grant_verified": "Grant participation verified",
    "teaching_verified": "Teaching portfolio verified",
}


def _serialize(doc: dict) -> dict:
    """Convert ObjectId and datetime fields to str."""
    if not doc:
        return {}
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def award_badge_if_not_exists(
    user_id: str, badge_type: str, db
) -> dict | None:
    """Award a badge to a user only if they don't already have it."""
    if badge_type not in BADGE_DEFINITIONS:
        logger.warning("Unknown badge type: %s", badge_type)
        return None

    existing = await db.verification_badges.find_one(
        {"user_id": user_id, "badge_type": badge_type}
    )
    if existing:
        return None  # Already awarded

    now = datetime.now(timezone.utc)
    badge_doc = {
        "user_id": user_id,
        "badge_type": badge_type,
        "description": BADGE_DEFINITIONS[badge_type],
        "awarded_at": now,
        "evidence_id": None,
    }
    result = await db.verification_badges.insert_one(badge_doc)
    badge_doc["_id"] = str(result.inserted_id)
    return _serialize(badge_doc)


async def award_level_badges(user_id: str, profile: dict, db) -> list:
    """Award all applicable badges based on current profile flags."""
    newly_awarded = []

    flag_to_badge = {
        "email_verified": "verified_email",
        "orcid_verified": "verified_orcid",
        "institution_verified": "verified_institution",
        "researcher_verified": "verified_researcher",
        "reviewer_verified": "verified_reviewer",
        "mentor_verified": "verified_mentor",
        "expert_verified": "expert_verified",
        "grant_verified": "grant_verified",
        "teaching_verified": "teaching_verified",
    }

    for flag, badge_type in flag_to_badge.items():
        if profile.get(flag):
            result = await award_badge_if_not_exists(user_id, badge_type, db)
            if result:
                newly_awarded.append(result)

    # Level-based special badges
    verification_level = int(profile.get("verification_level", 0) or 0)
    if verification_level >= 7:
        result = await award_badge_if_not_exists(user_id, "trusted_researcher", db)
        if result:
            newly_awarded.append(result)
    if verification_level >= 8:
        result = await award_badge_if_not_exists(user_id, "distinguished_scholar", db)
        if result:
            newly_awarded.append(result)

    return newly_awarded


async def get_user_badges(user_id: str, db) -> list:
    """Return all badges for a user, most recently awarded first."""
    cursor = db.verification_badges.find(
        {"user_id": user_id}
    ).sort("awarded_at", -1)
    docs = await cursor.to_list(length=200)
    return [_serialize(d) for d in docs]
