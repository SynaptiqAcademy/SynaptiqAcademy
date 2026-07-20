from __future__ import annotations

from typing import Any

from bson import ObjectId

from services.recommendation.profiles import get_or_refresh_profile
from services.recommendation.scoring import normalize_set, jaccard, clamp
from services.recommendation.explainer import explain_reviewer

_SENIORITY_SCORES: dict[str, float] = {
    "professor": 15.0,
    "associate_professor": 13.0,
    "senior_researcher": 12.0,
    "principal_investigator": 13.0,
    "emeritus": 10.0,
    "researcher": 8.0,
    "junior_researcher": 6.0,
    "postdoc": 6.0,
    "phd_student": 3.0,
}


async def match_reviewers(
    user_id: str,
    db,
    manuscript_id: str | None = None,
    project_id: str | None = None,
    limit: int = 20,
    interaction_cache: dict | None = None,
) -> list[dict]:
    """
    Return algorithmically scored reviewer recommendations.

    Conflict of interest exclusions:
    - co-authors of the manuscript
    - current collaborators (in collaborations collection)
    - same institution as the manuscript's lead author
    - suspended users
    - demo accounts
    - private profiles
    - self

    Sub-scores:
      expertise_score       = jaccard(candidate.research_areas, target.research_areas) * 40
      publication_score     = min(published_count / 10, 1.0) * 25
      review_history_score  = min(review_count / 5, 1.0) * 20
      seniority_score       = role-based, 0-15
      country_diversity     = 5 if different country from lead author
    """
    # ── Load requesting user's profile ──────────────────────────────────────
    user_p = await get_or_refresh_profile(user_id, db)

    if user_p.get("is_suspended") or user_p.get("is_demo"):
        return []

    # ── Resolve manuscript or project for context ────────────────────────────
    target_areas: set[str] = set()
    target_kws: set[str] = set()
    co_author_ids: set[str] = set()
    lead_institution: str = ""
    lead_country: str = ""

    if manuscript_id and ObjectId.is_valid(manuscript_id):
        manuscript = await db.manuscripts.find_one(
            {"_id": ObjectId(manuscript_id)},
            {"research_areas": 1, "keywords": 1, "authors": 1, "lead_author_id": 1},
        )
        if manuscript:
            target_areas = normalize_set(manuscript.get("research_areas") or [])
            target_kws = normalize_set(manuscript.get("keywords") or [])
            for author in (manuscript.get("authors") or []):
                co_author_ids.add(str(author))
            lead_id = manuscript.get("lead_author_id")
            if lead_id:
                co_author_ids.add(str(lead_id))
                lead_user = await db.users.find_one(
                    {"_id": ObjectId(lead_id)} if ObjectId.is_valid(lead_id) else {"_id": None},
                    {"institution": 1, "country": 1},
                )
                if lead_user:
                    lead_institution = (lead_user.get("institution") or "").strip().lower()
                    lead_country = (lead_user.get("country") or "").strip().lower()

    elif project_id and ObjectId.is_valid(project_id):
        project = await db.projects.find_one(
            {"_id": ObjectId(project_id)},
            {"research_areas": 1, "keywords": 1, "members": 1, "owner_id": 1},
        )
        if project:
            target_areas = normalize_set(project.get("research_areas") or [])
            target_kws = normalize_set(project.get("keywords") or [])
            for member in (project.get("members") or []):
                co_author_ids.add(str(member))
            owner_id = project.get("owner_id")
            if owner_id:
                co_author_ids.add(str(owner_id))

    # Fall back to user's own areas if no manuscript/project
    if not target_areas:
        target_areas = normalize_set(user_p.get("research_areas") or [])
        target_kws = normalize_set(user_p.get("research_keywords") or [])

    co_author_ids.discard(user_id)

    # ── Get current collaborators (conflict of interest) ─────────────────────
    collab_docs = await db.collaborations.find(
        {"members": user_id},
        {"members": 1},
    ).to_list(500)

    collaborator_ids: set[str] = set()
    for collab in collab_docs:
        for member in (collab.get("members") or []):
            collaborator_ids.add(str(member))
    collaborator_ids.discard(user_id)

    excluded_ids = co_author_ids | collaborator_ids
    excluded_ids.add(user_id)

    # ── Query candidate reviewers ────────────────────────────────────────────
    query: dict[str, Any] = {
        "is_suspended": {"$ne": True},
        "account_type": {"$ne": "demo"},
        "profile_visibility": {"$ne": "private"},
    }

    projection = {
        "_id": 1,
        "full_name": 1,
        "institution": 1,
        "country": 1,
        "academic_role": 1,
        "avatar_url": 1,
        "research_areas": 1,
    }

    candidates_raw = await db.users.find(query, projection).limit(500).to_list(500)

    # ── Batch-load profiles for publication/review counts ────────────────────
    candidate_ids = [str(c["_id"]) for c in candidates_raw]
    profile_docs = await db.recommendation_profiles.find(
        {"user_id": {"$in": candidate_ids}},
        {"user_id": 1, "published_count": 1, "review_count": 1},
    ).to_list(500)
    profile_map = {p["user_id"]: p for p in profile_docs}

    # ── Score each candidate ─────────────────────────────────────────────────
    results: list[dict] = []

    for cand in candidates_raw:
        cand_id = str(cand["_id"])

        if cand_id in excluded_ids:
            continue

        # Institution conflict of interest
        cand_institution = (cand.get("institution") or "").strip().lower()
        if lead_institution and cand_institution and lead_institution == cand_institution:
            continue

        cand_areas = normalize_set(cand.get("research_areas") or [])
        cand_country = (cand.get("country") or "").strip().lower()
        cand_role = (cand.get("academic_role") or "").strip().lower()

        cand_profile = profile_map.get(cand_id, {})
        published_count = int(cand_profile.get("published_count", 0))
        review_count = int(cand_profile.get("review_count", 0))

        # Sub-scores
        expertise_score = jaccard(target_areas, cand_areas) * 40
        publication_score = min(published_count / 10.0, 1.0) * 25
        review_history_score = min(review_count / 5.0, 1.0) * 20
        seniority_score = _SENIORITY_SCORES.get(cand_role, 5.0)
        country_diversity = 5.0 if (lead_country and cand_country and lead_country != cand_country) else 0.0

        sub_scores = {
            "expertise_score": expertise_score,
            "publication_score": publication_score,
            "review_history_score": review_history_score,
            "seniority_score": seniority_score,
            "country_diversity": country_diversity,
        }

        total = clamp(sum(sub_scores.values()))

        # Interaction penalty
        if interaction_cache:
            action = interaction_cache.get(cand_id)
            if action == "dismissed":
                total *= 0.2

        if total <= 0:
            continue

        reviewer_data = {
            "research_areas": list(cand_areas),
            "published_count": published_count,
            "review_count": review_count,
            "academic_role": cand_role,
            "country": cand_country,
        }

        explanation = explain_reviewer(user_p, reviewer_data, sub_scores)

        results.append({
            "user_id": cand_id,
            "full_name": (cand.get("full_name") or "").strip(),
            "institution": (cand.get("institution") or "").strip(),
            "country": (cand.get("country") or "").strip(),
            "academic_role": (cand.get("academic_role") or "").strip(),
            "avatar_url": cand.get("avatar_url") or None,
            "research_areas": [a.title() for a in sorted(cand_areas)],
            "publication_count": published_count,
            "review_count": review_count,
            "score": round(total, 1),
            "conflict_of_interest": False,  # Already excluded conflicts above
            "explanation": explanation,
        })

    # ── Sort and return top results ──────────────────────────────────────────
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
