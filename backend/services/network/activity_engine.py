"""Professional activity feed — academic events only, no vanity metrics."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


ACTIVITY_TYPES = [
    "publication_added", "grant_awarded", "collaboration_started",
    "conference_accepted", "review_completed", "project_launched",
    "community_announcement", "group_created", "event_created",
    "mentorship_started", "collaboration_opportunity", "open_access_published",
    "dataset_released", "award_received", "position_started",
]


async def post_activity(user_id: str, activity_type: str, data: dict, db) -> dict:
    activity = {
        "user_id": user_id,
        "type": activity_type,
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "link": data.get("link", ""),
        "metadata": data.get("metadata", {}),
        "visibility": data.get("visibility", "public"),
        "created_at": _now(),
    }
    r = await db["network_activity"].insert_one(activity)
    activity["id"] = str(r.inserted_id)
    activity.pop("_id", None)
    return activity


async def get_feed(db, user_id: str, page: int = 1, limit: int = 30) -> dict:
    """Return activity feed — prioritized by academic relevance, not engagement."""
    PRIORITY_TYPES = {
        "publication_added": 10, "grant_awarded": 10, "open_access_published": 9,
        "conference_accepted": 8, "collaboration_started": 8, "dataset_released": 7,
        "award_received": 9, "project_launched": 7, "review_completed": 6,
        "mentorship_started": 6, "community_announcement": 5, "group_created": 4,
        "event_created": 4, "collaboration_opportunity": 7, "position_started": 6,
    }

    query = {"visibility": "public"}
    skip = (page - 1) * limit
    cursor = db["network_activity"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["network_activity"].count_documents(query)

    uid_list = [d.get("user_id") for d in docs if d.get("user_id")]
    users = {}
    if uid_list:
        try:
            oids = [ObjectId(u) for u in uid_list]
            cur2 = db["users"].find(
                {"_id": {"$in": oids}},
                {"name": 1, "institution": 1, "profile_picture": 1}
            )
            for u in await cur2.to_list(len(oids)):
                users[str(u["_id"])] = u
        except Exception:
            pass

    results = []
    for d in docs:
        ad = _s(d)
        ad["priority_score"] = PRIORITY_TYPES.get(ad.get("type", ""), 3)
        if u := users.get(ad.get("user_id", "")):
            ad["author_name"] = u.get("name", "")
            ad["author_institution"] = u.get("institution", "")
        results.append(ad)

    results.sort(key=lambda x: (-x["priority_score"], x.get("created_at", "")))

    return {"results": results, "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def get_user_activity(user_id: str, db, page: int = 1, limit: int = 20) -> dict:
    query = {"user_id": user_id}
    skip = (page - 1) * limit
    cursor = db["network_activity"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["network_activity"].count_documents(query)
    return {"results": [_s(d) for d in docs], "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def delete_activity(activity_id: str, user_id: str, db) -> bool:
    try:
        oid = ObjectId(activity_id)
    except Exception:
        return False
    r = await db["network_activity"].delete_one({"_id": oid, "user_id": user_id})
    return bool(r.deleted_count)
