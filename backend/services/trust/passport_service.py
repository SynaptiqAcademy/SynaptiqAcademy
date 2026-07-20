"""
Academic Passport Service

Aggregates all verified credentials into a single, shareable Academic Passport.
Generates a unique share token and caches the passport in trust_passports.
"""
from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from bson import ObjectId

log = logging.getLogger("synaptiq.trust.passport")


def _ser(doc: dict) -> dict:
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def build_passport(user_id: str, db) -> dict:
    """
    Build the full Academic Passport for a user.
    Reads from: users, publications, grant_applications, reviews,
                trust_verifications, trust_badges, trust_scores.
    Writes to: trust_passports
    """
    from services.trust.badge_system import get_user_badges, evaluate_badges

    # ── Refresh badges first ──────────────────────────────────────────────────
    await evaluate_badges(user_id, db)

    # ── Gather all sources ────────────────────────────────────────────────────
    uid_obj = _safe_oid(user_id)

    user, score_doc, badges, pub_list, grant_list, review_list, verifications = await asyncio.gather(
        db.users.find_one({"_id": uid_obj}),
        db.trust_scores.find_one({"user_id": user_id}),
        get_user_badges(user_id, db),
        db.publications.find({"owner_id": user_id}).to_list(length=100),
        db.grant_applications.find({"applicant_id": user_id}).to_list(length=50),
        db.reviews.find({"reviewer_id": user_id}).to_list(length=50),
        db.trust_verifications.find({"user_id": user_id, "status": "verified"}).to_list(length=50),
    )

    now = datetime.now(timezone.utc)
    verified_types = {v["verification_type"] for v in verifications}

    # ── Generate share token ──────────────────────────────────────────────────
    existing = await db.trust_passports.find_one({"user_id": user_id})
    share_token = (existing or {}).get("share_token") or secrets.token_urlsafe(20)

    u = user or {}
    passport = {
        "user_id":            user_id,
        "share_token":        share_token,
        "name":               u.get("full_name") or u.get("name") or "Unknown",
        "photo_url":          u.get("avatar_url"),
        "email":              u.get("email") if u.get("email_verified") else None,
        "verified_institution":u.get("institution") if "institution_affiliation" in verified_types else None,
        "verified_department": u.get("department")  if "department"             in verified_types else None,
        "verified_position":   u.get("position")    if "academic_position"      in verified_types else None,
        "verified_orcid":      u.get("orcid")       if "orcid"                  in verified_types else None,
        "trust_score":         (score_doc or {}).get("score", 0),
        "trust_level":         (score_doc or {}).get("level", "Unverified"),
        "badges":              badges,
        "verified_pub_count":  len([p for p in pub_list if p.get("doi")]),
        "verified_grant_count":len(grant_list),
        "verified_review_count":len(review_list),
        "expertise":           u.get("expertise") or [],
        "research_interests":  u.get("research_interests") or [],
        "languages":           u.get("languages") or [],
        "country":             u.get("country"),
        "verification_types":  list(verified_types),
        "generated_at":        now,
        "public_url":          f"/passport/{share_token}",
    }

    await db.trust_passports.update_one(
        {"user_id": user_id},
        {"$set": {**passport, "updated_at": now}},
        upsert=True,
    )

    return _ser(passport)


async def get_passport_by_token(token: str, db) -> dict | None:
    doc = await db.trust_passports.find_one({"share_token": token})
    if not doc:
        return None
    return _ser(doc)


def _safe_oid(s: str):
    try:
        return ObjectId(s)
    except Exception:
        return s
