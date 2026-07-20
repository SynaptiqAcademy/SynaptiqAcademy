"""Research groups, labs, teaching communities — CRUD + membership."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


GROUP_TYPES = {
    "research_group", "research_lab", "center_of_excellence",
    "teaching_community", "reading_group", "working_group",
    "grant_team", "task_force",
}

MEMBER_ROLES = {"owner", "admin", "member", "observer"}


# ── Groups CRUD ──────────────────────────────────────────────────────────────

async def create_group(user_id: str, data: dict, db) -> dict:
    group = {
        "owner_id": user_id,
        "name": data["name"],
        "description": data.get("description", ""),
        "type": data.get("type", "research_group"),
        "discipline": data.get("discipline", ""),
        "keywords": data.get("keywords", []),
        "visibility": data.get("visibility", "public"),
        "institution": data.get("institution", ""),
        "country": data.get("country", ""),
        "max_members": data.get("max_members", 50),
        "member_count": 1,
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db["network_groups"].insert_one(group)
    gid = str(r.inserted_id)

    member = {
        "group_id": gid,
        "user_id": user_id,
        "role": "owner",
        "joined_at": _now(),
    }
    await db["network_group_members"].insert_one(member)

    group["id"] = gid
    group.pop("_id", None)
    return group


async def list_groups(db, filters: dict, user_id: str, page: int = 1, limit: int = 20) -> dict:
    query = {}
    if q := filters.get("q"):
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"discipline": {"$regex": q, "$options": "i"}},
        ]
    if t := filters.get("type"):
        query["type"] = t
    if vis := filters.get("visibility"):
        query["visibility"] = vis
    else:
        query["visibility"] = "public"

    skip = (page - 1) * limit
    cursor = db["network_groups"].find(query).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["network_groups"].count_documents(query)

    # Mark which groups the user is a member of
    gids = [str(d["_id"]) for d in docs]
    memberships = await db["network_group_members"].find(
        {"user_id": user_id, "group_id": {"$in": gids}}
    ).to_list(len(gids))
    member_set = {m["group_id"] for m in memberships}

    results = []
    for d in docs:
        gd = _s(d)
        gd["is_member"] = gd["id"] in member_set
        results.append(gd)

    return {"results": results, "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def get_group(group_id: str, db) -> dict | None:
    try:
        doc = await db["network_groups"].find_one({"_id": ObjectId(group_id)})
    except Exception:
        return None
    return _s(doc)


async def update_group(group_id: str, user_id: str, data: dict, db) -> dict | None:
    try:
        oid = ObjectId(group_id)
    except Exception:
        return None
    data["updated_at"] = _now()
    await db["network_groups"].update_one({"_id": oid, "owner_id": user_id}, {"$set": data})
    return await get_group(group_id, db)


async def delete_group(group_id: str, user_id: str, db) -> bool:
    try:
        oid = ObjectId(group_id)
    except Exception:
        return False
    r = await db["network_groups"].delete_one({"_id": oid, "owner_id": user_id})
    if r.deleted_count:
        await db["network_group_members"].delete_many({"group_id": group_id})
    return bool(r.deleted_count)


# ── Membership ───────────────────────────────────────────────────────────────

async def join_group(group_id: str, user_id: str, db) -> dict:
    existing = await db["network_group_members"].find_one({"group_id": group_id, "user_id": user_id})
    if existing:
        return {"status": "already_member"}

    await db["network_group_members"].insert_one({
        "group_id": group_id, "user_id": user_id,
        "role": "member", "joined_at": _now(),
    })
    await db["network_groups"].update_one(
        {"_id": ObjectId(group_id)}, {"$inc": {"member_count": 1}}
    )
    return {"status": "joined"}


async def leave_group(group_id: str, user_id: str, db) -> dict:
    r = await db["network_group_members"].delete_one({"group_id": group_id, "user_id": user_id})
    if r.deleted_count:
        await db["network_groups"].update_one(
            {"_id": ObjectId(group_id)}, {"$inc": {"member_count": -1}}
        )
        return {"status": "left"}
    return {"status": "not_member"}


async def get_group_members(group_id: str, db, limit: int = 50) -> list:
    cursor = db["network_group_members"].find({"group_id": group_id}).limit(limit)
    members = await cursor.to_list(limit)
    uid_list = [m["user_id"] for m in members]
    users = {}
    if uid_list:
        try:
            oids = [ObjectId(u) for u in uid_list]
            cur2 = db["users"].find(
                {"_id": {"$in": oids}},
                {"name": 1, "institution": 1, "career_stage": 1, "country": 1}
            )
            for u in await cur2.to_list(len(oids)):
                users[str(u["_id"])] = u
        except Exception:
            pass
    result = []
    for m in members:
        entry = {
            "user_id": m["user_id"],
            "role": m["role"],
            "joined_at": m["joined_at"],
        }
        if u := users.get(m["user_id"]):
            entry.update({
                "name": u.get("name", ""),
                "institution": u.get("institution", ""),
                "career_stage": u.get("career_stage", ""),
            })
        result.append(entry)
    return result


async def get_my_groups(user_id: str, db) -> list:
    memberships = await db["network_group_members"].find({"user_id": user_id}).to_list(100)
    gids = [m["group_id"] for m in memberships]
    if not gids:
        return []
    try:
        oids = [ObjectId(g) for g in gids]
    except Exception:
        return []
    cursor = db["network_groups"].find({"_id": {"$in": oids}})
    docs = await cursor.to_list(100)
    return [_s(d) for d in docs]
