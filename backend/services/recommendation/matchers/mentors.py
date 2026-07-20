from __future__ import annotations

from typing import Any

from services.recommendation.profiles import get_or_refresh_profile
from services.recommendation.scoring import normalize_set, jaccard, clamp
from services.recommendation.explainer import explain_mentor

def _normalize_role(role: str) -> str:
    """Normalize role: lowercase, replace spaces/hyphens with underscores."""
    return role.strip().lower().replace(" ", "_").replace("-", "_")


# Roles considered senior enough to mentor (normalized form)
_SENIOR_ROLES: set[str] = {
    "professor",
    "associate_professor",
    "senior_researcher",
    "senior_lecturer",
    "principal_investigator",
    "reader",
    "emeritus",
    "full_professor",
    "associate_research_professor",
}

# Ordered seniority levels (higher index = more senior)
_SENIORITY_RANK: dict[str, int] = {
    "student": 0,
    "undergraduate": 0,
    "phd_candidate": 1,
    "phd_student": 1,
    "postdoc": 2,
    "junior_researcher": 2,
    "assistant_professor": 3,
    "researcher": 3,
    "lecturer": 3,
    "associate_professor": 4,
    "senior_lecturer": 4,
    "senior_researcher": 4,
    "reader": 4,
    "principal_investigator": 5,
    "professor": 5,
    "full_professor": 5,
    "emeritus": 6,
}


def _is_senior(role: str) -> bool:
    norm = _normalize_role(role)
    return norm in _SENIOR_ROLES or "professor" in norm or "senior" in norm


def _user_rank(role: str) -> int:
    return _SENIORITY_RANK.get(_normalize_role(role), 3)


