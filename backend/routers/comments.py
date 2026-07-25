"""Generic Comments — polymorphic comment system (Workspace redesign Phase 3).

One `item_comments` collection for any commentable entity, instead of a
per-entity comments table. Authorization is resolved per `target_type` by
reusing each entity's OWN existing membership/authorship check — this
router never invents a new permission model, it just dispatches to the
real one for whatever the comment is attached to:

  workspace_item -> workspace membership   (_assert_member, routers.workspaces)
  workspace      -> workspace membership   (_assert_member, routers.workspaces)
  task           -> project membership     (_assert_project_member, routers.projects)
  manuscript     -> manuscript authorship  (_assert_author, routers.manuscripts)

`manuscript_comments` (the pre-existing manuscript-only comments collection
and its endpoints in routers/manuscripts.py) is left completely untouched —
nothing here reads or writes it, and none of its endpoints change. This
generic system is additive: it's what backs comments on the genuinely new
surfaces (workspace items, tasks, workspaces) that had no comment system
before. `manuscript` is accepted as a target_type so the model can
represent manuscript comments too, but the manuscript UI is intentionally
NOT rewired to this system in this pass — unifying a working, tested review
workflow needs its own careful migration, not a side-effect of this build.

Endpoints:
  GET    /api/comments?target_type=&target_id=&limit=&skip=
  POST   /api/comments
  PATCH  /api/comments/{comment_id}
  DELETE /api/comments/{comment_id}
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from auth_utils import get_current_user
from db import get_db
from models import GenericCommentCreate, GenericCommentUpdate, COMMENT_TARGET_TYPES
from rate_limit import limiter, WRITE_RATE
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from repo.audit import AuditTrail

log = logging.getLogger("synaptiq.comments")
router = APIRouter(prefix="/api/comments", tags=["comments"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


def _safe_oid(v: str) -> Optional[ObjectId]:
    try:
        return ObjectId(v)
    except Exception:
        return None


async def _resolve_target(db, target_type: str, target_id: str, user_id: str) -> dict:
    """Verify the user can access `target_id`, and return context for the
    comment: {workspace_id, can_admin} — can_admin means this user can
    moderate (resolve/reopen/delete) any comment on this target, not just
    their own.
    """
    oid = _safe_oid(target_id)
    if not oid:
        raise HTTPException(404, "Not found")

    if target_type == "workspace_item":
        from routers.workspaces import _assert_member, _role_of
        item = await db.workspace_items.find_one({"_id": oid, "deleted_at": None})
        if not item:
            raise HTTPException(404, "Not found")
        ws = await db.workspaces.find_one({"_id": ObjectId(item["workspace_id"])})
        if not ws:
            raise HTTPException(404, "Not found")
        _assert_member(ws, user_id)
        return {"workspace_id": item["workspace_id"], "can_admin": _role_of(ws, user_id) in ("Owner", "Administrator")}

    if target_type == "workspace":
        from routers.workspaces import _assert_member, _role_of
        ws = await db.workspaces.find_one({"_id": oid})
        if not ws:
            raise HTTPException(404, "Not found")
        _assert_member(ws, user_id)
        return {"workspace_id": target_id, "can_admin": _role_of(ws, user_id) in ("Owner", "Administrator")}

    if target_type == "task":
        from routers.projects import _assert_project_member
        task = await db.tasks.find_one({"_id": oid})
        if not task:
            raise HTTPException(404, "Not found")
        project = await _assert_project_member(db, task["project_id"], user_id)
        return {"workspace_id": None, "can_admin": project.get("owner_id") == user_id}

    if target_type == "manuscript":
        from routers.manuscripts import _assert_author
        doc = await db.manuscripts.find_one({"_id": oid})
        if not doc:
            raise HTTPException(404, "Not found")
        _assert_author(doc, user_id)
        return {"workspace_id": None, "can_admin": doc.get("lead_author_id") == user_id}

    raise HTTPException(400, f"target_type must be one of {COMMENT_TARGET_TYPES}")


async def _notify_mentions(db, *, mentions: list[str], author_id: str, author_name: str,
                            content: str, target_type: str, target_id: str) -> None:
    """Best-effort mention notifications — never blocks or fails the request."""
    if not mentions:
        return
    try:
        from repo.notifications import NotificationRepository
        repo = NotificationRepository(db, SecurityContext.system())
        preview = content.strip()[:140]
        for uid in set(mentions):
            if uid == author_id:
                continue
            await repo.create_notification(
                uid,
                title=f"{author_name} mentioned you",
                message=preview,
                type="mention",
                link=f"/{target_type}/{target_id}",
                meta={"target_type": target_type, "target_id": target_id},
            )
    except Exception as exc:
        log.warning("Mention notification failed (non-fatal): %s", exc)


@router.get("")
async def list_comments(
    target_type: str,
    target_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _resolve_target(db, target_type, target_id, user["id"])

    q = {"target_type": target_type, "target_id": target_id, "deleted_at": None}
    total = await db.item_comments.count_documents(q)
    docs = await db.item_comments.find(q).sort("created_at", 1).skip(skip).limit(limit).to_list(limit)
    return {"comments": [_ser(d) for d in docs], "total": total, "skip": skip, "limit": limit}


@router.post("", status_code=201)
@limiter.limit(WRITE_RATE)
async def create_comment(request: Request, payload: GenericCommentCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ctx = await _resolve_target(db, payload.target_type, payload.target_id, user["id"])

    parent_workspace_id = ctx.get("workspace_id")
    if payload.parent_comment_id:
        poid = _safe_oid(payload.parent_comment_id)
        if not poid:
            raise HTTPException(400, "Invalid parent_comment_id")
        parent = await db.item_comments.find_one({"_id": poid, "deleted_at": None})
        if not parent or parent["target_type"] != payload.target_type or parent["target_id"] != payload.target_id:
            raise HTTPException(400, "Parent comment not found on this target")

    now = _now()
    doc = {
        "target_type": payload.target_type,
        "target_id":   payload.target_id,
        "workspace_id": parent_workspace_id,
        "author_id":   user["id"],
        "author_name": user.get("full_name", "Someone"),
        "content":     payload.content,
        "parent_comment_id": payload.parent_comment_id,
        "mentions":    payload.mentions or [],
        "resolved":    False,
        "resolved_by": None,
        "resolved_at": None,
        "created_at":  now,
        "updated_at":  now,
        "deleted_at":  None,
    }
    res = await db.item_comments.insert_one(doc)
    doc["_id"] = res.inserted_id

    AuditTrail(db).record(
        ctx=SecurityContext.from_user(user), collection="item_comments",
        operation="create", doc_id=str(res.inserted_id), after=_ser(doc),
    )

    # Notify: explicit @mentions, plus the parent comment's author on a reply
    notify_ids = list(payload.mentions or [])
    if payload.parent_comment_id and parent.get("author_id"):
        notify_ids.append(parent["author_id"])
    await _notify_mentions(
        db, mentions=notify_ids, author_id=user["id"], author_name=doc["author_name"],
        content=payload.content, target_type=payload.target_type, target_id=payload.target_id,
    )

    return _ser(doc)


@router.patch("/{comment_id}")
async def update_comment(comment_id: str, payload: GenericCommentUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _safe_oid(comment_id)
    if not oid:
        raise HTTPException(404, "Not found")
    comment = await db.item_comments.find_one({"_id": oid, "deleted_at": None})
    if not comment:
        raise HTTPException(404, "Not found")

    ctx = await _resolve_target(db, comment["target_type"], comment["target_id"], user["id"])
    is_author = comment["author_id"] == user["id"]

    update: dict = {}
    if payload.content is not None:
        if not is_author:
            raise HTTPException(403, "Only the comment author can edit its content")
        update["content"] = payload.content
    if payload.resolved is not None:
        if not (is_author or ctx.get("can_admin")):
            raise HTTPException(403, "Only the author or a workspace admin can resolve/reopen this thread")
        update["resolved"] = payload.resolved
        update["resolved_by"] = user["id"] if payload.resolved else None
        update["resolved_at"] = _now() if payload.resolved else None

    if update:
        update["updated_at"] = _now()
        await db.item_comments.update_one({"_id": oid}, {"$set": update})
        AuditTrail(db).record(
            ctx=SecurityContext.from_user(user), collection="item_comments",
            operation="update", doc_id=comment_id, before=_ser(comment), after={**_ser(comment), **update},
        )

    fresh = await db.item_comments.find_one({"_id": oid})
    return _ser(fresh)


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(comment_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _safe_oid(comment_id)
    if not oid:
        raise HTTPException(404, "Not found")
    comment = await db.item_comments.find_one({"_id": oid, "deleted_at": None})
    if not comment:
        raise HTTPException(404, "Not found")

    ctx = await _resolve_target(db, comment["target_type"], comment["target_id"], user["id"])
    if not (comment["author_id"] == user["id"] or ctx.get("can_admin")):
        raise HTTPException(403, "Only the author or a workspace admin can delete this comment")

    await db.item_comments.update_one({"_id": oid}, {"$set": {"deleted_at": _now(), "updated_at": _now()}})
    AuditTrail(db).record(
        ctx=SecurityContext.from_user(user), collection="item_comments",
        operation="soft_delete", doc_id=comment_id, before=_ser(comment),
    )
