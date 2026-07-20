"""Evidence-based rating system — 5-dimension reviews tied to completed orders."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


RATING_DIMENSIONS = ["communication", "quality", "expertise", "timeliness", "value"]


async def submit_rating(buyer_user_id: str, data: dict, db) -> dict:
    order_id = data.get("order_id", "")
    try:
        order = await db["mkt_orders"].find_one({"_id": ObjectId(order_id)})
    except Exception:
        return {"error": "Invalid order"}
    if not order:
        return {"error": "Order not found"}
    if order.get("buyer_user_id") != buyer_user_id:
        return {"error": "Only the buyer can rate"}
    if order.get("status") != "completed":
        return {"error": "Can only rate completed orders"}

    existing = await db["mkt_ratings"].find_one({"order_id": order_id, "buyer_user_id": buyer_user_id})
    if existing:
        return {"error": "Already rated this order"}

    dims = {d: max(1, min(5, int(data.get(d, 3)))) for d in RATING_DIMENSIONS}
    overall = round(sum(dims.values()) / len(dims), 2)

    rating = {
        "order_id": order_id,
        "service_id": order.get("service_id", ""),
        "buyer_user_id": buyer_user_id,
        "provider_user_id": order["provider_user_id"],
        **dims,
        "overall": overall,
        "review_text": data.get("review_text", "")[:2000],
        "would_recommend": bool(data.get("would_recommend", True)),
        "is_verified": True,
        "helpful_count": 0,
        "provider_response": None,
        "provider_responded_at": None,
        "created_at": _now(),
    }
    r = await db["mkt_ratings"].insert_one(rating)
    rating["id"] = str(r.inserted_id)
    rating.pop("_id", None)

    await _recompute_provider_rating(order["provider_user_id"], db)
    await _recompute_service_rating(order.get("service_id", ""), db)

    return rating


async def _recompute_provider_rating(provider_user_id: str, db):
    ratings = await db["mkt_ratings"].find(
        {"provider_user_id": provider_user_id}
    ).to_list(10000)
    if not ratings:
        return
    avg = sum(r.get("overall", 0) for r in ratings) / len(ratings)
    rec_rate = sum(1 for r in ratings if r.get("would_recommend")) / len(ratings) * 100
    await db["mkt_providers"].update_one(
        {"user_id": provider_user_id},
        {"$set": {"average_rating": round(avg, 2), "rating_count": len(ratings),
                  "recommendation_rate": round(rec_rate, 1)}}
    )


async def _recompute_service_rating(service_id: str, db):
    if not service_id:
        return
    try:
        ratings = await db["mkt_ratings"].find({"service_id": service_id}).to_list(10000)
        if not ratings:
            return
        avg = sum(r.get("overall", 0) for r in ratings) / len(ratings)
        await db["mkt_services"].update_one(
            {"_id": ObjectId(service_id)},
            {"$set": {"average_rating": round(avg, 2), "rating_count": len(ratings)}}
        )
    except Exception:
        pass


async def get_ratings_for_provider(provider_user_id: str, db,
                                    page: int = 1, limit: int = 10) -> dict:
    query = {"provider_user_id": provider_user_id, "is_verified": True}
    skip = (page - 1) * limit
    cursor = db["mkt_ratings"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["mkt_ratings"].count_documents(query)

    # Enrich with buyer name
    uid_list = list({d["buyer_user_id"] for d in docs if d.get("buyer_user_id")})
    buyers = {}
    for uid in uid_list:
        try:
            u = await db["users"].find_one({"_id": ObjectId(uid)}, {"name": 1})
            if u:
                buyers[uid] = u.get("name", "Anonymous")
        except Exception:
            pass

    results = []
    for d in docs:
        sd = _s(d)
        sd["buyer_name"] = buyers.get(sd.get("buyer_user_id", ""), "Verified Buyer")
        results.append(sd)

    return {"results": results, "total": total, "page": page,
            "pages": max(1, -(-total // limit))}


async def get_ratings_for_service(service_id: str, db,
                                   page: int = 1, limit: int = 10) -> dict:
    query = {"service_id": service_id, "is_verified": True}
    skip = (page - 1) * limit
    cursor = db["mkt_ratings"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["mkt_ratings"].count_documents(query)
    return {"results": [_s(d) for d in docs], "total": total, "page": page,
            "pages": max(1, -(-total // limit))}


async def provider_respond_to_rating(rating_id: str, provider_user_id: str,
                                      response: str, db) -> dict:
    try:
        doc = await db["mkt_ratings"].find_one({"_id": ObjectId(rating_id)})
    except Exception:
        return {"error": "Invalid rating"}
    if not doc:
        return {"error": "Rating not found"}
    if doc.get("provider_user_id") != provider_user_id:
        return {"error": "Not authorized"}
    await db["mkt_ratings"].update_one(
        {"_id": ObjectId(rating_id)},
        {"$set": {"provider_response": response[:1000], "provider_responded_at": _now()}}
    )
    doc = await db["mkt_ratings"].find_one({"_id": ObjectId(rating_id)})
    return _s(doc)


async def mark_helpful(rating_id: str, db) -> dict:
    try:
        await db["mkt_ratings"].update_one(
            {"_id": ObjectId(rating_id)}, {"$inc": {"helpful_count": 1}}
        )
        doc = await db["mkt_ratings"].find_one({"_id": ObjectId(rating_id)})
        return _s(doc) or {}
    except Exception:
        return {"error": "Invalid rating"}


async def get_rating_summary(provider_user_id: str, db) -> dict:
    ratings = await db["mkt_ratings"].find(
        {"provider_user_id": provider_user_id, "is_verified": True}
    ).to_list(10000)

    if not ratings:
        return {"overall": 0, "count": 0, "dimensions": {}, "distribution": {str(i): 0 for i in range(1, 6)}}

    distribution = {str(i): 0 for i in range(1, 6)}
    for r in ratings:
        star = str(round(r.get("overall", 3)))
        if star in distribution:
            distribution[star] += 1

    dim_avgs = {}
    for dim in RATING_DIMENSIONS:
        vals = [r.get(dim, 0) for r in ratings if r.get(dim)]
        dim_avgs[dim] = round(sum(vals) / len(vals), 2) if vals else 0

    overall = sum(r.get("overall", 0) for r in ratings) / len(ratings)
    rec = sum(1 for r in ratings if r.get("would_recommend")) / len(ratings) * 100

    return {
        "overall": round(overall, 2),
        "count": len(ratings),
        "recommendation_rate": round(rec, 1),
        "dimensions": dim_avgs,
        "distribution": distribution,
    }
