"""Admin Content Dashboard — paginated views of all platform content.

Endpoints (all super_admin only):
  GET /api/admin/content/projects
  GET /api/admin/content/workspaces
  GET /api/admin/content/manuscripts
  GET /api/admin/content/publications
  GET /api/admin/content/collaborations
  GET /api/admin/content/conversations
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends

from db import get_db
from services.permissions import require_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin/content", tags=["admin-content"])

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _clamp(limit: int) -> int:
    return max(1, min(limit, _MAX_LIMIT))


def _serialize(docs: list) -> list:
    out = []
    for d in docs:
        d = dict(d)
        d["id"] = str(d.pop("_id", ""))
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@router.get("/projects", dependencies=[Depends(require_super_admin)])
async def list_all_projects(
    q: Optional[str] = None,
    owner_id: Optional[str] = None,
    page: int = 1,
    limit: int = _DEFAULT_LIMIT,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    limit = _clamp(limit)
    filt: dict = {}
    if owner_id:
        filt["owner_id"] = owner_id
    if q:
        import re
        filt["$or"] = [
            {"title": {"$regex": re.escape(q), "$options": "i"}},
            {"description": {"$regex": re.escape(q), "$options": "i"}},
        ]
    skip = (max(page, 1) - 1) * limit
    total = await db.projects.count_documents(filt)
    docs = await db.projects.find(filt, {"title": 1, "owner_id": 1, "members": 1, "status": 1, "created_at": 1}) \
        .sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"total": total, "page": page, "limit": limit, "items": _serialize(docs)}


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------

@router.get("/workspaces", dependencies=[Depends(require_super_admin)])
async def list_all_workspaces(
    q: Optional[str] = None,
    owner_id: Optional[str] = None,
    page: int = 1,
    limit: int = _DEFAULT_LIMIT,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    limit = _clamp(limit)
    filt: dict = {}
    if owner_id:
        filt["owner_id"] = owner_id
    if q:
        import re
        filt["name"] = {"$regex": re.escape(q), "$options": "i"}
    skip = (max(page, 1) - 1) * limit
    total = await db.workspaces.count_documents(filt)
    docs = await db.workspaces.find(filt, {"name": 1, "owner_id": 1, "members": 1, "status": 1, "created_at": 1}) \
        .sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"total": total, "page": page, "limit": limit, "items": _serialize(docs)}


# ---------------------------------------------------------------------------
# Manuscripts
# ---------------------------------------------------------------------------

@router.get("/manuscripts", dependencies=[Depends(require_super_admin)])
async def list_all_manuscripts(
    q: Optional[str] = None,
    lead_author_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = _DEFAULT_LIMIT,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    limit = _clamp(limit)
    filt: dict = {}
    if lead_author_id:
        filt["lead_author_id"] = lead_author_id
    if status:
        filt["status"] = status
    if q:
        import re
        filt["title"] = {"$regex": re.escape(q), "$options": "i"}
    skip = (max(page, 1) - 1) * limit
    total = await db.manuscripts.count_documents(filt)
    docs = await db.manuscripts.find(
        filt,
        {"title": 1, "lead_author_id": 1, "status": 1, "created_at": 1},
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"total": total, "page": page, "limit": limit, "items": _serialize(docs)}


# ---------------------------------------------------------------------------
# Publications
# ---------------------------------------------------------------------------

@router.get("/publications", dependencies=[Depends(require_super_admin)])
async def list_all_publications(
    q: Optional[str] = None,
    owner_id: Optional[str] = None,
    source: Optional[str] = None,
    page: int = 1,
    limit: int = _DEFAULT_LIMIT,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    limit = _clamp(limit)
    filt: dict = {}
    if owner_id:
        filt["owner_id"] = owner_id
    if source:
        filt["source"] = source
    if q:
        import re
        filt["title"] = {"$regex": re.escape(q), "$options": "i"}
    skip = (max(page, 1) - 1) * limit
    total = await db.publications.count_documents(filt)
    docs = await db.publications.find(
        filt,
        {"title": 1, "owner_id": 1, "year": 1, "source": 1, "doi": 1, "created_at": 1},
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"total": total, "page": page, "limit": limit, "items": _serialize(docs)}


# ---------------------------------------------------------------------------
# Collaborations
# ---------------------------------------------------------------------------

@router.get("/collaborations", dependencies=[Depends(require_super_admin)])
async def list_all_collaborations(
    q: Optional[str] = None,
    owner_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = _DEFAULT_LIMIT,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    limit = _clamp(limit)
    filt: dict = {}
    if owner_id:
        filt["owner_id"] = owner_id
    if status:
        filt["status"] = status
    if q:
        import re
        filt["title"] = {"$regex": re.escape(q), "$options": "i"}
    skip = (max(page, 1) - 1) * limit
    total = await db.collaborations.count_documents(filt)
    docs = await db.collaborations.find(
        filt,
        {"title": 1, "owner_id": 1, "status": 1, "members": 1, "created_at": 1},
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"total": total, "page": page, "limit": limit, "items": _serialize(docs)}


# ---------------------------------------------------------------------------
# Conversations (messaging metadata only — no message content)
# ---------------------------------------------------------------------------

@router.get("/conversations", dependencies=[Depends(require_super_admin)])
async def list_all_conversations(
    context_type: Optional[str] = None,
    page: int = 1,
    limit: int = _DEFAULT_LIMIT,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    limit = _clamp(limit)
    filt: dict = {}
    if context_type:
        filt["context_type"] = context_type
    skip = (max(page, 1) - 1) * limit
    total = await db.conversations.count_documents(filt)
    docs = await db.conversations.find(
        filt,
        {
            "context_type": 1, "context_id": 1, "participant_ids": 1,
            "message_count": 1, "last_message_at": 1, "created_at": 1,
        },
    ).sort("last_message_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"total": total, "page": page, "limit": limit, "items": _serialize(docs)}
