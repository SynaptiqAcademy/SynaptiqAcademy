"""Dispute resolution center — structured mediation workflow."""
from datetime import datetime, timezone
from bson import ObjectId

DISPUTE_REASONS = [
    "work_not_delivered", "quality_below_expectations", "scope_mismatch",
    "communication_breakdown", "late_delivery", "unauthorized_charges",
    "deliverable_inaccurate", "plagiarism_concern", "data_misuse", "other",
]

DISPUTE_STATES = frozenset({"open", "evidence_submitted", "under_review",
                             "mediation", "resolved_buyer", "resolved_provider",
                             "resolved_mutual", "closed"})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


async def open_dispute(claimant_user_id: str, data: dict, db) -> dict:
    order_id = data.get("order_id", "")
    try:
        order = await db["mkt_orders"].find_one({"_id": ObjectId(order_id)})
    except Exception:
        return {"error": "Invalid order"}
    if not order:
        return {"error": "Order not found"}

    if claimant_user_id not in (order.get("buyer_user_id"), order.get("provider_user_id")):
        return {"error": "Not a party to this order"}

    existing = await db["mkt_disputes"].find_one({"order_id": order_id, "status": {"$nin": ["closed"]}})
    if existing:
        return {"error": "A dispute is already open for this order"}

    respondent_id = (order["provider_user_id"] if claimant_user_id == order["buyer_user_id"]
                     else order["buyer_user_id"])

    dispute = {
        "order_id": order_id,
        "service_id": order.get("service_id", ""),
        "claimant_user_id": claimant_user_id,
        "respondent_user_id": respondent_id,
        "reason": data.get("reason", "other"),
        "description": data.get("description", "")[:3000],
        "desired_resolution": data.get("desired_resolution", ""),
        "status": "open",
        "evidence": [],
        "messages": [{
            "from": claimant_user_id,
            "text": data.get("description", ""),
            "at": _now(),
            "is_system": False,
        }],
        "resolution": None,
        "resolution_note": None,
        "resolved_by": None,
        "opened_at": _now(),
        "updated_at": _now(),
        "closed_at": None,
    }
    r = await db["mkt_disputes"].insert_one(dispute)
    dispute["id"] = str(r.inserted_id)
    dispute.pop("_id", None)

    await db["mkt_orders"].update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "disputed"}})
    return dispute


async def get_dispute(dispute_id: str, user_id: str, db) -> dict | None:
    try:
        doc = await db["mkt_disputes"].find_one({"_id": ObjectId(dispute_id)})
    except Exception:
        return None
    if not doc:
        return None
    if user_id not in (doc.get("claimant_user_id"), doc.get("respondent_user_id")):
        return None
    return _s(doc)


async def list_my_disputes(user_id: str, db) -> list:
    cursor = db["mkt_disputes"].find({
        "$or": [{"claimant_user_id": user_id}, {"respondent_user_id": user_id}]
    }).sort("opened_at", -1).limit(50)
    docs = await cursor.to_list(50)
    return [_s(d) for d in docs]


async def add_evidence(dispute_id: str, user_id: str, data: dict, db) -> dict:
    dispute = await get_dispute(dispute_id, user_id, db)
    if not dispute:
        return {"error": "Dispute not found or not authorized"}
    if dispute.get("status") not in ("open", "evidence_submitted"):
        return {"error": f"Cannot add evidence in status: {dispute.get('status')}"}

    evidence = {
        "submitted_by": user_id,
        "type": data.get("type", "statement"),
        "title": data.get("title", "Evidence"),
        "content": data.get("content", "")[:5000],
        "file_url": data.get("file_url", ""),
        "submitted_at": _now(),
    }
    await db["mkt_disputes"].update_one(
        {"_id": ObjectId(dispute_id)},
        {"$push": {"evidence": evidence},
         "$set": {"status": "evidence_submitted", "updated_at": _now()}}
    )
    doc = await db["mkt_disputes"].find_one({"_id": ObjectId(dispute_id)})
    return _s(doc)


async def add_message(dispute_id: str, user_id: str, text: str, db) -> dict:
    dispute = await get_dispute(dispute_id, user_id, db)
    if not dispute:
        return {"error": "Dispute not found or not authorized"}
    if dispute.get("status") in ("resolved_buyer", "resolved_provider", "resolved_mutual", "closed"):
        return {"error": "Dispute is already closed"}

    msg = {"from": user_id, "text": text[:2000], "at": _now(), "is_system": False}
    await db["mkt_disputes"].update_one(
        {"_id": ObjectId(dispute_id)},
        {"$push": {"messages": msg}, "$set": {"updated_at": _now()}}
    )
    doc = await db["mkt_disputes"].find_one({"_id": ObjectId(dispute_id)})
    return _s(doc)


async def resolve_dispute(dispute_id: str, resolver_user_id: str,
                          resolution: str, note: str, db) -> dict:
    try:
        doc = await db["mkt_disputes"].find_one({"_id": ObjectId(dispute_id)})
    except Exception:
        return {"error": "Invalid dispute"}
    if not doc:
        return {"error": "Dispute not found"}

    if resolution not in ("resolved_buyer", "resolved_provider", "resolved_mutual", "closed"):
        return {"error": "Invalid resolution"}

    system_msg = {
        "from": "system",
        "text": f"Dispute resolved: {resolution.replace('_', ' ').title()}. {note}",
        "at": _now(),
        "is_system": True,
    }
    await db["mkt_disputes"].update_one(
        {"_id": ObjectId(dispute_id)},
        {"$set": {"status": resolution, "resolution": resolution, "resolution_note": note,
                  "resolved_by": resolver_user_id, "closed_at": _now(), "updated_at": _now()},
         "$push": {"messages": system_msg}}
    )

    order_id = doc.get("order_id", "")
    if resolution == "resolved_buyer":
        from backend.services.acad_market import payment_engine
        await payment_engine.refund_escrow_to_buyer(order_id, db)
        await db["mkt_orders"].update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "cancelled"}})
    elif resolution in ("resolved_provider", "resolved_mutual"):
        from backend.services.acad_market import payment_engine
        claimant_is_buyer = doc.get("claimant_user_id") == doc.get("buyer_user_id") if hasattr(doc, "get") else False
        await payment_engine.release_escrow_to_provider(order_id, doc.get("respondent_user_id", ""), db)
        await db["mkt_orders"].update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "completed"}})

    doc = await db["mkt_disputes"].find_one({"_id": ObjectId(dispute_id)})
    return _s(doc)


async def get_admin_disputes(db, status_filter: str = None, page: int = 1, limit: int = 20) -> dict:
    query = {}
    if status_filter:
        query["status"] = status_filter
    skip = (page - 1) * limit
    cursor = db["mkt_disputes"].find(query).sort("opened_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["mkt_disputes"].count_documents(query)
    return {"results": [_s(d) for d in docs], "total": total, "page": page,
            "pages": max(1, -(-total // limit))}
