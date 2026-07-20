"""Proactive AI recommendations — collaborators, grants, journals, communities, etc."""
import asyncio
from datetime import datetime, timezone
from .matching_engine import get_matches_for_user, get_institution_matches


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


RECOMMENDATION_CATEGORIES = [
    "collaborator", "institution", "community", "group",
    "event", "collaboration", "mentor", "conference",
    "dataset", "software",
]


async def generate_recommendations(user_id: str, db) -> list:
    """Generate and persist proactive recommendations for a user."""
    from bson import ObjectId
    try:
        uid = ObjectId(user_id)
    except Exception:
        return []

    user, groups, communities, collabs, events, mentor_profile = await asyncio.gather(
        db["users"].find_one(
            {"_id": uid},
            {"research_interests": 1, "expertise": 1, "career_stage": 1, "country": 1, "department": 1}
        ),
        db["network_group_members"].count_documents({"user_id": user_id}),
        db["network_community_members"].count_documents({"user_id": user_id}),
        db["network_collaborations"].count_documents({"owner_id": user_id}),
        db["network_event_registrations"].count_documents({"user_id": user_id}),
        db["network_mentors"].find_one({"user_id": user_id}),
    )

    if not user:
        return []

    recs = []

    # Collaborator recommendations
    matches = await get_matches_for_user(user_id, db, limit=10)
    for m in matches[:5]:
        recs.append({
            "user_id": user_id,
            "category": "collaborator",
            "title": f"Connect with {m['name']}",
            "description": m["explanation"],
            "metadata": {
                "candidate_id": m["candidate_id"],
                "role": m["role"],
                "score": m["score"],
                "institution": m["institution"],
            },
            "action_url": "/network/people",
            "created_at": _now(),
        })

    # Institution recommendations
    inst_matches = await get_institution_matches(user_id, db, limit=3)
    for im in inst_matches[:2]:
        recs.append({
            "user_id": user_id,
            "category": "institution",
            "title": f"Explore {im['name']}",
            "description": im["explanation"],
            "metadata": {"institution_id": im["institution_id"], "score": im["score"]},
            "action_url": "/network/institutions",
            "created_at": _now(),
        })

    # Community recommendations (if user has few)
    if communities < 3:
        top_communities = await db["network_communities"].find(
            {"visibility": "public"}
        ).sort("member_count", -1).limit(3).to_list(3)
        for c in top_communities:
            recs.append({
                "user_id": user_id,
                "category": "community",
                "title": f"Join {c.get('name', 'community')}",
                "description": f"Popular academic community with {c.get('member_count', 0)} members. Topic: {c.get('topic', '')}.",
                "metadata": {"community_id": str(c["_id"])},
                "action_url": "/network/communities",
                "created_at": _now(),
            })

    # Group recommendations
    if groups < 2:
        top_groups = await db["network_groups"].find(
            {"visibility": "public"}
        ).sort("member_count", -1).limit(2).to_list(2)
        for g in top_groups:
            recs.append({
                "user_id": user_id,
                "category": "group",
                "title": f"Join {g.get('name', 'group')}",
                "description": f"Active {g.get('type', 'research group')} with {g.get('member_count', 0)} members.",
                "metadata": {"group_id": str(g["_id"])},
                "action_url": "/network/groups",
                "created_at": _now(),
            })

    # Event recommendations
    upcoming_events = await db["network_events"].find(
        {"status": "upcoming"}
    ).sort("start_date", 1).limit(3).to_list(3)
    for e in upcoming_events:
        recs.append({
            "user_id": user_id,
            "category": "event",
            "title": f"Register for: {e.get('title', 'event')}",
            "description": f"{e.get('type', 'event').replace('_', ' ').title()} on {e.get('start_date', '')[:10]}.",
            "metadata": {"event_id": str(e["_id"])},
            "action_url": "/network/conferences",
            "created_at": _now(),
        })

    # Collaboration recommendations
    open_collabs = await db["network_collaborations"].find(
        {"status": "open"}
    ).sort("created_at", -1).limit(3).to_list(3)
    for oc in open_collabs:
        recs.append({
            "user_id": user_id,
            "category": "collaboration",
            "title": oc.get("title", "Open Collaboration"),
            "description": oc.get("description", "")[:120],
            "metadata": {"collab_id": str(oc["_id"]), "type": oc.get("type", "")},
            "action_url": "/network/collaborations",
            "created_at": _now(),
        })

    # Mentor recommendation (if early/mid career and no requests sent)
    stage = user.get("career_stage", "")
    if stage in ("student", "postdoc", "early_career"):
        req_count = await db["network_mentorship_requests"].count_documents({"mentee_id": user_id})
        if req_count == 0:
            recs.append({
                "user_id": user_id,
                "category": "mentor",
                "title": "Find a Mentor",
                "description": "Connect with an experienced researcher for career guidance and publication coaching.",
                "metadata": {},
                "action_url": "/network/mentorship",
                "created_at": _now(),
            })

    # Persist — delete old non-dismissed, insert fresh
    await db["network_recommendations"].delete_many({"user_id": user_id, "dismissed": {"$ne": True}})
    if recs:
        await db["network_recommendations"].insert_many(recs)

    return recs


async def get_recommendations(user_id: str, db, category: str = None) -> list:
    query = {"user_id": user_id}
    if category:
        query["category"] = category
    cursor = db["network_recommendations"].find(query).sort("created_at", -1).limit(50)
    docs = await cursor.to_list(50)
    return [_s(d) for d in docs]


async def dismiss_recommendation(rec_id: str, user_id: str, db) -> bool:
    from bson import ObjectId
    try:
        oid = ObjectId(rec_id)
    except Exception:
        return False
    r = await db["network_recommendations"].update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": {"dismissed": True, "dismissed_at": _now()}}
    )
    return bool(r.modified_count)
