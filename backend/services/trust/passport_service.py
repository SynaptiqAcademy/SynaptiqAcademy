"""
Academic Passport Service

Aggregates all verified credentials into a single, shareable Academic Passport.
Generates a unique share token and caches the passport in trust_passports.
"""
from __future__ import annotations

import asyncio
import logging
import re
import secrets
from datetime import datetime, timezone
from bson import ObjectId

from services.passport.fingerprint import compute_fingerprint

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
        # P1 Phase 7 C3: this used to return the ENTIRE raw users.orcid dict
        # — including the encrypted access_token/refresh_token envelope —
        # whenever ORCID was verified. Nothing reads more than orcid_id from
        # this field (PassportHero.jsx only checks its truthiness; the real
        # orcid_id the UI displays comes from the already-safely-scrubbed
        # profile.orcid via auth_utils.serialize_user's _scrub_orcid). No
        # caller needs tokens here, so stop returning them.
        "verified_orcid":      (
            (u.get("orcid") or {}).get("orcid_id")
            if "orcid" in verified_types and isinstance(u.get("orcid"), dict)
            else None
        ),
        "trust_score":         (score_doc or {}).get("score", 0),
        "trust_level":         (score_doc or {}).get("level", "Unverified"),
        # Passport V2 (P1 Phase 7): distinguishes "never computed" (no
        # trust_scores doc exists — the common case, since compute_trust_score()
        # only runs when a user visits /trust/score or /trust/overview, never
        # on Passport load) from a genuinely-computed low/zero score. Without
        # this, the UI has no way to avoid presenting a stale default 0/
        # "Unverified" as if it contradicts verification_profiles, which is
        # computed fresh on every /verification/me call. Purely additive —
        # score_doc was already fetched above, no extra query, no write, no
        # change to the scoring algorithm itself.
        "trust_score_computed": score_doc is not None,
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
        # Non-biometric Academic Fingerprint (P1 Phase 7 C3) — deterministic
        # per-account HMAC, safe for public display. See
        # services/passport/fingerprint.py for the construction and its
        # non-reversibility rationale.
        "academic_fingerprint": compute_fingerprint(user_id),
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


async def sanitize_historical_verified_orcid(db) -> dict:
    """P1 Phase 7.1 §1 — one-time (idempotent) sanitization for
    trust_passports.verified_orcid documents written before the fix that
    made build_passport() return only a plain orcid_id string. Historical
    documents could hold the entire raw users.orcid object, including the
    encrypted OAuth token envelope.

    Only ever touches trust_passports.verified_orcid. Never touches
    users.orcid, ORCID OAuth credentials, or any other field. Never logs or
    returns token contents — only counts.

    Safe to re-run: once every verified_orcid is a string or null/missing,
    the $type: "object" query matches zero documents and this is a no-op.
    """
    query = {"verified_orcid": {"$type": "object"}}
    docs = await db.trust_passports.find(query, {"verified_orcid": 1}).to_list(length=10_000)

    migrated_to_string = 0
    nulled_no_valid_id = 0

    for doc in docs:
        vo = doc.get("verified_orcid") or {}
        orcid_id = vo.get("orcid_id")
        # A valid ORCID iD is a non-empty string in the standard
        # 0000-0000-0000-000X format — never guess/normalize beyond that.
        is_valid = isinstance(orcid_id, str) and bool(re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", orcid_id))
        new_value = orcid_id if is_valid else None
        await db.trust_passports.update_one(
            {"_id": doc["_id"]},
            {"$set": {"verified_orcid": new_value}},
        )
        if is_valid:
            migrated_to_string += 1
        else:
            nulled_no_valid_id += 1

    remaining_objects = await db.trust_passports.count_documents(query)

    return {
        "documents_found_as_object": len(docs),
        "migrated_to_string": migrated_to_string,
        "nulled_no_valid_id": nulled_no_valid_id,
        "remaining_object_type_after": remaining_objects,
    }
