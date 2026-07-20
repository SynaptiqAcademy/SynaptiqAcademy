import asyncio
from datetime import datetime, timezone
from bson import ObjectId


def _s(v):
    return str(v) if v is not None else None


async def get_or_create_reviewer_profile(user_id: str, db) -> dict:
    existing = await db["reviewer_profiles"].find_one({"user_id": user_id})
    if existing:
        existing["_id"] = _s(existing["_id"])
        return existing

    user = await db["users"].find_one({"_id": ObjectId(user_id)}) or {}
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "reviewer_status": "active",
        "reviewer_level": 1,
        "verified_reviewer": False,
        "reviewer_score": 0.0,
        "reviews_completed": 0,
        "average_rating": 0.0,
        "acceptance_rate": 0.0,
        "response_rate": 0.0,
        "on_time_rate": 0.0,
        "research_areas": user.get("research_interests") or [],
        "methods_expertise": [],
        "languages": ["English"],
        "institution": user.get("institution", ""),
        "country": user.get("country", ""),
        "availability_status": "available",
        "created_at": now,
        "updated_at": now,
    }
    result = await db["reviewer_profiles"].insert_one(doc)
    doc["_id"] = _s(result.inserted_id)
    return doc


async def update_reviewer_profile(user_id: str, updates: dict, db) -> dict:
    allowed_fields = {
        "research_areas",
        "methods_expertise",
        "languages",
        "availability_status",
        "country",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    filtered["updated_at"] = datetime.now(timezone.utc)

    await db["reviewer_profiles"].update_one(
        {"user_id": user_id},
        {"$set": filtered},
        upsert=True,
    )
    doc = await db["reviewer_profiles"].find_one({"user_id": user_id})
    if doc:
        doc["_id"] = _s(doc["_id"])
    return doc or {}


async def compute_reviewer_score(user_id: str, db) -> float:
    async def _get_profile_field(field):
        doc = await db["reviewer_profiles"].find_one(
            {"user_id": user_id}, {field: 1}
        )
        return (doc or {}).get(field, 0) or 0

    async def _get_sis():
        doc = await db["research_impact"].find_one({"user_id": user_id})
        return (doc or {}).get("sis_total", 0) or 0

    async def _get_pub_count():
        return await db["publications"].count_documents({"user_id": user_id})

    async def _get_reputation_score():
        doc = await db["research_reputation"].find_one({"user_id": user_id})
        return (doc or {}).get("overall_score", 0) or 0

    (
        reviews_completed,
        average_rating,
        on_time_rate,
        sis_total,
        pub_count,
        reputation_score,
    ) = await asyncio.gather(
        _get_profile_field("reviews_completed"),
        _get_profile_field("average_rating"),
        _get_profile_field("on_time_rate"),
        _get_sis(),
        _get_pub_count(),
        _get_reputation_score(),
    )

    review_activity = min(30, reviews_completed * 2)
    quality_component = average_rating * 6
    timeliness = on_time_rate * 10
    if sis_total:
        academic_standing = min(20, (sis_total / 10000) * 20)
    else:
        academic_standing = min(20, (reputation_score / 100) * 20)
    publication_contribution = min(10, pub_count)

    total = (
        review_activity
        + quality_component
        + timeliness
        + academic_standing
        + publication_contribution
    )
    total = round(min(100.0, max(0.0, total)), 2)

    if total < 20:
        level = 1
    elif total < 40:
        level = 2
    elif total < 60:
        level = 3
    elif total < 80:
        level = 4
    else:
        level = 5

    await db["reviewer_profiles"].update_one(
        {"user_id": user_id},
        {
            "$set": {
                "reviewer_score": total,
                "reviewer_level": level,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    return total


async def list_reviewers(
    db, filters: dict = None, page: int = 1, limit: int = 20
) -> dict:
    filters = filters or {}
    query = {}

    if filters.get("research_area"):
        query["research_areas"] = {"$in": [filters["research_area"]]}
    if filters.get("country"):
        query["country"] = filters["country"]
    if filters.get("methods_expertise"):
        query["methods_expertise"] = {"$in": [filters["methods_expertise"]]}
    if filters.get("availability_status"):
        query["availability_status"] = filters["availability_status"]
    if filters.get("reviewer_level") is not None:
        query["reviewer_level"] = filters["reviewer_level"]
    if filters.get("min_rating") is not None:
        query["average_rating"] = {"$gte": filters["min_rating"]}
    if filters.get("verified_reviewer") is not None:
        query["verified_reviewer"] = filters["verified_reviewer"]

    skip = (page - 1) * limit
    total = await db["reviewer_profiles"].count_documents(query)
    cursor = (
        db["reviewer_profiles"]
        .find(query)
        .sort("reviewer_score", -1)
        .skip(skip)
        .limit(limit)
    )
    profiles = await cursor.to_list(length=limit)

    items = []
    for profile in profiles:
        uid = profile.get("user_id")
        user = {}
        pub_profile = {}
        if uid:
            user = await db["users"].find_one({"_id": ObjectId(uid)}) or {}
            pub_profile = await db["public_profiles"].find_one({"user_id": uid}) or {}

        item = {
            "_id": _s(profile.get("_id")),
            "user_id": uid,
            "full_name": user.get("full_name", ""),
            "avatar_url": user.get("avatar_url", ""),
            "institution": user.get("institution", profile.get("institution", "")),
            "slug": pub_profile.get("slug", ""),
            "reviewer_score": profile.get("reviewer_score", 0),
            "reviewer_level": profile.get("reviewer_level", 1),
            "verified_reviewer": profile.get("verified_reviewer", False),
            "average_rating": profile.get("average_rating", 0),
            "reviews_completed": profile.get("reviews_completed", 0),
            "research_areas": profile.get("research_areas", []),
            "methods_expertise": profile.get("methods_expertise", []),
            "availability_status": profile.get("availability_status", "available"),
            "country": profile.get("country", ""),
        }
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }


async def get_reviewer_public_profile(user_id: str, db) -> dict:
    profile = await db["reviewer_profiles"].find_one({"user_id": user_id}) or {}
    if profile:
        profile["_id"] = _s(profile["_id"])

    user = await db["users"].find_one({"_id": ObjectId(user_id)}) or {}
    impact = await db["research_impact"].find_one({"user_id": user_id}) or {}
    reputation = await db["research_reputation"].find_one({"user_id": user_id}) or {}
    certifications_cursor = db["reviewer_certifications"].find({"user_id": user_id})
    certifications = await certifications_cursor.to_list(length=100)
    for cert in certifications:
        cert["_id"] = _s(cert["_id"])

    completed_reviews_count = await db["review_assignments"].count_documents(
        {"reviewer_user_id": user_id, "status": "completed"}
    )

    user_info = {
        "full_name": user.get("full_name", ""),
        "avatar_url": user.get("avatar_url", ""),
        "institution": user.get("institution", ""),
        "country": user.get("country", ""),
        "bio": user.get("bio", ""),
    }

    return {
        "reviewer_profile": profile,
        "user_info": user_info,
        "impact": {
            "sis_total": impact.get("sis_total", 0),
            "h_index": impact.get("h_index", 0),
        },
        "reputation": {
            "overall_score": reputation.get("overall_score", 0),
            "level": reputation.get("level", 1),
        },
        "certifications": certifications,
        "completed_reviews_count": completed_reviews_count,
    }


async def award_certification(user_id: str, cert_type: str, db) -> dict:
    valid_cert_types = {
        "verified_reviewer",
        "methodology_expert",
        "stats_expert",
        "grant_reviewer",
        "journal_reviewer",
        "conference_reviewer",
        "top_10_percent",
        "elite_reviewer",
    }
    if cert_type not in valid_cert_types:
        raise ValueError(f"Invalid cert_type '{cert_type}'. Must be one of: {sorted(valid_cert_types)}")

    existing = await db["reviewer_certifications"].find_one(
        {"user_id": user_id, "cert_type": cert_type}
    )
    if existing:
        existing["_id"] = _s(existing["_id"])
        return existing

    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "cert_type": cert_type,
        "awarded_at": now,
    }
    result = await db["reviewer_certifications"].insert_one(doc)
    doc["_id"] = _s(result.inserted_id)

    if cert_type == "verified_reviewer":
        await db["reviewer_profiles"].update_one(
            {"user_id": user_id},
            {"$set": {"verified_reviewer": True, "updated_at": now}},
        )

    return doc
