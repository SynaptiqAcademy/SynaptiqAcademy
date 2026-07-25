"""Workspace Items — generic content model (Workspace redesign Phase 2).

A reusable shape for workspace-owned content that isn't a project-scoped
`Task` (tasks keep their existing model/endpoints in routers/projects.py —
that system already works and backs the Kanban board, so it is deliberately
NOT migrated here). Used first for wiki pages (Phase 4); designed so
milestones/documents/timeline items can adopt it later.

Endpoints:
  POST   /api/workspaces/{workspace_id}/items
  GET    /api/workspaces/{workspace_id}/items
  GET    /api/items/{item_id}
  PATCH  /api/items/{item_id}
  DELETE /api/items/{item_id}          (soft delete)
  POST   /api/items/{item_id}/restore  (admin only)

Security: workspace_id is always taken from the authenticated route path or
from the item's own stored workspace_id — never trusted from the request
body — and membership is verified against the real `workspaces` document
before any read or write.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from models import WorkspaceItemCreate, WorkspaceItemUpdate, WORKSPACE_ITEM_TYPES
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from routers.workspaces import _assert_member, _assert_admin, _now, _ser

log = logging.getLogger("synaptiq.workspace_items")
router = APIRouter(prefix="/api", tags=["workspace-items"])


def _safe_oid(v: str) -> Optional[ObjectId]:
    try:
        return ObjectId(v)
    except Exception:
        return None


async def _get_workspace_or_404(db, workspace_id: str) -> dict:
    oid = _safe_oid(workspace_id)
    if not oid:
        raise HTTPException(404, "Not found")
    ws = await db.workspaces.find_one({"_id": oid})
    if not ws:
        raise HTTPException(404, "Not found")
    return ws


def detect_cycle(item_id: str, dependency_ids: list[str], all_deps: dict[str, list[str]]) -> bool:
    """DFS cycle detection: would adding `dependency_ids` to `item_id` create
    a circular dependency chain? `all_deps` maps id -> its current dependency
    list (excluding item_id's own, since we're testing the proposed new set).
    """
    graph = dict(all_deps)
    graph[item_id] = dependency_ids
    visiting, visited = set(), set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True  # cycle
        if node in visited:
            return False
        visiting.add(node)
        for dep in graph.get(node, []) or []:
            if visit(dep):
                return True
        visiting.discard(node)
        visited.add(node)
        return False

    return visit(item_id)


@router.post("/workspaces/{workspace_id}/items")
async def create_item(workspace_id: str, payload: WorkspaceItemCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws = await _get_workspace_or_404(db, workspace_id)
    _assert_member(ws, user["id"])

    now = _now()
    doc = {
        "workspace_id": workspace_id,
        "item_type":    payload.item_type,
        "project_id":   payload.project_id,
        "parent_id":    payload.parent_id,
        "title":        payload.title,
        "description":  payload.description or "",
        "content":      payload.content,
        "status":       payload.status or "draft",
        "priority":     payload.priority,
        "start_date":   payload.start_date,
        "due_date":     payload.due_date,
        "completed_at": None,
        "progress_percentage": payload.progress_percentage,
        "assignee_ids": payload.assignee_ids or [],
        "creator_id":   user["id"],
        "dependency_ids": payload.dependency_ids or [],
        "labels":       payload.labels or [],
        "position":     payload.position if payload.position is not None else 0,
        "icon":         payload.icon,
        "cover_image":  payload.cover_image,
        "created_at":   now,
        "updated_at":   now,
        "deleted_at":   None,
        "version":      1,
    }

    # No cycle check needed at creation time: a brand-new item can't already
    # be a dependency of anything else, so it can't participate in a cycle
    # yet — the check matters on update, where existing edges could close a loop.
    res = await db.workspace_items.insert_one(doc)
    doc["_id"] = res.inserted_id
    log.info("workspace_item created: ws=%s type=%s by=%s", workspace_id, payload.item_type, user["id"])
    return _ser(doc)


@router.get("/workspaces/{workspace_id}/items")
async def list_items(
    workspace_id: str,
    item_type: Optional[str] = None,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws = await _get_workspace_or_404(db, workspace_id)
    _assert_member(ws, user["id"])

    q: dict = {"workspace_id": workspace_id, "deleted_at": None}
    if item_type:
        if item_type not in WORKSPACE_ITEM_TYPES:
            raise HTTPException(400, f"item_type must be one of {WORKSPACE_ITEM_TYPES}")
        q["item_type"] = item_type
    if status:
        q["status"] = status
    if assignee_id:
        q["assignee_ids"] = assignee_id
    if parent_id is not None:
        q["parent_id"] = parent_id or None

    items = await db.workspace_items.find(q).sort([("position", 1), ("created_at", -1)]).to_list(limit)
    return [_ser(i) for i in items]


@router.get("/items/{item_id}")
async def get_item(item_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _safe_oid(item_id)
    if not oid:
        raise HTTPException(404, "Not found")
    item = await db.workspace_items.find_one({"_id": oid, "deleted_at": None})
    if not item:
        raise HTTPException(404, "Not found")
    ws = await _get_workspace_or_404(db, item["workspace_id"])
    _assert_member(ws, user["id"])
    return _ser(item)


@router.patch("/items/{item_id}")
async def update_item(item_id: str, payload: WorkspaceItemUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _safe_oid(item_id)
    if not oid:
        raise HTTPException(404, "Not found")
    item = await db.workspace_items.find_one({"_id": oid, "deleted_at": None})
    if not item:
        raise HTTPException(404, "Not found")
    ws = await _get_workspace_or_404(db, item["workspace_id"])
    _assert_member(ws, user["id"])

    if payload.expected_version is not None and item.get("version") != payload.expected_version:
        raise HTTPException(409, "This item was changed by someone else — reload and try again")

    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items()
              if v is not None and k != "expected_version"}

    if "dependency_ids" in update:
        existing = await db.workspace_items.find(
            {"workspace_id": item["workspace_id"], "deleted_at": None, "_id": {"$ne": oid}},
            {"_id": 1, "dependency_ids": 1},
        ).to_list(1000)
        all_deps = {str(d["_id"]): d.get("dependency_ids") or [] for d in existing}
        if detect_cycle(item_id, update["dependency_ids"], all_deps):
            raise HTTPException(400, "That dependency would create a circular reference")

    if update.get("status") == "published" and item.get("status") != "published":
        update.setdefault("completed_at", _now())

    # Wiki pages: snapshot the pre-edit content/title as a version whenever
    # content changes, so "Version History" reflects every real save rather
    # than only being populated by a dedicated endpoint.
    if item.get("item_type") == "wiki_page" and "content" in update:
        await db.wiki_page_versions.insert_one({
            "page_id":   item_id,
            "title":     item.get("title"),
            "content":   item.get("content"),
            "saved_by":  item.get("creator_id"),
            "created_at": item.get("updated_at") or item.get("created_at"),
        })

    if update:
        update["updated_at"] = _now()
        update["version"] = (item.get("version") or 1) + 1
        await db.workspace_items.update_one({"_id": oid}, {"$set": update})

    fresh = await db.workspace_items.find_one({"_id": oid})
    return _ser(fresh)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _safe_oid(item_id)
    if not oid:
        raise HTTPException(404, "Not found")
    item = await db.workspace_items.find_one({"_id": oid, "deleted_at": None})
    if not item:
        raise HTTPException(404, "Not found")
    ws = await _get_workspace_or_404(db, item["workspace_id"])
    _assert_member(ws, user["id"])

    await db.workspace_items.update_one({"_id": oid}, {"$set": {"deleted_at": _now(), "updated_at": _now()}})


@router.post("/items/{item_id}/restore")
async def restore_item(item_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _safe_oid(item_id)
    if not oid:
        raise HTTPException(404, "Not found")
    item = await db.workspace_items.find_one({"_id": oid})
    if not item:
        raise HTTPException(404, "Not found")
    ws = await _get_workspace_or_404(db, item["workspace_id"])
    _assert_admin(ws, user["id"])

    await db.workspace_items.update_one({"_id": oid}, {"$set": {"deleted_at": None, "updated_at": _now()}})
    fresh = await db.workspace_items.find_one({"_id": oid})
    return _ser(fresh)
