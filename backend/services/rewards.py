"""Rewards engine — issues credits, free months, and badges based on qualified
referral counts. Idempotent: each tier is rewarded at most once per user.

Tier table (per approved spec):
   1 qualified  → 100 credits
   3 qualified  → 1 free month
   5 qualified  → 500 credits
  10 qualified  → 3 free months
  25 qualified  → VIP Researcher badge
  50 qualified  → 1 year free subscription
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from bson import ObjectId

from db import get_db
from services.credits_service import grant_pack_credits, _record_transaction
from services.audit import write_audit
from repo.shim import DBProxy
from repo.security_context import SecurityContext


def _now(): return datetime.now(timezone.utc)
def _iso(): return _now().isoformat()


# (qualified_count_threshold, kind, payload)
REWARD_TIERS = [
    (1,  "credits",       {"credits": 100}),
    (3,  "free_months",   {"months": 1}),
    (5,  "credits",       {"credits": 500}),
    (10, "free_months",   {"months": 3}),
    (25, "vip_badge",     {"badge": "vip_researcher"}),
    (50, "free_year",     {"months": 12}),
]


async def _qualified_count(referrer_id: str) -> int:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    return await db.referrals.count_documents(
        {"referrer_id": referrer_id, "status": {"$in": ["qualified", "rewarded"]}}
    )


async def _granted_kinds(referrer_id: str) -> set[str]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.reward_grants.find({"user_id": referrer_id}).to_list(200)
    return {f"{d['tier_count']}|{d['kind']}" for d in docs}


async def _grant_free_months(uid: str, months: int) -> None:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user = await db.users.find_one({"_id": ObjectId(uid)})
    if not user: return
    cur = user.get("subscription_status")
    # Extend an existing subscription, or create a comp record for free users.
    sub = await db.subscriptions.find_one({"user_id": uid,
                                           "status": {"$in": ["active", "trialing", "past_due"]}})
    if sub:
        # Push the period end forward.
        end = sub.get("current_period_end")
        try:
            if isinstance(end, (int, float)):
                base = datetime.fromtimestamp(end, tz=timezone.utc)
            elif isinstance(end, str) and end:
                base = datetime.fromisoformat(end)
            else:
                base = _now()
        except Exception:
            base = _now()
        new_end = base + timedelta(days=30 * months)
        await db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {"current_period_end": new_end.isoformat(),
                      "extended_by_rewards_months": (sub.get("extended_by_rewards_months", 0) + months),
                      "updated_at": _iso()}},
        )
    else:
        # Free user — grant a comp subscription at researcher tier
        await db.subscriptions.insert_one({
            "user_id": uid,
            "plan_code": "researcher",
            "status": "active",
            "billing_period": "monthly",
            "stripe_subscription_id": "",
            "current_period_end": (_now() + timedelta(days=30 * months)).isoformat(),
            "source": "reward_grant",
            "comp": True,
            "created_at": _iso(), "updated_at": _iso(),
        })
        await db.users.update_one(
            {"_id": ObjectId(uid)},
            {"$set": {"plan_code": "researcher", "subscription_status": "active"}},
        )


async def _grant_credits(uid: str, credits: int, reason: str) -> None:
    # Use the existing pack-credit machinery — packs never expire, perfect for rewards.
    await grant_pack_credits(uid, pack_code=f"reward:{reason}",
                             credits=credits,
                             stripe_payment_intent_id="",
                             stripe_checkout_session_id="")


async def _grant_badge(uid: str, badge: str) -> None:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.users.update_one(
        {"_id": ObjectId(uid)},
        {"$addToSet": {"badges": badge}},
    )


async def process_rewards_for_referrer(referrer_id: str) -> dict:
    """Evaluate the referrer's qualified count and grant any tier not yet granted.
    Idempotent: each (count, kind) combo is recorded in `reward_grants` once.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    count = await _qualified_count(referrer_id)
    granted = await _granted_kinds(referrer_id)
    new_grants = []
    for threshold, kind, payload in REWARD_TIERS:
        key = f"{threshold}|{kind}"
        if count >= threshold and key not in granted:
            if kind == "credits":
                await _grant_credits(referrer_id, payload["credits"],
                                     reason=f"{threshold}_qualified_referrals")
            elif kind in ("free_months", "free_year"):
                await _grant_free_months(referrer_id, payload["months"])
            elif kind == "vip_badge":
                await _grant_badge(referrer_id, payload["badge"])
            await db.reward_grants.insert_one({
                "user_id": referrer_id,
                "tier_count": threshold,
                "kind": kind,
                "payload": payload,
                "created_at": _iso(),
            })
            new_grants.append({"threshold": threshold, "kind": kind, **payload})
            # Audit trail
            await write_audit(actor={"id": "system", "email": "system", "role": "system"},
                              action="reward_grant", entity_kind="user", entity_id=referrer_id,
                              target_user_id=referrer_id,
                              metadata={"threshold": threshold, "kind": kind, **payload})

    # Mark any qualified referrals as 'rewarded' so they don't double-fire.
    await db.referrals.update_many(
        {"referrer_id": referrer_id, "status": "qualified"},
        {"$set": {"status": "rewarded", "rewarded_at": _iso(), "updated_at": _iso()}},
    )
    return {"qualified_count": count, "new_grants": new_grants}


async def list_user_grants(user_id: str) -> list[dict]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.reward_grants.find({"user_id": user_id}).sort("created_at", -1).to_list(200)
    return [{
        "id": str(d["_id"]), "threshold": d["tier_count"], "kind": d["kind"],
        "payload": d.get("payload", {}), "created_at": d["created_at"],
    } for d in docs]
