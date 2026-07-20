from datetime import datetime, timezone
from bson import ObjectId

async def follow_researcher(follower_id: str, following_id: str, db) -> dict:
    if follower_id == following_id:
        raise ValueError("Cannot follow yourself")
    existing = await db.profile_followers.find_one({"follower_id": follower_id, "following_id": following_id})
    if existing:
        raise ValueError("Already following")
    now = datetime.now(timezone.utc).isoformat()
    await db.profile_followers.insert_one({"follower_id": follower_id, "following_id": following_id, "created_at": now})
    try:
        follower = await db.users.find_one({"_id": ObjectId(follower_id)}, {"full_name": 1})
        follower_name = (follower or {}).get("full_name","Someone")
        await db.notifications.insert_one({"user_id": following_id, "type": "new_follower", "message": f"{follower_name} started following you", "read": False, "created_at": now})
    except Exception:
        pass
    return {"following": True}

async def unfollow_researcher(follower_id: str, following_id: str, db) -> bool:
    result = await db.profile_followers.delete_one({"follower_id": follower_id, "following_id": following_id})
    return result.deleted_count > 0

async def get_followers(user_id: str, db, limit: int = 50) -> list:
    results = []
    async for f in db.profile_followers.find({"following_id": user_id}).sort("created_at", -1).limit(limit):
        fid = f["follower_id"]
        user = await db.users.find_one({"_id": ObjectId(fid)}, {"full_name": 1, "avatar_url": 1, "institution": 1})
        slug_doc = await db.public_profiles.find_one({"user_id": fid}, {"slug": 1})
        results.append({"user_id": fid, "full_name": (user or {}).get("full_name",""), "avatar_url": (user or {}).get("avatar_url"), "institution": (user or {}).get("institution",""), "slug": (slug_doc or {}).get("slug"), "followed_at": f.get("created_at","")})
    return results

async def get_following(user_id: str, db, limit: int = 50) -> list:
    results = []
    async for f in db.profile_followers.find({"follower_id": user_id}).sort("created_at", -1).limit(limit):
        fid = f["following_id"]
        user = await db.users.find_one({"_id": ObjectId(fid)}, {"full_name": 1, "avatar_url": 1, "institution": 1})
        slug_doc = await db.public_profiles.find_one({"user_id": fid}, {"slug": 1})
        results.append({"user_id": fid, "full_name": (user or {}).get("full_name",""), "avatar_url": (user or {}).get("avatar_url"), "institution": (user or {}).get("institution",""), "slug": (slug_doc or {}).get("slug"), "following_since": f.get("created_at","")})
    return results

async def is_following(follower_id: str, following_id: str, db) -> bool:
    doc = await db.profile_followers.find_one({"follower_id": follower_id, "following_id": following_id})
    return bool(doc)

async def get_follow_stats(user_id: str, db) -> dict:
    followers = await db.profile_followers.count_documents({"following_id": user_id})
    following = await db.profile_followers.count_documents({"follower_id": user_id})
    return {"followers": followers, "following": following}
