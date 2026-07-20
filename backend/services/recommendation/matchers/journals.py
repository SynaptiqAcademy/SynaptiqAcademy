from __future__ import annotations

from typing import Any

from services.recommendation.profiles import get_or_refresh_profile
from services.recommendation.scoring import normalize_set, jaccard, clamp
from services.recommendation.explainer import explain_journal

# Quartile score map
_QUARTILE_SCORES: dict[str, float] = {
    "q1": 25.0,
    "q2": 20.0,
    "q3": 10.0,
    "q4": 5.0,
}

_ACCEPTANCE_PROBABILITY: dict[str, str] = {
    "q1": "Low",
    "q2": "Moderate",
    "q3": "High",
    "q4": "High",
}

_REVIEW_TIME_ESTIMATES: dict[str, str] = {
    "q1": "8-16 weeks",
    "q2": "6-12 weeks",
    "q3": "4-8 weeks",
    "q4": "2-6 weeks",
}


async def match_journals(
    user_id: str,
    db,
    limit: int = 20,
    open_access_only: bool = False,
    quartile_filter: str | None = None,
    interaction_cache: dict | None = None,
) -> list[dict]:
    """
    Return algorithmically scored journal recommendations for a given user.

    Sub-scores:
      subject_score  = jaccard(user.research_areas, journal.subjects) * 40
      kw_score       = keyword matches in journal title/subjects → 0-25
      quartile_score = Q1=25, Q2=20, Q3=10, Q4=5
      oa_score       = 10 if open_access_only and journal.open_access else 0
    """
    # ── Load user profile ────────────────────────────────────────────────────
    user_p = await get_or_refresh_profile(user_id, db)

    if user_p.get("is_suspended") or user_p.get("is_demo"):
        return []

    user_areas = normalize_set(user_p.get("research_areas") or [])
    user_interests = normalize_set(user_p.get("research_interests") or [])
    user_kws = normalize_set(user_p.get("research_keywords") or [])
    # Combine areas and manuscript areas for broader matching
    user_manuscript_areas = normalize_set(user_p.get("manuscript_research_areas") or [])
    combined_areas = user_areas | user_interests | user_manuscript_areas

    if not combined_areas and not user_kws:
        return []

    # ── Build journal query ──────────────────────────────────────────────────
    query: dict[str, Any] = {}

    if open_access_only:
        query["open_access"] = True

    if quartile_filter:
        query["quartile"] = {"$regex": f"^{quartile_filter}$", "$options": "i"}

    # Filter journals to those with matching subjects (broad pre-filter)
    if combined_areas:
        area_list = list(combined_areas)
        # Case-insensitive subject overlap via $in with regex alternatives
        query["subjects"] = {
            "$elemMatch": {
                "$in": [a for a in area_list[:30]]  # top 30 to avoid oversized queries
            }
        }

    projection = {
        "_id": 1,
        "title": 1,
        "subjects": 1,
        "quartile": 1,
        "impact_factor": 1,
        "open_access": 1,
        "apc_usd": 1,
        "publisher": 1,
        "works_count": 1,
        "popularity_score": 1,
    }

    journals_raw = await db.journals.find(query, projection).limit(1000).to_list(1000)

    # If pre-filter returns nothing (e.g. subjects stored differently), fetch all and score
    if not journals_raw:
        journals_raw = await db.journals.find(
            {"open_access": True} if open_access_only else {},
            projection,
        ).limit(1000).to_list(1000)

    # ── Score each journal ───────────────────────────────────────────────────
    results: list[dict] = []

    for journal in journals_raw:
        journal_id = str(journal["_id"])

        journal_subjects = normalize_set(journal.get("subjects") or [])
        journal_title_lower = (journal.get("title") or "").lower()
        quartile_raw = (journal.get("quartile") or "").lower()

        # Subject score
        subject_score = jaccard(combined_areas, journal_subjects) * 40

        # Keyword score — check how many user keywords appear in journal title or subjects
        kw_hits = 0
        for kw in user_kws:
            if kw in journal_title_lower or kw in journal_subjects:
                kw_hits += 1
        kw_score = min(kw_hits * 5.0, 25.0)

        # Quartile score
        quartile_score = _QUARTILE_SCORES.get(quartile_raw, 3.0)

        # OA score
        oa_score = 10.0 if (open_access_only and journal.get("open_access")) else 0.0

        sub_scores = {
            "subject_score": subject_score,
            "kw_score": kw_score,
            "quartile_score": quartile_score,
            "oa_score": oa_score,
        }

        total = clamp(sum(sub_scores.values()))

        # Interaction penalty
        if interaction_cache:
            action = interaction_cache.get(journal_id)
            if action == "dismissed":
                total *= 0.2

        if total <= 0:
            continue

        quartile_display = quartile_raw.upper() if quartile_raw else None
        acceptance = _ACCEPTANCE_PROBABILITY.get(quartile_raw, "Moderate")
        review_time = _REVIEW_TIME_ESTIMATES.get(quartile_raw, "4-12 weeks")

        explanation = explain_journal(user_p, journal, sub_scores)

        results.append({
            "journal_id": journal_id,
            "title": (journal.get("title") or "").strip(),
            "subjects": [s.title() for s in sorted(journal_subjects)],
            "quartile": quartile_display,
            "impact_factor": journal.get("impact_factor") or None,
            "open_access": bool(journal.get("open_access")),
            "apc_usd": journal.get("apc_usd") or None,
            "publisher": (journal.get("publisher") or "").strip(),
            "works_count": int(journal.get("works_count") or 0),
            "score": round(total, 1),
            "explanation": explanation,
            "acceptance_probability": acceptance,
            "review_time_estimate": review_time,
        })

    # ── Sort and return top results ──────────────────────────────────────────
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
