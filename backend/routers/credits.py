from fastapi import APIRouter, Depends

from auth_utils import get_current_user
from db import get_db
from services.credits_service import ensure_user_credits
from plans_catalogue import CREDIT_COSTS, CREDIT_USAGE_DISPLAY
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("/balance")
async def balance(user: dict = Depends(get_current_user)):
    state = await ensure_user_credits(user["id"])
    return {**state, "costs": CREDIT_COSTS, "usage_catalogue": CREDIT_USAGE_DISPLAY}


@router.get("/usage")
async def usage(limit: int = 50, user: dict = Depends(get_current_user)):
    """Returns recent credit activity in the legacy shape (reads from credit_transactions)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.credit_transactions.find({"user_id": user["id"]}) \
        .sort("created_at", -1).limit(limit).to_list(limit)
    return [{
        "id": str(d["_id"]),
        "action": d.get("action") or d.get("kind", ""),
        # Legacy convention: positive = consume, negative = refund/grant
        "amount": d.get("amount", 0) if d.get("kind") == "consume" else -(d.get("amount", 0)),
        "metadata": {**(d.get("metadata") or {}), "kind": d.get("kind"), "bucket": d.get("bucket"),
                     "reason": d.get("reason", "")},
        "created_at": d["created_at"],
    } for d in docs]


@router.get("/transactions")
async def transactions(limit: int = 50, user: dict = Depends(get_current_user)):
    """Authoritative ledger view. Each row: kind, bucket, amount, action, reason."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.credit_transactions.find({"user_id": user["id"]}) \
        .sort("created_at", -1).limit(limit).to_list(limit)
    return [{
        "id": str(d["_id"]),
        "kind": d.get("kind"),
        "bucket": d.get("bucket"),
        "amount": d.get("amount", 0),
        "action": d.get("action", ""),
        "reason": d.get("reason", ""),
        "metadata": d.get("metadata", {}),
        "created_at": d["created_at"],
    } for d in docs]


@router.get("/purchases")
async def credit_pack_purchases(limit: int = 25, user: dict = Depends(get_current_user)):
    """User's credit-pack purchase history."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.credit_purchases.find({"user_id": user["id"]}) \
        .sort("created_at", -1).limit(limit).to_list(limit)
    return [{
        "id": str(d["_id"]),
        "pack_code": d.get("pack_code"),
        "credits": d.get("credits"),
        "status": d.get("status"),
        "stripe_session_id": d.get("stripe_checkout_session_id", ""),
        "created_at": d["created_at"],
    } for d in docs]
