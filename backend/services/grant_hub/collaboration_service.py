"""Grant Collaboration Hub — Core CRUD for grant collaboration workspaces.

Collections:
  grant_collaborations — deal-room workspace docs
  grant_team_members   — denormalized member records
  grant_positions      — open roles within a collaboration
  grant_work_packages  — work packages with tasks
  grant_collab_proposal_sections — collaborative proposal sections
  grant_team_invitations — invitation records
  grant_consortia      — consortium builder
  users                — for creator name join
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId


def _ser(d: dict) -> dict:
    """Serialize a MongoDB document: ObjectId → str, keep all fields."""
    if not d:
        return {}
    out = dict(d)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    # Serialize any nested ObjectIds
    for k, v in out.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── create ────────────────────────────────────────────────────────────────────

async def create_collaboration(user_id: str, data: dict, db) -> dict:
    """Insert a new collaboration workspace and add creator as lead member."""
    now = _now()
    doc = {
        "lead_user_id": user_id,
        "lead_institution_id": data.get("lead_institution_id"),
        "grant_id": data.get("grant_id"),
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "research_areas": data.get("research_areas", []),
        "countries_required": data.get("countries_required", []),
        "funding_source": data.get("funding_source", ""),
        "deadline": data.get("deadline", ""),
        "status": data.get("status", "open"),
        "visibility": data.get("visibility", "public"),
        "budget_total": float(data.get("budget_total", 0.0)),
        "member_count": 1,
        "created_at": now,
        "updated_at": now,
    }
    result = await db["grant_collaborations"].insert_one(doc)
    collab_id = str(result.inserted_id)
    doc["_id"] = result.inserted_id

    # Add creator as lead team member
    member_doc = {
        "collaboration_id": collab_id,
        "user_id": user_id,
        "role": "lead",
        "joined_at": now,
    }
    await db["grant_team_members"].insert_one(member_doc)

    return _ser(doc)


# ── read ──────────────────────────────────────────────────────────────────────

async def get_collaboration(collab_id: str, db) -> dict:
    """Fetch a single collaboration by id. Raises KeyError if not found."""
    try:
        oid = ObjectId(collab_id)
    except Exception:
        raise KeyError(f"Invalid collaboration id: {collab_id}")

    doc = await db["grant_collaborations"].find_one({"_id": oid})
    if not doc:
        raise KeyError(f"Collaboration {collab_id} not found")
    return _ser(doc)


async def list_collaborations(
    db,
    filters: Optional[dict] = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """List collaborations with optional filters. Joins creator name from users."""
    query: dict = {}
    if filters:
        if "status" in filters and filters["status"]:
            query["status"] = filters["status"]
        if "research_area" in filters and filters["research_area"]:
            query["research_areas"] = {"$in": [filters["research_area"]]}
        if "country" in filters and filters["country"]:
            query["countries_required"] = {"$in": [filters["country"]]}
        if "funding_source" in filters and filters["funding_source"]:
            query["funding_source"] = filters["funding_source"]
        if "visibility" in filters and filters["visibility"]:
            query["visibility"] = filters["visibility"]
        else:
            query["visibility"] = "public"
    else:
        query["visibility"] = "public"

    skip = (page - 1) * limit
    total, cursor = await asyncio.gather(
        db["grant_collaborations"].count_documents(query),
        asyncio.coroutine(lambda: db["grant_collaborations"].find(query).skip(skip).limit(limit).to_list(limit))(),
    )

    # Join creator names
    items = []
    for doc in cursor:
        item = _ser(doc)
        lead_uid = doc.get("lead_user_id")
        if lead_uid:
            try:
                user = await db["users"].find_one(
                    {"_id": ObjectId(lead_uid)},
                    {"first_name": 1, "last_name": 1, "name": 1, "email": 1},
                )
                if user:
                    item["lead_user_name"] = (
                        user.get("name")
                        or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                        or user.get("email", "")
                    )
            except Exception:
                pass
        items.append(item)

    pages = math.ceil(total / limit) if limit > 0 else 1
    return {"items": items, "total": total, "page": page, "pages": pages}


async def get_user_collaborations(user_id: str, db) -> list:
    """Return all collaborations where user is lead or team member."""
    # Get collaboration_ids from team membership
    member_docs = await db["grant_team_members"].find(
        {"user_id": user_id},
        {"collaboration_id": 1},
    ).to_list(500)

    collab_ids_str = {m["collaboration_id"] for m in member_docs}

    # Also include collabs where lead_user_id matches
    lead_docs = await db["grant_collaborations"].find(
        {"lead_user_id": user_id},
        {"_id": 1},
    ).to_list(500)
    for d in lead_docs:
        collab_ids_str.add(str(d["_id"]))

    # Fetch all
    oids = []
    for cid in collab_ids_str:
        try:
            oids.append(ObjectId(cid))
        except Exception:
            pass

    if not oids:
        return []

    docs = await db["grant_collaborations"].find({"_id": {"$in": oids}}).to_list(500)
    return [_ser(d) for d in docs]


# ── update ────────────────────────────────────────────────────────────────────

async def update_collaboration(collab_id: str, user_id: str, updates: dict, db) -> dict:
    """Update collaboration fields. Only lead may update."""
    collab = await get_collaboration(collab_id, db)
    if collab.get("lead_user_id") != user_id:
        raise PermissionError("Only the lead may update this collaboration")

    allowed = {
        "title", "description", "research_areas", "countries_required",
        "funding_source", "deadline", "status", "visibility", "budget_total",
        "lead_institution_id", "grant_id",
    }
    safe = {k: v for k, v in updates.items() if k in allowed}
    if "budget_total" in safe:
        safe["budget_total"] = float(safe["budget_total"])
    safe["updated_at"] = _now()

    await db["grant_collaborations"].update_one(
        {"_id": ObjectId(collab_id)},
        {"$set": safe},
    )
    return await get_collaboration(collab_id, db)


# ── stats ─────────────────────────────────────────────────────────────────────

async def get_collaboration_stats(collab_id: str, db) -> dict:
    """Aggregate statistics for a collaboration workspace."""
    (
        total_positions,
        open_positions,
        member_count,
        work_package_count,
        proposal_section_count,
        pending_invitations,
        consortium,
    ) = await asyncio.gather(
        db["grant_positions"].count_documents({"collaboration_id": collab_id}),
        db["grant_positions"].count_documents({"collaboration_id": collab_id, "status": "open"}),
        db["grant_team_members"].count_documents({"collaboration_id": collab_id}),
        db["grant_work_packages"].count_documents({"collaboration_id": collab_id}),
        db["grant_collab_proposal_sections"].count_documents({"collaboration_id": collab_id}),
        db["grant_team_invitations"].count_documents({"collaboration_id": collab_id, "status": "pending"}),
        db["grant_consortia"].find_one({"collaboration_id": collab_id}),
    )

    return {
        "collaboration_id": collab_id,
        "positions": {
            "total": total_positions,
            "open": open_positions,
            "filled": total_positions - open_positions,
        },
        "member_count": member_count,
        "work_package_count": work_package_count,
        "proposal_section_count": proposal_section_count,
        "pending_invitations": pending_invitations,
        "consortium": _ser(consortium) if consortium else None,
    }
