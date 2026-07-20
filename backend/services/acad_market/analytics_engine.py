"""Analytics for providers, buyers, and platform admin."""
import asyncio
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


async def get_provider_dashboard(provider_user_id: str, db) -> dict:
    (total_orders, pending_orders, active_orders, completed_orders,
     total_services, ratings, disputes, wallet) = await asyncio.gather(
        db["mkt_orders"].count_documents({"provider_user_id": provider_user_id}),
        db["mkt_orders"].count_documents({"provider_user_id": provider_user_id, "status": "pending"}),
        db["mkt_orders"].count_documents({"provider_user_id": provider_user_id,
                                          "status": {"$in": ["accepted", "in_progress", "under_review"]}}),
        db["mkt_orders"].count_documents({"provider_user_id": provider_user_id, "status": "completed"}),
        db["mkt_services"].count_documents({"provider_user_id": provider_user_id, "status": "active"}),
        db["mkt_ratings"].find({"provider_user_id": provider_user_id}).to_list(10000),
        db["mkt_disputes"].count_documents({"respondent_user_id": provider_user_id,
                                             "status": {"$nin": ["closed"]}}),
        db["mkt_wallet"].find_one({"user_id": provider_user_id}),
    )

    avg_rating = round(sum(r.get("overall", 0) for r in ratings) / len(ratings), 2) if ratings else 0
    success_rate = round(completed_orders / total_orders * 100, 1) if total_orders else 0

    recent_orders_cursor = db["mkt_orders"].find(
        {"provider_user_id": provider_user_id}
    ).sort("updated_at", -1).limit(5)
    recent_orders = await recent_orders_cursor.to_list(5)
    for o in recent_orders:
        o["id"] = str(o.pop("_id", ""))

    return {
        "orders": {
            "total": total_orders, "pending": pending_orders,
            "active": active_orders, "completed": completed_orders,
        },
        "services": {"active": total_services},
        "ratings": {"count": len(ratings), "average": avg_rating},
        "disputes": {"open": disputes},
        "success_rate": success_rate,
        "wallet": {
            "total_earned": (wallet or {}).get("total_earned", 0),
            "currency": (wallet or {}).get("currency", "USD"),
        },
        "recent_orders": recent_orders,
    }


async def get_buyer_dashboard(buyer_user_id: str, db) -> dict:
    (total_orders, active_orders, completed_orders,
     total_spent_agg, disputes) = await asyncio.gather(
        db["mkt_orders"].count_documents({"buyer_user_id": buyer_user_id}),
        db["mkt_orders"].count_documents({"buyer_user_id": buyer_user_id,
                                          "status": {"$in": ["pending", "accepted", "in_progress", "under_review"]}}),
        db["mkt_orders"].count_documents({"buyer_user_id": buyer_user_id, "status": "completed"}),
        db["mkt_orders"].aggregate([
            {"$match": {"buyer_user_id": buyer_user_id, "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$price"}}}
        ]).to_list(1),
        db["mkt_disputes"].count_documents({"claimant_user_id": buyer_user_id,
                                             "status": {"$nin": ["closed"]}}),
    )

    total_spent = total_spent_agg[0]["total"] if total_spent_agg else 0

    recent_orders_cursor = db["mkt_orders"].find(
        {"buyer_user_id": buyer_user_id}
    ).sort("updated_at", -1).limit(5)
    recent_orders = await recent_orders_cursor.to_list(5)
    for o in recent_orders:
        o["id"] = str(o.pop("_id", ""))

    return {
        "orders": {"total": total_orders, "active": active_orders, "completed": completed_orders},
        "total_spent": total_spent,
        "disputes": {"open": disputes},
        "recent_orders": recent_orders,
    }


async def get_platform_stats(db) -> dict:
    (total_providers, total_services, total_orders, completed_orders,
     open_disputes, active_users) = await asyncio.gather(
        db["mkt_providers"].count_documents({"active": True}),
        db["mkt_services"].count_documents({"status": "active"}),
        db["mkt_orders"].count_documents({}),
        db["mkt_orders"].count_documents({"status": "completed"}),
        db["mkt_disputes"].count_documents({"status": {"$nin": ["closed", "resolved_buyer",
                                                                 "resolved_provider", "resolved_mutual"]}}),
        db["mkt_orders"].distinct("buyer_user_id"),
    )

    revenue_agg = await db["mkt_orders"].aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$platform_fee"}, "gmv": {"$sum": "$price"}}}
    ]).to_list(1)

    revenue = revenue_agg[0] if revenue_agg else {"total": 0, "gmv": 0}

    categories_agg = await db["mkt_services"].aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]).to_list(10)

    return {
        "providers": total_providers,
        "services": total_services,
        "orders": {"total": total_orders, "completed": completed_orders,
                   "completion_rate": round(completed_orders / total_orders * 100, 1) if total_orders else 0},
        "disputes": {"open": open_disputes,
                     "rate": round(open_disputes / total_orders * 100, 2) if total_orders else 0},
        "buyers": len(active_users),
        "platform_revenue": round(revenue.get("total", 0), 2),
        "gmv": round(revenue.get("gmv", 0), 2),
        "top_categories": [{"category": c["_id"], "count": c["count"]} for c in categories_agg],
    }


async def get_service_analytics(service_id: str, provider_user_id: str, db) -> dict:
    try:
        service = await db["mkt_services"].find_one({"_id": ObjectId(service_id)})
    except Exception:
        return {"error": "Invalid service"}
    if not service or service.get("provider_user_id") != provider_user_id:
        return {"error": "Not authorized"}

    (orders, ratings, revenue_agg) = await asyncio.gather(
        db["mkt_orders"].count_documents({"service_id": service_id}),
        db["mkt_ratings"].find({"service_id": service_id}).to_list(10000),
        db["mkt_orders"].aggregate([
            {"$match": {"service_id": service_id, "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$provider_payout"}}}
        ]).to_list(1),
    )

    avg_rating = round(sum(r.get("overall", 0) for r in ratings) / len(ratings), 2) if ratings else 0
    revenue = revenue_agg[0]["total"] if revenue_agg else 0

    return {
        "service_id": service_id,
        "title": service.get("title", ""),
        "views": service.get("view_count", 0),
        "orders": orders,
        "conversion_rate": round(orders / service.get("view_count", 1) * 100, 2) if service.get("view_count") else 0,
        "rating": avg_rating,
        "rating_count": len(ratings),
        "revenue": round(revenue, 2),
    }
