"""Academic communities — discussions, resources, announcements, moderation."""
from datetime import datetime, timezone
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


COMMUNITY_TOPICS = [
    "research_methods", "ai_in_research", "statistics", "open_science",
    "peer_review", "grant_writing", "scientific_publishing", "teaching",
    "innovation", "discipline_specific", "software", "datasets",
]


async def create_community(user_id: str, data: dict, db) -> dict:
    community = {
        "owner_id": user_id,
        "name": data["name"],
        "description": data.get("description", ""),
        "topic": data.get("topic", "research_methods"),
        "tags": data.get("tags", []),
        "visibility": data.get("visibility", "public"),
        "moderation": data.get("moderation", "owner"),
        "member_count": 1,
        "post_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db["network_communities"].insert_one(community)
    cid = str(r.inserted_id)
    await db["network_community_members"].insert_one({
        "community_id": cid, "user_id": user_id,
        "role": "owner", "joined_at": _now()
    })
    community["id"] = cid
    community.pop("_id", None)
    return community


async def list_communities(db, filters: dict, user_id: str, page: int = 1, limit: int = 20) -> dict:
    query = {}
    if q := filters.get("q"):
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if t := filters.get("topic"):
        query["topic"] = t
    query["visibility"] = "public"

    skip = (page - 1) * limit
    cursor = db["network_communities"].find(query).sort("member_count", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["network_communities"].count_documents(query)

    cids = [str(d["_id"]) for d in docs]
    memberships = await db["network_community_members"].find(
        {"user_id": user_id, "community_id": {"$in": cids}}
    ).to_list(len(cids))
    member_set = {m["community_id"] for m in memberships}

    results = []
    for d in docs:
        cd = _s(d)
        cd["is_member"] = cd["id"] in member_set
        results.append(cd)

    return {"results": results, "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def get_community(community_id: str, db) -> dict | None:
    try:
        doc = await db["network_communities"].find_one({"_id": ObjectId(community_id)})
    except Exception:
        return None
    return _s(doc)


async def join_community(community_id: str, user_id: str, db) -> dict:
    existing = await db["network_community_members"].find_one(
        {"community_id": community_id, "user_id": user_id}
    )
    if existing:
        return {"status": "already_member"}
    await db["network_community_members"].insert_one({
        "community_id": community_id, "user_id": user_id,
        "role": "member", "joined_at": _now()
    })
    await db["network_communities"].update_one(
        {"_id": ObjectId(community_id)}, {"$inc": {"member_count": 1}}
    )
    return {"status": "joined"}


async def leave_community(community_id: str, user_id: str, db) -> dict:
    r = await db["network_community_members"].delete_one(
        {"community_id": community_id, "user_id": user_id}
    )
    if r.deleted_count:
        await db["network_communities"].update_one(
            {"_id": ObjectId(community_id)}, {"$inc": {"member_count": -1}}
        )
        return {"status": "left"}
    return {"status": "not_member"}


# ── Posts ────────────────────────────────────────────────────────────────────

async def create_post(community_id: str, user_id: str, data: dict, db) -> dict:
    membership = await db["network_community_members"].find_one(
        {"community_id": community_id, "user_id": user_id}
    )
    if not membership:
        return {"error": "Not a member"}

    post = {
        "community_id": community_id,
        "author_id": user_id,
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "type": data.get("type", "discussion"),
        "tags": data.get("tags", []),
        "reply_count": 0,
        "created_at": _now(),
    }
    r = await db["network_community_posts"].insert_one(post)
    await db["network_communities"].update_one(
        {"_id": ObjectId(community_id)}, {"$inc": {"post_count": 1}}
    )
    post["id"] = str(r.inserted_id)
    post.pop("_id", None)
    return post


async def list_posts(community_id: str, db, page: int = 1, limit: int = 20) -> dict:
    query = {"community_id": community_id}
    skip = (page - 1) * limit
    cursor = db["network_community_posts"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["network_community_posts"].count_documents(query)
    return {"results": [_s(d) for d in docs], "total": total, "page": page, "pages": max(1, -(-total // limit))}


async def get_my_communities(user_id: str, db) -> list:
    memberships = await db["network_community_members"].find({"user_id": user_id}).to_list(100)
    cids = [m["community_id"] for m in memberships]
    if not cids:
        return []
    try:
        oids = [ObjectId(c) for c in cids]
    except Exception:
        return []
    cursor = db["network_communities"].find({"_id": {"$in": oids}})
    return [_s(d) for d in await cursor.to_list(100)]
