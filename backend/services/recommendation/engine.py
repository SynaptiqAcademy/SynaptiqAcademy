from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from services.recommendation.matchers.researchers import match_researchers
from services.recommendation.matchers.projects import match_projects
from services.recommendation.matchers.journals import match_journals
from services.recommendation.matchers.conferences import match_conferences
from services.recommendation.matchers.grants import match_grants
from services.recommendation.matchers.reviewers import match_reviewers
from services.recommendation.matchers.mentors import match_mentors

_VALID_CATEGORIES = frozenset({
    "researchers",
    "projects",
    "journals",
    "conferences",
    "grants",
    "reviewers",
    "mentors",
})

_CACHE_TTL_HOURS = 6


def _filters_hash(filters: dict | None) -> str:
    """Produce a stable short hash for a filters dict for use as a cache key component."""
    if not filters:
        return "none"
    normalized = json.dumps(filters, sort_keys=True, default=str)
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


def _is_cache_fresh(computed_at: Any, ttl_hours: int = _CACHE_TTL_HOURS) -> bool:
    """Return True if the computed_at timestamp is within the TTL window."""
    if not computed_at:
        return False
    try:
        if isinstance(computed_at, datetime):
            dt = computed_at.replace(tzinfo=timezone.utc) if computed_at.tzinfo is None else computed_at
        else:
            dt = datetime.fromisoformat(str(computed_at))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age_hours < ttl_hours
    except (ValueError, TypeError):
        return False


async def _load_interaction_cache(user_id: str, rec_type: str, db) -> dict:
    """Load the user's interaction history for a category into {target_id: action} dict."""
    try:
        docs = await db.recommendation_interactions.find(
            {"user_id": user_id, "recommendation_type": rec_type},
            {"target_id": 1, "action": 1},
        ).to_list(1000)
        # If multiple interactions for the same target, keep the most recent
        result: dict[str, str] = {}
        for doc in docs:
            tid = doc.get("target_id")
            action = doc.get("action")
            if tid and action:
                result[str(tid)] = str(action)
        return result
    except Exception:
        return {}


async def get_recommendations(
    user_id: str,
    category: str,
    db,
    limit: int = 20,
    force_refresh: bool = False,
    filters: dict | None = None,
    manuscript_id: str | None = None,
    project_id: str | None = None,
) -> dict:
    """
    Main entry point for the recommendation engine.

    1. Check recommendation_scores for a cached entry (< 6 hours old).
    2. Load interaction_cache for this user+category.
    3. Dispatch to the appropriate matcher.
    4. Upsert result into recommendation_scores.
    5. Return { category, results, computed_at, total, from_cache }.
    """
    if category not in _VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}'. Must be one of: {sorted(_VALID_CATEGORIES)}"
        )

    fhash = _filters_hash(filters)
    cache_key = {"user_id": user_id, "category": category}

    # ── Cache lookup ─────────────────────────────────────────────────────────
    if not force_refresh:
        cached = await db.recommendation_scores.find_one(cache_key)
        # Also verify filters match — if user changed filters, recompute
        if cached and cached.get("filters_hash") != fhash:
            cached = None
        if cached and _is_cache_fresh(cached.get("computed_at")):
            return {
                "category": category,
                "results": cached.get("results", []),
                "computed_at": str(cached.get("computed_at", "")),
                "total": cached.get("total", len(cached.get("results", []))),
                "from_cache": True,
            }

    # ── Load interaction cache ───────────────────────────────────────────────
    interaction_cache = await _load_interaction_cache(user_id, category, db)

    # ── Dispatch to matcher ──────────────────────────────────────────────────
    f = filters or {}

    if category == "researchers":
        results = await match_researchers(
            user_id=user_id,
            db=db,
            limit=limit,
            country_filter=f.get("country"),
            area_filter=f.get("area"),
            role_filter=f.get("role"),
            interaction_cache=interaction_cache,
        )

    elif category == "projects":
        results = await match_projects(
            user_id=user_id,
            db=db,
            limit=limit,
            area_filter=f.get("area"),
            interaction_cache=interaction_cache,
        )

    elif category == "journals":
        results = await match_journals(
            user_id=user_id,
            db=db,
            limit=limit,
            open_access_only=bool(f.get("open_access")),
            quartile_filter=f.get("quartile"),
            interaction_cache=interaction_cache,
        )

    elif category == "conferences":
        results = await match_conferences(
            user_id=user_id,
            db=db,
            limit=limit,
            area_filter=f.get("area"),
            deadline_state=f.get("deadline_state", "open"),
            interaction_cache=interaction_cache,
        )

    elif category == "grants":
        results = await match_grants(
            user_id=user_id,
            db=db,
            limit=limit,
            area_filter=f.get("area"),
            interaction_cache=interaction_cache,
        )

    elif category == "reviewers":
        results = await match_reviewers(
            user_id=user_id,
            db=db,
            manuscript_id=manuscript_id,
            project_id=project_id,
            limit=limit,
            interaction_cache=interaction_cache,
        )

    elif category == "mentors":
        results = await match_mentors(
            user_id=user_id,
            db=db,
            limit=limit,
            area_filter=f.get("area"),
            interaction_cache=interaction_cache,
        )

    else:
        results = []

    # ── Store result in cache ────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    score_doc = {
        **cache_key,
        "filters_hash": fhash,
        "results": results,
        "total": len(results),
        "computed_at": now,
        "filters": filters or {},
    }

    await db.recommendation_scores.update_one(
        cache_key,
        {"$set": score_doc},
        upsert=True,
    )

    return {
        "category": category,
        "results": results,
        "computed_at": now.isoformat(),
        "total": len(results),
        "from_cache": False,
    }