async def match_mentors(
    user_id: str,
    db,
    limit: int = 20,
    area_filter: str | None = None,
    interaction_cache: dict | None = None,
) -> list[dict]:
    """
    Return algorithmically scored mentor recommendations for a given user.

    Only recommends users with senior academic roles:
    - professor, associate_professor, senior_researcher, principal_investigator, emeritus

    Excluded:
    - users with same or lower seniority
    - suspended users
    - private profiles
    - already connected (in same collaboration)
    - self

    Sub-scores:
      area_score         = jaccard(user.research_areas, mentor.research_areas) * 35
      kw_score           = jaccard(user.keywords, mentor.keywords) * 20
      rep_score          = min(mentor.reputation_score / 100, 1.0) * 20
      publication_score  = min(mentor.published_count / 20, 1.0) * 15
      teaching_score     = min(mentor.teaching_count / 5, 1.0) * 10
    """
    # ── Load requesting user's profile ──────────────────────────────────────
    user_p = await get_or_refresh_profile(user_id, db)

    if user_p.get("is_suspended") or user_p.get("is_demo"):
        return []

    user_role = (user_p.get("academic_role") or "").strip().lower()
    user_rank = _user_rank(user_role)

    # If user is already at top seniority, skip mentor matching
    if user_rank >= _SENIORITY_RANK.get("professor", 5):
        return []

    user_areas = normalize_set(user_p.get("research_areas") or [])
    user_kws = normalize_set(
        (user_p.get("research_keywords") or []) + (user_p.get("research_interests") or [])
    )

    # ── Get already-connected collaborator IDs ───────────────────────────────
    collab_docs = await db.collaborations.find(
        {"members": user_id},
        {"members": 1},
    ).to_list(500)

    connected_ids: set[str] = set()
    for collab in collab_docs:
        for member in (collab.get("members") or []):
            connected_ids.add(str(member))
    connected_ids.discard(user_id)

    # ── Query senior candidates ──────────────────────────────────────────────
    # DB stores roles in mixed case (e.g. "Associate Professor", "Professor")
    # Use regex to match any senior-level title
    senior_role_pattern = r"professor|senior|principal investigator|emeritus|reader"
    query: dict[str, Any] = {
        "academic_role": {"$regex": senior_role_pattern, "$options": "i"},
        "is_suspended": {"$ne": True},
        "profile_visibility": {"$ne": "private"},
        "account_type": {"$ne": "demo"},
    }

    if area_filter:
        query["research_areas"] = {"$regex": area_filter, "$options": "i"}

    projection = {
        "_id": 1,
        "full_name": 1,
        "institution": 1,
        "country": 1,
        "academic_role": 1,
        "avatar_url": 1,
        "research_areas": 1,
        "research_keywords": 1,
        "research_interests": 1,
    }

    mentors_raw = await db.users.find(query, projection).limit(500).to_list(500)

    # ── Batch-load profiles for reputation/publication/teaching counts ────────
    mentor_ids = [str(m["_id"]) for m in mentors_raw]
    profile_docs = await db.recommendation_profiles.find(
        {"user_id": {"$in": mentor_ids}},
        {"user_id": 1, "reputation_score": 1, "published_count": 1},
    ).to_list(500)
    profile_map = {p["user_id"]: p for p in profile_docs}

    # ── Batch-load teaching workspace counts ─────────────────────────────────
    try:
        teaching_counts_cursor = db.teaching_workspaces.aggregate([
            {"$match": {"$or": [
                {"owner_id": {"$in": mentor_ids}},
                {"member_ids": {"$in": mentor_ids}},
            ]}},
            {"$group": {"_id": "$owner_id", "count": {"$sum": 1}}},
        ])
        teaching_counts_raw = await teaching_counts_cursor.to_list(500)
        teaching_count_map: dict[str, int] = {t["_id"]: t["count"] for t in teaching_counts_raw}
    except Exception:
        teaching_count_map = {}

    # ── Score each mentor ─────────────────────────────────────────────────────
    results: list[dict] = []

    for mentor in mentors_raw:
        mentor_id = str(mentor["_id"])

        if mentor_id == user_id:
            continue
        if mentor_id in connected_ids:
            continue

        mentor_role = (mentor.get("academic_role") or "").strip().lower()
        mentor_rank = _user_rank(mentor_role)

        # Only recommend if mentor is strictly more senior
        if mentor_rank <= user_rank:
            continue

        mentor_areas = normalize_set(mentor.get("research_areas") or [])
        mentor_kws = normalize_set(
            (mentor.get("research_keywords") or []) + (mentor.get("research_interests") or [])
        )

        mentor_profile = profile_map.get(mentor_id, {})
        reputation_score = int(mentor_profile.get("reputation_score", 0))
        published_count = int(mentor_profile.get("published_count", 0))
        teaching_count = int(teaching_count_map.get(mentor_id, 0))

        # Sub-scores
        area_score = jaccard(user_areas, mentor_areas) * 35
        kw_score = jaccard(user_kws, mentor_kws) * 20
        rep_score = min(reputation_score / 100.0, 1.0) * 20
        publication_score = min(published_count / 20.0, 1.0) * 15
        teaching_score = min(teaching_count / 5.0, 1.0) * 10

        sub_scores = {
            "area_score": area_score,
            "kw_score": kw_score,
            "rep_score": rep_score,
            "publication_score": publication_score,
            "teaching_score": teaching_score,
        }

        total = clamp(sum(sub_scores.values()))

        # Interaction penalty
        if interaction_cache:
            action = interaction_cache.get(mentor_id)
            if action == "dismissed":
                total *= 0.2

        if total <= 0:
            continue

        mentor_data = {
            "research_areas": list(mentor_areas),
            "reputation_score": reputation_score,
            "published_count": published_count,
            "academic_role": mentor_role,
        }

        explanation = explain_mentor(user_p, mentor_data, sub_scores)

        # Mentorship areas = first 3 research areas
        mentorship_areas = [a.title() for a in sorted(mentor_areas)][:3]

        results.append({
            "user_id": mentor_id,
            "full_name": (mentor.get("full_name") or "").strip(),
            "institution": (mentor.get("institution") or "").strip(),
            "country": (mentor.get("country") or "").strip(),
            "academic_role": (mentor.get("academic_role") or "").strip(),
            "avatar_url": mentor.get("avatar_url") or None,
            "research_areas": [a.title() for a in sorted(mentor_areas)],
            "publication_count": published_count,
            "reputation_score": reputation_score,
            "score": round(total, 1),
            "explanation": explanation,
            "mentorship_areas": mentorship_areas,
        })

    # ── Sort and return top results ──────────────────────────────────────────
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
