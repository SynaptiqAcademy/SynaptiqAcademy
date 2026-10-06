from __future__ import annotations

from typing import Any

from bson import ObjectId

from services.recommendation.profiles import get_or_refresh_profile
from services.permissions import REAL_CUSTOMER_FILTER
from services.collab_intelligence.researcher_profiler import build_researcher_profile
from services.collab_intelligence.matching_engine import rank_matches
from services.safe_search import contains as safe_contains


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
    Return researcher recommendations for a given user.

    P1 Phase 6 consolidation: this function no longer computes its own
    independent compatibility formula. Scoring is delegated entirely to the
    canonical deterministic matching engine
    (services/collab_intelligence/matching_engine.py) via rank_matches().
    This function still owns everything that is genuinely candidate
    ELIGIBILITY rather than compatibility SCORING: excluding suspended/demo/
    private/internal-staff accounts, excluding already-connected
    collaborators, and the optional country/area/role query filters — none
    of that is duplicate matching math, it's the same eligibility layer
    every consumer of the canonical engine builds on top of it.

    The canonical engine itself never reads reputation/trust collections
    (by design — see services/collab_intelligence/researcher_profiler.py).
    This function reads `recommendation_profiles.reputation_score` (as it
    always has) and passes it into build_researcher_profile()'s optional
    `reputation_score` parameter, which only exists so callers like this one
    can supply it without the engine reaching into a collection it has no
    reason to know about. The engine's own `reputation_compatibility`
    dimension (added in the Phase 1 matching-signal migration, weighted
    0.04) is what actually uses it now, replacing this file's old one-sided
    `rep_score = min(cand_rep/200,1)*5` term with the engine's existing
    symmetric formula.

    Response shape (list of flat dicts with `user_id`, `score` 0-100,
    `match_label`, `explanation`, etc.) and the public function signature
    are unchanged, for backward compatibility with existing callers
    (services/recommendation/engine.py, routers/recommendations.py,
    frontend/src/pages/Researchers.jsx and Recommendations.jsx).
    """
    # ── Load requesting user's profile (eligibility gate + reputation) ──────
    user_p = await get_or_refresh_profile(user_id, db)

    if user_p.get("is_suspended") or user_p.get("is_demo"):
        return []

    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        return []
    user_doc["_id"] = user_id

    source_rep_doc = await db.recommendation_profiles.find_one(
        {"user_id": user_id}, {"reputation_score": 1})
    source_reputation = int((source_rep_doc or {}).get("reputation_score", 0))

    # ── Get already-connected collaborator IDs (eligibility, not scoring) ───
    collab_docs = await db.collaborations.find(
        {"members": user_id},
        {"members": 1},
    ).to_list(500)

    connected_ids: set[str] = set()
    for collab in collab_docs:
        for member in (collab.get("members") or []):
            connected_ids.add(str(member))
    connected_ids.discard(user_id)

    # ── Build candidate query (eligibility, not scoring) ─────────────────────
    query: dict[str, Any] = {
        "is_suspended": {"$ne": True},
        "is_demo": {"$ne": True},
        "profile_visibility": {"$ne": "private"},
        **REAL_CUSTOMER_FILTER,
    }

    if country_filter:
        query["country"] = safe_contains(country_filter)

    if area_filter:
        query["research_areas"] = safe_contains(area_filter)

    if role_filter:
        query["academic_role"] = safe_contains(role_filter)

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
        "is_demo": 1,
    }

    candidates_raw = await db.users.find(query, projection).limit(500).to_list(500)
    candidates_raw = [
        c for c in candidates_raw
        if str(c["_id"]) != user_id and str(c["_id"]) not in connected_ids
    ]

    if not candidates_raw:
        return []

    # ── Batch-load reputation_score/publication_count — the canonical engine
    #    never reads this collection itself; this file does, as before.
    candidate_ids = [str(c["_id"]) for c in candidates_raw]
    profile_docs = await db.recommendation_profiles.find(
        {"user_id": {"$in": candidate_ids}},
        {"user_id": 1, "reputation_score": 1, "publication_count": 1},
    ).to_list(500)
    profile_map = {p["user_id"]: p for p in profile_docs}

    # ── Build canonical ResearcherProfile objects ─────────────────────────────
    source_profile = build_researcher_profile(user_doc, reputation_score=source_reputation)

    candidate_profiles = []
    display_data: dict[str, dict] = {}
    for cand in candidates_raw:
        cand_id = str(cand["_id"])
        cand_rep_doc = profile_map.get(cand_id, {})
        cand_rep = int(cand_rep_doc.get("reputation_score", 0))
        cand_pub_count = int(cand_rep_doc.get("publication_count", 0))

        display_data[cand_id] = {
            "full_name": (cand.get("full_name") or "").strip(),
            "institution": (cand.get("institution") or "").strip(),
            "country": (cand.get("country") or "").strip(),
            "academic_role": (cand.get("academic_role") or "").strip(),
            "avatar_url": cand.get("avatar_url") or None,
            "orcid": cand.get("orcid") or None,
            "research_areas": [a.strip().title() for a in (cand.get("research_areas") or []) if a],
            "reputation_score": cand_rep,
            "publication_count": cand_pub_count,
        }

        cand_doc = dict(cand)
        cand_doc["_id"] = cand_id
        candidate_profiles.append(build_researcher_profile(cand_doc, reputation_score=cand_rep))

    # ── Dismissal penalty — now applied by the canonical engine's own
    #    rank_matches(), same 0.2x semantics as this file's old inline logic.
    dismissed_ids = None
    if interaction_cache:
        dismissed_ids = {
            cid for cid, action in interaction_cache.items() if action == "dismissed"
        }

    ranked = rank_matches(source_profile, candidate_profiles, top_n=limit, dismissed_ids=dismissed_ids)

    results: list[dict] = []
    for m in ranked:
        extra = display_data.get(m.researcher_b_id, {})
        score_rounded = round(m.overall_score * 100, 1)
        results.append({
            "user_id": m.researcher_b_id,
            "full_name": extra.get("full_name", ""),
            "institution": extra.get("institution", ""),
            "country": extra.get("country", ""),
            "academic_role": extra.get("academic_role", ""),
            "avatar_url": extra.get("avatar_url"),
            "orcid": extra.get("orcid"),
            "research_areas": extra.get("research_areas", []),
            "reputation_score": extra.get("reputation_score", 0),
            "publication_count": extra.get("publication_count", 0),
            "score": score_rounded,
            "explanation": m.explanation,
            "match_label": f"{int(score_rounded)}% Match",
        })

    return results
