"""Credits service — dual-balance model.

Two balances per user:
  - monthly_balance: refills to plan allowance each cycle (does NOT roll over)
  - pack_balance: from one-time pack purchases; NEVER expires, NEVER resets

Consume order: monthly first, then pack. So users always burn the "free" portion
of their subscription before touching what they paid extra for.

`credit_transactions` is the sole authoritative ledger. `credit_usage` is a
deprecated collection — no longer written to.
"""
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import HTTPException

from db import get_db
from plans_catalogue import get_plan, CREDIT_COSTS
from repo.shim import DBProxy
from repo.security_context import SecurityContext


def _now():
    return datetime.now(timezone.utc)


def _now_iso():
    return _now().isoformat()


def _next_reset_iso():
    return (_now() + timedelta(days=30)).isoformat()


async def ensure_user_credits(user_id: str) -> dict:
    """Make sure the user has a credits state and reset monthly if due."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan_code = user.get("plan_code") or "free"
    plan = get_plan(plan_code)
    monthly_allowance = plan["credits_per_month"]

    if "credits_balance" not in user:
        # First-time initialisation — no race risk (field missing = unique state)
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "credits_balance": monthly_allowance,
                "credits_monthly_allowance": monthly_allowance,
                "credits_pack_balance": user.get("credits_pack_balance", 0),
                "credits_reset_at": _next_reset_iso(),
                "plan_code": plan_code,
            }},
        )
    else:
        # Monthly reset check — uses compare-and-swap (F2 fix).
        # Two concurrent requests both seeing reset_at < now would each call
        # find_one_and_update; only the first match updates the document.
        # The second sees a changed credits_reset_at and gets None — no duplicate entry.
        try:
            reset_at = datetime.fromisoformat(user.get("credits_reset_at", ""))
        except Exception:
            reset_at = _now() - timedelta(days=1)

        if reset_at < _now():
            prior = await db.users.find_one_and_update(
                {
                    "_id": ObjectId(user_id),
                    "credits_reset_at": user.get("credits_reset_at"),
                },
                {"$set": {
                    "credits_balance": monthly_allowance,
                    "credits_monthly_allowance": monthly_allowance,
                    "credits_reset_at": _next_reset_iso(),
                }},
                return_document=False,
            )
            if prior is not None:
                # This request won the race — emit exactly one ledger entry.
                await _record_transaction(
                    user_id, kind="monthly_grant", amount=monthly_allowance,
                    bucket="monthly", reason="Monthly allowance refill",
                )

        # Patch any stale/missing fields (idempotent, no ledger impact)
        misc: dict = {}
        if user.get("credits_monthly_allowance") != monthly_allowance and reset_at >= _now():
            misc["credits_monthly_allowance"] = monthly_allowance
        if "credits_pack_balance" not in user:
            misc["credits_pack_balance"] = 0
        if misc:
            await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": misc})

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    monthly = user.get("credits_balance", 0)
    pack = user.get("credits_pack_balance", 0)
    return {
        "plan_code": user.get("plan_code", "free"),
        "balance": monthly + pack,
        "monthly_balance": monthly,
        "pack_balance": pack,
        "monthly_allowance": user.get("credits_monthly_allowance", monthly_allowance),
        "reset_at": user.get("credits_reset_at"),
    }


async def _record_transaction(user_id: str, *, kind: str, amount: int, bucket: str,
                              reason: str = "", action: str = "", metadata: dict | None = None):
    """Authoritative ledger entry. Always positive `amount` — `kind` describes direction.

    kinds:
      - 'consume': monthly/pack credits deducted by an AI action
      - 'refund': prior consume reversed
      - 'monthly_grant': monthly allowance refill at billing cycle reset
      - 'pack_grant': pack purchase credited
      - 'admin_adjust': manual ops adjustment
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    tx = {
        "user_id": user_id,
        "kind": kind,
        "bucket": bucket,            # 'monthly' | 'pack' | 'mixed'
        "amount": amount,
        "action": action,
        "reason": reason,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }
    await db.credit_transactions.insert_one(tx)


