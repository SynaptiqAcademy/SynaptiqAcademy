from __future__ import annotations

import ast
import re
from datetime import datetime, timezone
from typing import Any

from services.recommendation.profiles import get_or_refresh_profile
from services.recommendation.scoring import normalize_set, jaccard, clamp
from services.recommendation.explainer import explain_grant

# Career stage → grant eligibility text keywords
_ROLE_KEYWORDS: dict[str, list[str]] = {
    "phd_student":            ["phd", "doctoral", "graduate", "student", "early career"],
    "postdoc":                ["postdoc", "postdoctoral", "early career", "post-doctoral"],
    "researcher":             ["researcher", "early career", "mid career", "junior"],
    "junior_researcher":      ["junior", "early career", "researcher"],
    "senior_researcher":      ["senior", "mid career", "experienced", "researcher"],
    "associate_professor":    ["faculty", "mid career", "associate professor", "academic"],
    "professor":              ["faculty", "senior", "professor", "established", "academic"],
    "principal_investigator": ["pi", "principal investigator", "established", "faculty", "senior"],
    "emeritus":               ["emeritus", "senior", "established", "professor"],
}


def _parse_research_areas(raw: Any) -> list[str]:
    """Grant.research_areas is stored as a Python list string: "['Healthcare', 'AI']"."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, str):
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if x]
        except (ValueError, SyntaxError):
            pass
        return [raw] if raw.strip() else []
    return []


def _career_match_score(role: str, eligibility_text: str) -> float:
    """Score 0-25 based on how well user role aligns with grant eligibility text."""
    if not eligibility_text:
        return 20.0  # Open to all → partial credit

    et_lower = eligibility_text.lower()
    if "open to qualified researchers" in et_lower or "open to all" in et_lower:
        return 20.0

    aliases = _ROLE_KEYWORDS.get(role.strip().lower(), [role])
    for alias in aliases:
        if alias in et_lower:
            return 25.0

    return 8.0  # Eligibility text exists but no role keyword match → partial


def _is_deadline_open(deadline_str: str | None) -> bool:
    if not deadline_str:
        return True
    try:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(str(deadline_str)[:19], fmt)
                return dt.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
            except ValueError:
                continue
        return True
    except Exception:
        return True


async def match_grants(
    user_id: str,
    db,
    limit: int = 20,
    area_filter: str | None = None,
    interaction_cache: dict | None = None,
) -> list[dict]:
    """
    Return algorithmically scored grant recommendations.

    Sub-scores:
      area_score    = jaccard(user.research_areas, grant.research_areas) * 40
      career_score  = 0-25 based on role match to eligibility text
      universal_score = 20 (all grants get this since country eligibility is not structured)
      kw_score      = min(description keyword matches * 3, 15)
    """
    user_p = await get_or_refresh_profile(user_id, db)
    if user_p.get("is_suspended") or user_p.get("is_demo"):
        return []

    user_areas = normalize_set(user_p.get("research_areas") or [])
    user_kws = normalize_set(user_p.get("research_keywords") or [])
    user_role = (user_p.get("academic_role") or "").strip().lower()

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    query: dict[str, Any] = {
        "$or": [
            {"deadline": {"$gt": now_str}},
            {"deadline": None},
            {"deadline": {"$exists": False}},
        ]
    }
    if area_filter:
        query["research_areas"] = {"$regex": area_filter, "$options": "i"}

    projection = {
        "_id": 1,
        "title": 1,
        "description": 1,
        "agency": 1,
        "research_areas": 1,
        "eligibility": 1,
        "deadline": 1,
        "amount": 1,
        "duration": 1,
        "funding_type": 1,
    }

    grants_raw = await db.grants.find(query, projection).limit(500).to_list(500)

    results: list[dict] = []

    for grant in grants_raw:
        grant_id = str(grant["_id"])

        if not _is_deadline_open(grant.get("deadline")):
            continue

        grant_areas = normalize_set(_parse_research_areas(grant.get("research_areas")))
        eligibility_text = grant.get("eligibility") or ""
        description_text = (grant.get("description") or "").lower()

        area_score = jaccard(user_areas, grant_areas) * 40
        career_score = _career_match_score(user_role, eligibility_text)

        shared_kws = {kw for kw in user_kws if kw in description_text}
        kw_score = min(len(shared_kws) * 3.0, 15.0)

        # Country eligibility not structured — give universal score
        universal_score = 20.0

        sub_scores = {
            "area_score": area_score,
            "career_score": career_score,
            "universal_score": universal_score,
            "kw_score": kw_score,
        }

        total = clamp(sum(sub_scores.values()))

        if interaction_cache and interaction_cache.get(grant_id) == "dismissed":
            total *= 0.2

        if total <= 0:
            continue

        eligibility_score = clamp(career_score + universal_score)
        explanation = explain_grant(user_p, {
            **grant,
            "research_areas": list(grant_areas),
            "agency": grant.get("agency") or "",
            "eligibility": eligibility_text,
        }, sub_scores)

        results.append({
            "grant_id": grant_id,
            "title": (grant.get("title") or "").strip(),
            "sponsor": (grant.get("agency") or "").strip(),  # alias for frontend
            "agency": (grant.get("agency") or "").strip(),
            "research_areas": [a.title() for a in sorted(grant_areas)],
            "eligibility": eligibility_text[:200] if eligibility_text else None,
            "deadline": str(grant.get("deadline")) if grant.get("deadline") else None,
            "amount": grant.get("amount") or None,
            "duration": grant.get("duration") or None,
            "funding_type": grant.get("funding_type") or None,
            "score": round(total, 1),
            "eligibility_score": round(eligibility_score, 1),
            "explanation": explanation,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
