"""Research Reputation Event Engine — Phase XX.

Accumulates reputation POINTS from verified platform actions.
Every point-earning action generates a permanent, idempotent audit record.
Suspended/demo users cannot earn points. No admin modification of scores.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.reputation.events")

POINT_MAP: dict[str, int] = {
    "profile_completed": 20,
    "orcid_verified": 25,
    "project_created": 5,
    "project_completed": 20,
    "collaboration_created": 5,
    "collaboration_accepted": 10,
    "workspace_created": 5,
    "workspace_contribution": 3,
    "manuscript_created": 5,
    "manuscript_submitted": 15,
    "manuscript_published": 50,
    "grant_application_submitted": 20,
    "grant_awarded": 100,
    "peer_review_completed": 15,
    "teaching_lesson_published": 10,
    "conference_participation": 10,
    "citation_milestone": 5,
    "mentor_session_completed": 15,
}

REPUTATION_LEVELS = [
    {"level": 1, "label": "Research Explorer",      "min": 0,    "max": 99},
    {"level": 2, "label": "Emerging Researcher",    "min": 100,  "max": 249},
    {"level": 3, "label": "Active Researcher",      "min": 250,  "max": 499},
    {"level": 4, "label": "Established Researcher", "min": 500,  "max": 999},
    {"level": 5, "label": "Advanced Researcher",    "min": 1000, "max": 1999},
    {"level": 6, "label": "Research Leader",        "min": 2000, "max": 4999},
    {"level": 7, "label": "Distinguished Scholar",  "min": 5000, "max": 9_999_999},
]


def get_reputation_level(score: int) -> dict:
    for lvl in reversed(REPUTATION_LEVELS):
        if score >= lvl["min"]:
            return lvl
    return REPUTATION_LEVELS[0]


def get_next_level(score: int) -> Optional[dict]:
    current = get_reputation_level(score)
    for lvl in REPUTATION_LEVELS:
        if lvl["level"] == current["level"] + 1:
            return lvl
    return None


def get_progress_to_next(score: int) -> int:
    current = get_reputation_level(score)
    next_lvl = get_next_level(score)
    if not next_lvl:
        return 100
    span = current["max"] - current["min"] + 1
    within = score - current["min"]
    return min(100, round((within / span) * 100))


def _event_category(event_type: str) -> str:
    """Map event type to sub-score category."""
    mapping = {
        "manuscript_created": "publication",
        "manuscript_submitted": "publication",
        "manuscript_published": "publication",
        "citation_milestone": "publication",
        "peer_review_completed": "reviewer",
        "teaching_lesson_published": "teaching",
        "mentor_session_completed": "teaching",
        "collaboration_created": "collaboration",
        "collaboration_accepted": "collaboration",
        "workspace_created": "collaboration",
        "workspace_contribution": "collaboration",
        "grant_application_submitted": "research",
        "grant_awarded": "research",
        "project_created": "research",
        "project_completed": "research",
        "conference_participation": "research",
        "profile_completed": "profile",
        "orcid_verified": "profile",
    }
    return mapping.get(event_type, "research")


async def _count_events_by_type(db, user_id: str) -> dict:
    """Count significant activities by type for the user."""
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
    ]
    results = await db.research_reputation_events.aggregate(pipeline).to_list(100)
    return {r["_id"]: r["count"] for r in results}


async def _evaluate_badges(db, user_id: str, score: int) -> None:
    """Evaluate all 16 badges, store in research_reputation_badges, update badge count."""
    event_counts = await _count_events_by_type(db, user_id)
    rep_doc = await db.research_reputation.find_one({"user_id": user_id}) or {}

    # Look up user profile for orcid/profile completeness
    user = await db.users.find_one({"_id": ObjectId(user_id)}) or {}

    earned: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    def _badge(code: str, label: str, description: str, rarity: str = "common") -> dict:
        return {
            "code": code,
            "label": label,
            "description": description,
            "rarity": rarity,
            "earned_at": now_iso,
        }

    # 1. orcid_verified — user has orcid field set
    orcid_field = user.get("orcid")
    orcid_verified_event = event_counts.get("orcid_verified", 0)
    if orcid_field or orcid_verified_event > 0:
        earned.append(_badge("orcid_verified", "ORCID Verified",
                              "Connected and verified your ORCID iD.", "uncommon"))

    # 2. profile_complete — profile_completed event fired
    if event_counts.get("profile_completed", 0) > 0:
        earned.append(_badge("profile_complete", "Profile Complete",
                              "Completed your researcher profile.", "common"))

    # 3. first_publication — at least 1 manuscript published
    pubs = event_counts.get("manuscript_published", 0)
    if pubs >= 1:
        earned.append(_badge("first_publication", "First Publication",
                              "Published your first manuscript on the platform.", "common"))

    # 4. published_author — 3+ publications
    if pubs >= 3:
        earned.append(_badge("published_author", "Published Author",
                              "Published 3 or more manuscripts on the platform.", "uncommon"))

    # 5. research_collaborator — 1+ collaboration accepted/created
    collab_count = (event_counts.get("collaboration_created", 0)
                    + event_counts.get("collaboration_accepted", 0))
    if collab_count >= 1:
        earned.append(_badge("research_collaborator", "Research Collaborator",
                              "Participated in at least one research collaboration.", "common"))

    # 6. peer_reviewer — 1+ peer review completed
    if event_counts.get("peer_review_completed", 0) >= 1:
        earned.append(_badge("peer_reviewer", "Peer Reviewer",
                              "Completed at least one peer review.", "common"))

    # 7. mentor — 1+ mentor session completed
    if event_counts.get("mentor_session_completed", 0) >= 1:
        earned.append(_badge("mentor", "Mentor",
                              "Completed at least one mentoring session.", "uncommon"))

    # 8. grant_winner — grant_awarded event fired
    if event_counts.get("grant_awarded", 0) >= 1:
        earned.append(_badge("grant_winner", "Grant Winner",
                              "Successfully received a research grant.", "rare"))

    # 9. conference_speaker — conference participation event
    if event_counts.get("conference_participation", 0) >= 1:
        earned.append(_badge("conference_speaker", "Conference Speaker",
                              "Participated in a research conference.", "uncommon"))

    # 10. teaching_contributor — teaching lesson published
    if event_counts.get("teaching_lesson_published", 0) >= 1:
        earned.append(_badge("teaching_contributor", "Teaching Contributor",
                              "Published at least one teaching lesson.", "common"))

    # 11-13. Percentile badges — from rank fields
    percentile = rep_doc.get("percentile_global", 0) or 0
    if percentile >= 90:
        earned.append(_badge("top_10_percent", "Top 10%",
                              "Ranked in the top 10% of researchers globally.", "rare"))
    if percentile >= 95:
        earned.append(_badge("top_5_percent", "Top 5%",
                              "Ranked in the top 5% of researchers globally.", "rare"))
    if percentile >= 99:
        earned.append(_badge("top_1_percent", "Top 1%",
                              "Ranked in the top 1% of researchers globally.", "legendary"))

    # 14. institution_leader — rank_institution == 1
    if rep_doc.get("rank_institution") == 1:
        earned.append(_badge("institution_leader", "Institution Leader",
                              "Top-ranked researcher at your institution.", "legendary"))

    # 15. country_leader — rank_country == 1
    if rep_doc.get("rank_country") == 1:
        earned.append(_badge("country_leader", "Country Leader",
                              "Top-ranked researcher in your country.", "legendary"))

    # 16. global_leader — rank_global == 1
    if rep_doc.get("rank_global") == 1:
        earned.append(_badge("global_leader", "Global Leader",
                              "Top-ranked researcher on the platform.", "legendary"))

    # Store badges
    await db.research_reputation_badges.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "badges": earned,
            "badges_count": len(earned),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    # Update badge count in research_reputation
    await db.research_reputation.update_one(
        {"user_id": user_id},
        {"$set": {"badges_count": len(earned)}},
    )


async def _update_reputation(db, user_id: str, event_type: str, points: int, now: datetime) -> None:
    """Atomically update the reputation doc, recompute level, update sub-score counts."""
    category = _event_category(event_type)

    # Map category to sub-score field
    category_field_map = {
        "publication": "publication_score",
        "reviewer": "reviewer_score",
        "teaching": "teaching_score",
        "collaboration": "collaboration_score",
        "profile": "profile_score",
        "research": "research_score",
    }
    sub_field = category_field_map.get(category, "research_score")

    # Fetch current doc to recompute level
    existing = await db.research_reputation.find_one({"user_id": user_id}) or {}
    current_score = existing.get("overall_score", 0) or 0
    new_score = current_score + points

    level_info = get_reputation_level(new_score)
    next_lvl = get_next_level(new_score)
    progress = get_progress_to_next(new_score)

    # Ensure the document exists with zeroed sub-scores before $inc.
    # Use a separate insert-only op to avoid $setOnInsert conflicting with $inc on same field.
    existing = await db.research_reputation.find_one({"user_id": user_id}, {"_id": 1})
    if not existing:
        await db.research_reputation.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {
                "user_id": user_id,
                "created_at": now.isoformat(),
                "rank_global": None,
                "rank_country": None,
                "rank_institution": None,
                "percentile_global": 0,
                "badges_count": 0,
                "overall_score": 0,
                "research_score": 0,
                "publication_score": 0,
                "collaboration_score": 0,
                "reviewer_score": 0,
                "teaching_score": 0,
                "profile_score": 0,
            }},
            upsert=True,
        )

    update_fields: dict = {
        "overall_score": new_score,
        "reputation_level": level_info["level"],
        "reputation_label": level_info["label"],
        "progress_to_next": progress,
        "updated_at": now.isoformat(),
    }
    if next_lvl:
        update_fields["next_level_min"] = next_lvl["min"]
        update_fields["next_level_label"] = next_lvl["label"]

    await db.research_reputation.update_one(
        {"user_id": user_id},
        {
            "$inc": {sub_field: points},
            "$set": update_fields,
        },
    )

    # Re-evaluate badges with the new score
    await _evaluate_badges(db, user_id, new_score)


async def emit_reputation_event(
    user_id: str,
    event_type: str,
    source_entity: str,
    source_entity_id: str,
    description: Optional[str] = None,
    *,
    db=None,
) -> bool:
    """Emit a reputation event and award points.

    Idempotent: the same (user_id, event_type, source_entity_id) triple will not
    award points twice. Suspended or demo users cannot earn points.

    Returns True if points were awarded, False if skipped (duplicate or ineligible).
    """
    if db is None:
        db = get_db()

        db = DBProxy(db, SecurityContext.system())

    if event_type not in POINT_MAP:
        logger.warning("Unknown reputation event type: %s", event_type)
        return False

    # Check user eligibility
    try:
        user = await db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"status": 1, "is_demo": 1, "suspended": 1},
        )
    except Exception:
        logger.warning("Invalid user_id for reputation event: %s", user_id)
        return False

    if not user:
        logger.warning("User not found for reputation event: %s", user_id)
        return False

    if user.get("suspended") or user.get("status") == "suspended":
        logger.info("Skipping reputation event for suspended user: %s", user_id)
        return False

    if user.get("is_demo"):
        logger.info("Skipping reputation event for demo user: %s", user_id)
        return False

    # Idempotency check — unique compound (user_id + event_type + source_entity_id)
    existing = await db.research_reputation_events.find_one({
        "user_id": user_id,
        "event_type": event_type,
        "source_entity_id": source_entity_id,
    })
    if existing:
        logger.debug("Duplicate reputation event skipped: %s / %s / %s",
                     user_id, event_type, source_entity_id)
        return False

    points = POINT_MAP[event_type]
    now = datetime.now(timezone.utc)

    event_doc = {
        "event_id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_type": event_type,
        "source_entity": source_entity,
        "source_entity_id": source_entity_id,
        "points": points,
        "category": _event_category(event_type),
        "description": description or event_type.replace("_", " ").title(),
        "created_at": now.isoformat(),
    }

    try:
        await db.research_reputation_events.insert_one(event_doc)
    except Exception as exc:
        # E11000 duplicate key on race condition — treat as idempotent skip
        err_str = str(exc)
        if "E11000" in err_str or "duplicate key" in err_str.lower():
            logger.debug("Race condition duplicate event skipped: %s / %s / %s",
                         user_id, event_type, source_entity_id)
            return False
        logger.error("Failed to insert reputation event: %s", exc)
        raise

    await _update_reputation(db, user_id, event_type, points, now)
    logger.info("Reputation event: user=%s type=%s points=+%d", user_id, event_type, points)
    return True


async def get_research_reputation(user_id: str, db=None) -> dict:
    """Return full reputation doc with level/progress/badges attached.

    Returns an empty skeleton if no doc exists yet.
    """
    if db is None:
        db = get_db()

        db = DBProxy(db, SecurityContext.system())

    doc = await db.research_reputation.find_one({"user_id": user_id})
    badges_doc = await db.research_reputation_badges.find_one({"user_id": user_id})

    if not doc:
        # Return empty skeleton so callers always get a consistent shape
        level_info = get_reputation_level(0)
        return {
            "user_id": user_id,
            "overall_score": 0,
            "reputation_level": level_info["level"],
            "reputation_label": level_info["label"],
            "progress_to_next": 0,
            "next_level_min": REPUTATION_LEVELS[1]["min"],
            "next_level_label": REPUTATION_LEVELS[1]["label"],
            "research_score": 0,
            "publication_score": 0,
            "collaboration_score": 0,
            "reviewer_score": 0,
            "teaching_score": 0,
            "profile_score": 0,
            "rank_global": None,
            "rank_country": None,
            "rank_institution": None,
            "percentile_global": 0,
            "badges": [],
            "badges_count": 0,
            "created_at": None,
            "updated_at": None,
        }

    doc.pop("_id", None)
    doc["badges"] = (badges_doc or {}).get("badges", [])
    return doc


async def get_recent_events(user_id: str, limit: int = 20, db=None) -> list:
    """Return the most recent reputation events for a user."""
    if db is None:
        db = get_db()

        db = DBProxy(db, SecurityContext.system())

    cursor = db.research_reputation_events.find(
        {"user_id": user_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(limit)

    return await cursor.to_list(limit)


async def compute_rankings(db=None) -> dict:
    """Compute global/country/institution ranks and percentiles.

    Updates rank fields in research_reputation and stores a snapshot
    in research_rankings.
    """
    if db is None:
        db = get_db()

        db = DBProxy(db, SecurityContext.system())

    now = datetime.now(timezone.utc)

    # Fetch all reputation docs with user info
    pipeline = [
        {"$sort": {"overall_score": -1}},
        {
            "$lookup": {
                "from": "users",
                "let": {"uid": "$user_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$uid"]}}},
                    {"$project": {"country": 1, "institution": 1}},
                ],
                "as": "user_info",
            }
        },
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "user_id": 1,
                "overall_score": 1,
                "country": "$user_info.country",
                "institution": "$user_info.institution",
            }
        },
    ]

    all_docs = await db.research_reputation.aggregate(pipeline).to_list(10000)
    total_users = len(all_docs)

    if not total_users:
        return {"ranked": 0, "timestamp": now.isoformat()}

    # Assign global ranks
    global_rank_map: dict[str, int] = {}
    for rank, doc in enumerate(all_docs, start=1):
        global_rank_map[doc["user_id"]] = rank

    # Build country and institution sub-rankings
    country_groups: dict[str, list] = {}
    institution_groups: dict[str, list] = {}

    for doc in all_docs:
        uid = doc["user_id"]
        country = (doc.get("country") or "").strip()
        institution = (doc.get("institution") or "").strip()

        if country:
            country_groups.setdefault(country, []).append(uid)
        if institution:
            institution_groups.setdefault(institution, []).append(uid)

    # country rank maps — already sorted by overall_score desc from pipeline
    country_rank_map: dict[str, int] = {}
    for members in country_groups.values():
        for rank, uid in enumerate(members, start=1):
            country_rank_map[uid] = rank

    institution_rank_map: dict[str, int] = {}
    for members in institution_groups.values():
        for rank, uid in enumerate(members, start=1):
            institution_rank_map[uid] = rank

    # Batch update all docs
    for doc in all_docs:
        uid = doc["user_id"]
        g_rank = global_rank_map.get(uid)
        c_rank = country_rank_map.get(uid)
        i_rank = institution_rank_map.get(uid)
        percentile = round(((total_users - g_rank) / total_users) * 100, 1) if g_rank else 0

        await db.research_reputation.update_one(
            {"user_id": uid},
            {"$set": {
                "rank_global": g_rank,
                "rank_country": c_rank,
                "rank_institution": i_rank,
                "percentile_global": percentile,
                "rankings_computed_at": now.isoformat(),
            }},
        )

    # Store snapshot in research_rankings
    snapshot = {
        "computed_at": now.isoformat(),
        "total_users": total_users,
        "top_10": [
            {
                "rank": global_rank_map[d["user_id"]],
                "user_id": d["user_id"],
                "overall_score": d.get("overall_score", 0),
            }
            for d in all_docs[:10]
        ],
    }
    await db.research_rankings.insert_one(snapshot)

    return {
        "ranked": total_users,
        "timestamp": now.isoformat(),
    }
