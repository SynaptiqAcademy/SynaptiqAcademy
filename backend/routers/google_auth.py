"""Google OAuth router (AUTH-013).

Endpoints:
  GET /api/google/config            — check if Google OAuth is configured
  GET /api/google/authorize         — get authorization URL
  GET /api/google/callback          — OAuth callback (browser redirect from Google)
  POST /api/google/disconnect       — unlink Google from account
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from auth_utils import (
    get_current_user, get_optional_user, serialize_user,
    set_csrf_cookie,
)
from db import get_db
from plans_catalogue import get_plan
from routers.auth import _issue_tokens_and_cookies
from services import google_oauth as G
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.google_auth")
router = APIRouter(prefix="/api/google", tags=["google-auth"])


@router.get("/config")
async def get_config():
    return G.config_info()


@router.get("/authorize")
async def authorize(
    mode: Literal["login", "signup", "link"] = "login",
    user: Optional[dict] = Depends(get_optional_user),
):
    if mode == "link" and not user:
        raise HTTPException(401, "Sign in first to link your Google account")
    url = G.authorization_url(mode, requesting_user_id=user["id"] if user else None)
    return {"authorization_url": url, "configured": True}


@router.get("/callback")
async def callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None,
):
    frontend = G.FRONTEND_BASE_URL

    if error or not code or not state:
        return RedirectResponse(f"{frontend}/login?google_error={error or 'cancelled'}")

    try:
        payload = G.decode_state(state)
    except ValueError as e:
        logger.warning("Google callback state error: %s", e)
        return RedirectResponse(f"{frontend}/login?google_error=state_invalid")

    mode = payload.get("mode", "login")
    requesting_uid = payload.get("uid")

    try:
        token_data = await G.exchange_code(code)
    except Exception as e:
        logger.error("Google code exchange failed: %s", e)
        return RedirectResponse(f"{frontend}/login?google_error=exchange_failed")

    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(f"{frontend}/login?google_error=no_access_token")

    try:
        ginfo = await G.get_user_info(access_token)
    except Exception as e:
        logger.error("Google userinfo failed: %s", e)
        return RedirectResponse(f"{frontend}/login?google_error=userinfo_failed")

    google_id = ginfo.get("id")
    google_email = (ginfo.get("email") or "").lower().strip()
    google_name = ginfo.get("name") or ""
    google_verified = ginfo.get("verified_email", False)

    if not google_id or not google_email:
        return RedirectResponse(f"{frontend}/login?google_error=missing_profile")

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = datetime.now(timezone.utc).isoformat()

    if mode == "link":
        if not requesting_uid:
            return RedirectResponse(f"{frontend}/settings?google_error=no_session")
        # Block if another account already owns this Google id
        conflict = await db.users.find_one({"google_id": google_id})
        if conflict and str(conflict["_id"]) != requesting_uid:
            return RedirectResponse(f"{frontend}/settings?google_error=already_linked_to_other_account")
        await db.users.update_one(
            {"_id": ObjectId(requesting_uid)},
            {"$set": {"google_id": google_id, "google_email": google_email}},
        )
        resp = RedirectResponse(f"{frontend}/settings?google=connected")
        resp_uid = requesting_uid
        resp_email = google_email
        resp_obj = await db.users.find_one({"_id": ObjectId(requesting_uid)})
    else:
        # login / signup
        user_doc = await db.users.find_one({"google_id": google_id})
        if not user_doc:
            # Try matching by verified email
            if google_verified:
                user_doc = await db.users.find_one({"email": google_email})
                if user_doc:
                    await db.users.update_one(
                        {"_id": user_doc["_id"]},
                        {"$set": {"google_id": google_id}},
                    )
        if not user_doc:
            # New account via Google
            doc = {
                "email": google_email,
                "password_hash": None,
                "full_name": google_name,
                "first_name": (google_name.split() + [""])[0],
                "last_name": " ".join(google_name.split()[1:]),
                "role": "user",
                "google_id": google_id,
                "google_email": google_email,
                "institution": "", "department": "", "country": "", "academic_role": "",
                "user_type": None, "primary_domain": None,
                "teaching_areas": [], "professional_expertise": [],
                "biography": "", "orcid": "", "google_scholar": "", "researchgate": "",
                "scopus_id": "", "linkedin": "", "website": "",
                "research_areas": [], "research_interests": [], "research_keywords": [],
                "skills": [], "can_contribute": [], "looking_for": [],
                "availability": "Available", "avatar_url": ginfo.get("picture") or "",
                "h_index": 0, "publications_count": 0, "conferences_count": 0,
                "collaboration_score": 50, "publication_score": 0,
                "expertise_score": 50, "community_score": 50,
                "connections": [],
                "onboarded": False,
                "plan_code": "free",
                "credits_balance": get_plan("free")["credits_per_month"],
                "credits_monthly_allowance": get_plan("free")["credits_per_month"],
                "credits_reset_at": now,
                "email_verified": google_verified,
                "email_verified_at": now if google_verified else None,
                "failed_login_count": 0, "locked_until": None,
                "last_failed_login": None, "last_successful_login": now,
                "created_at": now,
            }
            r = await db.users.insert_one(doc)
            user_doc = {**doc, "_id": r.inserted_id}
        resp_uid = str(user_doc["_id"])
        resp_email = user_doc.get("email") or google_email
        is_new = not user_doc.get("onboarded")
        post_redirect = f"{frontend}/onboarding" if is_new else f"{frontend}/discover"
        resp = RedirectResponse(post_redirect)
        resp_obj = user_doc

    # BLOCKER-3: Do not issue tokens when email verification is required and the
    # resolved user account has an unverified email.  The "link" mode is exempt —
    # the user already holds a valid authenticated session.
    if mode != "link":
        _evr = os.environ.get("EMAIL_VERIFICATION_REQUIRED", "0") == "1"
        if _evr and not resp_obj.get("email_verified"):
            logger.info("Google callback: blocking token issuance for unverified email uid=%s", str(resp_obj["_id"]))
            return RedirectResponse(f"{frontend}/verify-email-pending")

    await _issue_tokens_and_cookies(resp, str(resp_obj["_id"]), resp_obj.get("email") or google_email)
    return resp


@router.post("/disconnect")
async def disconnect(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$unset": {"google_id": "", "google_email": ""}},
    )
    return {"ok": True}
