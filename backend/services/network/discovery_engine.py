"""Discovery engine — search and filter people, institutions, projects, grants."""
import asyncio
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def _serialize(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


# ── Field sets returned by list queries (lightweight) ───────────────────────

_USER_FIELDS = {
    "name": 1, "email": 1, "institution": 1, "department": 1,
    "research_interests": 1, "expertise": 1, "career_stage": 1,
    "country": 1, "profile_picture": 1, "verification_level": 1,
    "trust_score": 1, "created_at": 1,
}

_INST_FIELDS = {
    "name": 1, "country": 1, "type": 1, "departments": 1,
    "research_focus": 1, "ranking": 1, "established": 1,
}


# ── People search ────────────────────────────────────────────────────────────

async def search_people(db, filters: dict, page: int = 1, limit: int = 20) -> dict:
    query = {}

    if q := filters.get("q"):
        terms = q.strip()
        query["$or"] = [
            {"name": {"$regex": terms, "$options": "i"}},
            {"research_interests": {"$regex": terms, "$options": "i"}},
            {"expertise": {"$regex": terms, "$options": "i"}},
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
