import asyncio
import ast
from bson import ObjectId

from services.reviewer_marketplace.conflict_detection import has_conflict


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


async def match_reviewers_for_request(request_id: str, db, limit: int = 10) -> list:
    request = await db["review_requests"].find_one({"_id": ObjectId(request_id)})
    if not request:
        return []

    requester_user_id = request.get("requester_user_id", "")
    request_research_area = request.get("research_area", "")
    required_expertise = request.get("required_expertise") or []
    methodology = request.get("methodology", "")

    request_terms = set(
        [t.lower() for t in required_expertise if t]
        + ([request_research_area.lower()] if request_research_area else [])
        + ([methodology.lower()] if methodology else [])
    )

    requester_user = await db["users"].find_one({"_id": ObjectId(requester_user_id)}) if requester_user_id else {}
    requester_country = (requester_user or {}).get("country", "")

    query = {
        "availability_status": {"$ne": "unavailable"},
    }
    if requester_user_id:
        query["user_id"] = {"$ne": requester_user_id}

    cursor = db["reviewer_profiles"].find(query).sort("reviewer_score", -1).limit(50)
    candidates = await cursor.to_list(length=50)

    scored = []
    for profile in candidates:
        uid = profile.get("user_id", "")

        reviewer_terms = set(
            [a.lower() for a in (profile.get("research_areas") or []) if a]
            + [m.lower() for m in (profile.get("methods_expertise") or []) if m]
        )
        area_score = _jaccard(request_terms, reviewer_terms) * 40

        reviewer_score_val = profile.get("reviewer_score", 0) or 0
        quality_score = (reviewer_score_val / 100) * 30

        avail = profile.get("availability_status", "available")
        if avail == "available":
            availability_score = 15
        elif avail == "busy":
            availability_score = 8
        else:
            availability_score = 0

        reviewer_country = profile.get("country", "")
        diversity_score = 15 if (reviewer_country and reviewer_country != requester_country) else 5

        total_match_score = area_score + quality_score + availability_score + diversity_score

        scored.append({
            "_profile": profile,
            "reviewer_user_id": uid,
            "reviewer_score": reviewer_score_val,
            "total_match_score": round(total_match_score, 2),
            "area_score": round(area_score, 2),
            "quality_score": round(quality_score, 2),
            "availability_score": availability_score,
            "diversity_score": diversity_score,
        })

    scored.sort(key=lambda x: x["total_match_score"], reverse=True)

    results = []
    for entry in scored:
        if len(results) >= limit:
            break
        uid = entry["reviewer_user_id"]
        conflict = await has_conflict(request_id, uid, db)
        if conflict:
            continue

        user = await db["users"].find_one({"_id": ObjectId(uid)}) if uid else {}
        pub_profile = await db["public_profiles"].find_one({"user_id": uid}) if uid else {}

        results.append({
            "reviewer_user_id": uid,
            "full_name": (user or {}).get("full_name", ""),
            "avatar_url": (user or {}).get("avatar_url", ""),
            "institution": (user or {}).get("institution", ""),
            "reviewer_score": entry["reviewer_score"],
            "total_match_score": entry["total_match_score"],
            "area_score": entry["area_score"],
            "quality_score": entry["quality_score"],
            "slug": (pub_profile or {}).get("slug", ""),
        })

    await db["review_requests"].update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"review_matches": results}},
    )

    return results
