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


def _scrub_orcid_field(orcid):
    """Same rule as auth_utils._scrub_orcid — strips OAuth access/refresh
    tokens, keeps only what's safe to show another user (P1 Phase 8B §3:
    the confirmed leak this phase fixes was a *different* serializer,
    services/collab_intelligence's collaboration_intelligence.py, doing this
    same job without this scrub — kept here as its own small helper rather
    than importing auth_utils into this module, since this file has no
    other dependency on it and the rule is a two-line dict literal)."""
    if isinstance(orcid, dict):
        return {"orcid_id": orcid.get("orcid_id"), "verified_at": orcid.get("verified_at")}
    return None


def _serialize_person(doc):
    """People-search-specific serialization on top of _serialize(): scrubs
    ORCID to a connected/not-connected + public id (never tokens), and
    derives the same institution_verified signal
    services/verification/profile_service.py's canonical institution_verified
    check uses (user.institution_id set) — a boolean derived from a field
    already in the lightweight projection, not a second verification model.
    """
    if not doc:
        return doc
    orcid_scrubbed = _scrub_orcid_field(doc.pop("orcid", None))
    institution_id = doc.pop("institution_id", None)
    doc = _serialize(doc)
    doc["orcid_verified"] = orcid_scrubbed is not None
    doc["orcid_id"] = orcid_scrubbed.get("orcid_id") if orcid_scrubbed else None
    doc["institution_verified"] = institution_id is not None
    return doc


def _to_object_id(uid: str):
    try:
        return ObjectId(uid)
    except (InvalidId, TypeError):
        return uid


# ── Field sets returned by list queries (lightweight) ───────────────────────
# P1 Phase 8B §5: career_stage/verification_level/trust_score removed — none
# of the three is ever actually set on a real users document (confirmed
# against production: 0 of 75 users have any of these fields at all), so
# projecting and filtering on them was dead weight that could never match —
# exactly the "filter with no data pipeline" this phase's audit flagged.
# `expertise` removed for the same reason (also 0/75 in production; the real
# field is `research_areas`/`research_keywords`). Added the fields the new
# Research & Experts filters/cards actually need, all real per the Phase 8A
# field audit.
_USER_FIELDS = {
    "full_name": 1, "institution": 1, "department": 1,
    "research_areas": 1, "research_interests": 1, "research_keywords": 1,
    "methods": 1, "software_skills": 1,
    "academic_role": 1, "professional_role": 1, "professional_expertise": 1,
    "user_type": 1, "languages": 1,
    "country": 1, "avatar_url": 1, "orcid": 1, "institution_id": 1,
    "available_for_collaboration": 1, "available_for_reviewing": 1,
    "available_for_supervision": 1, "available_for_consulting": 1,
    "publications_count": 1, "h_index": 1, "created_at": 1,
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
    """Canonical people-retrieval layer (P1 Phase 8B §2/§9) — backend-side
    filtered + paginated, privacy-enforced via _discovery_exclusions(). Every
    filter below maps to a real, populated field (confirmed against the
    Phase 8A field audit + production data) — career_stage/verification_
    level/trust_score were removed here for the reason _USER_FIELDS' comment
    above explains (§5: dead filters, zero real data pipeline).
    """
    from services.permissions import REAL_CUSTOMER_FILTER
    query: dict = {
        "profile_visibility": {"$ne": "private"},
        "is_demo": {"$ne": True},
        **REAL_CUSTOMER_FILTER,
    }

    if q := filters.get("q"):
        terms = q.strip()
        query["$or"] = [
            {"full_name": {"$regex": terms, "$options": "i"}},
            {"research_areas": {"$regex": terms, "$options": "i"}},
            {"research_interests": {"$regex": terms, "$options": "i"}},
            {"research_keywords": {"$regex": terms, "$options": "i"}},
            {"methods": {"$regex": terms, "$options": "i"}},
            {"software_skills": {"$regex": terms, "$options": "i"}},
            {"professional_role": {"$regex": terms, "$options": "i"}},
            {"professional_expertise": {"$regex": terms, "$options": "i"}},
            {"institution": {"$regex": terms, "$options": "i"}},
            {"department": {"$regex": terms, "$options": "i"}},
        ]

    for field in ("institution", "country", "department", "professional_role"):
        if v := filters.get(field):
            query[field] = {"$regex": v, "$options": "i"}

    # Array-field filters — exact element match via $in, not regex (these
    # are chip-selected values from a controlled or free-tag list, not
    # prose); accepts either a single value or a list of values per field.
    for field in ("research_areas", "research_keywords", "methods",
                  "software_skills", "professional_expertise", "languages"):
        if v := filters.get(field):
            query[field] = {"$in": v if isinstance(v, list) else [v]}

    if disc := filters.get("discipline"):
        query["$or"] = query.get("$or", []) + [
            {"research_areas": {"$regex": disc, "$options": "i"}},
            {"research_interests": {"$regex": disc, "$options": "i"}},
            {"research_keywords": {"$regex": disc, "$options": "i"}},
        ]

    for field in ("available_for_collaboration", "available_for_reviewing",
                  "available_for_supervision", "available_for_consulting"):
        v = filters.get(field)
        if v is not None:
            query[field] = bool(v)

    # Derived-boolean filters (§13 "Verification indicators") — real signals
    # already used elsewhere (routers/orcid.py's authenticated-connection
    # check; services/verification/profile_service.py's institution_verified
    # check), not a new verification concept.
    if filters.get("orcid_verified"):
        query["orcid.orcid_id"] = {"$exists": True, "$ne": None}
    if filters.get("institution_verified"):
        query["institution_id"] = {"$exists": True, "$ne": None}

    excluded = await _discovery_exclusions(db, viewer_id)
    id_nin = list(excluded)
    if viewer_id:
        id_nin.append(viewer_id)  # self-exclusion, consistent with discover_sections
    if id_nin:
        query["_id"] = {"$nin": [_to_object_id(x) for x in id_nin]}

    skip = (page - 1) * limit
    cursor = db["users"].find(query, _USER_FIELDS).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["users"].count_documents(query)

    return {
        "results": [_serialize_person(d) for d in docs],
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
