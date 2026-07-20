"""Email preferences and unsubscribe endpoints.

Public:
  GET  /api/unsubscribe?token=...   — one-click unsubscribe link (email link)
  POST /api/unsubscribe             — programmatic unsubscribe (body: {token})

Authenticated:
  GET  /api/user/email-preferences  — get current preferences
  POST /api/user/email-preferences  — update preferences
"""
from __future__ import annotations
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from routers.admin_email_center import verify_unsubscribe_token, make_unsubscribe_token
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(tags=["email-preferences"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Public unsubscribe
# ---------------------------------------------------------------------------

@router.get("/api/unsubscribe")
async def unsubscribe_link(token: str = Query(default="")):
    """One-click unsubscribe — called when a user clicks the link in a bulk email.
    Sets email_marketing_consent = False and redirects to a confirmation page.
    """
    if not token:
        raise HTTPException(status_code=400, detail="Unsubscribe token required")

    user_id = verify_unsubscribe_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired unsubscribe token")

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "email_marketing_consent": False,
            "email_unsubscribed_at": _now_iso(),
        }},
    )

    import os
    # FRONTEND_BASE_URL is canonical; APP_BASE_URL is a deprecated backward-
    # compatible alias (see ENVIRONMENT_VARIABLES.md).
    base = (os.environ.get("FRONTEND_BASE_URL") or os.environ.get("APP_BASE_URL", "")).rstrip("/")
    return RedirectResponse(url=f"{base}/unsubscribed", status_code=302)


@router.post("/api/unsubscribe")
async def unsubscribe_post(body: dict):
    """Programmatic unsubscribe. Body: {token: string}"""
    token = (body or {}).get("token", "")
    if not token:
        raise HTTPException(status_code=400, detail="token required")

    user_id = verify_unsubscribe_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired unsubscribe token")

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "email_marketing_consent": False,
            "email_unsubscribed_at": _now_iso(),
        }},
    )
    return {"ok": True, "unsubscribed": True}


# ---------------------------------------------------------------------------
# Authenticated email preferences
# ---------------------------------------------------------------------------

class EmailPreferencesUpdate(BaseModel):
    email_marketing_consent: bool
    email_notifications_enabled: bool = True
    email_digest_enabled: bool = True


@router.get("/api/user/email-preferences")
async def get_email_preferences(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    u = await db.users.find_one(
        {"_id": ObjectId(user["id"])},
        {"email_marketing_consent": 1, "email_notifications_enabled": 1,
         "email_digest_enabled": 1, "email_unsubscribed_at": 1},
    )
    return {
        "email_marketing_consent": (u or {}).get("email_marketing_consent", True),
        "email_notifications_enabled": (u or {}).get("email_notifications_enabled", True),
        "email_digest_enabled": (u or {}).get("email_digest_enabled", True),
        "unsubscribed_at": (u or {}).get("email_unsubscribed_at"),
        "unsubscribe_token": make_unsubscribe_token(user["id"]),
    }


@router.post("/api/user/email-preferences")
async def update_email_preferences(body: EmailPreferencesUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    update: dict = {
        "email_marketing_consent": body.email_marketing_consent,
        "email_notifications_enabled": body.email_notifications_enabled,
        "email_digest_enabled": body.email_digest_enabled,
    }
    if not body.email_marketing_consent:
        update["email_unsubscribed_at"] = _now_iso()
    else:
        update["email_unsubscribed_at"] = None

    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update})
    return {"ok": True, **update}
