"""Rule-based service recommendations — no LLM calls."""
import asyncio
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _tokenise(text: str) -> set[str]:
    return set(text.lower().split()) if text else set()


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


async def generate_recommendations(user_id: str, db) -> list:
    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
    except Exception:
        return []
    if not user:
        return []

    user_tokens = _tokenise(" ".join([
        " ".join(user.get("research_interests", [])),
        " ".join(user.get("expertise", [])),
        user.get("academic_field", ""),
        user.get("department", ""),
    ]))

    category_pref = user.get("preferred_service_categories", [])

    (services_cursor_result, past_orders) = await asyncio.gather(
        db["mkt_services"].find({"status": "active"}).sort("average_rating", -1).limit(200).to_list(200),
        db["mkt_orders"].find({"buyer_user_id": user_id}).to_list(100),
    )

    ordered_service_ids = {o.get("service_id") for o in past_orders}

    scored = []
    for svc in services_cursor_result:
        svc_id = str(svc.get("_id", ""))
        if svc_id in ordered_service_ids:
            continue

        svc_tokens = _tokenise(" ".join([
            svc.get("title", ""),
            svc.get("description", ""),
            " ".join(svc.get("tags", [])),
        ]))

        relevance = _jaccard(user_tokens, svc_tokens)
        rating_boost = svc.get("average_rating", 0) * 0.1
        category_boost = 0.2 if svc.get("category") in category_pref else 0
        popularity_boost = min(0.1, svc.get("order_count", 0) * 0.005)

        total = relevance + rating_boost + category_boost + popularity_boost
        if total > 0:
            scored.append((total, svc_id, svc))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:20]

    recommendations = []
    for score, svc_id, svc in top:
        svc.pop("_id", None)
        recommendations.append({
            "service_id": svc_id,
            "title": svc.get("title", ""),
            "category": svc.get("category", ""),
            "provider_user_id": svc.get("provider_user_id", ""),
            "average_rating": svc.get("average_rating", 0),
            "rating_count": svc.get("rating_count", 0),
            "score": round(score, 4),
            "reason": _explain_recommendation(score, svc, user_tokens, category_pref),
        })

    await db["mkt_recommendations"].delete_many({"user_id": user_id})
    if recommendations:
        await db["mkt_recommendations"].insert_many([
            {"user_id": user_id, "created_at": _now(), **r} for r in recommendations
        ])
    return recommendations


def _explain_recommendation(score: float, svc: dict, user_tokens: set, category_pref: list) -> str:
    parts = []
    if svc.get("average_rating", 0) >= 4.5:
        parts.append("highly rated")
    if svc.get("category") in category_pref:
        parts.append("matches your preferred categories")
    svc_tokens = _tokenise(svc.get("title", "") + " " + " ".join(svc.get("tags", [])))
    shared = user_tokens & svc_tokens
    if shared:
        sample = ", ".join(list(shared)[:3])
        parts.append(f"relevant to {sample}")
    if svc.get("order_count", 0) > 10:
        parts.append("popular with researchers")
    return "; ".join(parts) if parts else "Recommended based on your profile"


async def get_recommendations(user_id: str, db, category: str = None) -> list:
    query = {"user_id": user_id}
    if category:
        query["category"] = category

    docs = await db["mkt_recommendations"].find(query).sort("score", -1).limit(20).to_list(20)
    if not docs:
        return await generate_recommendations(user_id, db)

    # Enrich with current service data
    results = []
    for doc in docs:
        doc.pop("_id", None)
        service_id = doc.get("service_id", "")
        if service_id:
            try:
                svc = await db["mkt_services"].find_one({"_id": ObjectId(service_id)})
                if svc and svc.get("status") == "active":
                    svc.pop("_id", None)
                    doc["service"] = svc
                    results.append(doc)
            except Exception:
                pass
    return results


async def dismiss_recommendation(user_id: str, service_id: str, db) -> bool:
    r = await db["mkt_recommendations"].delete_one(
        {"user_id": user_id, "service_id": service_id}
    )
    return bool(r.deleted_count)


async def get_trending_services(db, limit: int = 10) -> list:
    """Services with highest order velocity in the last 30 days."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$service_id", "recent_orders": {"$sum": 1}}},
        {"$sort": {"recent_orders": -1}},
        {"$limit": limit},
    ]
    trending_agg = await db["mkt_orders"].aggregate(pipeline).to_list(limit)

    results = []
    for item in trending_agg:
        svc_id = item["_id"]
        if not svc_id:
            continue
        try:
            svc = await db["mkt_services"].find_one({"_id": ObjectId(svc_id), "status": "active"})
            if svc:
                svc["id"] = str(svc.pop("_id", ""))
                svc["recent_orders"] = item["recent_orders"]
                results.append(svc)
        except Exception:
            pass
    return results


async def get_featured_providers(db, limit: int = 8) -> list:
    cursor = db["mkt_providers"].find(
        {"active": True, "completed_orders": {"$gte": 5}, "average_rating": {"$gte": 4.0}}
    ).sort("average_rating", -1).limit(limit)
    docs = await cursor.to_list(limit)
    for d in docs:
        d.pop("_id", None)
    return docs
