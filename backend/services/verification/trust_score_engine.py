"""Trust Score Engine — detailed breakdown of verification trust score components.

Computes each score component individually so users and admins can see exactly
how the trust score is derived. No estimates or mock values — all reads come
from source-of-truth collections.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from bson import ObjectId

logger = logging.getLogger("synaptiq.verification.trust_score")

# Level descriptions for next_level_requirements
_LEVEL_DESCRIPTIONS: dict[int, str] = {
    0: "Verify your email address to reach Level 1.",
    1: "Link your ORCID profile or verify your institutional affiliation to reach Level 2.",
    2: "Link your ORCID profile to reach Level 3, or verify your institution to reach Level 4.",
    3: "Verify your institutional affiliation and publish at least one paper to reach Level 5.",
    4: "Publish at least one paper with a verified ORCID or institution to reach Level 5.",
    5: "Publish 5+ papers to reach Level 6 (Expert Verified).",
    6: "Reach a trust score of 400+ and have 3+ collaborations to reach Level 7 (Trusted Researcher).",
    7: "Reach trust score 600+, complete 5+ reviews, publish 10+ papers, and teach 3+ lessons to reach Level 8 (Distinguished Scholar).",
    8: "You have reached the highest verification level: Distinguished Scholar.",
}


async def compute_trust_breakdown(user_id: str, db) -> dict:
    """Compute per-component trust score breakdown for a user."""
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
    )

    impact = impact or {}
    reputation = reputation or {}
    reviewer_profile = reviewer_profile or {}

    h_index = int(impact.get("h_index", 0) or 0)
    citation_count = int(impact.get("citation_count", 0) or 0)
    publication_count_impact = int(impact.get("publication_count", 0) or 0)
    reputation_score = float(reputation.get("overall_score", 0.0) or 0.0)
    reviews_completed = int(reviewer_profile.get("reviews_completed", 0) or 0)
    publication_count = max(int(pub_count or 0), publication_count_impact)

    # Fetch institution membership
    institution_membership_active = await db.institution_memberships.count_documents(
        {"user_id": user_id, "status": "active"}
    )

    email_verified = bool(user and user.get("email"))
    orcid_verified = bool(user and user.get("orcid") and str(user.get("orcid", "")).strip())
    institution_verified = bool(
        user
        and user.get("institution")
        and (user.get("institution_id") or institution_membership_active > 0)
    )

    # Component calculations
    email_pts = 50 if email_verified else 0
    orcid_pts = 100 if orcid_verified else 0
    institution_pts = 150 if institution_verified else 0
    pub_pts = min(150, publication_count * 5)
    citation_pts = min(100, int(citation_count / 10))
    h_index_pts = min(100, h_index * 10)
    reputation_pts = min(100, int(reputation_score / 10))
    review_pts = min(60, reviews_completed * 3)
    collab_pts = min(50, int(collaborations_count or 0) * 5)
    teaching_pts = min(40, int(teaching_count or 0) * 2)
    project_pts = min(50, int(projects_count or 0) * 5)

    total_score = min(
        1000,
        email_pts + orcid_pts + institution_pts + pub_pts + citation_pts
        + h_index_pts + reputation_pts + review_pts + collab_pts
        + teaching_pts + project_pts,
    )

    # Determine current level (same logic as profile_service)
    researcher_verified = bool(publication_count >= 1 and (orcid_verified or institution_verified))
    expert_verified = bool(publication_count >= 5 and researcher_verified)

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
    if expert_verified and total_score >= 400 and int(collaborations_count or 0) >= 3:
        level = max(level, 7)
    if (
        total_score >= 600
        and reviews_completed >= 5
        and publication_count >= 10
        and int(teaching_count or 0) >= 3
    ):
        level = max(level, 8)

    next_level_req = _LEVEL_DESCRIPTIONS.get(level, "Maximum level achieved.")

    return {
        "total_score": total_score,
        "components": {
            "email_verified": {
                "points": email_pts,
                "earned": email_verified,
                "max": 50,
            },
            "orcid_verified": {
                "points": orcid_pts,
                "earned": orcid_verified,
                "max": 100,
            },
            "institution_verified": {
                "points": institution_pts,
                "earned": institution_verified,
                "max": 150,
            },
            "publications": {
                "points": pub_pts,
                "count": publication_count,
                "max": 150,
            },
            "citations": {
                "points": citation_pts,
                "count": citation_count,
                "max": 100,
            },
            "h_index": {
                "points": h_index_pts,
                "value": h_index,
                "max": 100,
            },
            "reputation": {
                "points": reputation_pts,
                "score": reputation_score,
                "max": 100,
            },
            "reviews": {
                "points": review_pts,
                "count": reviews_completed,
                "max": 60,
            },
            "collaborations": {
                "points": collab_pts,
                "count": int(collaborations_count or 0),
                "max": 50,
            },
            "teaching": {
                "points": teaching_pts,
                "count": int(teaching_count or 0),
                "max": 40,
            },
            "projects": {
                "points": project_pts,
                "count": int(projects_count or 0),
                "max": 50,
            },
        },
        "verification_level": level,
        "next_level_requirements": next_level_req,
    }


async def get_platform_trust_stats(db) -> dict:
    """Return platform-wide verification statistics."""
    # Count profiles by verification level
    level_pipeline = [
        {
            "$group": {
                "_id": "$verification_level",
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    level_cursor = db.verification_profiles.aggregate(level_pipeline)
    level_docs = await level_cursor.to_list(length=20)
    levels_breakdown = {str(int(d["_id"] or 0)): d["count"] for d in level_docs}

    # Average trust score
    avg_pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_score": {"$avg": "$verification_score"},
                "total": {"$sum": 1},
            }
        }
    ]
    avg_cursor = db.verification_profiles.aggregate(avg_pipeline)
    avg_docs = await avg_cursor.to_list(length=1)
    avg_trust_score = round(float((avg_docs[0]["avg_score"] or 0) if avg_docs else 0), 2)
    total_profiles = int((avg_docs[0]["total"] or 0) if avg_docs else 0)

    # Badge type counts
    badge_pipeline = [
        {
            "$group": {
                "_id": "$badge_type",
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]
    badge_cursor = db.verification_badges.aggregate(badge_pipeline)
    badge_docs = await badge_cursor.to_list(length=50)
    badge_counts = {d["_id"]: d["count"] for d in badge_docs if d.get("_id")}

    # Total verified users (level >= 3)
    verified_users = await db.verification_profiles.count_documents(
        {"verification_level": {"$gte": 3}}
    )

    return {
        "total_profiles": total_profiles,
        "total_verified_users": verified_users,
        "average_trust_score": avg_trust_score,
        "levels_breakdown": levels_breakdown,
        "badge_counts": badge_counts,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
