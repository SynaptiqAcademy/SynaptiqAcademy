"""Referral system — qualified-referral tracking + reward grants.

Schema (`referrals` collection):
  - referrer_id           (user who shared the link)
  - referee_id            (user who signed up)
  - referee_email
  - code                  (referrer's stable referral code)
  - status                'pending' | 'qualified' | 'rewarded' | 'rejected'
  - qualifications        {email_verified, onboarded, sessions, minutes,
                           project_created, workspace_created}
  - qualified_at
  - rewarded_at
  - created_at, updated_at

Qualification rules (all must be true):
  - email_verified
  - onboarded
  - sessions >= 3
  - minutes  >= 30
  - project_created
  - workspace_created
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

QUAL_SESSIONS_MIN = 3
QUAL_MINUTES_MIN = 30


def _now_iso(): return datetime.now(timezone.utc).isoformat()


async def ensure_referral_code(user_id: str) -> str:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    u = await db.users.find_one({"_id": ObjectId(user_id)})
    if not u: raise HTTPException(404, "User not found")
    code = u.get("referral_code")
    if code: return code
    code = secrets.token_urlsafe(6)[:10]
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"referral_code": code}})
    return code


async def attribute_signup(*, referee_id: str, code: str | None) -> None:
    """Called from /api/auth/register when ?ref=CODE was carried in.

    Creates a pending referral. Self-referrals + repeats are silently ignored.
    """
    if not code: return
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    referrer = await db.users.find_one({"referral_code": code})
    if not referrer: return
    if str(referrer["_id"]) == referee_id: return    # self-referral
    existing = await db.referrals.find_one({"referee_id": referee_id})
    if existing: return                              # already attributed

    referee = await db.users.find_one({"_id": ObjectId(referee_id)})
    await db.referrals.insert_one({
        "referrer_id": str(referrer["_id"]),
        "referee_id": referee_id,
        "referee_email": (referee or {}).get("email"),
        "code": code,
        "status": "pending",
        "qualifications": {
            "email_verified": False, "onboarded": False, "sessions": 0,
            "minutes": 0, "project_created": False, "workspace_created": False,
        },
        "qualified_at": None, "rewarded_at": None,
        "created_at": _now_iso(), "updated_at": _now_iso(),
    })


async def _project_count(uid: str) -> int:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    return await db.projects.count_documents({"owner_id": uid})


async def _workspace_count(uid: str) -> int:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    return await db.workspaces.count_documents({"owner_id": uid})


async def update_qualifications(user_id: str) -> dict | None:
    """Recompute the referee's qualification stats and, if all-true, mark
    qualified + trigger the reward engine for the referrer.

    Returns the updated referral doc or None.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    ref = await db.referrals.find_one({"referee_id": user_id, "status": {"$in": ["pending"]}})
    if not ref: return None

    referee = await db.users.find_one({"_id": ObjectId(user_id)})
    sessions = await db.session_events.count_documents(
        {"user_id": user_id, "event": "session_start"}
    )
    # Approximate active minutes from session_events durations
    minutes_agg = await db.session_events.aggregate([
        {"$match": {"user_id": user_id, "event": "session_end"}},
        {"$group": {"_id": None, "minutes": {"$sum": "$duration_minutes"}}},
    ]).to_list(1)
    minutes = int((minutes_agg[0]["minutes"] if minutes_agg else 0))

    quals = {
        "email_verified": bool((referee or {}).get("email_verified")),
        "onboarded": bool((referee or {}).get("onboarded")),
        "sessions": sessions,
        "minutes": minutes,
        "project_created": (await _project_count(user_id)) >= 1,
        "workspace_created": (await _workspace_count(user_id)) >= 1,
    }
    qualified = (
        quals["email_verified"] and quals["onboarded"]
        and quals["sessions"] >= QUAL_SESSIONS_MIN
        and quals["minutes"] >= QUAL_MINUTES_MIN
        and quals["project_created"] and quals["workspace_created"]
    )

    updates = {"qualifications": quals, "updated_at": _now_iso()}
    if qualified and ref["status"] == "pending":
        updates["status"] = "qualified"
        updates["qualified_at"] = _now_iso()
    await db.referrals.update_one({"_id": ref["_id"]}, {"$set": updates})

    if qualified and ref["status"] == "pending":
        # Defer reward processing to rewards.py to avoid import cycles.
        from services.rewards import process_rewards_for_referrer
        await process_rewards_for_referrer(ref["referrer_id"])

    return await db.referrals.find_one({"_id": ref["_id"]})


async def list_for_user(user_id: str) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    code = await ensure_referral_code(user_id)
    docs = await db.referrals.find({"referrer_id": user_id}).sort("created_at", -1).to_list(200)
    rows = [{
        "id": str(d["_id"]),
        "referee_email": d.get("referee_email"),
        "status": d.get("status"),
        "qualifications": d.get("qualifications", {}),
        "qualified_at": d.get("qualified_at"),
        "rewarded_at": d.get("rewarded_at"),
        "created_at": d.get("created_at"),
    } for d in docs]
    qualified_count = sum(1 for r in rows if r["status"] in ("qualified", "rewarded"))
    return {
        "code": code,
        "referrals": rows,
        "totals": {
            "all": len(rows),
            "pending": sum(1 for r in rows if r["status"] == "pending"),
            "qualified": qualified_count,
            "rewarded": sum(1 for r in rows if r["status"] == "rewarded"),
        },
    }
