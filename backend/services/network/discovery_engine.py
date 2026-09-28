"""Discovery engine — search and filter people, institutions, projects, grants."""
import asyncio
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId


def _now():
    return datetime.now(timezone.utc)


def _serialize(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
        # Project real schema fields (full_name/avatar_url) but keep the
        # response shape's existing key names (name/profile_picture) so
        # this doesn't require a frontend change.
        if "full_name" in doc:
            doc["name"] = doc.pop("full_name")
        if "avatar_url" in doc:
            doc["profile_picture"] = doc.pop("avatar_url")
    return doc


def _to_object_id(uid: str):
    try:
        return ObjectId(uid)
    except (InvalidId, TypeError):
        return uid


# ── Field sets returned by list queries (lightweight) ───────────────────────

_USER_FIELDS = {
    "full_name": 1, "institution": 1, "department": 1,
    "research_interests": 1, "expertise": 1, "career_stage": 1,
    "country": 1, "avatar_url": 1, "verification_level": 1,
    "trust_score": 1, "created_at": 1,
}


async def _discovery_exclusions(db, viewer_id: str | None) -> set[str]:
    """User ids to exclude from discovery results: anyone who has opted out
    via show_in_discovery=False, plus a symmetric block (viewer blocked them,
    or they blocked viewer) when a viewer is known."""
    excluded: set[str] = set()
    async for s in db["network_settings"].find(
        {"show_in_discovery": False}, {"user_id": 1}
    ):
        if uid := s.get("user_id"):
            excluded.add(uid)
    if viewer_id:
        viewer_settings = await db["network_settings"].find_one({"user_id": viewer_id})
        if viewer_settings:
            excluded.update(viewer_settings.get("blocked_users") or [])
        async for s in db["network_settings"].find(
            {"blocked_users": viewer_id}, {"user_id": 1}
        ):
            if uid := s.get("user_id"):
                excluded.add(uid)
        excluded.discard(viewer_id)
    return excluded

_INST_FIELDS = {
    "name": 1, "country": 1, "type": 1, "departments": 1,
    "research_focus": 1, "ranking": 1, "established": 1,
}


# ── People search ────────────────────────────────────────────────────────────

async def search_people(db, filters: dict, page: int = 1, limit: int = 20, viewer_id: str | None = None) -> dict:
    query: dict = {"profile_visibility": {"$ne": "private"}}

    if q := filters.get("q"):
        terms = q.strip()
        query["$or"] = [
            {"full_name": {"$regex": terms, "$options": "i"}},
            {"research_interests": {"$regex": terms, "$options": "i"}},
            {"department": {"$regex": terms, "$options": "i"}},
        ]

    for field in ("institution", "country", "career_stage", "department"):
        if v := filters.get(field):
            query[field] = {"$regex": v, "$options": "i"}

    if disc := filters.get("discipline"):
        query["$or"] = query.get("$or", []) + [
            {"research_interests": {"$regex": disc, "$options": "i"}},
            {"expertise": {"$regex": disc, "$options": "i"}},
        ]

    if vl := filters.get("verification_level"):
        query["verification_level"] = {"$gte": int(vl)}

    if ts := filters.get("min_trust_score"):
        query["trust_score"] = {"$gte": float(ts)}

    excluded = await _discovery_exclusions(db, viewer_id)
    if excluded:
        query["_id"] = {"$nin": [_to_object_id(x) for x in excluded]}

    skip = (page - 1) * limit
    cursor = db["users"].find(query, _USER_FIELDS).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["users"].count_documents(query)

    return {
        "results": [_serialize(d) for d in docs],
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
    }


# ── Institution search ───────────────────────────────────────────────────────

async def search_institutions(db, filters: dict, page: int = 1, limit: int = 20) -> dict:
    query = {}

    if q := filters.get("q"):
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"research_focus": {"$regex": q, "$options": "i"}},
        ]

    for field in ("country", "type"):
        if v := filters.get(field):
            query[field] = {"$regex": v, "$options": "i"}

    skip = (page - 1) * limit
    cursor = db["institutions"].find(query, _INST_FIELDS).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["institutions"].count_documents(query)

    return {
        "results": [_serialize(d) for d in docs],
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
    }


# ── Project search ───────────────────────────────────────────────────────────

async def search_projects(db, filters: dict, page: int = 1, limit: int = 20) -> dict:
    query = {"status": {"$in": ["active", "recruiting"]}}

    if q := filters.get("q"):
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"keywords": {"$regex": q, "$options": "i"}},
        ]

    for field in ("discipline", "methodology"):
        if v := filters.get(field):
            query[field] = {"$regex": v, "$options": "i"}

    skip = (page - 1) * limit
    cursor = db["projects"].find(query).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["projects"].count_documents(query)

    return {
        "results": [_serialize(d) for d in docs],
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
    }


# ── Grant team search ────────────────────────────────────────────────────────

async def search_grant_teams(db, filters: dict, page: int = 1, limit: int = 20) -> dict:
    query = {"status": "recruiting", "collection": "grant_applications"}
    if q := filters.get("q"):
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    skip = (page - 1) * limit
    cursor = db["grant_applications"].find(
        {"status": "recruiting", **({
            "$or": [
                {"title": {"$regex": filters["q"], "$options": "i"}},
                {"description": {"$regex": filters["q"], "$options": "i"}},
            ]
        } if filters.get("q") else {})}
    ).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["grant_applications"].count_documents({"status": "recruiting"})
    return {
        "results": [_serialize(d) for d in docs],
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
    }


# ── Discovery home stats ─────────────────────────────────────────────────────

async def get_discovery_stats(db) -> dict:
    users, institutions, projects, collab, grants, groups, communities, events = await asyncio.gather(
        db["users"].count_documents({}),
        db["institutions"].count_documents({}),
        db["projects"].count_documents({"status": "active"}),
        db["network_collaborations"].count_documents({"status": "open"}),
        db["grant_applications"].count_documents({}),
        db["network_groups"].count_documents({}),
        db["network_communities"].count_documents({}),
        db["network_events"].count_documents({"status": "upcoming"}),
    )
    return {
        "researchers": users,
        "institutions": institutions,
        "active_projects": projects,
        "open_collaborations": collab,
        "grant_applications": grants,
        "research_groups": groups,
        "communities": communities,
        "upcoming_events": events,
    }
