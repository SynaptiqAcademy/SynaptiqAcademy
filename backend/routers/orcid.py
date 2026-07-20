"""ORCID router — OAuth + sync + publications surface.

All endpoints respond gracefully when ORCID is not configured.
AUTH-012: ORCID access_token and refresh_token are encrypted at rest using
          services.encryption_service before being written to MongoDB.
"""
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from auth_utils import get_current_user, serialize_user, get_optional_user
from db import get_db
from plans_catalogue import get_plan
from services.orcid import oauth as O
from services.orcid.sync import sync_user, enrich_publications_with_openalex
from services.encryption_service import encrypt_field
from routers.auth import _issue_tokens_and_cookies
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.orcid.router")
router = APIRouter(prefix="/api/orcid", tags=["orcid"])


def _encrypt_orcid_tokens(nt: dict) -> dict:
    """Encrypt sensitive token fields before persisting (AUTH-012)."""
    enc = dict(nt)
    if enc.get("access_token"):
        enc["access_token"] = encrypt_field(enc["access_token"])
    if enc.get("refresh_token"):
        enc["refresh_token"] = encrypt_field(enc.get("refresh_token") or "")
    return enc


# ============================= CONFIG ======================================
@router.get("/config")
async def get_config():
    return O.config_info()


# ============================= OAUTH FLOW ==================================
@router.get("/authorize")
async def authorize(mode: Literal["login", "signup", "link"] = "login",
                    user: Optional[dict] = Depends(get_optional_user)):
    if mode == "link" and not user:
        raise HTTPException(401, "Sign in first to link your ORCID")
    url = O.authorization_url(mode, requesting_user_id=user["id"] if user else None)
    return {"authorization_url": url, "configured": True}


@router.get("/callback")
async def callback(code: Optional[str] = None, state: Optional[str] = None,
                   error: Optional[str] = None, request: Request = None):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    if error or not code or not state:
        return RedirectResponse(f"{O.FRONTEND_BASE_URL}/settings?orcid_error={error or 'cancelled'}")
    try:
        payload = O.decode_state(state)
    except Exception:
        raise HTTPException(400, "Invalid state parameter")
    mode = payload.get("mode", "login")
    requesting_uid = payload.get("uid")

    token = await O.exchange_code(code)
    nt = O.normalize_token(token)
    orcid_id = nt["orcid_id"]
    if not orcid_id:
        raise HTTPException(400, "ORCID iD missing from token response")

    enc_nt = _encrypt_orcid_tokens(nt)

    linked = await db.users.find_one({"orcid.orcid_id": orcid_id})
    user_doc = None

    if mode == "link":
        if not requesting_uid:
            raise HTTPException(400, "No active session")
        if linked and str(linked["_id"]) != requesting_uid:
            return RedirectResponse(f"{O.FRONTEND_BASE_URL}/settings?orcid_error=already_linked_to_other_account")
        user_doc = await db.users.find_one({"_id": ObjectId(requesting_uid)})
        if not user_doc:
            raise HTTPException(404, "User not found")
        existing_history = (user_doc.get("orcid", {}) or {}).get("sync_history", [])
        await db.users.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {"orcid": {**enc_nt, "sync_history": existing_history}}},
        )
    else:
        if linked:
            user_doc = linked
            await db.users.update_one(
                {"_id": linked["_id"]},
                {"$set": {
                    "orcid.verified_at":  enc_nt["verified_at"],
                    "orcid.access_token": enc_nt["access_token"],
                    "orcid.refresh_token": enc_nt["refresh_token"],
                    "orcid.expires_at":   enc_nt["expires_at"],
                }},
            )
        else:
            now = datetime.now(timezone.utc).isoformat()
            doc = {
                "email": None, "password_hash": None,
                "full_name": nt.get("name") or f"ORCID {orcid_id}",
                "role": "researcher",
                "credits_balance": get_plan("free")["credits_per_month"], "plan_code": "free",
                "credits_monthly_allowance": get_plan("free")["credits_per_month"],
                "credits_reset_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "orcid": enc_nt,
                "onboarded": False,
                "email_verified": False, "email_verified_at": None,
                "failed_login_count": 0, "locked_until": None,
                "last_failed_login": None, "last_successful_login": None,
                "created_at": now, "updated_at": now,
            }
            r = await db.users.insert_one(doc)
            user_doc = {**doc, "_id": r.inserted_id}

    uid_str = str(user_doc["_id"])

    # BLOCKER-3: Do not issue tokens when email verification is required and the
    # user's email exists but is unverified.  ORCID-only users with no email
    # cannot complete email verification, so they are allowed through (their
    # ORCID identity is the trust anchor).  The "link" mode is also exempt —
    # the user already holds a valid authenticated session.
    if mode != "link":
        _evr = os.environ.get("EMAIL_VERIFICATION_REQUIRED", "0") == "1"
        _has_email = bool(user_doc.get("email"))
        _verified = bool(user_doc.get("email_verified"))
        if _evr and _has_email and not _verified:
            logger.info("ORCID callback: blocking token issuance for unverified email uid=%s", uid_str)
            return RedirectResponse(f"{O.FRONTEND_BASE_URL}/verify-email-pending")

    is_new_account = mode != "link" and not user_doc.get("onboarded")
    post_redirect = (
        f"{O.FRONTEND_BASE_URL}/onboarding"
        if is_new_account
        else f"{O.FRONTEND_BASE_URL}/settings?orcid=connected"
    )
    resp = RedirectResponse(post_redirect)
    await _issue_tokens_and_cookies(resp, uid_str, user_doc.get("email") or "")
    try:
        await sync_user(uid_str, trigger="initial")
    except Exception as e:
        logger.warning("Initial ORCID sync failed: %s", e)
    # Emit reputation event for ORCID verification (idempotent)
    try:
        from services.reputation.events import emit_reputation_event
        await emit_reputation_event(uid_str, "orcid_verified", "orcid", orcid_id)
    except Exception as _rep_e:
        logger.warning("ORCID reputation event failed: %s", _rep_e)
    return resp


