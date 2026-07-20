"""Modular payment architecture — wallet, escrow, academic credits, refunds.

No payment provider is hardcoded. All financial operations go through an
internal ledger (mkt_wallet, mkt_escrow, mkt_transactions). A real provider
adapter can be injected at the payment gateway layer without changing this module.
"""
from datetime import datetime, timezone
from bson import ObjectId

TX_TYPES = {
    "deposit", "withdrawal", "escrow_hold", "escrow_release", "escrow_refund",
    "credit_purchase", "credit_spend", "coupon_applied", "platform_fee",
    "provider_payout", "refund",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


# ── Wallet ───────────────────────────────────────────────────────────────────

async def get_wallet(user_id: str, db) -> dict:
    wallet = await db["mkt_wallet"].find_one({"user_id": user_id})
    if not wallet:
        wallet = {
            "user_id": user_id,
            "balance": 0.0,
            "currency": "USD",
            "credits": 0,
            "escrow_held": 0.0,
            "total_spent": 0.0,
            "total_earned": 0.0,
            "created_at": _now(),
        }
        await db["mkt_wallet"].insert_one(wallet)
        wallet = await db["mkt_wallet"].find_one({"user_id": user_id})
    wallet.pop("_id", None)
    return wallet


async def add_credits(user_id: str, credits: int, reason: str, db) -> dict:
    await db["mkt_wallet"].update_one(
        {"user_id": user_id}, {"$inc": {"credits": credits}}, upsert=True
    )
    await _record_transaction(user_id, "credit_purchase", 0, 0, credits, reason, db)
    return await get_wallet(user_id, db)


async def spend_credits(user_id: str, credits: int, order_id: str, db) -> dict:
    wallet = await get_wallet(user_id, db)
    if wallet.get("credits", 0) < credits:
        return {"error": "Insufficient credits"}
    await db["mkt_wallet"].update_one(
        {"user_id": user_id}, {"$inc": {"credits": -credits, "total_spent": float(credits)}}
    )
    await _record_transaction(user_id, "credit_spend", float(credits), 0, -credits,
                              f"Order {order_id}", db)
    return await get_wallet(user_id, db)


# ── Escrow ───────────────────────────────────────────────────────────────────

async def hold_in_escrow(order_id: str, buyer_user_id: str, amount: float,
                          currency: str, db) -> dict:
    existing = await db["mkt_escrow"].find_one({"order_id": order_id})
    if existing:
        return _s(existing)

    escrow = {
        "order_id": order_id,
        "buyer_user_id": buyer_user_id,
        "amount": amount,
        "currency": currency,
        "status": "held",
        "held_at": _now(),
        "released_at": None,
        "released_to": None,
    }
    r = await db["mkt_escrow"].insert_one(escrow)
    await db["mkt_wallet"].update_one(
        {"user_id": buyer_user_id}, {"$inc": {"escrow_held": amount}}, upsert=True
    )
    await _record_transaction(buyer_user_id, "escrow_hold", amount, 0, 0,
                              f"Escrow for order {order_id}", db)
    escrow["id"] = str(r.inserted_id)
    escrow.pop("_id", None)
    return escrow


async def release_escrow_to_provider(order_id: str, provider_user_id: str, db) -> dict:
    escrow = await db["mkt_escrow"].find_one({"order_id": order_id, "status": "held"})
    if not escrow:
        return {"error": "No held escrow found"}

    order = await db["mkt_orders"].find_one({"_id": ObjectId(order_id)})
    payout = (order or {}).get("provider_payout", escrow["amount"] * 0.85)
    platform_fee = (order or {}).get("platform_fee", escrow["amount"] * 0.15)

    await db["mkt_escrow"].update_one(
        {"order_id": order_id},
        {"$set": {"status": "released", "released_at": _now(), "released_to": provider_user_id}}
    )
    await db["mkt_wallet"].update_one(
        {"user_id": escrow["buyer_user_id"]},
        {"$inc": {"escrow_held": -escrow["amount"], "total_spent": escrow["amount"]}}
    )
    await db["mkt_wallet"].update_one(
        {"user_id": provider_user_id},
        {"$inc": {"total_earned": payout}}, upsert=True
    )
    await _record_transaction(provider_user_id, "provider_payout", payout, platform_fee, 0,
                              f"Payout for order {order_id}", db)
    return {"status": "released", "payout": payout, "platform_fee": platform_fee}


async def refund_escrow_to_buyer(order_id: str, db) -> dict:
    escrow = await db["mkt_escrow"].find_one({"order_id": order_id, "status": "held"})
    if not escrow:
        return {"error": "No held escrow found"}
    await db["mkt_escrow"].update_one(
        {"order_id": order_id},
        {"$set": {"status": "refunded", "released_at": _now(), "released_to": escrow["buyer_user_id"]}}
    )
    await db["mkt_wallet"].update_one(
        {"user_id": escrow["buyer_user_id"]},
        {"$inc": {"escrow_held": -escrow["amount"], "balance": escrow["amount"]}}
    )
    await _record_transaction(escrow["buyer_user_id"], "escrow_refund", escrow["amount"], 0, 0,
                              f"Refund for order {order_id}", db)
    return {"status": "refunded", "refunded_amount": escrow["amount"]}


async def get_escrow(order_id: str, db) -> dict | None:
    doc = await db["mkt_escrow"].find_one({"order_id": order_id})
    if doc:
        doc.pop("_id", None)
    return doc


# ── Transactions ──────────────────────────────────────────────────────────────

async def _record_transaction(user_id: str, tx_type: str, amount: float,
                               fee: float, credits: int, note: str, db):
    await db["mkt_transactions"].insert_one({
        "user_id": user_id,
        "type": tx_type,
        "amount": amount,
        "fee": fee,
        "credits": credits,
        "note": note,
        "created_at": _now(),
    })


async def get_transactions(user_id: str, db, page: int = 1, limit: int = 30) -> dict:
    query = {"user_id": user_id}
    skip = (page - 1) * limit
    cursor = db["mkt_transactions"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["mkt_transactions"].count_documents(query)
    for d in docs:
        d.pop("_id", None)
    return {"results": docs, "total": total, "page": page,
            "pages": max(1, -(-total // limit))}


async def get_invoice(order_id: str, user_id: str, db) -> dict:
    try:
        order = await db["mkt_orders"].find_one({"_id": ObjectId(order_id)})
    except Exception:
        return {"error": "Invalid order"}
    if not order:
        return {"error": "Order not found"}
    if order["buyer_user_id"] != user_id and order["provider_user_id"] != user_id:
        return {"error": "Not authorized"}

    order["id"] = order_id
    order.pop("_id", None)
    escrow = await get_escrow(order_id, db)

    return {
        "invoice_number": f"INV-{order_id[-8:].upper()}",
        "order": order,
        "escrow": escrow,
        "issued_at": order.get("created_at", _now()),
        "service_title": order.get("service_title", ""),
        "buyer_user_id": order["buyer_user_id"],
        "provider_user_id": order["provider_user_id"],
        "amount": order.get("price", 0),
        "platform_fee": order.get("platform_fee", 0),
        "provider_payout": order.get("provider_payout", 0),
        "currency": order.get("currency", "USD"),
        "status": escrow.get("status", "pending") if escrow else "pending",
    }