async def consume_credits(user_id: str, action: str, metadata: dict | None = None) -> dict:
    """Atomically consume credits. Burns monthly first, then pack. 402 if both empty.

    Returns the resulting balances + per-bucket split of what was consumed.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cost = CREDIT_COSTS.get(action)
    if cost is None:
        raise HTTPException(status_code=400, detail=f"Unknown credit action: {action}")
    if cost == 0:
        # Free action — log to ledger so analytics see usage, but don't touch balances
        await _record_transaction(user_id, kind="consume", amount=0, bucket="monthly",
                                  action=action, metadata=metadata)
        state = await ensure_user_credits(user_id)
        return {"consumed": 0, "from_monthly": 0, "from_pack": 0,
                "balance": state["balance"], "action": action}

    state = await ensure_user_credits(user_id)
    if state["balance"] < cost:
        raise HTTPException(
            status_code=402,
            detail={
                "message": "Insufficient research credits. Buy a credit pack to continue.",
                "needed": cost,
                "balance": state["balance"],
                "action": action,
                "credit_pack_url": "/pricing#credit-packs",
            },
        )

    from_monthly = min(cost, state["monthly_balance"])
    from_pack = cost - from_monthly

    # Two atomic updates — monthly first, then pack. Both guarded by $gte.
    if from_monthly > 0:
        r = await db.users.update_one(
            {"_id": ObjectId(user_id), "credits_balance": {"$gte": from_monthly}},
            {"$inc": {"credits_balance": -from_monthly}},
        )
        if r.modified_count == 0:
            raise HTTPException(status_code=402, detail="Insufficient credits (race).")
    if from_pack > 0:
        r = await db.users.update_one(
            {"_id": ObjectId(user_id), "credits_pack_balance": {"$gte": from_pack}},
            {"$inc": {"credits_pack_balance": -from_pack}},
        )
        if r.modified_count == 0:
            # Rollback monthly deduction we already did
            if from_monthly > 0:
                await db.users.update_one({"_id": ObjectId(user_id)},
                                          {"$inc": {"credits_balance": from_monthly}})
            raise HTTPException(status_code=402, detail="Insufficient credits (race).")

    bucket = "monthly" if from_pack == 0 else ("pack" if from_monthly == 0 else "mixed")
    await _record_transaction(user_id, kind="consume", amount=cost, bucket=bucket,
                              action=action,
                              metadata={**(metadata or {}),
                                        "from_monthly": from_monthly,
                                        "from_pack": from_pack})

    new_balance = state["balance"] - cost
    return {"consumed": cost, "from_monthly": from_monthly, "from_pack": from_pack,
            "balance": new_balance, "action": action}


async def refund_credits(user_id: str, action: str, reason: str = ""):
    """Refund credits to the original source bucket (F3 fix).

    Looks up the most recent consume transaction for this action to determine
    how much came from monthly vs pack, then restores each bucket exactly.
    Falls back to monthly if no prior transaction is found.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cost = CREDIT_COSTS.get(action, 0)
    if cost == 0:
        return

    # Determine the bucket split from the most recent matching consume record.
    tx = await db.credit_transactions.find_one(
        {"user_id": user_id, "kind": "consume", "action": action},
        sort=[("created_at", -1)],
    )
    if tx and (tx.get("metadata") or {}):
        from_monthly = (tx["metadata"].get("from_monthly") or 0)
        from_pack = (tx["metadata"].get("from_pack") or 0)
        # Guard against malformed metadata — split must sum to cost
        if from_monthly + from_pack != cost:
            from_monthly, from_pack = cost, 0
    else:
        from_monthly, from_pack = cost, 0

    if from_monthly > 0:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"credits_balance": from_monthly}},
        )
    if from_pack > 0:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"credits_pack_balance": from_pack}},
        )

    bucket = "monthly" if from_pack == 0 else ("pack" if from_monthly == 0 else "mixed")
    await _record_transaction(
        user_id, kind="refund", amount=cost, bucket=bucket,
        action=action, reason=reason,
        metadata={"from_monthly": from_monthly, "from_pack": from_pack},
    )


async def grant_pack_credits(user_id: str, *, pack_code: str, credits: int,
                             stripe_payment_intent_id: str = "",
                             stripe_checkout_session_id: str = "") -> dict:
    """Credit a pack purchase to the user. Also records in `credit_purchases`."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"credits_pack_balance": credits}},
    )
    await db.credit_purchases.insert_one({
        "user_id": user_id,
        "pack_code": pack_code,
        "credits": credits,
        "stripe_payment_intent_id": stripe_payment_intent_id,
        "stripe_checkout_session_id": stripe_checkout_session_id,
        "status": "paid",
        "created_at": _now_iso(),
    })
    await _record_transaction(user_id, kind="pack_grant", amount=credits, bucket="pack",
                              reason=f"Credit pack purchase: {pack_code}",
                              metadata={"pack_code": pack_code,
                                        "stripe_session_id": stripe_checkout_session_id})
    # Audit
    try:
        from services.audit import write_audit
        await write_audit(actor={"id": "system", "email": "stripe_webhook", "role": "system"},
                          action="credit_pack_grant", entity_kind="user", entity_id=user_id,
                          target_user_id=user_id,
                          metadata={"pack_code": pack_code, "credits": credits,
                                    "stripe_session_id": stripe_checkout_session_id})
    except Exception:
        pass
    state = await ensure_user_credits(user_id)
    return state
