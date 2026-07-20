from __future__ import annotations

from typing import Any

from bson import ObjectId

from services.recommendation.profiles import get_or_refresh_profile
from services.recommendation.scoring import normalize_set, jaccard, clamp, career_complement
from services.recommendation.explainer import explain_researcher


async def match_researchers(
    user_id: str,
    db,
    limit: int = 20,
    country_filter: str | None = None,
    area_filter: str | None = None,
    role_filter: str | None = None,
    interaction_cache: dict | None = None,
) -> list[dict]:
    """
    Return algorithmically scored researcher recommendations for a given user.

    Scores are purely algorithmic (no LLM). Excluded:
    - suspended users
    - demo accounts
    - private profiles
    - self
    - already-connected collaborators
    - dismissed items (penalized by 0.2x)

    Sub-scores:
      area_score      = jaccard(areas) * 35
      kw_score        = jaccard(keywords) * 25
      method_score    = jaccard(methods) * 15
      diversity_score = 10 if different country else 5
      complement_score = career_complement(roles) * 10
      rep_score       = min(reputation / 200, 1.0) * 5
    Total capped at 100.
    """
    # ── Load requesting user's profile ──────────────────────────────────────
    user_p = await get_or_refresh_profile(user_id, db)

    if user_p.get("is_suspended") or user_p.get("is_demo"):
        return []

    user_areas = normalize_set(user_p.get("research_areas") or [])
    user_kws = normalize_set(user_p.get("research_keywords") or [])
    user_methods = normalize_set(user_p.get("methods") or [])
    user_country = (user_p.get("country") or "").strip().lower()
    user_role = (user_p.get("academic_role") or "").strip().lower()

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

    # ── Build query ──────────────────────────────────────────────────────────
    query: dict[str, Any] = {
        "is_suspended": {"$ne": True},
        "account_type": {"$ne": "demo"},
        "profile_visibility": {"$ne": "private"},
    }

    if country_filter:
        query["country"] = {"$regex": country_filter, "$options": "i"}

    if area_filter:
        query["research_areas"] = {"$regex": area_filter, "$options": "i"}

    if role_filter:
        query["academic_role"] = {"$regex": role_filter, "$options": "i"}

    projection = {
        "_id": 1,
        "full_name": 1,
        "institution": 1,
        "country": 1,
        "academic_role": 1,
        "avatar_url": 1,
        "orcid": 1,
        "research_areas": 1,
        "research_keywords": 1,
        "methods": 1,
        "profile_visibility": 1,
        "is_suspended": 1,
        "account_type": 1,
    }

    candidates_raw = await db.users.find(query, projection).limit(500).to_list(500)

    # ── Batch-load profiles for reputation_score and publication_count ────────
    # We'll need recommendation_profiles for richer data; fall back gracefully
    candidate_ids = [str(c["_id"]) for c in candidates_raw]
    profile_docs = await db.recommendation_profiles.find(
        {"user_id": {"$in": candidate_ids}},
        {"user_id": 1, "reputation_score": 1, "publication_count": 1},
    ).to_list(500)
    profile_map = {p["user_id"]: p for p in profile_docs}

    # ── Score each candidate ─────────────────────────────────────────────────
    results: list[dict] = []

    for cand in candidates_raw:
        cand_id = str(cand["_id"])

        # Exclusions
        if cand_id == user_id:
            continue
        if cand_id in connected_ids:
            continue

        cand_areas = normalize_set(cand.get("research_areas") or [])
        cand_kws = normalize_set(cand.get("research_keywords") or [])
        cand_methods = normalize_set(cand.get("methods") or [])
        cand_country = (cand.get("country") or "").strip().lower()
        cand_role = (cand.get("academic_role") or "").strip().lower()

        cand_profile = profile_map.get(cand_id, {})
        cand_rep = int(cand_profile.get("reputation_score", 0))
        cand_pub_count = int(cand_profile.get("publication_count", 0))

        # Sub-scores
        area_score = jaccard(user_areas, cand_areas) * 35
        kw_score = jaccard(user_kws, cand_kws) * 25
        method_score = jaccard(user_methods, cand_methods) * 15
        diversity_score = 10.0 if (user_country and cand_country and user_country != cand_country) else 5.0
        complement_score = career_complement(user_role, cand_role) * 10
        rep_score = min(cand_rep / 200.0, 1.0) * 5

        sub_scores = {
            "area_score": area_score,
            "kw_score": kw_score,
            "method_score": method_score,
            "diversity_score": diversity_score,
            "complement_score": complement_score,
            "rep_score": rep_score,
        }

        total = clamp(sum(sub_scores.values()))

        # Interaction penalty
        if interaction_cache:
            action = interaction_cache.get(cand_id)
            if action == "dismissed":
                total *= 0.2

        # Skip zero-score candidates (no overlap at all)
        if total <= 0:
            continue

        cand_p_for_explain = {
            "research_areas": list(cand_areas),
            "research_keywords": list(cand_kws),
            "methods": list(cand_methods),
            "country": cand_country,
            "academic_role": cand_role,
            "reputation_score": cand_rep,
        }

        explanation = explain_researcher(user_p, cand_p_for_explain, sub_scores)

        score_rounded = round(total, 1)
        results.append({
            "user_id": cand_id,
            "full_name": (cand.get("full_name") or "").strip(),
            "institution": (cand.get("institution") or "").strip(),
            "country": (cand.get("country") or "").strip(),
            "academic_role": (cand.get("academic_role") or "").strip(),
            "avatar_url": cand.get("avatar_url") or None,
            "orcid": cand.get("orcid") or None,
            "research_areas": [a.title() for a in sorted(cand_areas)],
            "reputation_score": cand_rep,
            "publication_count": cand_pub_count,
            "score": score_rounded,
            "explanation": explanation,
            "match_label": f"{int(score_rounded)}% Match",
        })

    # ── Sort and return top results ──────────────────────────────────────────
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
