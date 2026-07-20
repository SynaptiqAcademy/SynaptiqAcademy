"""Promotion engine — SUPER_ADMIN-issued grants.

SUPER_ADMIN can grant:
  - Credits (any quantity → pack_balance)
  - Discounts (Stripe coupons; activates only when Stripe is configured)
  - Free Months / Free Year (extends subscription)
  - VIP Status (badge)
  - Beta Access (badge / feature flag)
  - Early Access (badge / feature flag)
  - Custom Promotions (free-form metadata)

Every grant is written to `promotions` collection AND to `audit_log`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from fastapi import HTTPException

from db import get_db
from services.audit import write_audit
from services.rewards import _grant_credits, _grant_free_months, _grant_badge
from services import stripe_service
from repo.shim import DBProxy
from repo.security_context import SecurityContext


def _iso(): return datetime.now(timezone.utc).isoformat()


PROMO_KINDS = {"credits", "discount", "free_months", "vip", "beta", "early_access", "custom"}


async def issue_promotion(
    *, actor: dict, target_user_id: str | None, kind: Literal["credits","discount","free_months","vip","beta","early_access","custom"],
    payload: dict, target_email: str | None = None,
) -> dict:
    if kind not in PROMO_KINDS:
        raise HTTPException(400, f"Unknown promotion kind: {kind}")
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    # Resolve target by email if no id provided
    if not target_user_id and target_email:
        u = await db.users.find_one({"email": target_email.lower().strip()})
        if not u: raise HTTPException(404, "Target user not found by email.")
        target_user_id = str(u["_id"])
    if not target_user_id:
        raise HTTPException(400, "Provide target_user_id or target_email.")

    # Effect application
    effect = {}
    if kind == "credits":
        credits = int(payload.get("credits", 0))
        if credits <= 0: raise HTTPException(400, "credits must be > 0")
        await _grant_credits(target_user_id, credits, reason=f"promo:{actor.get('email','admin')}")
        effect = {"credits_added": credits}

    elif kind == "free_months":
        months = int(payload.get("months", 1))
        if months <= 0 or months > 24: raise HTTPException(400, "months must be 1..24")
        await _grant_free_months(target_user_id, months)
        effect = {"months_added": months}

    elif kind == "vip":
        await _grant_badge(target_user_id, "vip")
        effect = {"badge": "vip"}

    elif kind == "beta":
        await _grant_badge(target_user_id, "beta_access")
        effect = {"badge": "beta_access"}

    elif kind == "early_access":
        await _grant_badge(target_user_id, "early_access")
        effect = {"badge": "early_access"}

    elif kind == "discount":
        # Pure Stripe-coupon flow. Without Stripe configured we just persist the
        # intent; Stripe sync runs once keys are wired.
        percent = int(payload.get("percent_off", 0))
        duration = payload.get("duration", "once")     # once | repeating | forever
        if percent <= 0 or percent > 100: raise HTTPException(400, "percent_off must be 1..100")
        coupon_id = ""
        if stripe_service.is_configured():
            try:
                stripe = stripe_service._stripe()
                c = stripe.Coupon.create(percent_off=percent, duration=duration, name=payload.get("name") or None)
                coupon_id = c.id
            except Exception as e:
                raise HTTPException(502, f"Stripe coupon creation failed: {e}")
        effect = {"percent_off": percent, "duration": duration, "stripe_coupon_id": coupon_id}

    elif kind == "custom":
        # Free-form: just persist for audit + optional email delivery downstream.
        effect = {"custom": payload}

    # Record
    record = {
        "actor_id": actor.get("id"),
        "actor_email": actor.get("email"),
        "target_user_id": target_user_id,
        "kind": kind,
        "payload": payload,
        "effect": effect,
        "created_at": _iso(),
    }
    result = await db.promotions.insert_one(record)
    record.pop("_id", None)
    record["id"] = str(result.inserted_id)

    await write_audit(actor=actor, action="promotion_issue",
                      entity_kind="user", entity_id=target_user_id,
                      target_user_id=target_user_id,
                      metadata={"kind": kind, "payload": payload, "effect": effect})
    return record


async def list_promotions(*, target_user_id: str | None = None, limit: int = 100) -> list[dict]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    q = {}
    if target_user_id: q["target_user_id"] = target_user_id
    docs = await db.promotions.find(q).sort("created_at", -1).limit(limit).to_list(limit)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        out.append(d)
    return out
