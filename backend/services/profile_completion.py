"""Shared profile-completion scoring.

Extracted from routers/users.py's GET /me/profile-completion so the
Getting-Started email (worker/handlers.py) and the API endpoint compute the
exact same score from the exact same fields — one source of truth, no risk
of the two drifting apart over time.
"""
from __future__ import annotations

from bson import ObjectId


async def compute_profile_completion(db, user_id: str) -> dict | None:
    """Return the real-data profile completion score with per-item breakdown,
    or None if the user no longer exists.

    Scoring breakdown (max 100): avatar +10, biography +10, institution +10,
    keywords +10, methods +5, social +5, availability +5, orcid_connected +15,
    publications +15, employment +10, education +5.
    """
    u = await db.users.find_one({"_id": ObjectId(user_id)})
    if not u:
        return None

    orcid = (u.get("orcid") or {}) if isinstance(u.get("orcid"), dict) else {}
    pub_count = await db.publications.count_documents({"owner_id": user_id})
    has_social = bool(
        orcid.get("orcid_id") or u.get("google_scholar") or
        u.get("researchgate") or u.get("linkedin")
    )

    items = [
        {"key": "avatar", "label": "Profile photo", "points": 10,
         "earned": bool(u.get("avatar_url")), "action": "/profile", "action_label": "Add photo"},
        {"key": "biography", "label": "Biography written", "points": 10,
         "earned": len(u.get("biography") or "") > 20, "action": "/profile", "action_label": "Edit profile"},
        {"key": "institution", "label": "Institution filled", "points": 10,
         "earned": bool(u.get("institution")), "action": "/profile", "action_label": "Edit profile"},
        {"key": "keywords", "label": "Research keywords", "points": 10,
         "earned": len(u.get("research_keywords") or []) > 0, "action": "/profile", "action_label": "Edit profile"},
        {"key": "methods", "label": "Research methods", "points": 5,
         "earned": len(u.get("methods") or []) > 0, "action": "/profile", "action_label": "Edit profile"},
        {"key": "social", "label": "Academic profile linked", "points": 5,
         "earned": has_social, "action": "/profile", "action_label": "Edit profile"},
        {"key": "availability", "label": "Availability set", "points": 5,
         "earned": bool(u.get("availability")), "action": "/profile", "action_label": "Edit profile"},
        {"key": "orcid_connected", "label": "ORCID connected", "points": 15,
         "earned": bool(orcid.get("orcid_id")), "action": "/settings", "action_label": "Connect ORCID"},
        {"key": "publications", "label": "Publications imported", "points": 15,
         "earned": pub_count > 0, "action": "/settings", "action_label": "Sync ORCID"},
        {"key": "employment", "label": "Employment on record", "points": 10,
         "earned": bool(u.get("orcid_employments")), "action": "/settings", "action_label": "Sync ORCID"},
        {"key": "education", "label": "Education on record", "points": 5,
         "earned": bool(u.get("orcid_educations")), "action": "/settings", "action_label": "Sync ORCID"},
    ]
    earned = sum(i["points"] for i in items if i["earned"])
    total = sum(i["points"] for i in items)
    return {
        "score": earned,
        "max": total,
        "percentage": round(earned / total * 100) if total else 0,
        "items": items,
        "orcid_id": orcid.get("orcid_id"),
        "publications_count": pub_count,
    }
