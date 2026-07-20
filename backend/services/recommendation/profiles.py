from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from db import get_db
from repo.shim import make_db_proxy


def _str_id(doc_id: Any) -> str:
    """Convert ObjectId or str to plain string."""
    if doc_id is None:
        return ""
    return str(doc_id)


def _normalize_list(items: Any) -> list[str]:
    """Return a deduplicated lowercase list from a potentially None list."""
    if not items:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and isinstance(item, str):
            normalized = item.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
    return result


async def build_profile(user_id: str, db) -> dict:
    """
    Pull all relevant data for a user and return a normalized profile dict.
    """
    db = make_db_proxy(db, system=True)
    if not ObjectId.is_valid(user_id):
        raise ValueError(f"Invalid user_id: {user_id}")

    oid = ObjectId(user_id)

    # ── Fetch user document ──────────────────────────────────────────────────
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise ValueError(f"User not found: {user_id}")

    # ── Fetch manuscripts authored by user ───────────────────────────────────
    manuscripts_cursor = db.manuscripts.find(
        {"$or": [{"authors": user_id}, {"lead_author_id": user_id}]},
        {"research_areas": 1, "keywords": 1, "status": 1, "authors": 1},
    )
    manuscripts = await manuscripts_cursor.to_list(500)

    publication_count = len(manuscripts)
    published_count = sum(1 for m in manuscripts if m.get("status") == "published")

    manuscript_areas: set[str] = set()
    manuscript_keywords: set[str] = set()
    for m in manuscripts:
        for area in (m.get("research_areas") or []):
            if area and isinstance(area, str):
                manuscript_areas.add(area.strip().lower())
        for kw in (m.get("keywords") or []):
            if kw and isinstance(kw, str):
                manuscript_keywords.add(kw.strip().lower())

    # ── Fetch projects user is part of ──────────────────────────────────────
    project_count = await db.projects.count_documents(
        {"$or": [{"owner_id": user_id}, {"members": user_id}]}
    )

    # ── Fetch grant applications where user is PI ────────────────────────────
    grant_count = await db.grant_applications.count_documents({"pi_id": user_id})

    # ── Fetch collaborations ─────────────────────────────────────────────────
    collaboration_count = await db.collaborations.count_documents(
        {"members": user_id}
    )

    # ── Fetch completed/submitted reviews ────────────────────────────────────
    review_count = await db.review_requests.count_documents(
        {"reviewer_id": user_id, "status": {"$in": ["completed", "submitted"]}}
    )

    # ── Fetch reputation score ───────────────────────────────────────────────
    rep_doc = await db.research_reputation.find_one({"user_id": user_id})
    reputation_score = int((rep_doc or {}).get("overall_score", 0))

    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "user_id": user_id,
        "full_name": (user.get("full_name") or "").strip(),
        "email": (user.get("email") or "").strip(),
        "institution": (user.get("institution") or "").strip(),
        "country": (user.get("country") or "").strip(),
        "academic_role": (user.get("academic_role") or "").strip().lower(),
        "orcid": user.get("orcid") or None,
        "avatar_url": user.get("avatar_url") or None,
        "research_areas": _normalize_list(user.get("research_areas")),
        "research_keywords": _normalize_list(user.get("research_keywords")),
        "research_interests": _normalize_list(user.get("research_interests")),
        "methods": _normalize_list(user.get("methods")),
        "skills": _normalize_list(user.get("skills")),
        "software_skills": _normalize_list(user.get("software_skills")),
        "publication_count": publication_count,
        "published_count": published_count,
        "project_count": project_count,
        "grant_count": grant_count,
        "collaboration_count": collaboration_count,
        "review_count": review_count,
        "reputation_score": reputation_score,
        "is_private": (user.get("profile_visibility") or "") == "private",
        "is_suspended": bool(user.get("is_suspended", False)),
        "is_demo": (user.get("account_type") or "") == "demo",
        "manuscript_research_areas": sorted(manuscript_areas),
        "manuscript_keywords": sorted(manuscript_keywords),
        "updated_at": now_iso,
    }


async def get_or_refresh_profile(user_id: str, db, max_age_hours: int = 12) -> dict:
    """
    Return cached profile from recommendation_profiles if < max_age_hours old,
    else rebuild and upsert into recommendation_profiles.
    """
    db = make_db_proxy(db, system=True)
    cached = await db.recommendation_profiles.find_one({"user_id": user_id})

    if cached:
        updated_at_raw = cached.get("updated_at")
        if updated_at_raw:
            try:
                if isinstance(updated_at_raw, datetime):
                    updated_at = updated_at_raw.replace(tzinfo=timezone.utc) if updated_at_raw.tzinfo is None else updated_at_raw
                else:
                    updated_at = datetime.fromisoformat(str(updated_at_raw))
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=timezone.utc)

                age_hours = (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600
                if age_hours < max_age_hours:
                    # Return cached (strip MongoDB _id)
                    cached.pop("_id", None)
                    return cached
            except (ValueError, TypeError):
                pass  # fall through to rebuild

    profile = await build_profile(user_id, db)

    await db.recommendation_profiles.update_one(
        {"user_id": user_id},
        {"$set": profile},
        upsert=True,
    )

    return profile


async def refresh_all_profiles(db, limit: int = 500) -> int:
    """Refresh profiles for up to `limit` users (for background refresh jobs). Returns count refreshed."""
    db = make_db_proxy(db, system=True)
    users_cursor = db.users.find(
        {"is_suspended": {"$ne": True}, "account_type": {"$ne": "demo"}},
        {"_id": 1},
        limit=limit,
    )
    users = await users_cursor.to_list(limit)

    count = 0
    for u in users:
        uid = _str_id(u["_id"])
        try:
            profile = await build_profile(uid, db)
            await db.recommendation_profiles.update_one(
                {"user_id": uid},
                {"$set": profile},
                upsert=True,
            )
            count += 1
        except Exception:
            # Skip users that fail (e.g. missing required fields) to avoid aborting the whole batch
            continue

    return count
