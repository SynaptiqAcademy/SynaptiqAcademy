"""Service listings — CRUD, packages, FAQs, AI quality estimate."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


PACKAGE_TIERS = ("basic", "standard", "premium")


async def create_service(provider_user_id: str, data: dict, db) -> dict:
    provider = await db["mkt_providers"].find_one({"user_id": provider_user_id})
    if not provider:
        return {"error": "Create a provider profile first"}

    service = {
        "provider_user_id": provider_user_id,
        "provider_id": str(provider["_id"]),
        "title": data["title"],
        "description": data.get("description", ""),
        "category": data.get("category", "custom_service"),
        "tags": data.get("tags", []),
        "methodology": data.get("methodology", ""),
        "deliverables": data.get("deliverables", []),
        "languages": data.get("languages", ["English"]),
        "packages": data.get("packages", []),
        "faqs": data.get("faqs", []),
        "sample_output": data.get("sample_output", ""),
        "requirements_from_client": data.get("requirements_from_client", ""),
        "status": "active",
        "order_count": 0,
        "view_count": 0,
        "average_rating": 0.0,
        "rating_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db["mkt_services"].insert_one(service)
    service["id"] = str(r.inserted_id)
    service.pop("_id", None)
    return service


async def get_service(service_id: str, db) -> dict | None:
    try:
        doc = await db["mkt_services"].find_one({"_id": ObjectId(service_id)})
    except Exception:
        return None
    if doc:
        await db["mkt_services"].update_one({"_id": doc["_id"]}, {"$inc": {"view_count": 1}})
    return _s(doc)


async def list_services(db, filters: dict, page: int = 1, limit: int = 20) -> dict:
    query = {"status": "active"}
    if q := filters.get("q"):
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]
    if cat := filters.get("category"):
        query["category"] = cat
    if lang := filters.get("language"):
        query["languages"] = lang
    if max_price := filters.get("max_price"):
        query["packages"] = {"$elemMatch": {"price": {"$lte": float(max_price)}}}

    sort_map = {"rating": ("average_rating", -1), "popular": ("order_count", -1),
                "newest": ("created_at", -1), "price_asc": ("packages.0.price", 1)}
    sort_key, sort_dir = sort_map.get(filters.get("sort", "rating"), ("average_rating", -1))

    skip = (page - 1) * limit
    cursor = db["mkt_services"].find(query).sort(sort_key, sort_dir).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["mkt_services"].count_documents(query)

    # Enrich with provider info
    uid_list = [d.get("provider_user_id") for d in docs if d.get("provider_user_id")]
    providers = {}
    if uid_list:
        try:
            oids = [ObjectId(u) for u in uid_list]
            prov_cursor = db["mkt_providers"].find(
                {"user_id": {"$in": uid_list}},
                {"user_id": 1, "display_name": 1, "average_rating": 1,
                 "completed_orders": 1, "trust_score": 1, "verification_level": 1}
            )
            for p in await prov_cursor.to_list(len(uid_list)):
                providers[p["user_id"]] = p
        except Exception:
            pass

    results = []
    for d in docs:
        sd = _s(d)
        if prov := providers.get(sd.get("provider_user_id", "")):
            prov.pop("_id", None)
            sd["provider"] = prov
        results.append(sd)

    return {"results": results, "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def update_service(service_id: str, provider_user_id: str, data: dict, db) -> dict | None:
    try:
        oid = ObjectId(service_id)
    except Exception:
        return None
    for key in ("provider_user_id", "_id", "order_count", "view_count",
                "average_rating", "rating_count", "created_at"):
        data.pop(key, None)
    data["updated_at"] = _now()
    await db["mkt_services"].update_one(
        {"_id": oid, "provider_user_id": provider_user_id}, {"$set": data}
    )
    return await get_service(service_id, db)


async def delete_service(service_id: str, provider_user_id: str, db) -> bool:
    try:
        r = await db["mkt_services"].update_one(
            {"_id": ObjectId(service_id), "provider_user_id": provider_user_id},
            {"$set": {"status": "deleted", "updated_at": _now()}}
        )
        return bool(r.modified_count)
    except Exception:
        return False


async def get_my_services(provider_user_id: str, db) -> list:
    cursor = db["mkt_services"].find(
        {"provider_user_id": provider_user_id, "status": {"$ne": "deleted"}}
    ).sort("created_at", -1).limit(50)
    docs = await cursor.to_list(50)
    return [_s(d) for d in docs]


def estimate_service_quality(service: dict, provider: dict) -> dict:
    """Rule-based quality estimate — no LLM calls."""
    score = 50
    reasons = []

    if len(service.get("description", "")) > 200:
        score += 10
        reasons.append("Detailed service description")
    if service.get("methodology"):
        score += 10
        reasons.append("Methodology documented")
    if len(service.get("deliverables", [])) >= 3:
        score += 8
        reasons.append("Clear deliverables listed")
    if len(service.get("faqs", [])) >= 2:
        score += 5
        reasons.append("FAQ provided")
    if len(service.get("packages", [])) >= 2:
        score += 5
        reasons.append("Multiple packages available")

    trust = provider.get("trust_score", 0)
    if trust >= 800:
        score += 15
        reasons.append("Elite trust score")
    elif trust >= 600:
        score += 10
        reasons.append("High trust score")
    elif trust >= 400:
        score += 5

    verif = provider.get("verification_level", 0)
    if verif >= 4:
        score += 12
        reasons.append("Expert verified")
    elif verif >= 3:
        score += 8
        reasons.append("Institution verified")
    elif verif >= 2:
        score += 4

    rating = provider.get("average_rating", 0)
    if rating >= 4.8:
        score += 15
        reasons.append("Outstanding ratings")
    elif rating >= 4.5:
        score += 10
        reasons.append("Excellent ratings")
    elif rating >= 4.0:
        score += 5

    completed = provider.get("completed_orders", 0)
    if completed >= 50:
        score += 10
        reasons.append("Highly experienced")
    elif completed >= 20:
        score += 6
    elif completed >= 5:
        score += 3

    return {
        "quality_score": min(100, score),
        "quality_label": "Excellent" if score >= 85 else "Very Good" if score >= 70 else "Good" if score >= 55 else "Standard",
        "reasons": reasons,
    }
