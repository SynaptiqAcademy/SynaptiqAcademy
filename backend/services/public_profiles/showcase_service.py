from datetime import datetime, timezone
from bson import ObjectId

def _s(v):
    return str(v) if v is not None else None

VALID_ITEM_TYPES = {"publication", "project", "grant", "award", "teaching", "dataset", "patent"}

async def get_showcase(user_id: str, db) -> list:
    items = []
    async for s in db.profile_showcases.find({"user_id": user_id}).sort("order", 1):
        item = {"id": _s(s["_id"]), "user_id": s["user_id"], "item_type": s.get("item_type"), "item_id": s.get("item_id"), "order": s.get("order",0), "custom_label": s.get("custom_label",""), "created_at": s.get("created_at","")}
        itype = s.get("item_type","")
        iid = s.get("item_id","")
        try:
            if itype == "publication":
                p = await db.publications.find_one({"_id": ObjectId(iid)}, {"title": 1})
                item["title"] = (p or {}).get("title","")
            elif itype == "project":
                p = await db.projects.find_one({"_id": ObjectId(iid)}, {"title": 1})
                item["title"] = (p or {}).get("title","")
            elif itype == "grant":
                ga = await db.grant_applications.find_one({"_id": ObjectId(iid)}, {"grant_id": 1})
                if ga and ga.get("grant_id"):
                    g = await db.grants.find_one({"_id": ObjectId(ga["grant_id"])}, {"title": 1})
                    item["title"] = (g or {}).get("title","")
            else:
                item["title"] = item.get("custom_label","")
        except Exception:
            item["title"] = item.get("custom_label","")
        items.append(item)
    return items

async def add_showcase_item(user_id: str, item_type: str, item_id: str, custom_label: str, db) -> dict:
    if item_type not in VALID_ITEM_TYPES:
        raise ValueError(f"Invalid item_type. Must be one of: {', '.join(VALID_ITEM_TYPES)}")
    count = await db.profile_showcases.count_documents({"user_id": user_id})
    if count >= 10:
        raise ValueError("Maximum 10 showcase items allowed")
    pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "max_order": {"$max": "$order"}}}]
    result = [r async for r in db.profile_showcases.aggregate(pipeline)]
    max_order = (result[0]["max_order"] if result else -1) or -1
    now = datetime.now(timezone.utc).isoformat()
    doc = {"user_id": user_id, "item_type": item_type, "item_id": item_id, "order": max_order + 1, "custom_label": custom_label, "created_at": now}
    ins = await db.profile_showcases.insert_one(doc)
    doc["_id"] = _s(ins.inserted_id)
    return doc

async def update_showcase_order(user_id: str, ordered_ids: list, db) -> list:
    for idx, sid in enumerate(ordered_ids):
        try:
            await db.profile_showcases.update_one({"_id": ObjectId(sid), "user_id": user_id}, {"$set": {"order": idx}})
        except Exception:
            pass
    return await get_showcase(user_id, db)

async def remove_showcase_item(user_id: str, showcase_id: str, db) -> bool:
    try:
        result = await db.profile_showcases.delete_one({"_id": ObjectId(showcase_id), "user_id": user_id})
        return result.deleted_count > 0
    except Exception:
        return False
