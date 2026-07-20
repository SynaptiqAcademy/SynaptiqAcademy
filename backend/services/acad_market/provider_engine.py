"""Provider profiles, portfolios, verification for the Academic Services Marketplace."""
import asyncio
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


SERVICE_CATEGORIES = [
    "statistical_analysis", "research_methodology", "experimental_design",
    "survey_design", "data_collection", "data_cleaning", "data_visualization",
    "systematic_review", "scoping_review", "meta_analysis",
    "scientific_writing", "academic_editing", "proofreading", "translation",
    "journal_selection", "conference_selection",
    "grant_writing", "grant_review", "peer_review", "reviewer_simulation",
    "research_consulting", "teaching_consulting", "curriculum_design", "course_development",
    "presentation_design", "scientific_illustration", "poster_design",
    "research_software", "programming", "machine_learning", "artificial_intelligence",
    "bibliometric_analysis", "patent_consulting", "research_ethics", "open_science",
    "data_management", "research_impact", "citation_strategy",
    "academic_career_coaching", "mentorship", "institution_consulting", "custom_service",
]

VERIFICATION_TIERS = {0: "Unverified", 1: "Email Verified", 2: "ID Verified",
                      3: "Institution Verified", 4: "Expert Verified", 5: "Elite"}


async def create_provider_profile(user_id: str, data: dict, db) -> dict:
    existing = await db["mkt_providers"].find_one({"user_id": user_id})
    if existing:
        return _s(existing)

    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)},
                                          {"name": 1, "institution": 1, "country": 1,
                                           "research_interests": 1, "expertise": 1,
                                           "career_stage": 1, "trust_score": 1,
                                           "verification_level": 1})
    except Exception:
        user = {}

    profile = {
        "user_id": user_id,
        "display_name": data.get("display_name") or (user or {}).get("name", ""),
        "headline": data.get("headline", ""),
        "bio": data.get("bio", ""),
        "categories": data.get("categories", []),
        "expertise_tags": data.get("expertise_tags", []),
        "languages": data.get("languages", ["English"]),
        "institution": data.get("institution") or (user or {}).get("institution", ""),
        "country": data.get("country") or (user or {}).get("country", ""),
        "availability": data.get("availability", "available"),
        "response_time_hours": data.get("response_time_hours", 24),
        "hourly_rate": data.get("hourly_rate", 0),
        "currency": data.get("currency", "USD"),
        "verification_level": int((user or {}).get("verification_level", 0)),
        "trust_score": float((user or {}).get("trust_score", 0)),
        "completed_orders": 0,
        "success_rate": 0.0,
        "average_rating": 0.0,
        "rating_count": 0,
        "total_earned": 0.0,
        "badges": [],
        "certifications": data.get("certifications", []),
        "active": True,
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db["mkt_providers"].insert_one(profile)
    profile["id"] = str(r.inserted_id)
    profile.pop("_id", None)
    return profile


async def get_provider_by_user(user_id: str, db) -> dict | None:
    doc = await db["mkt_providers"].find_one({"user_id": user_id})
    return _s(doc)


async def get_provider(provider_id: str, db) -> dict | None:
    try:
        doc = await db["mkt_providers"].find_one({"_id": ObjectId(provider_id)})
    except Exception:
        return None
    return _s(doc)


async def update_provider_profile(user_id: str, data: dict, db) -> dict | None:
    for key in ("user_id", "_id", "completed_orders", "success_rate",
                "average_rating", "rating_count", "total_earned"):
        data.pop(key, None)
    data["updated_at"] = _now()
    await db["mkt_providers"].update_one({"user_id": user_id}, {"$set": data})
    return await get_provider_by_user(user_id, db)


async def search_providers(db, filters: dict, page: int = 1, limit: int = 20) -> dict:
    query = {"active": True}
    if q := filters.get("q"):
        query["$or"] = [
            {"display_name": {"$regex": q, "$options": "i"}},
            {"headline": {"$regex": q, "$options": "i"}},
            {"bio": {"$regex": q, "$options": "i"}},
            {"expertise_tags": {"$regex": q, "$options": "i"}},
        ]
    if cat := filters.get("category"):
        query["categories"] = cat
    if lang := filters.get("language"):
        query["languages"] = lang
    if country := filters.get("country"):
        query["country"] = {"$regex": country, "$options": "i"}
    if avail := filters.get("availability"):
        query["availability"] = avail
    if min_rating := filters.get("min_rating"):
        query["average_rating"] = {"$gte": float(min_rating)}
    if min_trust := filters.get("min_trust_score"):
        query["trust_score"] = {"$gte": float(min_trust)}

    sort_field = filters.get("sort", "average_rating")
    sort_map = {"rating": "average_rating", "trust": "trust_score",
                "completed": "completed_orders", "recent": "created_at",
                "average_rating": "average_rating"}
    sort = sort_map.get(sort_field, "average_rating")

    skip = (page - 1) * limit
    cursor = db["mkt_providers"].find(query).sort(sort, -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["mkt_providers"].count_documents(query)
    return {"results": [_s(d) for d in docs], "total": total, "page": page,
            "pages": max(1, -(-total // limit))}


async def get_portfolio(user_id: str, db) -> dict:
    provider = await get_provider_by_user(user_id, db)
    if not provider:
        return {"error": "Provider not found"}

    portfolio_items, completed_orders, reviews = await asyncio.gather(
        db["mkt_portfolio_items"].find({"user_id": user_id}).sort("created_at", -1).limit(20).to_list(20),
        db["mkt_orders"].count_documents({"provider_user_id": user_id, "status": "completed"}),
        db["mkt_ratings"].find({"provider_user_id": user_id}).sort("created_at", -1).limit(5).to_list(5),
    )
    return {
        "provider": provider,
        "portfolio_items": [_s(p) for p in portfolio_items],
        "completed_orders": completed_orders,
        "recent_reviews": [_s(r) for r in reviews],
    }


async def add_portfolio_item(user_id: str, data: dict, db) -> dict:
    item = {
        "user_id": user_id,
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "category": data.get("category", ""),
        "type": data.get("type", "case_study"),
        "link": data.get("link", ""),
        "tags": data.get("tags", []),
        "created_at": _now(),
    }
    r = await db["mkt_portfolio_items"].insert_one(item)
    item["id"] = str(r.inserted_id)
    item.pop("_id", None)
    return item


async def delete_portfolio_item(item_id: str, user_id: str, db) -> bool:
    try:
        r = await db["mkt_portfolio_items"].delete_one(
            {"_id": ObjectId(item_id), "user_id": user_id}
        )
        return bool(r.deleted_count)
    except Exception:
        return False


async def update_provider_stats(provider_user_id: str, db):
    """Recompute aggregate stats from live order/rating data."""
    completed = await db["mkt_orders"].count_documents(
        {"provider_user_id": provider_user_id, "status": "completed"}
    )
    total_orders = await db["mkt_orders"].count_documents(
        {"provider_user_id": provider_user_id, "status": {"$in": ["completed", "cancelled"]}}
    )
    success_rate = round(completed / total_orders * 100, 1) if total_orders else 0.0

    ratings_cursor = db["mkt_ratings"].find({"provider_user_id": provider_user_id})
    ratings = await ratings_cursor.to_list(1000)
    if ratings:
        avg = sum(r.get("overall", 0) for r in ratings) / len(ratings)
        average_rating = round(avg, 2)
        rating_count = len(ratings)
    else:
        average_rating = 0.0
        rating_count = 0

    total_earned_pipeline = [
        {"$match": {"provider_user_id": provider_user_id, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$provider_payout"}}}
    ]
    earned_agg = await db["mkt_orders"].aggregate(total_earned_pipeline).to_list(1)
    total_earned = earned_agg[0]["total"] if earned_agg else 0.0

    await db["mkt_providers"].update_one(
        {"user_id": provider_user_id},
        {"$set": {
            "completed_orders": completed,
            "success_rate": success_rate,
            "average_rating": average_rating,
            "rating_count": rating_count,
            "total_earned": total_earned,
            "updated_at": _now(),
        }}
    )
