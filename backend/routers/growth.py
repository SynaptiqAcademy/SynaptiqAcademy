"""Growth router — referrals + rewards + session telemetry endpoints (user-facing)."""
from fastapi import APIRouter, Depends, Request

from auth_utils import get_current_user
from db import get_db
from datetime import datetime, timezone

from services.referrals import (
    ensure_referral_code, list_for_user, update_qualifications,
)
from services.rewards import list_user_grants
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api", tags=["growth"])


@router.get("/referrals/me")
async def my_referrals(user: dict = Depends(get_current_user)):
    return await list_for_user(user["id"])


@router.post("/referrals/recompute")
async def recompute_referral(user: dict = Depends(get_current_user)):
    """Triggered by the frontend after milestone events. Idempotent."""
    res = await update_qualifications(user["id"])
    return {"ok": True, "referral": (res or None)}


@router.get("/rewards/me")
async def my_rewards(user: dict = Depends(get_current_user)):
    grants = await list_user_grants(user["id"])
    return {"grants": grants}


@router.post("/session/event")
async def session_event(payload: dict, request: Request, user: dict = Depends(get_current_user)):
    """Lightweight client-side telemetry. The frontend posts:
       session_start | session_end | page_view | feature_use
    Used by engagement scoring + analytics.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    evt = payload.get("event")
    if evt not in {"session_start", "session_end", "page_view", "feature_use"}:
        return {"ok": False, "error": "unknown_event"}
    doc = {
        "user_id": user["id"],
        "event": evt,
        "path": payload.get("path"),
        "feature": payload.get("feature"),
        "duration_minutes": float(payload.get("duration_minutes", 0) or 0),
        "metadata": payload.get("metadata", {}),
        "ip": (request.headers.get("x-forwarded-for") or "").split(",")[0].strip(),
        "user_agent": request.headers.get("user-agent", "")[:200],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.session_events.insert_one(doc)
    # Cheap referral re-qualification on milestone events
    if evt in ("session_start", "session_end", "feature_use"):
        try: await update_qualifications(user["id"])
        except Exception: pass
    return {"ok": True}
