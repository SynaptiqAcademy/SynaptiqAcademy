"""Network analytics — collaboration growth, international reach, influence."""
import asyncio
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


async def get_network_overview(user_id: str, db) -> dict:
    groups, communities, collabs_owned, collabs_applied, mentorship, events, activity = await asyncio.gather(
        db["network_group_members"].count_documents({"user_id": user_id}),
        db["network_community_members"].count_documents({"user_id": user_id}),
        db["network_collaborations"].count_documents({"owner_id": user_id}),
        db["network_collaboration_applications"].count_documents({"applicant_id": user_id}),
        db["network_mentorship_requests"].count_documents({"$or": [{"mentee_id": user_id}, {"mentor_user_id": user_id}]}),
        db["network_event_registrations"].count_documents({"user_id": user_id}),
        db["network_activity"].count_documents({"user_id": user_id}),
    )
    return {
        "groups": groups,
        "communities": communities,
        "collaborations_created": collabs_owned,
        "collaborations_applied": collabs_applied,
        "mentorship_connections": mentorship,
        "events_attended": events,
        "activities_posted": activity,
        "network_score": _compute_network_score(
            groups, communities, collabs_owned, collabs_applied, mentorship, events
        ),
    }


def _compute_network_score(groups, communities, collabs_owned, collabs_applied, mentorship, events) -> int:
    score = 0
    score += min(groups * 10, 30)
    score += min(communities * 8, 24)
    score += min(collabs_owned * 15, 30)
    score += min(collabs_applied * 5, 15)
    score += min(mentorship * 10, 20)
    score += min(events * 3, 15)
    return min(score, 100)


async def get_platform_network_stats(db) -> dict:
    total_researchers, total_groups, total_communities, open_collabs, upcoming_events, mentors = await asyncio.gather(
        db["users"].count_documents({}),
        db["network_groups"].count_documents({}),
        db["network_communities"].count_documents({}),
        db["network_collaborations"].count_documents({"status": "open"}),
        db["network_events"].count_documents({"status": "upcoming"}),
        db["network_mentors"].count_documents({"active": True}),
    )
    return {
        "total_researchers": total_researchers,
        "total_groups": total_groups,
        "total_communities": total_communities,
        "open_collaborations": open_collabs,
        "upcoming_events": upcoming_events,
        "active_mentors": mentors,
        "computed_at": _now(),
    }


async def get_collaboration_analytics(user_id: str, db) -> dict:
    owned_open = await db["network_collaborations"].count_documents({"owner_id": user_id, "status": "open"})
    owned_closed = await db["network_collaborations"].count_documents({"owner_id": user_id, "status": "closed"})
    received_applications = await db["network_collaboration_applications"].count_documents({})

    my_collabs_cursor = db["network_collaborations"].find({"owner_id": user_id}, {"_id": 1}).limit(100)
    my_collab_ids = [str(d["_id"]) async for d in my_collabs_cursor]

    total_received = await db["network_collaboration_applications"].count_documents(
        {"collab_id": {"$in": my_collab_ids}}
    )
    accepted = await db["network_collaboration_applications"].count_documents(
        {"collab_id": {"$in": my_collab_ids}, "status": "accepted"}
    )

    my_applications = await db["network_collaboration_applications"].count_documents(
        {"applicant_id": user_id}
    )
    my_accepted = await db["network_collaboration_applications"].count_documents(
        {"applicant_id": user_id, "status": "accepted"}
    )

    return {
        "posted_open": owned_open,
        "posted_closed": owned_closed,
        "received_applications": total_received,
        "accepted_collaborators": accepted,
        "sent_applications": my_applications,
        "accepted_as_collaborator": my_accepted,
        "acceptance_rate_as_owner": round(accepted / total_received * 100, 1) if total_received else 0,
        "acceptance_rate_as_applicant": round(my_accepted / my_applications * 100, 1) if my_applications else 0,
    }


async def get_group_analytics(user_id: str, db) -> dict:
    owned = await db["network_groups"].count_documents({"owner_id": user_id})
    member_of = await db["network_group_members"].count_documents({"user_id": user_id})
    total_members_in_owned_groups = 0
    if owned > 0:
        owned_groups_cursor = db["network_groups"].find({"owner_id": user_id}, {"member_count": 1}).limit(20)
        async for g in owned_groups_cursor:
            total_members_in_owned_groups += g.get("member_count", 0)

    return {
        "groups_created": owned,
        "groups_joined": member_of,
        "total_members_in_groups": total_members_in_owned_groups,
    }
