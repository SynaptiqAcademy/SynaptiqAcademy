from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.recommendation.profiles import get_or_refresh_profile
from services.recommendation.scoring import normalize_set, jaccard, clamp
from services.recommendation.explainer import explain_conference

_RANK_SCORES: dict[str, float] = {
    "a*": 30.0,
    "a": 20.0,
    "b": 10.0,
    "c": 5.0,
}

_TOPIC_FIT_THRESHOLDS = [
    (0.5, "Strong"),
    (0.25, "Good"),
    (0.0, "Moderate"),
]


def _days_until(deadline_str: str | None) -> int | None:
    """Return days until deadline, or None if unparseable."""
    if not deadline_str:
        return None
    try:
        # Try common ISO formats
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(str(deadline_str)[:19], fmt)
                dt = dt.replace(tzinfo=timezone.utc)
                delta = dt - datetime.now(timezone.utc)
                return max(int(delta.days), 0)
            except ValueError:
                continue
        return None
    except Exception:
        return None


def _deadline_label(days: int | None) -> str:
    if days is None:
        return "unknown"
    if days == 0:
        return "today"
    if days <= 7:
        return f"{days} days left"
    if days <= 30:
        return f"{days} days left"
    if days <= 90:
        return f"~{days // 7} weeks left"
    return f"~{days // 30} months left"


async def match_conferences(
    user_id: str,
    db,
    limit: int = 20,
    area_filter: str | None = None,
    deadline_state: str = "open",
    interaction_cache: dict | None = None,
) -> list[dict]:
    """
    Return algorithmically scored conference recommendations for a given user.

    Sub-scores:
      area_score       = jaccard(user.research_areas, conf.research_areas) * 50
      rank_score       = A*=30, A=20, B=10, C=5, unranked=3
      deadline_urgency = +10 if closing within 30 days
      format_score     = +5 if virtual/hybrid
    """
    # ── Load user profile ────────────────────────────────────────────────────
    user_p = await get_or_refresh_profile(user_id, db)

    if user_p.get("is_suspended") or user_p.get("is_demo"):
        return []

    user_areas = normalize_set(user_p.get("research_areas") or [])
    user_interests = normalize_set(user_p.get("research_interests") or [])
    combined_user_areas = user_areas | user_interests

    # ── Build conference query ───────────────────────────────────────────────
    query: dict[str, Any] = {}

    now_iso = datetime.now(timezone.utc).isoformat()

    if deadline_state == "open":
        # Only conferences with future submission deadlines (or no deadline stored)
        query["$or"] = [
            {"deadline": {"$gt": now_iso[:10]}},
            {"deadline": None},
            {"deadline": {"$exists": False}},
        ]

    if area_filter:
        query["research_areas"] = {"$regex": area_filter, "$options": "i"}

    projection = {
        "_id": 1,
        "name": 1,
        "research_areas": 1,
        "rank": 1,
        "country": 1,
        "deadline": 1,
        "format": 1,
    }

    confs_raw = await db.conferences.find(query, projection).limit(500).to_list(500)

    # ── Score each conference ────────────────────────────────────────────────
    results: list[dict] = []

    for conf in confs_raw:
        conf_id = str(conf["_id"])

        conf_areas = normalize_set(conf.get("research_areas") or [])
        rank_raw = (conf.get("rank") or "").lower().strip()
        fmt = (conf.get("format") or "").lower().strip()
        deadline_str = conf.get("deadline")

        area_score = jaccard(combined_user_areas, conf_areas) * 50

        rank_score = _RANK_SCORES.get(rank_raw, 3.0)

        days_left = _days_until(deadline_str)
        deadline_urgency = 10.0 if (days_left is not None and 0 < days_left <= 30) else 0.0

        format_score = 5.0 if fmt in ("virtual", "hybrid") else 0.0

        sub_scores = {
            "area_score": area_score,
            "rank_score": rank_score,
            "deadline_urgency": deadline_urgency,
            "format_score": format_score,
        }

        total = clamp(sum(sub_scores.values()))

        # Interaction penalty
        if interaction_cache:
            action = interaction_cache.get(conf_id)
            if action == "dismissed":
                total *= 0.2

        if total <= 0 and area_score <= 0:
            continue

        # Topic fit label based on Jaccard
        topic_fit = "Moderate"
        jac = jaccard(combined_user_areas, conf_areas)
        for threshold, label in _TOPIC_FIT_THRESHOLDS:
            if jac >= threshold:
                topic_fit = label
                break

        # Deadline state label
        if days_left is None:
            dl_state = "unknown"
        elif days_left == 0:
            dl_state = "closing_today"
        elif days_left <= 7:
            dl_state = "closing_soon"
        elif days_left <= 30:
            dl_state = "open_soon"
        else:
            dl_state = "open"

        explanation = explain_conference(user_p, conf, sub_scores)

        results.append({
            "conference_id": conf_id,
            "name": (conf.get("name") or "").strip(),
            "research_areas": [a.title() for a in sorted(conf_areas)],
            "rank": (conf.get("rank") or "").upper() or None,
            "country": (conf.get("country") or "").strip(),
            "deadline": str(deadline_str) if deadline_str else None,
            "deadline_state": dl_state,
            "deadline_label": _deadline_label(days_left),
            "format": (conf.get("format") or "").strip(),
            "score": round(total, 1),
            "explanation": explanation,
            "topic_fit": topic_fit,
        })

    # ── Sort and return top results ──────────────────────────────────────────
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
