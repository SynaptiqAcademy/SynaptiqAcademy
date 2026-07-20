"""Mentorship platform — mentor profiles, requests, matching, tracking."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


EXPERTISE_AREAS = [
    "publication_coaching", "grant_writing", "career_planning",
    "peer_review", "statistical_methods", "research_design",
    "teaching", "industry_transition", "leadership", "funding",
]


# ── Mentor profiles ──────────────────────────────────────────────────────────

async def create_mentor_profile(user_id: str, data: dict, db) -> dict:
    existing = await db["network_mentors"].find_one({"user_id": user_id})
    if existing:
        return _s(existing)

    profile = {
        "user_id": user_id,
        "bio": data.get("bio", ""),
        "expertise_areas": data.get("expertise_areas", []),
        "availability": data.get("availability", "limited"),
        "max_mentees": data.get("max_mentees", 3),
        "current_mentees": 0,
        "career_stage": data.get("career_stage", ""),
        "institution": data.get("institution", ""),
        "languages": data.get("languages", ["English"]),
        "preferences": data.get("preferences", {}),
        "rating": 0.0,
        "rating_count": 0,
        "active": True,
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db["network_mentors"].insert_one(profile)
    profile["id"] = str(r.inserted_id)
    profile.pop("_id", None)
    return profile


async def get_mentor_profile(user_id: str, db) -> dict | None:
    doc = await db["network_mentors"].find_one({"user_id": user_id})
    return _s(doc)


async def update_mentor_profile(user_id: str, data: dict, db) -> dict | None:
    data["updated_at"] = _now()
    await db["network_mentors"].update_one({"user_id": user_id}, {"$set": data})
    return await get_mentor_profile(user_id, db)


async def list_mentors(db, filters: dict, user_id: str, page: int = 1, limit: int = 20) -> dict:
    query = {"active": True}

    if q := filters.get("q"):
        query["$or"] = [
            {"bio": {"$regex": q, "$options": "i"}},
            {"expertise_areas": {"$regex": q, "$options": "i"}},
        ]
    if ea := filters.get("expertise_area"):
        query["expertise_areas"] = ea
    if av := filters.get("availability"):
        query["availability"] = av

    skip = (page - 1) * limit
    cursor = db["network_mentors"].find(query).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["network_mentors"].count_documents(query)

    uid_list = [d["user_id"] for d in docs]
    users = {}
    if uid_list:
        try:
            oids = [ObjectId(u) for u in uid_list]
            cur2 = db["users"].find(
                {"_id": {"$in": oids}},
                {"name": 1, "institution": 1, "country": 1, "career_stage": 1, "profile_picture": 1}
            )
            for u in await cur2.to_list(len(oids)):
                users[str(u["_id"])] = u
        except Exception:
            pass

    results = []
    for d in docs:
        md = _s(d)
        if u := users.get(md.get("user_id", "")):
            md["name"] = u.get("name", "")
            md["institution"] = u.get("institution", "")
            md["country"] = u.get("country", "")
        results.append(md)

    return {"results": results, "total": total, "page": page, "pages": max(1, -(-total // limit))}


# ── Mentorship requests ──────────────────────────────────────────────────────

async def create_mentorship_request(mentee_id: str, mentor_user_id: str, data: dict, db) -> dict:
    existing = await db["network_mentorship_requests"].find_one({
        "mentee_id": mentee_id, "mentor_user_id": mentor_user_id, "status": "pending"
    })
    if existing:
        return _s(existing)

    req = {
        "mentee_id": mentee_id,
        "mentor_user_id": mentor_user_id,
        "message": data.get("message", ""),
        "goals": data.get("goals", []),
        "duration_months": data.get("duration_months", 6),
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db["network_mentorship_requests"].insert_one(req)
    req["id"] = str(r.inserted_id)
    req.pop("_id", None)
    return req


async def get_my_requests(user_id: str, db, role: str = "mentee") -> list:
    field = "mentee_id" if role == "mentee" else "mentor_user_id"
    cursor = db["network_mentorship_requests"].find({field: user_id}).sort("created_at", -1).limit(50)
    docs = await cursor.to_list(50)
    return [_s(d) for d in docs]


async def respond_to_request(request_id: str, mentor_user_id: str, status: str, db) -> dict | None:
    try:
        oid = ObjectId(request_id)
    except Exception:
        return None
    updates = {"status": status, "updated_at": _now()}
    if status == "accepted":
        updates["matched_at"] = _now()
    await db["network_mentorship_requests"].update_one(
        {"_id": oid, "mentor_user_id": mentor_user_id}, {"$set": updates}
    )
    doc = await db["network_mentorship_requests"].find_one({"_id": oid})
    return _s(doc)


async def rate_mentor(user_id: str, mentor_user_id: str, rating: float, db) -> dict:
    mentor = await db["network_mentors"].find_one({"user_id": mentor_user_id})
    if not mentor:
        return {"error": "Mentor not found"}
    old_rating = mentor.get("rating", 0.0)
    old_count = mentor.get("rating_count", 0)
    new_count = old_count + 1
    new_rating = (old_rating * old_count + rating) / new_count
    await db["network_mentors"].update_one(
        {"user_id": mentor_user_id},
        {"$set": {"rating": round(new_rating, 2), "rating_count": new_count, "updated_at": _now()}}
    )
    return {"rating": round(new_rating, 2), "rating_count": new_count}
