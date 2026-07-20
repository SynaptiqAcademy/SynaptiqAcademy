"""Open collaboration marketplace — post and apply for collaboration opportunities."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


COLLAB_TYPES = [
    "co_author", "statistician", "ai_specialist", "data_analyst",
    "reviewer", "translator", "supervisor", "institution_partner",
    "grant_partner", "educator", "research_assistant", "industry_expert",
    "software_engineer", "field_researcher", "clinical_specialist",
]


async def create_collaboration(user_id: str, data: dict, db) -> dict:
    collab = {
        "owner_id": user_id,
        "title": data["title"],
        "description": data.get("description", ""),
        "type": data.get("type", "co_author"),
        "discipline": data.get("discipline", ""),
        "skills_required": data.get("skills_required", []),
        "duration": data.get("duration", ""),
        "commitment": data.get("commitment", ""),
        "remote": data.get("remote", True),
        "compensation": data.get("compensation", "unpaid"),
        "deadline": data.get("deadline", ""),
        "slots": data.get("slots", 1),
        "applicant_count": 0,
        "status": "open",
        "tags": data.get("tags", []),
        "institution": data.get("institution", ""),
        "country": data.get("country", ""),
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db["network_collaborations"].insert_one(collab)
    collab["id"] = str(r.inserted_id)
    collab.pop("_id", None)
    return collab


async def list_collaborations(db, filters: dict, page: int = 1, limit: int = 20) -> dict:
    query = {"status": "open"}
    if q := filters.get("q"):
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"discipline": {"$regex": q, "$options": "i"}},
        ]
    if t := filters.get("type"):
        query["type"] = t
    if disc := filters.get("discipline"):
        query["discipline"] = {"$regex": disc, "$options": "i"}
    if remote := filters.get("remote"):
        query["remote"] = remote == "true"

    skip = (page - 1) * limit
    cursor = db["network_collaborations"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["network_collaborations"].count_documents(query)

    # Enrich with owner info
    oids = []
    for d in docs:
        try:
            oids.append(ObjectId(d.get("owner_id", "")))
        except Exception:
            pass
    owners = {}
    if oids:
        cur2 = db["users"].find(
            {"_id": {"$in": oids}},
            {"name": 1, "institution": 1, "career_stage": 1}
        )
        for u in await cur2.to_list(len(oids)):
            owners[str(u["_id"])] = u

    results = []
    for d in docs:
        cd = _s(d)
        if ow := owners.get(cd.get("owner_id", "")):
            cd["owner_name"] = ow.get("name", "")
            cd["owner_institution"] = ow.get("institution", "")
        results.append(cd)

    return {"results": results, "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def get_collaboration(collab_id: str, db) -> dict | None:
    try:
        doc = await db["network_collaborations"].find_one({"_id": ObjectId(collab_id)})
    except Exception:
        return None
    return _s(doc)


async def apply_to_collaboration(collab_id: str, user_id: str, data: dict, db) -> dict:
    collab = await get_collaboration(collab_id, db)
    if not collab:
        return {"error": "Not found"}
    if collab.get("owner_id") == user_id:
        return {"error": "Cannot apply to your own collaboration"}

    existing = await db["network_collaboration_applications"].find_one(
        {"collab_id": collab_id, "applicant_id": user_id}
    )
    if existing:
        return {"error": "Already applied"}

    application = {
        "collab_id": collab_id,
        "applicant_id": user_id,
        "message": data.get("message", ""),
        "cv_summary": data.get("cv_summary", ""),
        "skills": data.get("skills", []),
        "status": "pending",
        "created_at": _now(),
    }
    r = await db["network_collaboration_applications"].insert_one(application)
    await db["network_collaborations"].update_one(
        {"_id": ObjectId(collab_id)}, {"$inc": {"applicant_count": 1}}
    )
    application["id"] = str(r.inserted_id)
    application.pop("_id", None)
    return application


async def get_collaboration_applications(collab_id: str, owner_id: str, db) -> list:
    collab = await get_collaboration(collab_id, db)
    if not collab or collab.get("owner_id") != owner_id:
        return []
    cursor = db["network_collaboration_applications"].find(
        {"collab_id": collab_id}
    ).sort("created_at", -1).limit(50)
    docs = await cursor.to_list(50)
    return [_s(d) for d in docs]


async def respond_to_application(app_id: str, owner_id: str, status: str, db) -> dict | None:
    try:
        oid = ObjectId(app_id)
    except Exception:
        return None
    app = await db["network_collaboration_applications"].find_one({"_id": oid})
    if not app:
        return None
    collab = await get_collaboration(app["collab_id"], db)
    if not collab or collab.get("owner_id") != owner_id:
        return None
    await db["network_collaboration_applications"].update_one(
        {"_id": oid}, {"$set": {"status": status, "responded_at": _now()}}
    )
    doc = await db["network_collaboration_applications"].find_one({"_id": oid})
    return _s(doc)


async def get_my_collaborations(user_id: str, db) -> dict:
    owned = await db["network_collaborations"].find({"owner_id": user_id}).sort("created_at", -1).limit(20).to_list(20)
    applied_raw = await db["network_collaboration_applications"].find(
        {"applicant_id": user_id}
    ).sort("created_at", -1).limit(20).to_list(20)
    return {
        "owned": [_s(d) for d in owned],
        "applied": [_s(d) for d in applied_raw],
    }


async def close_collaboration(collab_id: str, owner_id: str, db) -> bool:
    try:
        oid = ObjectId(collab_id)
    except Exception:
        return False
    r = await db["network_collaborations"].update_one(
        {"_id": oid, "owner_id": owner_id},
        {"$set": {"status": "closed", "updated_at": _now()}}
    )
    return bool(r.modified_count)
