"""Saved opportunities — bookmark people, groups, events, collaborations, etc."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


SAVEABLE_TYPES = {
    "person", "institution", "group", "community",
    "collaboration", "event", "grant", "project",
}


async def save_item(user_id: str, item_type: str, item_id: str, data: dict, db) -> dict:
    if item_type not in SAVEABLE_TYPES:
        return {"error": f"Cannot save type: {item_type}"}

    existing = await db["network_saved"].find_one(
        {"user_id": user_id, "item_type": item_type, "item_id": item_id}
    )
    if existing:
        return {"status": "already_saved", "id": str(existing["_id"])}

    saved = {
        "user_id": user_id,
        "item_type": item_type,
        "item_id": item_id,
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "notes": data.get("notes", ""),
        "saved_at": _now(),
    }
    r = await db["network_saved"].insert_one(saved)
    saved["id"] = str(r.inserted_id)
    saved.pop("_id", None)
    return {"status": "saved", **saved}


async def unsave_item(user_id: str, item_type: str, item_id: str, db) -> bool:
    r = await db["network_saved"].delete_one(
        {"user_id": user_id, "item_type": item_type, "item_id": item_id}
    )
    return bool(r.deleted_count)


async def get_saved(user_id: str, db, item_type: str = None) -> dict:
    query = {"user_id": user_id}
    if item_type:
        query["item_type"] = item_type

    cursor = db["network_saved"].find(query).sort("saved_at", -1).limit(200)
    docs = await cursor.to_list(200)
    items = [_s(d) for d in docs]

    grouped: dict[str, list] = {}
    for item in items:
        t = item.get("item_type", "other")
        grouped.setdefault(t, []).append(item)

    return {
        "items": items,
        "by_type": grouped,
        "total": len(items),
    }


async def update_notes(saved_id: str, user_id: str, notes: str, db) -> dict | None:
    try:
        oid = ObjectId(saved_id)
    except Exception:
        return None
    await db["network_saved"].update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": {"notes": notes, "updated_at": _now()}}
    )
    doc = await db["network_saved"].find_one({"_id": oid})
    return _s(doc)


async def is_saved(user_id: str, item_type: str, item_id: str, db) -> bool:
    doc = await db["network_saved"].find_one(
        {"user_id": user_id, "item_type": item_type, "item_id": item_id}
    )
    return doc is not None
