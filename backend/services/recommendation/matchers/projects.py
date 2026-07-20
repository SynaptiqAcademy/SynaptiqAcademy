from __future__ import annotations

import re
from typing import Any

from bson import ObjectId

from services.recommendation.profiles import get_or_refresh_profile
from services.recommendation.scoring import normalize_set, clamp
from services.recommendation.explainer import explain_project


def _text_keyword_score(user_kws: set, user_areas: set, text: str, max_score: float) -> tuple[float, list[str]]:
    """
    Count how many user keywords/areas appear in the given text (lowercase).
    Returns (score, matched_terms).
    """
    text_lower = text.lower()
    matched: list[str] = []
    for term in user_kws | user_areas:
        if term and len(term) > 2 and re.search(r'\b' + re.escape(term) + r'\b', text_lower):
            matched.append(term)
    score = min(len(matched) * (max_score / max(len(user_kws | user_areas), 10)), max_score)
    return score, matched


async def match_projects(
    user_id: str,
    db,
    limit: int = 20,
    area_filter: str | None = None,
    interaction_cache: dict | None = None,
) -> list[dict]:
    """
    Return algorithmically scored project recommendations for a given user.

    Note: Projects in the DB do not have research_areas. Matching is done via
    text search on title + description against user's research keywords and areas.

    Sub-scores:
      text_score     = keyword/area matches in title+description → 0-55
      skill_score    = jaccard(user.skills, project.skills_needed if available) * 15
      title_score    = title keyword hits → 0-15
      open_score     = 15 (base score for any open/non-private project)
    """
    user_p = await get_or_refresh_profile(user_id, db)
    if user_p.get("is_suspended") or user_p.get("is_demo"):
        return []

    user_areas = normalize_set(user_p.get("research_areas") or [])
    user_kws = normalize_set(user_p.get("research_keywords") or [])
    user_skills = normalize_set(user_p.get("skills") or [])

    combined_terms = user_areas | user_kws

    query: dict[str, Any] = {
        "visibility": {"$ne": "private"},
        "members": {"$ne": user_id},
        "owner_id": {"$ne": user_id},
    }

    projection = {
        "_id": 1,
        "title": 1,
        "description": 1,
        "status": 1,
        "owner_id": 1,
        "members": 1,
    }

    projects_raw = await db.projects.find(query, projection).limit(500).to_list(500)

    owner_ids_raw = list({p.get("owner_id") for p in projects_raw if p.get("owner_id")})
    owner_ids_oid = [ObjectId(oid) for oid in owner_ids_raw if ObjectId.is_valid(oid)]
    owner_docs = await db.users.find(
        {"_id": {"$in": owner_ids_oid}},
        {"_id": 1, "full_name": 1},
    ).to_list(len(owner_ids_oid) or 1)
    owner_name_map: dict[str, str] = {str(u["_id"]): (u.get("full_name") or "") for u in owner_docs}

    results: list[dict] = []

    for proj in projects_raw:
        proj_id = str(proj["_id"])

        title = proj.get("title") or ""
        description = proj.get("description") or ""
        full_text = title + " " + description

        if not combined_terms:
            text_score = 5.0
            matched_terms = []
        else:
            text_score, matched_terms = _text_keyword_score(user_kws, user_areas, full_text, 55.0)

        title_score, title_matched = _text_keyword_score(user_kws, user_areas, title, 15.0)

        open_score = 15.0

        sub_scores = {
            "text_score": text_score,
            "title_score": title_score,
            "open_score": open_score,
        }

        total = clamp(sum(sub_scores.values()))

        if interaction_cache and interaction_cache.get(proj_id) == "dismissed":
            total *= 0.2

        if total <= open_score + 0.1 and not matched_terms:
            continue  # Skip projects with zero text relevance

        description_short = description[:200] + ("..." if len(description) > 200 else "")
        owner_id = proj.get("owner_id") or ""
        owner_name = owner_name_map.get(owner_id, "")
        member_count = len(proj.get("members") or [])
        status = (proj.get("status") or "open").lower()

        proj_ctx = {
            "title": title,
            "description": description,
            "matched_terms": matched_terms,
            "status": status,
        }
        explanation = explain_project(user_p, proj_ctx, sub_scores)

        results.append({
            "project_id": proj_id,
            "title": title.strip(),
            "description": description_short,
            "research_areas": [],
            "status": status,
            "owner_name": owner_name.strip(),
            "member_count": member_count,
            "score": round(total, 1),
            "explanation": explanation,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
