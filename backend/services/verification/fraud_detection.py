"""Fraud Detection Service — rule-based anomaly detection for verification integrity.

No ML. All checks are deterministic, based on real platform data.
Designed to flag suspicious patterns for manual admin review.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId

logger = logging.getLogger("synaptiq.verification.fraud")


async def check_for_anomalies(user_id: str, db) -> dict:
    """Run fraud/anomaly checks for a single user."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # ── Parallel data fetch ────────────────────────────────────────────────────
    (
        user,
        impact,
        reviewer_profile,
        verification_profile,
        recent_history_count,
        institution_membership,
    ) = await asyncio.gather(
        db.users.find_one({"_id": ObjectId(user_id)}),
        db.research_impact.find_one({"user_id": user_id}),
        db.reviewer_profiles.find_one({"user_id": user_id}),
        db.verification_profiles.find_one({"user_id": user_id}),
        db.verification_history.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": seven_days_ago},
        }),
        db.institution_memberships.find_one({"user_id": user_id, "status": "active"}),
    )

    user = user or {}
    impact = impact or {}
    reviewer_profile = reviewer_profile or {}
    verification_profile = verification_profile or {}

    flags: list[dict] = []
    risk_score = 0

    # ── Check 1: Multiple accounts with same full_name ─────────────────────────
    full_name = user.get("full_name") or user.get("name", "")
    if full_name:
        same_name_count = await db.users.count_documents(
            {"$or": [{"full_name": full_name}, {"name": full_name}],
             "_id": {"$ne": ObjectId(user_id)}}
        )
        if same_name_count >= 1:
            flags.append({
                "type": "duplicate_name",
                "severity": "medium",
                "description": (
                    f"Found {same_name_count} other account(s) with the same "
                    f"full name '{full_name}'. Possible duplicate account."
                ),
            })
            risk_score += 20

    # ── Check 2: Expertise claimed but 0 publications ─────────────────────────
    research_interests = user.get("research_interests", [])
    publication_count = int(impact.get("publication_count", 0) or 0)
    if research_interests and len(research_interests) > 0 and publication_count == 0:
        # Only flag if they list many research interests (claims expertise)
        if len(research_interests) >= 3:
            flags.append({
                "type": "unsubstantiated_expertise",
                "severity": "low",
                "description": (
                    f"User lists {len(research_interests)} research interests but "
                    "has 0 verified publications. Expertise claims unsubstantiated."
                ),
            })
            risk_score += 10

    # ── Check 3: Institution claimed but no membership ─────────────────────────
    claimed_institution = user.get("institution", "")
    if claimed_institution and not institution_membership:
        flags.append({
            "type": "institution_mismatch",
            "severity": "low",
            "description": (
                f"User claims affiliation with '{claimed_institution}' but has "
                "no active institution membership record on the platform."
            ),
        })
        risk_score += 10

    # ── Check 4: High verification level but no activity ─────────────────────
    verification_level = int(verification_profile.get("verification_level", 0) or 0)
    sis_total = float(impact.get("sis_total", 0.0) or 0.0)
    reviews_completed = int(reviewer_profile.get("reviews_completed", 0) or 0)
    if verification_level >= 5 and sis_total == 0.0 and reviews_completed == 0:
        flags.append({
            "type": "activity_inconsistency",
            "severity": "high",
            "description": (
                f"User is at verification level {verification_level} but has "
                "SIS score of 0 and 0 reviews completed. Activity is inconsistent "
                "with stated verification level."
            ),
        })
        risk_score += 30

    # ── Check 5: Rapid verification changes ───────────────────────────────────
    if recent_history_count > 3:
        flags.append({
            "type": "rapid_verification_changes",
            "severity": "medium",
            "description": (
                f"User had {recent_history_count} verification level changes "
                "in the last 7 days. Unusually rapid progression."
            ),
        })
        risk_score += 20

    # ── Determine recommendation ───────────────────────────────────────────────
    if risk_score < 20:
        recommendation = "low_risk"
    elif risk_score <= 50:
        recommendation = "review_recommended"
    else:
        recommendation = "manual_review_required"

    return {
        "risk_score": risk_score,
        "flags": flags,
        "checked_at": now.isoformat(),
        "recommendation": recommendation,
    }


async def get_platform_fraud_overview(db) -> dict:
    """Return a platform-wide fraud / anomaly overview from audit logs."""
    now = datetime.now(timezone.utc)

    # Count flagged audit actions by recommendation type stored in verification_audits
    review_recommended_count = await db.verification_audits.count_documents(
        {"action": "fraud_check", "details.recommendation": "review_recommended"}
    )
    manual_review_count = await db.verification_audits.count_documents(
        {"action": "fraud_check", "details.recommendation": "manual_review_required"}
    )

    # Count distinct users flagged (any fraud check audit in last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    pipeline = [
        {
            "$match": {
                "action": "fraud_check",
                "created_at": {"$gte": thirty_days_ago},
                "details.recommendation": {"$in": ["review_recommended", "manual_review_required"]},
            }
        },
        {"$group": {"_id": "$user_id"}},
        {"$count": "total"},
    ]
    cursor = db.verification_audits.aggregate(pipeline)
    result_docs = await cursor.to_list(length=1)
    total_flagged_users = int(result_docs[0]["total"] if result_docs else 0)

    # Count total accounts
    total_profiles = await db.verification_profiles.count_documents({})

    return {
        "total_profiles": total_profiles,
        "total_flagged_users_30d": total_flagged_users,
        "review_recommended_count": review_recommended_count,
        "manual_review_required_count": manual_review_count,
        "flag_rate_pct": (
            round(100.0 * total_flagged_users / total_profiles, 2)
            if total_profiles > 0
            else 0.0
        ),
        "computed_at": now.isoformat(),
    }
