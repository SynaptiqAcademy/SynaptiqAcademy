from datetime import datetime, timezone
from bson import ObjectId


async def detect_conflicts(request_id: str, reviewer_user_id: str, db) -> list:
    now = datetime.now(timezone.utc)
    conflicts = []

    request = await db["review_requests"].find_one({"_id": ObjectId(request_id)}) or {}
    requester_user_id = request.get("requester_user_id", "")

    if not requester_user_id or requester_user_id == reviewer_user_id:
        return conflicts

    async def _store_conflict(conflict_type: str, details: str):
        doc = {
            "request_id": request_id,
            "reviewer_user_id": reviewer_user_id,
            "conflict_type": conflict_type,
            "details": details,
            "detected_at": now,
            "auto_detected": True,
        }
        await db["review_conflicts"].insert_one(doc)
        doc["_id"] = str(doc.get("_id", ""))
        conflicts.append(doc)

    # 1. Co-authorship check
    reviewer_pubs = await db["publications"].find(
        {"$or": [
            {"user_id": reviewer_user_id},
            {"collaborators": reviewer_user_id},
            {"authors": reviewer_user_id},
        ]},
        {"_id": 1, "title": 1},
    ).to_list(length=500)

    requester_pubs = await db["publications"].find(
        {"$or": [
            {"user_id": requester_user_id},
            {"collaborators": requester_user_id},
            {"authors": requester_user_id},
        ]},
        {"_id": 1, "title": 1},
    ).to_list(length=500)

    reviewer_pub_ids = {str(p["_id"]) for p in reviewer_pubs}
    requester_pub_ids = {str(p["_id"]) for p in requester_pubs}
    shared_pub_ids = reviewer_pub_ids & requester_pub_ids

    if shared_pub_ids:
        await _store_conflict(
            "co_author",
            f"Shared publications detected: {len(shared_pub_ids)} publication(s) in common.",
        )

    # 2. Active collaboration check
    active_collab = await db["collaborations"].find_one({
        "$or": [
            {"created_by": requester_user_id, "participants": reviewer_user_id},
            {"created_by": reviewer_user_id, "participants": requester_user_id},
            {"participants": {"$all": [requester_user_id, reviewer_user_id]}},
        ]
    })
    if active_collab:
        await _store_conflict(
            "active_collaboration",
            f"Active collaboration found (id: {str(active_collab.get('_id', ''))}).",
        )

    # 3. Shared projects check
    shared_project = await db["projects"].find_one({
        "$or": [
            {"created_by": requester_user_id, "members": reviewer_user_id},
            {"created_by": reviewer_user_id, "members": requester_user_id},
            {"members": {"$all": [requester_user_id, reviewer_user_id]}},
        ]
    })
    if shared_project:
        await _store_conflict(
            "shared_project",
            f"Shared project found (id: {str(shared_project.get('_id', ''))}).",
        )

    # 4. Shared grants check
    reviewer_grant_ids_cursor = db["grant_applications"].find(
        {"user_id": reviewer_user_id}, {"grant_id": 1}
    )
    reviewer_grant_apps = await reviewer_grant_ids_cursor.to_list(length=200)
    reviewer_grant_ids = {str(a.get("grant_id", "")) for a in reviewer_grant_apps if a.get("grant_id")}

    if reviewer_grant_ids:
        requester_shared_grant = await db["grant_applications"].find_one({
            "user_id": requester_user_id,
            "grant_id": {"$in": list(reviewer_grant_ids)},
        })
        if requester_shared_grant:
            await _store_conflict(
                "shared_grant",
                f"Both users applied for the same grant (grant_id: {str(requester_shared_grant.get('grant_id', ''))}).",
            )

    # 5. Shared institution check
    reviewer_user = await db["users"].find_one({"_id": ObjectId(reviewer_user_id)}) or {}
    requester_user = await db["users"].find_one({"_id": ObjectId(requester_user_id)}) or {}

    reviewer_institution = (reviewer_user.get("institution") or "").strip().lower()
    requester_institution = (requester_user.get("institution") or "").strip().lower()

    if reviewer_institution and requester_institution and reviewer_institution == requester_institution:
        await _store_conflict(
            "shared_institution",
            f"Both users belong to the same institution: '{reviewer_user.get('institution', '')}'.",
        )

    return conflicts


async def get_conflicts_for_request(request_id: str, db) -> list:
    cursor = db["review_conflicts"].find({"request_id": request_id})
    docs = await cursor.to_list(length=200)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs


async def has_conflict(request_id: str, reviewer_user_id: str, db) -> bool:
    doc = await db["review_conflicts"].find_one(
        {"request_id": request_id, "reviewer_user_id": reviewer_user_id}
    )
    return doc is not None