async def record_interaction(
    user_id: str,
    rec_type: str,
    target_id: str,
    action: str,
    db,
) -> None:
    """
    Upsert an interaction record into recommendation_interactions.
    If action is 'dismissed', also invalidate the cached results for this user+type
    so next fetch re-computes without the dismissed item.
    """
    if rec_type not in _VALID_CATEGORIES:
        raise ValueError(f"Invalid rec_type: {rec_type}")

    valid_actions = {"clicked", "dismissed", "bookmarked", "accepted", "ignored"}
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")

    now = datetime.now(timezone.utc)

    await db.recommendation_interactions.update_one(
        {"user_id": user_id, "recommendation_type": rec_type, "target_id": target_id},
        {
            "$set": {
                "user_id": user_id,
                "recommendation_type": rec_type,
                "target_id": target_id,
                "action": action,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    # Invalidate cache for this user+category when they dismiss an item
    if action == "dismissed":
        await db.recommendation_scores.delete_many(
            {"user_id": user_id, "category": rec_type}
        )


async def get_all_recommendations(
    user_id: str,
    db,
    limit_each: int = 6,
) -> dict:
    """
    Return top-N recommendations across all categories for dashboard display.
    Runs all matchers in parallel using asyncio.gather.

    Returns:
    {
      "researchers": [...],
      "projects": [...],
      "journals": [...],
      "conferences": [...],
      "grants": [...],
      "mentors": [...],
    }
    Note: "reviewers" is excluded from dashboard (requires manuscript/project context).
    """
    dashboard_categories = [
        "researchers",
        "projects",
        "journals",
        "conferences",
        "grants",
        "mentors",
    ]

    async def _safe_fetch(category: str) -> tuple[str, list]:
        try:
            result = await get_recommendations(
                user_id=user_id,
                category=category,
                db=db,
                limit=limit_each,
                force_refresh=False,
                filters=None,
            )
            return category, result.get("results", [])
        except Exception:
            return category, []

    tasks = [_safe_fetch(cat) for cat in dashboard_categories]
    gathered = await asyncio.gather(*tasks)

    return {category: results for category, results in gathered}
