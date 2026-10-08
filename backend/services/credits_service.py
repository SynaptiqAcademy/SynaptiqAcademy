"""Credits service — dual-balance model with reservations.

Two balances per user (field names kept for production-data compatibility):
  - subscription credits  (users.credits_balance): the plan's monthly
    allocation. Reset to the plan allowance on each successful renewal;
    unused credits do NOT roll over.
  - purchased credits     (users.credits_pack_balance): from credit packs.
    Never expire, never reset — but only usable while on a paid plan.

Consume order: subscription first, then purchased.

AI request lifecycle (credit_reservations collection):
  RESERVED  — credits atomically deducted before the provider is called
  COMPLETED — the AI operation succeeded (telemetry attached)
  RELEASED  — the operation failed internally; credits returned exactly to
              the buckets they came from (at most once — status CAS)
  FAILED    — reserved for operations recorded as failed without a refund
              (not produced by this module today)

Every existing call site keeps using consume_credits()/refund_credits(); the
reservation is tracked in a per-request context (services/monetization_middleware.py
opens it, finalizes RESERVED -> COMPLETED on success and -> RELEASED when
the request ends with an error status), so no AI call site has to change to
get exact, idempotent refunds.

`credit_transactions` is the sole authoritative ledger. `ledger_type` carries
the canonical type (SUBSCRIPTION_ALLOCATION, AI_RESERVATION, AI_CONSUMPTION,
AI_REFUND, CREDIT_PACK_PURCHASE, ADMIN_ADJUSTMENT); the older `kind` field is
kept unchanged ('consume', 'refund', 'monthly_grant', 'pack_grant',
'admin_*') because admin dashboards and engagement scoring aggregate on it.
AI_CONSUMPTION rows are balance-neutral (the debit is the AI_RESERVATION row)
and use kind='ai_consumption' so existing 'consume' sums do not double count.
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
import os
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument

from db import get_db
from plans_catalogue import get_plan, CREDIT_COSTS, operation_for_action
from rate_limit import check_ai_rate_limit
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.credits")

RESERVED, COMPLETED, RELEASED, FAILED = "RESERVED", "COMPLETED", "RELEASED", "FAILED"

# Per-request AI context, opened by the monetization middleware. Holds the
# reservations made during this request and the client's Idempotency-Key.
_request_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "synaptiq_ai_request_ctx", default=None,
)


def open_request_context(idempotency_key: str | None = None) -> contextvars.Token:
    return _request_ctx.set({"reservations": [], "idempotency_key": idempotency_key, "used_keys": set()})


def close_request_context(token: contextvars.Token) -> None:
    _request_ctx.reset(token)


def current_request_context() -> dict | None:
    return _request_ctx.get()


def current_reservation() -> dict | None:
    """Most recent reservation of this request (for telemetry attribution)."""
    ctx = _request_ctx.get()
    if ctx and ctx["reservations"]:
        return ctx["reservations"][-1]
    return None


def _db():
    return DBProxy(get_db(), SecurityContext.system())


def _now():
    return datetime.now(timezone.utc)


def _now_iso():
    return _now().isoformat()


def _next_reset_iso():
    return (_now() + timedelta(days=30)).isoformat()


def _allowance_for(user: dict) -> int:
    from services.entitlements import effective_plan_code
    allowance = get_plan(effective_plan_code(user))["credits_per_month"]
    return max(allowance, 0) if allowance != -1 else 10**9


async def ensure_user_credits(user_id: str) -> dict:
    """Make sure the user has a credits state; reset if a non-Stripe cycle is due.

    Paid subscriptions billed through Stripe (credits_source='stripe') are reset
    ONLY by the verified renewal webhook (allocate_subscription_credits) — never
    by this timer, so a delayed or failed renewal can't hand out credits.
    """
    db = _db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan_code = user.get("plan_code") or "free"
    monthly_allowance = _allowance_for(user)
    stripe_managed = user.get("credits_source") == "stripe" and plan_code != "free"

    if "credits_balance" not in user:
        await db.users.update_one(
            {"_id": ObjectId(user_id), "credits_balance": {"$exists": False}},
            {"$set": {
                "credits_balance": monthly_allowance,
                "credits_monthly_allowance": monthly_allowance,
                "credits_pack_balance": user.get("credits_pack_balance", 0),
                "credits_reset_at": _next_reset_iso(),
                "plan_code": plan_code,
            }},
        )
    elif not stripe_managed:
        # Timer-based cycle for non-Stripe accounts (Free, admin-assigned plans).
        # Compare-and-swap on credits_reset_at: only one concurrent request wins.
        try:
            reset_at = datetime.fromisoformat(user.get("credits_reset_at", ""))
        except Exception:
            reset_at = _now() - timedelta(days=1)

        if reset_at < _now():
            prior = await db.users.find_one_and_update(
                {"_id": ObjectId(user_id), "credits_reset_at": user.get("credits_reset_at")},
                {"$set": {
                    "credits_balance": monthly_allowance,
                    "credits_monthly_allowance": monthly_allowance,
                    "credits_reset_at": _next_reset_iso(),
                }},
                return_document=ReturnDocument.BEFORE,
            )
            if prior is not None and monthly_allowance > 0:
                await _record_transaction(
                    user_id, kind="monthly_grant", ledger_type="SUBSCRIPTION_ALLOCATION",
                    amount=monthly_allowance, bucket="monthly",
                    reason="Monthly allowance refill",
                )

        misc: dict = {}
        if user.get("credits_monthly_allowance") != monthly_allowance and reset_at >= _now():
            misc["credits_monthly_allowance"] = monthly_allowance
        if "credits_pack_balance" not in user:
            misc["credits_pack_balance"] = 0
        if misc:
            await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": misc})

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    return _credit_state(user)


def _credit_state(user: dict) -> dict:
    from services.entitlements import tier_for
    monthly = max(user.get("credits_balance", 0) or 0, 0)
    pack = max(user.get("credits_pack_balance", 0) or 0, 0)
    plan_code = user.get("plan_code", "free")
    usable = tier_for(user) != "FREE"
    return {
        "plan_code": plan_code,
        "plan_name": get_plan(plan_code).get("name", "Free"),
        "balance": monthly + pack,
        "monthly_balance": monthly,
        "pack_balance": pack,
        # Canonical names (same values) for the new UI.
        "subscription_credits": monthly,
        "purchased_credits": pack,
        "total_credits": monthly + pack,
        # Purchased credits are preserved on Free but can't be used there.
        "credits_usable": usable,
        "monthly_allowance": user.get("credits_monthly_allowance", 0),
        "reset_at": user.get("credits_reset_at"),
    }


async def _record_transaction(user_id: str, *, kind: str, ledger_type: str, amount: int,
                              bucket: str, reason: str = "", action: str = "",
                              metadata: dict | None = None, reservation_id: str | None = None,
                              balance_effect: int | None = None):
    """Authoritative ledger entry. `amount` is always positive; `ledger_type`
    gives the direction. `balance_effect` is the signed change to the user's
    total balance (0 for informational rows such as AI_CONSUMPTION)."""
    tx = {
        "user_id": user_id,
        "kind": kind,
        "ledger_type": ledger_type,
        "bucket": bucket,            # 'monthly' | 'pack' | 'mixed'
        "amount": amount,
        "balance_effect": balance_effect,
        "action": action,
        "reason": reason,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }
    if reservation_id:
        tx["reservation_id"] = reservation_id
    await _db().credit_transactions.insert_one(tx)


def _ai_not_included(user: dict) -> HTTPException:
    return HTTPException(
        status_code=402,
        detail={
            "code": "upgrade_required",
            "capability": "can_use_research_assistant",
            "message": "AI tools are part of Pro and Pro Advanced. Upgrade to use AI credits.",
            "required_plan": "researcher",
            "required_plan_name": get_plan("researcher")["name"],
            "current_plan": user.get("plan_code") or "free",
            "upgrade_url": "/pricing",
        },
    )


def _insufficient(cost: int, state: dict, action: str) -> HTTPException:
    return HTTPException(
        status_code=402,
        detail={
            "code": "credits_exhausted",
            "message": (f"This analysis requires {cost} AI Credits. "
                        f"You currently have {state['balance']}."),
            "needed": cost,
            "balance": state["balance"],
            "monthly_balance": state["monthly_balance"],
            "pack_balance": state["pack_balance"],
            "action": action,
            "operation": operation_for_action(action),
            "buy_credits_url": "/billing/credits",
            "upgrade_url": "/pricing",
        },
    )


async def _check_idempotency(db, user_id: str, action: str, key: str) -> None:
    """Reject replays of an idempotency key that already holds credits."""
    prior = await db.credit_reservations.find_one(
        {"user_id": user_id, "idempotency_key": key, "action": action})
    if not prior:
        return
    if prior["status"] in (RESERVED, COMPLETED):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_request",
                "message": ("This request is already being processed." if prior["status"] == RESERVED
                            else "This request was already completed — no additional credits were charged."),
                "reservation_status": prior["status"],
            },
        )
    # RELEASED/FAILED: the earlier attempt was refunded — free the key so a
    # genuine retry can reserve again (charged once, for the retry).
    await db.credit_reservations.update_one(
        {"_id": prior["_id"]},
        {"$set": {"idempotency_key": f"{key}#retired#{prior['_id']}"}},
    )


async def consume_credits(user_id: str, action: str, metadata: dict | None = None,
                          *, idempotency_key: str | None = None) -> dict:
    """Reserve (atomically deduct) the credits for an AI action.

    402 upgrade_required on Free / lapsed plans, 402 credits_exhausted when the
    balance is too low, 409 duplicate_request on a replayed idempotency key.
    Returns balances, the per-bucket split and the reservation_id.
    """
    # Rate limit at this single chokepoint (429) — see rate_limit.check_ai_rate_limit.
    check_ai_rate_limit(user_id)

    db = _db()
    cost = CREDIT_COSTS.get(action)
    if cost is None:
        raise HTTPException(status_code=400, detail=f"Unknown credit action: {action}")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from services.entitlements import tier_for
    if tier_for(user) == "FREE":
        raise _ai_not_included(user)

    if cost == 0:
        await _record_transaction(user_id, kind="consume", ledger_type="AI_RESERVATION",
                                  amount=0, bucket="monthly", action=action,
                                  metadata=metadata, balance_effect=0)
        state = await ensure_user_credits(user_id)
        return {"consumed": 0, "from_monthly": 0, "from_pack": 0,
                "balance": state["balance"], "action": action, "reservation_id": None}

    ctx = _request_ctx.get()
    key = idempotency_key
    if key is None and ctx and ctx.get("idempotency_key"):
        # One client key covers one reservation per action per request.
        if action not in ctx["used_keys"]:
            key = ctx["idempotency_key"]
    if key:
        await _check_idempotency(db, user_id, action, key)

    state = await ensure_user_credits(user_id)
    if state["balance"] < cost:
        try:
            from services.product_analytics import track_server_event
            await track_server_event(user_id, "credits_exhausted",
                                     {"action": action, "needed": cost, "balance": state["balance"]})
        except Exception:
            pass
        raise _insufficient(cost, state, action)

    from_monthly = min(cost, state["monthly_balance"])
    from_pack = cost - from_monthly

    # Two atomic updates — subscription first, then purchased. Both guarded by
    # $gte so concurrent requests can never drive a balance negative.
    if from_monthly > 0:
        r = await db.users.update_one(
            {"_id": ObjectId(user_id), "credits_balance": {"$gte": from_monthly}},
            {"$inc": {"credits_balance": -from_monthly}},
        )
        if r.modified_count == 0:
            raise _insufficient(cost, await ensure_user_credits(user_id), action)
    if from_pack > 0:
        r = await db.users.update_one(
            {"_id": ObjectId(user_id), "credits_pack_balance": {"$gte": from_pack}},
            {"$inc": {"credits_pack_balance": -from_pack}},
        )
        if r.modified_count == 0:
            if from_monthly > 0:
                await db.users.update_one({"_id": ObjectId(user_id)},
                                          {"$inc": {"credits_balance": from_monthly}})
            raise _insufficient(cost, await ensure_user_credits(user_id), action)

    reservation = {
        "user_id": user_id,
        "action": action,
        "operation": operation_for_action(action),
        "credits": cost,
        "from_monthly": from_monthly,
        "from_pack": from_pack,
        "status": RESERVED,
        "plan_code": user.get("plan_code") or "free",
        # "request": finalized by the monetization middleware when the HTTP
        # request ends; "background": finalized by the job that created it.
        "origin": "request" if ctx is not None else "background",
        "created_at": _now_iso(),
        "telemetry": {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                      "cache_read_tokens": 0, "cache_write_tokens": 0, "cost_usd": 0.0},
    }
    if key:
        reservation["idempotency_key"] = key
    try:
        res = await db.credit_reservations.insert_one(reservation)
    except Exception as exc:
        # Unique (user_id, idempotency_key) race: another request with the same
        # key won. Undo our deduction and report the duplicate.
        await _restore_buckets(db, user_id, from_monthly, from_pack)
        if "E11000" in str(exc) or "duplicate key" in str(exc).lower():
            raise HTTPException(status_code=409, detail={
                "code": "duplicate_request", "message": "This request is already being processed."})
        raise
    reservation_id = str(res.inserted_id)
    reservation["_id"] = res.inserted_id

    bucket = "monthly" if from_pack == 0 else ("pack" if from_monthly == 0 else "mixed")
    await _record_transaction(user_id, kind="consume", ledger_type="AI_RESERVATION",
                              amount=cost, bucket=bucket, action=action,
                              reservation_id=reservation_id, balance_effect=-cost,
                              metadata={**(metadata or {}),
                                        "from_monthly": from_monthly, "from_pack": from_pack})

    await _track(user_id, "ai_operation_started",
                 {"feature": action, "operation": reservation["operation"], "credits": cost,
                  "reservation_id": reservation_id})

    if ctx is not None:
        ctx["reservations"].append({"id": reservation_id, "user_id": user_id, "action": action,
                                    "operation": reservation["operation"], "credits": cost,
                                    "plan_code": reservation["plan_code"]})
        if key:
            ctx["used_keys"].add(action)

    return {"consumed": cost, "from_monthly": from_monthly, "from_pack": from_pack,
            "balance": state["balance"] - cost, "action": action,
            "reservation_id": reservation_id}


async def _track(user_id: str, event: str, props: dict) -> None:
    try:
        from services.product_analytics import track_server_event
        await track_server_event(user_id, event, props)
    except Exception:
        pass


async def _restore_buckets(db, user_id: str, from_monthly: int, from_pack: int) -> None:
    inc = {}
    if from_monthly > 0:
        inc["credits_balance"] = from_monthly
    if from_pack > 0:
        inc["credits_pack_balance"] = from_pack
    if inc:
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$inc": inc})


async def release_reservation(reservation_id: str, reason: str = "") -> bool:
    """RESERVED/COMPLETED -> RELEASED exactly once, returning the credits to
    the buckets they came from. Returns False if already released."""
    db = _db()
    res = await db.credit_reservations.find_one_and_update(
        {"_id": ObjectId(reservation_id), "status": {"$in": [RESERVED, COMPLETED]}},
        {"$set": {"status": RELEASED, "released_at": _now_iso(), "release_reason": reason[:300]}},
        return_document=ReturnDocument.BEFORE,
    )
    if res is None:
        return False
    await _restore_buckets(db, res["user_id"], res.get("from_monthly", 0), res.get("from_pack", 0))
    fm, fp = res.get("from_monthly", 0), res.get("from_pack", 0)
    bucket = "monthly" if fp == 0 else ("pack" if fm == 0 else "mixed")
    await _record_transaction(res["user_id"], kind="refund", ledger_type="AI_REFUND",
                              amount=res["credits"], bucket=bucket, action=res["action"],
                              reason=reason[:300], reservation_id=reservation_id,
                              balance_effect=res["credits"],
                              metadata={"from_monthly": fm, "from_pack": fp})
    await _track(res["user_id"], "ai_operation_failed",
                 {"feature": res["action"], "operation": res.get("operation"),
                  "credits_refunded": res["credits"], "reason": reason[:120]})
    return True


# A request-scoped reservation is always finalized (COMPLETED or RELEASED)
# when its HTTP request ends. One still RESERVED long after any request could
# have finished was abandoned: the worker was killed (timeout, deploy, crash,
# --max-requests recycling) before the middleware ran. Its credits are
# returned. Legacy rows without an origin are only touched after a day.
STALE_REQUEST_RESERVATION_MINUTES = int(os.environ.get("STALE_RESERVATION_MINUTES", "30"))
STALE_LEGACY_RESERVATION_HOURS = 24


async def release_stale_reservations(limit: int = 500) -> dict:
    """Release abandoned reservations. Safe to run concurrently and
    repeatedly: release_reservation() transitions each one exactly once."""
    db = _db()
    now = _now()
    req_cutoff = (now - timedelta(minutes=STALE_REQUEST_RESERVATION_MINUTES)).isoformat()
    legacy_cutoff = (now - timedelta(hours=STALE_LEGACY_RESERVATION_HOURS)).isoformat()
    cursor = db.credit_reservations.find(
        {"status": RESERVED, "$or": [
            {"origin": "request", "created_at": {"$lt": req_cutoff}},
            {"origin": {"$exists": False}, "created_at": {"$lt": legacy_cutoff}},
        ]},
        {"_id": 1, "credits": 1},
    ).limit(limit)
    released, credits = 0, 0
    async for r in cursor:
        if await release_reservation(str(r["_id"]), reason="abandoned: request did not finish"):
            released += 1
            credits += int(r.get("credits") or 0)
    return {"released": released, "credits_returned": credits}


async def complete_reservation(reservation_id: str) -> bool:
    """RESERVED -> COMPLETED (idempotent). Writes the balance-neutral
    AI_CONSUMPTION ledger row on the first transition only."""
    db = _db()
    res = await db.credit_reservations.find_one_and_update(
        {"_id": ObjectId(reservation_id), "status": RESERVED},
        {"$set": {"status": COMPLETED, "completed_at": _now_iso()}},
        return_document=ReturnDocument.BEFORE,
    )
    if res is None:
        return False
    await _record_transaction(res["user_id"], kind="ai_consumption", ledger_type="AI_CONSUMPTION",
                              amount=res["credits"], bucket="n/a", action=res["action"],
                              reservation_id=reservation_id, balance_effect=0,
                              metadata={"operation": res.get("operation"),
                                        "telemetry": res.get("telemetry")})
    await _track(res["user_id"], "ai_operation_completed",
                 {"feature": res["action"], "operation": res.get("operation"), "credits": res["credits"]})
    return True


async def attach_telemetry(reservation_id: str, *, input_tokens: int = 0, output_tokens: int = 0,
                           cache_read_tokens: int = 0, cache_write_tokens: int = 0,
                           cost_usd: float = 0.0, model: str = "") -> None:
    """Accumulate provider usage on the reservation (one request can make
    several provider calls). Best-effort; never raises."""
    try:
        update = {"$inc": {"telemetry.calls": 1,
                           "telemetry.input_tokens": int(input_tokens or 0),
                           "telemetry.output_tokens": int(output_tokens or 0),
                           "telemetry.cache_read_tokens": int(cache_read_tokens or 0),
                           "telemetry.cache_write_tokens": int(cache_write_tokens or 0),
                           "telemetry.cost_usd": float(cost_usd or 0.0)}}
        if model:
            update["$addToSet"] = {"telemetry.models": model}
        await _db().credit_reservations.update_one({"_id": ObjectId(reservation_id)}, update)
    except Exception as exc:
        logger.warning("attach_telemetry failed (non-blocking): %s", exc)


async def finalize_request_reservations(ctx: dict, *, success: bool, reason: str = "") -> None:
    """Called once per request by the monetization middleware."""
    for r in (ctx or {}).get("reservations", []):
        try:
            if success:
                await complete_reservation(r["id"])
            else:
                await release_reservation(r["id"], reason or "request_failed")
        except Exception as exc:
            logger.error("finalize reservation %s failed: %s", r.get("id"), exc)


@contextlib.asynccontextmanager
async def billed_background_operation(user_id: str, action: str, metadata: dict | None = None):
    """Credit-billed AI work that runs outside an HTTP request (worker jobs,
    scheduled missions). Reserves before the body runs; completes on success,
    releases (refunds) if the body raises. Raises the usual 402 when the user's
    plan has no AI or the balance is too low — so background AI can never run
    unbilled for a user."""
    token = open_request_context()
    try:
        res = await consume_credits(user_id, action, metadata)
        try:
            yield res
        except BaseException:
            if res.get("reservation_id"):
                await release_reservation(res["reservation_id"], "background_operation_failed")
            raise
        else:
            if res.get("reservation_id"):
                await complete_reservation(res["reservation_id"])
    finally:
        close_request_context(token)


async def refund_credits(user_id: str, action: str, reason: str = "",
                         *, reservation_id: str | None = None) -> bool:
    """Refund an action's credits — at most once per reservation.

    Resolves the reservation explicitly, else from this request's context,
    else the user's most recent un-released reservation for the action made
    in the last 15 minutes (for callers outside a request context).
    """
    db = _db()
    if CREDIT_COSTS.get(action, 0) == 0 and not reservation_id:
        return False
    if not reservation_id:
        ctx = _request_ctx.get()
        for r in reversed((ctx or {}).get("reservations", [])):
            if r["user_id"] == user_id and r["action"] == action:
                reservation_id = r["id"]
                break
    if not reservation_id:
        cutoff = (_now() - timedelta(minutes=15)).isoformat()
        doc = await db.credit_reservations.find_one(
            {"user_id": user_id, "action": action, "status": {"$in": [RESERVED, COMPLETED]},
             "created_at": {"$gte": cutoff}},
            sort=[("created_at", -1)],
        )
        reservation_id = str(doc["_id"]) if doc else None
    if not reservation_id:
        logger.warning("refund_credits: no reservation for user=%s action=%s — nothing refunded",
                       user_id, action)
        return False
    return await release_reservation(reservation_id, reason)


# ───────────────────────── subscription allocation ─────────────────────────

async def allocate_subscription_credits(user_id: str, *, plan_code: str, cycle_key: str,
                                        period_end_iso: str | None = None,
                                        reason: str = "subscription_renewal") -> bool:
    """Reset subscription credits to the plan allowance for a new billing
    cycle. Idempotent per cycle_key (e.g. '<stripe_sub_id>:<period_start>'):
    a replayed or duplicate renewal event never resets twice. Purchased
    credits are untouched."""
    allowance = max(get_plan(plan_code)["credits_per_month"], 0)
    db = _db()
    prior = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id), "credits_cycle_key": {"$ne": cycle_key}},
        {"$set": {
            "credits_balance": allowance,
            "credits_monthly_allowance": allowance,
            "credits_cycle_key": cycle_key,
            "credits_cycle_granted": allowance,
            "credits_source": "stripe",
            "credits_reset_at": period_end_iso or _next_reset_iso(),
        }},
        return_document=ReturnDocument.BEFORE,
    )
    if prior is None:
        return False
    await _record_transaction(user_id, kind="monthly_grant", ledger_type="SUBSCRIPTION_ALLOCATION",
                              amount=allowance, bucket="monthly", reason=reason,
                              balance_effect=allowance - max(prior.get("credits_balance", 0) or 0, 0),
                              metadata={"plan_code": plan_code, "cycle_key": cycle_key,
                                        "previous_subscription_credits": prior.get("credits_balance", 0)})
    return True


async def apply_plan_change_credits(user_id: str, *, from_plan: str, to_plan: str,
                                    cycle_key: str | None = None,
                                    period_end_iso: str | None = None) -> dict:
    """Mid-cycle plan change. Rules (documented in docs/MONETIZATION.md):

      upgrade   (e.g. Pro -> Pro Advanced): top up subscription credits by
                (new allowance - credits already granted this cycle), so the
                cycle's total grant equals the higher plan's allowance. Repeated
                down/up switches in one cycle can't grant more than that.
      downgrade (paid -> lower paid): subscription credits capped at the new
                allowance ($min). Nothing is refunded; data is untouched.
      to Free:  subscription credits -> 0. Purchased credits are preserved
                (usable again after re-subscribing).
    Every branch is idempotent.
    """
    from plans_catalogue import PLAN_RANK
    db = _db()
    new_allowance = max(get_plan(to_plan)["credits_per_month"], 0)
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return {"applied": "none"}

    if to_plan == "free":
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {
            "credits_balance": 0, "credits_monthly_allowance": 0, "credits_source": "timer",
            "credits_cycle_granted": 0, "credits_reset_at": _next_reset_iso(),
        }})
        prev = max(user.get("credits_balance", 0) or 0, 0)
        if prev:
            await _record_transaction(user_id, kind="admin_deduct", ledger_type="SUBSCRIPTION_ALLOCATION",
                                      amount=prev, bucket="monthly", balance_effect=-prev,
                                      reason=f"Subscription ended ({from_plan} -> free): subscription credits expire",
                                      metadata={"from_plan": from_plan, "to_plan": to_plan})
        return {"applied": "to_free"}

    same_cycle = cycle_key is not None and user.get("credits_cycle_key") == cycle_key
    if from_plan == "free" or not same_cycle:
        # Fresh cycle on the new plan.
        if cycle_key:
            await allocate_subscription_credits(user_id, plan_code=to_plan, cycle_key=cycle_key,
                                                period_end_iso=period_end_iso,
                                                reason=f"Plan start: {to_plan}")
        return {"applied": "new_cycle"}

    if PLAN_RANK.get(to_plan, 0) > PLAN_RANK.get(from_plan, 0):
        granted = int(user.get("credits_cycle_granted") or 0)
        top_up = max(0, new_allowance - granted)
        if top_up:
            r = await db.users.update_one(
                {"_id": ObjectId(user_id), "credits_cycle_granted": user.get("credits_cycle_granted")},
                {"$inc": {"credits_balance": top_up},
                 "$set": {"credits_cycle_granted": granted + top_up,
                          "credits_monthly_allowance": new_allowance}},
            )
            if r.modified_count:
                await _record_transaction(user_id, kind="monthly_grant", ledger_type="SUBSCRIPTION_ALLOCATION",
                                          amount=top_up, bucket="monthly", balance_effect=top_up,
                                          reason=f"Upgrade {from_plan} -> {to_plan}: cycle top-up",
                                          metadata={"cycle_key": cycle_key, "granted_before": granted})
        else:
            await db.users.update_one({"_id": ObjectId(user_id)},
                                      {"$set": {"credits_monthly_allowance": new_allowance}})
        return {"applied": "upgrade", "top_up": top_up}

    await db.users.update_one({"_id": ObjectId(user_id)},
                              {"$min": {"credits_balance": new_allowance},
                               "$set": {"credits_monthly_allowance": new_allowance}})
    return {"applied": "downgrade"}


# ───────────────────────── credit packs ─────────────────────────

async def grant_pack_credits(user_id: str, *, pack_code: str, credits: int,
                             stripe_payment_intent_id: str = "",
                             stripe_checkout_session_id: str = "") -> dict | None:
    """Credit a verified pack purchase. Idempotent per Checkout Session: the
    unique index on credit_purchases.stripe_checkout_session_id means a
    replayed webhook can never grant twice. Returns None on a duplicate."""
    db = _db()
    try:
        await db.credit_purchases.insert_one({
            "user_id": user_id,
            "pack_code": pack_code,
            "credits": credits,
            "stripe_payment_intent_id": stripe_payment_intent_id,
            "stripe_checkout_session_id": stripe_checkout_session_id or None,
            "status": "paid",
            "created_at": _now_iso(),
        })
    except Exception as exc:
        if "E11000" in str(exc) or "duplicate key" in str(exc).lower():
            logger.info("grant_pack_credits: session %s already fulfilled", stripe_checkout_session_id)
            return None
        raise

    await db.users.update_one({"_id": ObjectId(user_id)}, {"$inc": {"credits_pack_balance": credits}})
    await _record_transaction(user_id, kind="pack_grant", ledger_type="CREDIT_PACK_PURCHASE",
                              amount=credits, bucket="pack", balance_effect=credits,
                              reason=f"Credit pack purchase: {pack_code}",
                              metadata={"pack_code": pack_code,
                                        "stripe_session_id": stripe_checkout_session_id})
    try:
        from services.audit import write_audit
        await write_audit(actor={"id": "system", "email": "stripe_webhook", "role": "system"},
                          action="credit_pack_grant", entity_kind="user", entity_id=user_id,
                          target_user_id=user_id,
                          metadata={"pack_code": pack_code, "credits": credits,
                                    "stripe_session_id": stripe_checkout_session_id})
    except Exception:
        pass
    return await ensure_user_credits(user_id)


async def ensure_credit_indexes(db) -> None:
    """Indexes the reservation/idempotency guarantees rely on. Each step is
    isolated so one failure (e.g. legacy duplicate data) never blocks the
    rest of startup index creation; failures are logged loudly."""
    steps = [
        ("reservation idempotency", lambda: db.credit_reservations.create_index(
            [("user_id", 1), ("idempotency_key", 1)], unique=True,
            partialFilterExpression={"idempotency_key": {"$type": "string"}},
            name="uniq_user_idempotency_key")),
        ("reservation lookup", lambda: db.credit_reservations.create_index(
            [("user_id", 1), ("action", 1), ("created_at", -1)])),
        ("reservation status", lambda: db.credit_reservations.create_index(
            [("status", 1), ("created_at", -1)])),
        ("ledger type", lambda: db.credit_transactions.create_index(
            [("ledger_type", 1), ("created_at", -1)])),
        ("cost counters", lambda: db.ai_user_cost_counters.create_index([("user_id", 1), ("period", 1)])),
        ("ai_requests by user", lambda: db.ai_requests.create_index([("user_id", 1), ("timestamp", -1)])),
        # Same spec/name as server.py's startup index — webhook idempotency.
        ("billing event idempotency", lambda: db.billing_events.create_index(
            [("stripe_event_id", 1)], unique=True, sparse=True, name="billing_events_idempotency")),
    ]
    for label, step in steps:
        try:
            await step()
        except Exception as exc:
            logger.error("credit index '%s' failed: %s", label, exc)

    # Pack fulfilment idempotency: replace the old non-unique sparse index on
    # the same key with a unique one (same key + different options conflict).
    try:
        info = await db.credit_purchases.index_information()
        for name, spec in info.items():
            if spec.get("key") == [("stripe_checkout_session_id", 1)] and not spec.get("unique"):
                await db.credit_purchases.drop_index(name)
        await db.credit_purchases.create_index(
            "stripe_checkout_session_id", unique=True,
            partialFilterExpression={"stripe_checkout_session_id": {"$gt": ""}},
            name="uniq_checkout_session",
        )
    except Exception as exc:
        logger.error("credit_purchases unique checkout-session index failed — pack grants "
                     "still deduplicated by billing_events, but investigate: %s", exc)
