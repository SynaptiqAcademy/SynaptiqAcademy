"""Verification Profile Service — computes and persists verification profiles
for each user based on real activity across platform collections.

No mock data. All reads come from source-of-truth collections.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from bson import ObjectId

logger = logging.getLogger("synaptiq.verification.profile")


def _serialize(doc: dict) -> dict:
    """Convert ObjectId fields to str for JSON serialisation."""
    if doc is None:
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


async def get_or_create_verification_profile(user_id: str, db) -> dict:
    """Return existing profile or create a default one."""
    doc = await db.verification_profiles.find_one({"user_id": user_id})
    if doc:
        return _serialize(doc)

    now = datetime.now(timezone.utc)
    default = {
        "user_id": user_id,
        "verification_score": 0,
        "identity_verified": False,
        "email_verified": False,
        "orcid_verified": False,
        "institution_verified": False,
        "researcher_verified": False,
        "reviewer_verified": False,
        "mentor_verified": False,
        "expert_verified": False,
        "grant_verified": False,
        "teaching_verified": False,
        "verification_level": 0,
        "verified_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.verification_profiles.insert_one(default)
    default["_id"] = str(result.inserted_id)
    return _serialize(default)


async def compute_verification_profile(user_id: str, db) -> dict:
    """Recompute all verification flags, trust score and level for a user."""
    now = datetime.now(timezone.utc)

    # ── Parallel data fetch ────────────────────────────────────────────────────
    (
        user,
        impact,
        reputation,
        reviewer_profile,
        projects_count,
        collaborations_count,
        teaching_count,
        pub_count,
        existing_profile,
        approved_evidence_count,
    ) = await asyncio.gather(
        db.users.find_one({"_id": ObjectId(user_id)}),
        db.research_impact.find_one({"user_id": user_id}),
        db.research_reputation.find_one({"user_id": user_id}),
        db.reviewer_profiles.find_one({"user_id": user_id}),
        db.projects.count_documents({"created_by": user_id}),
        db.collaborations.count_documents({
            "$or": [{"created_by": user_id}, {"participants": user_id}]
        }),
        db.teaching_lessons.count_documents({"created_by": user_id}),
        db.publications.count_documents({"author_ids": user_id}),
        db.verification_profiles.find_one({"user_id": user_id}),
        db.verification_evidence.count_documents({"user_id": user_id, "status": "approved"}),
    )

    # ── Extract raw metrics ────────────────────────────────────────────────────
    impact = impact or {}
    reputation = reputation or {}
    reviewer_profile = reviewer_profile or {}

    h_index = int(impact.get("h_index", 0) or 0)
    sis_total = float(impact.get("sis_total", 0.0) or 0.0)
    publication_count_impact = int(impact.get("publication_count", 0) or 0)
    citation_count = int(impact.get("citation_count", 0) or 0)
    reputation_score = float(reputation.get("overall_score", 0.0) or 0.0)
    reviews_completed = int(reviewer_profile.get("reviews_completed", 0) or 0)

    # Use the larger of impact publication count vs direct publication query
    publication_count = max(int(pub_count or 0), publication_count_impact)

    # ── Institution membership check ───────────────────────────────────────────
    institution_membership_active = await db.institution_memberships.count_documents(
        {"user_id": user_id, "status": "active"}
    )

    # ── Grant verification check ───────────────────────────────────────────────
    grant_verified_count = await db.grant_applications.count_documents(
        {"user_id": user_id, "status": {"$in": ["funded", "awarded", "approved"]}}
    )

    # ── Boolean flags ──────────────────────────────────────────────────────────
    email_verified: bool = bool(user and user.get("email"))
    orcid_verified: bool = bool(user and user.get("orcid") and str(user.get("orcid", "")).strip())
    institution_verified: bool = bool(
        user
        and user.get("institution")
        and (user.get("institution_id") or institution_membership_active > 0)
    )
    researcher_verified: bool = bool(publication_count >= 1 and (orcid_verified or institution_verified))
    reviewer_verified: bool = bool(reviews_completed >= 1)
    mentor_verified: bool = bool(int(teaching_count or 0) >= 3)
    expert_verified: bool = bool(publication_count >= 5 and researcher_verified)
    grant_verified: bool = bool(grant_verified_count > 0)
    teaching_verified: bool = bool(int(teaching_count or 0) >= 5)
    identity_verified: bool = bool(email_verified and (institution_verified or orcid_verified))

    # ── Trust score (0-1000) ───────────────────────────────────────────────────
    score = 0
    if email_verified:
        score += 50
    if orcid_verified:
        score += 100
    if institution_verified:
        score += 150
    score += min(150, publication_count * 5)
    score += min(100, int(citation_count / 10))
    score += min(100, h_index * 10)
    score += min(100, int(reputation_score / 10))
    score += min(60, reviews_completed * 3)
    score += min(50, int(collaborations_count or 0) * 5)
    score += min(40, int(teaching_count or 0) * 2)
    score += min(50, int(projects_count or 0) * 5)
    trust_score = min(1000, score)

    # ── Verification level (take highest matching) ─────────────────────────────
    level = 0
    if email_verified:
        level = max(level, 1)
    if email_verified and (institution_verified or orcid_verified):
        level = max(level, 2)
    if orcid_verified and email_verified:
        level = max(level, 3)
    if institution_verified and email_verified:
        level = max(level, 4)
    if researcher_verified and institution_verified:
        level = max(level, 5)
    if expert_verified:
        level = max(level, 6)
    if expert_verified and trust_score >= 400 and int(collaborations_count or 0) >= 3:
        level = max(level, 7)
    if (
        trust_score >= 600
        and reviews_completed >= 5
        and publication_count >= 10
        and int(teaching_count or 0) >= 3
    ):
        level = max(level, 8)

    verification_level = level

    # ── Detect level change ────────────────────────────────────────────────────
    prev_level = int((existing_profile or {}).get("verification_level", 0) or 0)
    level_changed = verification_level != prev_level

    # ── Upsert profile ─────────────────────────────────────────────────────────
    update_fields: dict = {
        "verification_score": trust_score,
        "identity_verified": identity_verified,
        "email_verified": email_verified,
        "orcid_verified": orcid_verified,
        "institution_verified": institution_verified,
        "researcher_verified": researcher_verified,
        "reviewer_verified": reviewer_verified,
        "mentor_verified": mentor_verified,
        "expert_verified": expert_verified,
        "grant_verified": grant_verified,
        "teaching_verified": teaching_verified,
        "verification_level": verification_level,
        "updated_at": now,
    }
    if level_changed:
        update_fields["verified_at"] = now

    await db.verification_profiles.update_one(
        {"user_id": user_id},
        {"$set": update_fields, "$setOnInsert": {"created_at": now, "user_id": user_id}},
        upsert=True,
    )

    # ── History + badges on level change ──────────────────────────────────────
    if level_changed:
        history_doc = {
            "user_id": user_id,
            "event_type": "level_change",
            "level_before": prev_level,
            "level_after": verification_level,
            "details": f"Level changed from {prev_level} to {verification_level}",
            "created_at": now,
        }
        await db.verification_history.insert_one(history_doc)

        audit_doc = {
            "user_id": user_id,
            "action": "verification_level_change",
            "actor_id": user_id,
            "details": {
                "level_before": prev_level,
                "level_after": verification_level,
                "trust_score": trust_score,
            },
            "created_at": now,
        }
        await db.verification_audits.insert_one(audit_doc)

        # Award badges based on updated profile
        from services.verification.badge_service import award_level_badges
        profile_snapshot = dict(update_fields)
        profile_snapshot["user_id"] = user_id
        await award_level_badges(user_id, profile_snapshot, db)

    updated = await db.verification_profiles.find_one({"user_id": user_id})
    return _serialize(updated or update_fields)


async def get_public_verification_profile(user_id: str, db) -> dict:
    """Return public-facing verification fields only."""
    profile = await db.verification_profiles.find_one({"user_id": user_id})
    if not profile:
        return {
            "user_id": user_id,
            "verification_level": 0,
            "verification_score": 0,
            "email_verified": False,
            "orcid_verified": False,
            "institution_verified": False,
            "researcher_verified": False,
            "reviewer_verified": False,
            "mentor_verified": False,
            "expert_verified": False,
            "grant_verified": False,
            "teaching_verified": False,
            "identity_verified": False,
            "badges": [],
            "verified": False,
        }

    from services.verification.badge_service import get_user_badges
    badges = await get_user_badges(user_id, db)

    return {
        "user_id": user_id,
        "verification_level": profile.get("verification_level", 0),
        "verification_score": profile.get("verification_score", 0),
        "email_verified": profile.get("email_verified", False),
        "orcid_verified": profile.get("orcid_verified", False),
        "institution_verified": profile.get("institution_verified", False),
        "researcher_verified": profile.get("researcher_verified", False),
        "reviewer_verified": profile.get("reviewer_verified", False),
        "mentor_verified": profile.get("mentor_verified", False),
        "expert_verified": profile.get("expert_verified", False),
        "grant_verified": profile.get("grant_verified", False),
        "teaching_verified": profile.get("teaching_verified", False),
        "identity_verified": profile.get("identity_verified", False),
        "verified": profile.get("verification_level", 0) >= 3,
        "badges": badges,
        "verified_at": profile.get("verified_at").isoformat() if profile.get("verified_at") else None,
    }


async def get_verification_history(user_id: str, db) -> list:
    """Return verification history for a user, most recent first."""
    cursor = db.verification_history.find(
        {"user_id": user_id}
    ).sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return [_serialize(d) for d in docs]
