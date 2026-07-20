"""Academic events — seminars, conferences, workshops, webinars, journal clubs."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


EVENT_TYPES = [
    "seminar", "conference", "webinar", "workshop",
    "journal_club", "training", "grant_info_session",
    "networking", "teaching_event", "symposium",
]


async def create_event(user_id: str, data: dict, db) -> dict:
    event = {
        "organizer_id": user_id,
        "title": data["title"],
        "description": data.get("description", ""),
        "type": data.get("type", "seminar"),
        "discipline": data.get("discipline", ""),
        "location": data.get("location", ""),
        "online": data.get("online", True),
        "link": data.get("link", ""),
        "start_date": data.get("start_date", ""),
        "end_date": data.get("end_date", ""),
        "timezone": data.get("timezone", "UTC"),
        "capacity": data.get("capacity", 0),
        "registration_count": 0,
        "registration_required": data.get("registration_required", False),
        "tags": data.get("tags", []),
        "status": "upcoming",
        "created_at": _now(),
    }
    r = await db["network_events"].insert_one(event)
    event["id"] = str(r.inserted_id)
    event.pop("_id", None)
    return event


async def list_events(db, filters: dict, page: int = 1, limit: int = 20) -> dict:
    query = {"status": "upcoming"}
    if q := filters.get("q"):
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if t := filters.get("type"):
        query["type"] = t
    if online := filters.get("online"):
        query["online"] = online == "true"

    skip = (page - 1) * limit
    cursor = db["network_events"].find(query).sort("start_date", 1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["network_events"].count_documents(query)
    return {"results": [_s(d) for d in docs], "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def get_event(event_id: str, db) -> dict | None:
    try:
        doc = await db["network_events"].find_one({"_id": ObjectId(event_id)})
    except Exception:
        return None
    return _s(doc)


async def register_for_event(event_id: str, user_id: str, db) -> dict:
    existing = await db["network_event_registrations"].find_one(
        {"event_id": event_id, "user_id": user_id}
    )
    if existing:
        return {"status": "already_registered"}

    event = await get_event(event_id, db)
    if not event:
        return {"error": "Event not found"}
    if event.get("capacity", 0) > 0 and event.get("registration_count", 0) >= event["capacity"]:
        return {"error": "Event is full"}

    await db["network_event_registrations"].insert_one({
        "event_id": event_id, "user_id": user_id, "registered_at": _now()
    })
    await db["network_events"].update_one(
        {"_id": ObjectId(event_id)}, {"$inc": {"registration_count": 1}}
    )
    return {"status": "registered"}


async def unregister_from_event(event_id: str, user_id: str, db) -> dict:
    r = await db["network_event_registrations"].delete_one(
        {"event_id": event_id, "user_id": user_id}
    )
    if r.deleted_count:
        await db["network_events"].update_one(
            {"_id": ObjectId(event_id)}, {"$inc": {"registration_count": -1}}
        )
        return {"status": "unregistered"}
    return {"status": "not_registered"}


async def get_my_events(user_id: str, db) -> dict:
    registrations = await db["network_event_registrations"].find({"user_id": user_id}).to_list(50)
    event_ids = [r["event_id"] for r in registrations]
    registered = []
    if event_ids:
        try:
            oids = [ObjectId(e) for e in event_ids]
            cursor = db["network_events"].find({"_id": {"$in": oids}})
            registered = [_s(d) for d in await cursor.to_list(50)]
        except Exception:
            pass

    organized = await db["network_events"].find(
        {"organizer_id": user_id}
    ).sort("start_date", 1).limit(20).to_list(20)

    return {
        "registered": registered,
        "organized": [_s(d) for d in organized],
    }