@router.post("/disconnect")
async def disconnect(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$unset": {"orcid": ""}})
    return {"ok": True}


# ============================= SYNC ========================================
@router.post("/sync")
async def trigger_sync(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    orcid_field = (u or {}).get("orcid")
    orcid = orcid_field if isinstance(orcid_field, dict) else {}
    if not orcid.get("orcid_id"):
        raise HTTPException(400, "ORCID not connected")
    return await sync_user(user["id"], trigger="manual")


@router.post("/enrich-openalex")
async def trigger_enrich(user: dict = Depends(get_current_user)):
    return await enrich_publications_with_openalex(user["id"])


@router.get("/sync-history")
async def history(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    orcid_field = (u or {}).get("orcid")
    orcid = orcid_field if isinstance(orcid_field, dict) else {}
    return orcid.get("sync_history") or []


@router.get("/status")
async def status(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    orcid_field = (u or {}).get("orcid")
    orcid = orcid_field if isinstance(orcid_field, dict) else {}
    pub_count = await db.publications.count_documents({"owner_id": user["id"], "source": "orcid"})
    return {
        "connected":             bool(orcid.get("orcid_id")),
        "verified":              bool(orcid.get("verified_at")),
        "orcid_id":              orcid.get("orcid_id"),
        "verified_at":           orcid.get("verified_at"),
        "last_sync_at":          orcid.get("last_sync_at"),
        "publications_imported": pub_count,
        "scope":                 orcid.get("scope"),
        "environment":           "sandbox" if "sandbox" in O.ORCID_BASE_URL else "production",
    }


# ============================= PUBLICATIONS ================================
@router.get("/publications")
async def list_publications(
    owner_id: Optional[str] = None,
    q: Optional[str] = None, type: Optional[str] = None,
    has_doi: Optional[bool] = None, limit: int = 50, skip: int = 0,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    qf: dict = {"owner_id": owner_id or user["id"]}
    if type:
        qf["type"] = type
    if has_doi is True:
        qf["doi"] = {"$ne": None}
    if has_doi is False:
        qf["doi"] = None
    if q:
        qf["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"journal": {"$regex": q, "$options": "i"}},
            {"concepts": {"$regex": q, "$options": "i"}},
        ]
    total = await db.publications.count_documents(qf)
    docs = await db.publications.find(qf).sort([("year", -1), ("title", 1)]).skip(skip).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return {"results": docs, "total": total}
