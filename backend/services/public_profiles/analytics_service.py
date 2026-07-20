import hashlib
from datetime import datetime, timezone, timedelta

async def record_view(profile_user_id: str, viewer_ip: str, referrer: str, db) -> None:
    try:
        viewer_hash = hashlib.sha256(viewer_ip.encode()).hexdigest()[:16]
        now = datetime.now(timezone.utc).isoformat()
        await db.profile_views.insert_one({"profile_user_id": profile_user_id, "viewer_hash": viewer_hash, "referrer": (referrer or "")[:200], "viewed_at": now})
        await db.public_profiles.update_one({"user_id": profile_user_id}, {"$inc": {"view_count": 1}}, upsert=False)
    except Exception:
        pass

async def get_profile_analytics(user_id: str, db) -> dict:
    total_views = await db.profile_views.count_documents({"profile_user_id": user_id})
    now = datetime.now(timezone.utc)
    cutoff_30 = (now - timedelta(days=30)).isoformat()
    cutoff_7 = (now - timedelta(days=7)).isoformat()
    views_30 = await db.profile_views.count_documents({"profile_user_id": user_id, "viewed_at": {"$gte": cutoff_30}})
    views_7 = await db.profile_views.count_documents({"profile_user_id": user_id, "viewed_at": {"$gte": cutoff_7}})
    views_by_day = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        count = await db.profile_views.count_documents({"profile_user_id": user_id, "viewed_at": {"$gte": day, "$lt": day + "T23:59:59"}})
        views_by_day.append({"date": day, "count": count})
    referrer_pipeline = [
        {"$match": {"profile_user_id": user_id, "referrer": {"$ne": ""}}},
        {"$group": {"_id": "$referrer", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_referrers = [{"referrer": r["_id"], "count": r["count"]} async for r in db.profile_views.aggregate(referrer_pipeline)]
    followers_count = await db.profile_followers.count_documents({"following_id": user_id})
    following_count = await db.profile_followers.count_documents({"follower_id": user_id})
    return {"total_views": total_views, "views_last_30_days": views_30, "views_last_7_days": views_7, "views_by_day": views_by_day, "top_referrers": top_referrers, "followers_count": followers_count, "following_count": following_count}
