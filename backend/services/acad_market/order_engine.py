"""Order lifecycle state machine for Academic Services Marketplace."""
from datetime import datetime, timezone
from bson import ObjectId

# Order states: pending → accepted → in_progress → under_review → completed
#                                  ↘ declined          ↘ revision_requested → in_progress
#                                  ↘ cancelled (any state before completed)

ORDER_STATES = frozenset({
    "pending", "accepted", "in_progress", "under_review",
    "revision_requested", "completed", "cancelled", "declined", "disputed",
})

VALID_TRANSITIONS = {
    "pending":            {"accepted", "declined", "cancelled"},
    "accepted":           {"in_progress", "cancelled"},
    "in_progress":        {"under_review", "cancelled", "disputed"},
    "under_review":       {"completed", "revision_requested", "disputed"},
    "revision_requested": {"in_progress", "cancelled", "disputed"},
    "completed":          {"disputed"},
    "declined":           set(),
    "cancelled":          set(),
    "disputed":           {"completed", "cancelled"},
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


async def create_order(buyer_user_id: str, data: dict, db) -> dict | dict:
    service_id = data.get("service_id", "")
    try:
        service = await db["mkt_services"].find_one({"_id": ObjectId(service_id)})
    except Exception:
        return {"error": "Invalid service"}
    if not service:
        return {"error": "Service not found"}
    if service.get("provider_user_id") == buyer_user_id:
        return {"error": "Cannot order your own service"}

    package_tier = data.get("package_tier", "basic")
    packages = {p["tier"]: p for p in (service.get("packages") or [])}
    package = packages.get(package_tier, {})

    price = data.get("custom_price") or package.get("price", 0)
    delivery_days = data.get("custom_delivery_days") or package.get("delivery_days", 7)

    order = {
        "buyer_user_id": buyer_user_id,
        "provider_user_id": service["provider_user_id"],
        "service_id": service_id,
        "service_title": service.get("title", ""),
        "category": service.get("category", ""),
        "package_tier": package_tier,
        "package": package,
        "price": float(price),
        "currency": data.get("currency", "USD"),
        "platform_fee": round(float(price) * 0.15, 2),
        "provider_payout": round(float(price) * 0.85, 2),
        "delivery_days": int(delivery_days),
        "requirements": data.get("requirements", ""),
        "milestones": data.get("milestones", []),
        "revisions_allowed": package.get("revisions", 1),
        "revisions_used": 0,
        "status": "pending",
        "timeline": [{"status": "pending", "note": "Order placed", "at": _now()}],
        "deliverables": [],
        "revision_notes": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db["mkt_orders"].insert_one(order)
    order["id"] = str(r.inserted_id)
    order.pop("_id", None)

    await db["mkt_services"].update_one({"_id": ObjectId(service_id)}, {"$inc": {"order_count": 1}})
    return order


async def get_order(order_id: str, db) -> dict | None:
    try:
        doc = await db["mkt_orders"].find_one({"_id": ObjectId(order_id)})
    except Exception:
        return None
    return _s(doc)


async def transition_order(order_id: str, actor_user_id: str, new_status: str,
                            note: str, db) -> dict:
    order = await get_order(order_id, db)
    if not order:
        return {"error": "Order not found"}

    is_buyer = order["buyer_user_id"] == actor_user_id
    is_provider = order["provider_user_id"] == actor_user_id
    if not (is_buyer or is_provider):
        return {"error": "Not authorized"}

    current = order["status"]
    if new_status not in VALID_TRANSITIONS.get(current, set()):
        return {"error": f"Cannot transition from {current} to {new_status}"}

    buyer_only = {"completed", "revision_requested", "disputed"}
    provider_only = {"accepted", "declined", "in_progress", "under_review"}

    if new_status in buyer_only and not is_buyer:
        return {"error": f"Only the buyer can set {new_status}"}
    if new_status in provider_only and not is_provider:
        return {"error": f"Only the provider can set {new_status}"}

    timeline_entry = {"status": new_status, "note": note or new_status, "at": _now(),
                      "by": "buyer" if is_buyer else "provider"}
    updates = {
        "status": new_status,
        "updated_at": _now(),
        "$push": {"timeline": timeline_entry},
    }

    if new_status == "revision_requested":
        updates["$inc"] = {"revisions_used": 1}
    if new_status == "completed":
        updates["completed_at"] = _now()
        await db["mkt_providers"].update_one(
            {"user_id": order["provider_user_id"]}, {"$inc": {"completed_orders": 1}}
        )

    push_val = updates.pop("$push", None)
    await db["mkt_orders"].update_one({"_id": ObjectId(order_id)}, {"$set": updates})
    if push_val:
        await db["mkt_orders"].update_one({"_id": ObjectId(order_id)}, {"$push": push_val})

    return await get_order(order_id, db)


async def submit_deliverable(order_id: str, provider_user_id: str, data: dict, db) -> dict:
    order = await get_order(order_id, db)
    if not order:
        return {"error": "Order not found"}
    if order["provider_user_id"] != provider_user_id:
        return {"error": "Not authorized"}
    if order["status"] not in ("in_progress", "revision_requested"):
        return {"error": f"Cannot submit deliverable in status: {order['status']}"}

    deliverable = {
        "title": data.get("title", "Deliverable"),
        "description": data.get("description", ""),
        "file_url": data.get("file_url", ""),
        "submitted_at": _now(),
    }
    await db["mkt_orders"].update_one(
        {"_id": ObjectId(order_id)},
        {
            "$push": {"deliverables": deliverable},
            "$set": {"status": "under_review", "updated_at": _now()},
        }
    )
    await db["mkt_orders"].update_one(
        {"_id": ObjectId(order_id)},
        {"$push": {"timeline": {"status": "under_review", "note": "Deliverable submitted for review", "at": _now(), "by": "provider"}}}
    )
    return await get_order(order_id, db)


async def list_orders(user_id: str, db, role: str = "buyer",
                      status_filter: str = None, page: int = 1, limit: int = 20) -> dict:
    field = "buyer_user_id" if role == "buyer" else "provider_user_id"
    query = {field: user_id}
    if status_filter:
        query["status"] = status_filter
    skip = (page - 1) * limit
    cursor = db["mkt_orders"].find(query).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["mkt_orders"].count_documents(query)
    return {"results": [_s(d) for d in docs], "total": total, "page": page,
            "pages": max(1, -(-total // limit))}


async def add_revision_note(order_id: str, buyer_user_id: str, note: str, db) -> dict:
    order = await get_order(order_id, db)
    if not order or order["buyer_user_id"] != buyer_user_id:
        return {"error": "Not authorized"}
    await db["mkt_orders"].update_one(
        {"_id": ObjectId(order_id)},
        {"$push": {"revision_notes": {"note": note, "at": _now()}},
         "$set": {"updated_at": _now()}}
    )
    return await get_order(order_id, db)
