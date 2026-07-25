"""Knowledge Wiki — workspace wiki pages (Workspace redesign Phase 4).

Wiki pages themselves are workspace_items with item_type="wiki_page"
(created/read/updated/deleted via the generic /api/items endpoints in
workspace_items.py — content auto-versions to wiki_page_versions on every
save, see that router). This module adds only the operations that are
genuinely wiki-specific and don't belong on the generic item model:

  GET  /api/wiki/pages/{page_id}/versions            version history
  POST /api/wiki/pages/{page_id}/versions/{v_id}/restore
  POST /api/wiki/pages/{page_id}/duplicate
  GET  /api/workspaces/{workspace_id}/wiki/search?q=
"""
from __future__ import annotations

import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from routers.workspaces import _assert_member, _now, _ser
from routers.workspace_items import _get_workspace_or_404, _safe_oid

log = logging.getLogger("synaptiq.wiki")
router = APIRouter(prefix="/api", tags=["wiki"])


async def _get_wiki_page_or_404(db, page_id: str) -> dict:
    oid = _safe_oid(page_id)
    if not oid:
        raise HTTPException(404, "Not found")
    page = await db.workspace_items.find_one({"_id": oid, "item_type": "wiki_page", "deleted_at": None})
    if not page:
        raise HTTPException(404, "Not found")
    return page


def _extract_text(node) -> str:
    """Recursively pull plain text out of a Tiptap/ProseMirror JSON doc, for search."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return " ".join(_extract_text(n) for n in node)
    if isinstance(node, dict):
        parts = []
        if node.get("type") == "text" and node.get("text"):
            parts.append(node["text"])
        for child in node.get("content") or []:
            parts.append(_extract_text(child))
        return " ".join(p for p in parts if p)
    return ""


@router.get("/wiki/pages/{page_id}/versions")
async def list_versions(page_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    page = await _get_wiki_page_or_404(db, page_id)
    ws = await _get_workspace_or_404(db, page["workspace_id"])
    _assert_member(ws, user["id"])

    versions = await db.wiki_page_versions.find({"page_id": page_id}).sort("created_at", -1).to_list(200)
    return [_ser(v) for v in versions]


@router.post("/wiki/pages/{page_id}/versions/{version_id}/restore")
async def restore_version(page_id: str, version_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    page = await _get_wiki_page_or_404(db, page_id)
    ws = await _get_workspace_or_404(db, page["workspace_id"])
    _assert_member(ws, user["id"])

    void = _safe_oid(version_id)
    if not void:
        raise HTTPException(404, "Version not found")
    version = await db.wiki_page_versions.find_one({"_id": void, "page_id": page_id})
    if not version:
        raise HTTPException(404, "Version not found")

    # Snapshot the CURRENT content before overwriting, so restoring is itself
    # undoable — never a destructive, one-way action.
    await db.wiki_page_versions.insert_one({
        "page_id": page_id, "title": page.get("title"), "content": page.get("content"),
        "saved_by": user["id"], "created_at": _now(),
    })
    await db.workspace_items.update_one(
        {"_id": ObjectId(page_id)},
        {"$set": {
            "content": version.get("content"),
            "title": version.get("title") or page.get("title"),
            "updated_at": _now(),
        }, "$inc": {"version": 1}},
    )
    fresh = await db.workspace_items.find_one({"_id": ObjectId(page_id)})
    return _ser(fresh)


@router.post("/wiki/pages/{page_id}/duplicate")
async def duplicate_page(page_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    page = await _get_wiki_page_or_404(db, page_id)
    ws = await _get_workspace_or_404(db, page["workspace_id"])
    _assert_member(ws, user["id"])

    now = _now()
    copy_doc = {
        "workspace_id": page["workspace_id"],
        "item_type":    "wiki_page",
        "project_id":   page.get("project_id"),
        "parent_id":    page.get("parent_id"),
        "title":        f"{page.get('title', 'Untitled')} (copy)",
        "description":  page.get("description", ""),
        "content":      page.get("content"),
        "status":       "draft",
        "priority":     None,
        "start_date":   None,
        "due_date":     None,
        "completed_at": None,
        "progress_percentage": None,
        "assignee_ids": [],
        "creator_id":   user["id"],
        "dependency_ids": [],
        "labels":       page.get("labels") or [],
        "position":     (page.get("position") or 0) + 1,
        "icon":         page.get("icon"),
        "cover_image":  page.get("cover_image"),
        "created_at":   now,
        "updated_at":   now,
        "deleted_at":   None,
        "version":      1,
    }
    res = await db.workspace_items.insert_one(copy_doc)
    copy_doc["_id"] = res.inserted_id
    return _ser(copy_doc)


@router.get("/workspaces/{workspace_id}/wiki/search")
async def search_wiki(
    workspace_id: str,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws = await _get_workspace_or_404(db, workspace_id)
    _assert_member(ws, user["id"])

    # Title matches first (fast, indexed-ish via prefix), then fall back to
    # scanning content for a text match — wiki content is Tiptap JSON, not a
    # plain string, so full-text indexing it needs a materialized text field
    # (a real future improvement); this is an honest, working search for the
    # sizes a single workspace's wiki reasonably reaches today.
    pages = await db.workspace_items.find(
        {"workspace_id": workspace_id, "item_type": "wiki_page", "deleted_at": None}
    ).to_list(1000)

    ql = q.lower()
    results = []
    for p in pages:
        title = (p.get("title") or "")
        body_text = _extract_text(p.get("content"))
        title_hit = ql in title.lower()
        body_hit = ql in body_text.lower()
        if title_hit or body_hit:
            snippet = None
            if body_hit and not title_hit:
                idx = body_text.lower().find(ql)
                start = max(0, idx - 60)
                snippet = ("…" if start > 0 else "") + body_text[start:idx + len(q) + 60]
            results.append({**_ser(p), "_match": "title" if title_hit else "content", "_snippet": snippet})

    results.sort(key=lambda r: 0 if r["_match"] == "title" else 1)
    return results[:limit]
