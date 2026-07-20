"""Reputation badge system — automatic award based on verified platform activity.

Badge awards are computed from the same data as reputation scores. No manual
assignment. No fake achievements. Every badge maps to a specific, verifiable
threshold in the database.

Anti-gaming: badges are computed from read-only aggregate counts. Users cannot
inflate them by submitting claims — the system reads from source-of-truth
collections (manuscripts, collaborations, reviews, teaching_lessons, etc.).
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

# ── Badge catalog ─────────────────────────────────────────────────────────────

BADGE_CATALOG: dict[str, dict] = {
    # ── Research ──────────────────────────────────────────────────────────────
    "published_author": {
        "code": "published_author",
        "label": "Published Author",
        "category": "research",
        "icon": "BookOpen",
        "description": "Published at least one manuscript on the platform.",
        "rarity": "common",
    },
    "active_researcher": {
        "code": "active_researcher",
        "label": "Active Researcher",
        "category": "research",
        "icon": "PenLine",
        "description": "Completed 10+ manuscript edits in the last 90 days.",
        "rarity": "common",
    },
    "collaboration_leader": {
        "code": "collaboration_leader",
        "label": "Collaboration Leader",
        "category": "research",
        "icon": "Users",
        "description": "Created and led 3 or more research collaborations.",
        "rarity": "uncommon",
    },
    "top_reviewer": {
        "code": "top_reviewer",
        "label": "Top Reviewer",
        "category": "research",
        "icon": "CheckCircle2",
        "description": "Completed 10 or more peer reviews on the platform.",
        "rarity": "uncommon",
    },
    "grant_contributor": {
        "code": "grant_contributor",
        "label": "Grant Contributor",
        "category": "research",
        "icon": "DollarSign",
        "description": "At least one awarded research grant linked to your work.",
        "rarity": "rare",
    },
    "research_mentor": {
        "code": "research_mentor",
        "label": "Research Mentor",
        "category": "research",
        "icon": "GraduationCap",
        "description": "Mentored 3+ researchers across workspace collaborations.",
        "rarity": "rare",
    },
    # ── Teaching ──────────────────────────────────────────────────────────────
    "lesson_designer": {
        "code": "lesson_designer",
        "label": "Lesson Designer",
        "category": "teaching",
        "icon": "FileText",
        "description": "Created 3 or more lesson plans in the Teaching Hub.",
        "rarity": "common",
    },
    "assessment_creator": {
        "code": "assessment_creator",
        "label": "Assessment Creator",
        "category": "teaching",
        "icon": "ClipboardCheck",
        "description": "Built 3 or more assessments or rubrics.",
        "rarity": "common",
    },
    "teaching_contributor": {
        "code": "teaching_contributor",
        "label": "Teaching Contributor",
        "category": "teaching",
        "icon": "MessageSquare",
        "description": "Sent 20 or more messages in Teaching Workspaces.",
        "rarity": "common",
    },
    "educational_mentor": {
        "code": "educational_mentor",
        "label": "Educational Mentor",
        "category": "teaching",
        "icon": "Heart",
        "description": "Participated in 2 or more educational collaborations.",
        "rarity": "uncommon",
    },
    "curriculum_builder": {
        "code": "curriculum_builder",
        "label": "Curriculum Builder",
        "category": "teaching",
        "icon": "BookCopy",
        "description": "Created 10+ lesson plans, showing sustained curriculum development.",
        "rarity": "rare",
    },
    # ── Community ─────────────────────────────────────────────────────────────
    "network_builder": {
        "code": "network_builder",
        "label": "Network Builder",
        "category": "community",
        "icon": "Network",
        "description": "Joined or accepted to 5 or more collaborations.",
        "rarity": "common",
    },
    "community_contributor": {
        "code": "community_contributor",
        "label": "Community Contributor",
        "category": "community",
        "icon": "Activity",
        "description": "Community reputation score of 40 or higher.",
        "rarity": "uncommon",
    },
    "collaboration_champion": {
        "code": "collaboration_champion",
        "label": "Collaboration Champion",
        "category": "community",
        "icon": "Trophy",
        "description": "Created 5+ collaborations and been accepted to 10+ more.",
        "rarity": "rare",
    },
    "trusted_member": {
        "code": "trusted_member",
        "label": "Trusted Member",
        "category": "community",
        "icon": "ShieldCheck",
        "description": "Overall reputation score of 60 or higher.",
        "rarity": "rare",
    },
    # ── Special ───────────────────────────────────────────────────────────────
    "early_adopter": {
        "code": "early_adopter",
        "label": "Early Adopter",
        "category": "special",
        "icon": "Star",
        "description": "Joined SYNAPTIQ in its first 6 months of operation.",
        "rarity": "special",
    },
    "founding_member": {
        "code": "founding_member",
        "label": "Founding Member",
        "category": "special",
        "icon": "Flame",
        "description": "Among the first members on the platform.",
        "rarity": "special",
    },
    "platform_pioneer": {
        "code": "platform_pioneer",
        "label": "Platform Pioneer",
        "category": "special",
        "icon": "Rocket",
        "description": "Early adopter who has also achieved an overall reputation of 40+.",
        "rarity": "special",
    },
}

# Platform launch date — used for "early adopter" / "founding member" thresholds.
# Adjust to your actual launch date.
PLATFORM_LAUNCH_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)
EARLY_ADOPTER_DAYS   = 180   # joined within 6 months of launch
FOUNDING_MEMBER_DAYS = 30    # joined within first 30 days


async def _check_research_badges(db, uid: str, score_doc: dict) -> list[str]:
    """Derive which research badges the user qualifies for from score_doc + DB."""
    earned: list[str] = []
    pub = score_doc.get("publication", {})
    rev = score_doc.get("reviewer",    {})
    fund = score_doc.get("funding",    {})
    collab = score_doc.get("collaboration", {})
    act = score_doc.get("activity", {})

    if pub.get("platform_published", 0) >= 1:
        earned.append("published_author")

    if act.get("manuscript_edits_90d", 0) >= 10:
        earned.append("active_researcher")

    if collab.get("owned", 0) >= 3:
        earned.append("collaboration_leader")

    if rev.get("completed", 0) >= 10:
        earned.append("top_reviewer")

    if fund.get("awarded", 0) >= 1:
        earned.append("grant_contributor")

    # Research mentor — led workspaces that have >= 3 distinct member_ids not equal to uid
    pipeline = [
        {"$match": {"owner_id": uid}},
        {"$project": {"member_ids": 1}},
        {"$unwind": "$member_ids"},
        {"$match": {"member_ids": {"$ne": uid}}},
        {"$group": {"_id": "$member_ids"}},
        {"$count": "total"},
    ]
    out = await db.workspaces.aggregate(pipeline).to_list(1)
    mentored = (out[0].get("total") if out else 0) or 0
    if mentored >= 3:
        earned.append("research_mentor")

    return earned


async def _check_teaching_badges(db, uid: str, score_doc: dict) -> list[str]:
    """Derive teaching badges from real teaching_* collection counts."""
    earned: list[str] = []
    teaching = score_doc.get("teaching", {})

    lessons    = teaching.get("lessons_created", 0)
    assessments = teaching.get("assessments_created", 0)
    chat_msgs  = teaching.get("workspace_messages", 0)
    collabs    = teaching.get("teaching_collaborations", 0)

    if lessons >= 3:
        earned.append("lesson_designer")
    if assessments >= 3:
        earned.append("assessment_creator")
    if chat_msgs >= 20:
        earned.append("teaching_contributor")
    if collabs >= 2:
        earned.append("educational_mentor")
    if lessons >= 10:
        earned.append("curriculum_builder")

    return earned


async def _check_community_badges(db, uid: str, score_doc: dict) -> list[str]:
    """Derive community badges."""
    earned: list[str] = []
    collab = score_doc.get("collaboration", {})
    community_score = score_doc.get("community_score", 0)
    overall = score_doc.get("overall", 0)

    total_joined = collab.get("accepted", 0) + collab.get("owned", 0)
    if total_joined >= 5:
        earned.append("network_builder")

    if community_score >= 40:
        earned.append("community_contributor")

    if collab.get("owned", 0) >= 5 and collab.get("accepted", 0) >= 10:
        earned.append("collaboration_champion")

    if overall >= 60:
        earned.append("trusted_member")

    return earned


async def _check_special_badges(db, uid: str, score_doc: dict) -> list[str]:
    """Derive special badges based on join date and overall score."""
    earned: list[str] = []
    user = await db.users.find_one({"_id": ObjectId(uid)}, {"created_at": 1})
    if not user:
        return earned

    created_at_raw = user.get("created_at")
    if not created_at_raw:
        return earned

    if isinstance(created_at_raw, datetime):
        created_at = created_at_raw.replace(tzinfo=timezone.utc) if created_at_raw.tzinfo is None else created_at_raw
    else:
        try:
            created_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
        except Exception:
            return earned

    days_since_launch = (created_at - PLATFORM_LAUNCH_DATE).days
    overall = score_doc.get("overall", 0)

    if days_since_launch <= EARLY_ADOPTER_DAYS:
        earned.append("early_adopter")

    if days_since_launch <= FOUNDING_MEMBER_DAYS:
        earned.append("founding_member")

    if days_since_launch <= EARLY_ADOPTER_DAYS and overall >= 40:
        earned.append("platform_pioneer")

    return earned


async def compute_badges(user_id: str, score_doc: dict) -> list[dict]:
    """Compute all earned badges for a user.

    Returns a list of badge dicts (catalog entry + earned_at).
    Persists to reputation_badges collection (upsert per user).
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    research_codes  = await _check_research_badges(db, user_id, score_doc)
    teaching_codes  = await _check_teaching_badges(db, user_id, score_doc)
    community_codes = await _check_community_badges(db, user_id, score_doc)
    special_codes   = await _check_special_badges(db, user_id, score_doc)

    all_codes = set(research_codes + teaching_codes + community_codes + special_codes)

    # Load existing earned_at timestamps so we don't reset the date on re-compute
    existing = await db.reputation_badges.find_one({"user_id": user_id}) or {}
    existing_map: dict[str, str] = {
        b["code"]: b["earned_at"]
        for b in existing.get("badges", [])
        if isinstance(b, dict) and b.get("code")
    }

    now = datetime.now(timezone.utc).isoformat()
    badges: list[dict] = []
    for code in sorted(all_codes):
        catalog_entry = BADGE_CATALOG.get(code)
        if not catalog_entry:
            continue
        badges.append({
            **catalog_entry,
            "earned_at": existing_map.get(code, now),
        })

    await db.reputation_badges.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "badges": badges, "updated_at": now}},
        upsert=True,
    )
    return badges


def get_catalog() -> list[dict]:
    """Return badge catalog sorted by category."""
    order = {"research": 0, "teaching": 1, "community": 2, "special": 3}
    return sorted(BADGE_CATALOG.values(), key=lambda b: (order.get(b["category"], 9), b["label"]))
