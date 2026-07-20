"""Messaging system — conversations, messages, attachments, shared resources, real-time."""
import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from auth_utils import get_current_user, JWT_ALGORITHM
from db import get_db
from services.realtime import manager
from services.storage_service import put_object, get_object, build_path
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.messaging")

router = APIRouter(prefix="/api", tags=["messaging"])

ALLOWED_MIME = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

CONTEXT_TYPES = {"direct", "collaboration", "project", "workspace", "manuscript"}

# Academic resources that can be shared inline
ACADEMIC_TYPES = {"journal", "conference", "grant", "publication", "project", "manuscript"}

REACTION_EMOJIS = {"👍", "🎉", "✅", "💡", "❓"}


# ============== Schemas ==============
class CreateConversationIn(BaseModel):
    type: str  # one of CONTEXT_TYPES
    context_id: Optional[str] = ""  # required for non-direct
    other_user_id: Optional[str] = ""  # for direct
    title: Optional[str] = ""


class MessageIn(BaseModel):
    content: Optional[str] = ""
    attachment_ids: Optional[List[str]] = []
    shared_resources: Optional[List[dict]] = []  # [{type, id, title, subtitle}]
    reply_to_id: Optional[str] = ""


class MessageEdit(BaseModel):
    content: str


class TypingIn(BaseModel):
    typing: bool


class ReactionIn(BaseModel):
    emoji: str


# ============== Helpers ==============
def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


async def _is_member(conv_id: str, user_id: str) -> bool:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    return bool(await db.conversation_members.find_one({"conversation_id": conv_id, "user_id": user_id}))


async def _assert_member(conv_id: str, user_id: str):
    if not await _is_member(conv_id, user_id):
        raise HTTPException(status_code=403, detail="Not a member of this conversation")


async def _enrich_message(m: dict, reactions_map: "dict | None" = None) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    out = _ser(m)
    sender = await db.users.find_one({"_id": ObjectId(m["sender_id"])})
    if sender:
        out["sender"] = {
            "id": str(sender["_id"]),
            "full_name": sender.get("full_name", ""),
            "avatar_url": sender.get("avatar_url", ""),
        }
    # resolve attachments
    att_ids = m.get("attachment_ids") or []
    if att_ids:
        try:
            oids = [ObjectId(a) for a in att_ids]
        except Exception:
            oids = []
        atts = await db.message_attachments.find({"_id": {"$in": oids}}).to_list(20)
        out["attachments"] = [
            {
                "id": str(a["_id"]),
                "filename": a.get("original_filename", ""),
                "content_type": a.get("content_type", ""),
                "size": a.get("size", 0),
                "kind": a.get("kind", "file"),
            }
            for a in atts
        ]
    else:
        out["attachments"] = []
    out["shared_resources"] = m.get("shared_resources") or []
    # edit metadata
    out["edited_at"] = m.get("edited_at")
    out["edited"] = bool(m.get("edited_at"))
    # reply preview
    if m.get("reply_to_id"):
        try:
            parent = await db.messages.find_one({"_id": ObjectId(m["reply_to_id"])})
        except Exception:
            parent = None
        if parent:
            psender = await db.users.find_one({"_id": ObjectId(parent["sender_id"])})
            snippet = (parent.get("content") or "📎 Attachment")[:140]
            out["reply_to"] = {
                "id": str(parent["_id"]),
                "snippet": snippet,
                "sender_name": (psender or {}).get("full_name", ""),
                "deleted": bool(parent.get("deleted")),
            }
    # reactions: {emoji: [{user_id, full_name}]} — use pre-loaded map when available
    mid = str(m["_id"])
    if reactions_map is not None:
        out["reactions"] = reactions_map.get(mid, {})
    else:
        r_docs = await db.message_reactions.find({"message_id": mid}).to_list(500)
        r_agg: dict = {}
        for r in r_docs:
            e = r["emoji"]
            if e not in r_agg:
                r_agg[e] = []
            r_agg[e].append({"user_id": r["user_id"], "full_name": r.get("full_name", "")})
        out["reactions"] = r_agg
    return out


async def _get_or_create_direct(user_a: str, user_b: str) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    if user_a == user_b:
        raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself")
    sorted_ids = sorted([user_a, user_b])
    key = f"direct:{sorted_ids[0]}:{sorted_ids[1]}"
    conv = await db.conversations.find_one({"context_key": key})
    if conv:
        return conv
    doc = {
        "type": "direct",
        "context_id": "",
        "context_key": key,
        "title": "",
        "created_by": user_a,
        "created_at": _now_iso(),
        "last_message_at": _now_iso(),
        "last_message_preview": "",
    }
    res = await db.conversations.insert_one(doc)
    doc["_id"] = res.inserted_id
    for uid in sorted_ids:
        await db.conversation_members.insert_one({
            "conversation_id": str(res.inserted_id),
            "user_id": uid,
            "role": "member",
            "joined_at": _now_iso(),
            "last_read_at": _now_iso(),
            "muted": False,
        })
    return doc


async def _get_or_create_context(context_type: str, context_id: str, creator_id: str) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    if context_type not in CONTEXT_TYPES or context_type == "direct":
        raise HTTPException(status_code=400, detail="Invalid context_type")
    key = f"{context_type}:{context_id}"
    conv = await db.conversations.find_one({"context_key": key})

    # Resolve members + title from context
    member_ids, title = await _resolve_context_members(context_type, context_id, creator_id)
    if creator_id not in member_ids:
        member_ids = [creator_id] + member_ids

    if conv:
        # Sync membership for context conversations (people accepted into a collab show up)
        existing = {m["user_id"] async for m in db.conversation_members.find({"conversation_id": str(conv["_id"])})}
        for uid in member_ids:
            if uid not in existing:
                await db.conversation_members.insert_one({
                    "conversation_id": str(conv["_id"]),
                    "user_id": uid,
                    "role": "member",
                    "joined_at": _now_iso(),
                    "last_read_at": _now_iso(),
                    "muted": False,
                })
        return conv

    doc = {
        "type": context_type,
        "context_id": context_id,
        "context_key": key,
        "title": title,
        "created_by": creator_id,
        "created_at": _now_iso(),
        "last_message_at": _now_iso(),
        "last_message_preview": "",
    }
    res = await db.conversations.insert_one(doc)
    for uid in set(member_ids):
        await db.conversation_members.insert_one({
            "conversation_id": str(res.inserted_id),
            "user_id": uid,
            "role": "member",
            "joined_at": _now_iso(),
            "last_read_at": _now_iso(),
            "muted": False,
        })
    doc["_id"] = res.inserted_id
    return doc


async def _resolve_context_members(context_type: str, context_id: str, fallback_user_id: str):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(context_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid context_id")
    if context_type == "collaboration":
        c = await db.collaborations.find_one({"_id": oid})
        if not c:
            raise HTTPException(status_code=404, detail="Collaboration not found")
        return list(c.get("members", [])), f"Collab · {c.get('title','')}"[:80]
    if context_type == "project":
        p = await db.projects.find_one({"_id": oid})
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        return list(p.get("members", [])), f"Project · {p.get('title','')}"[:80]
    if context_type == "workspace":
        w = await db.workspaces.find_one({"_id": oid})
        if not w:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return list(w.get("members", [])), f"Workspace · {w.get('name','')}"[:80]
    if context_type == "manuscript":
        m = await db.manuscripts.find_one({"_id": oid})
        if not m:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return list(m.get("authors", [])), f"Manuscript · {m.get('title','')}"[:80]
    return [fallback_user_id], ""


# ============== Conversation endpoints ==============
@router.get("/conversations")
async def list_conversations(type: Optional[str] = None, q: Optional[str] = None, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    memberships = await db.conversation_members.find({"user_id": user["id"]}).to_list(500)
    conv_ids = [m["conversation_id"] for m in memberships]
    if not conv_ids:
        return []
    try:
        oids = [ObjectId(c) for c in conv_ids]
    except Exception:
        oids = []
    query = {"_id": {"$in": oids}}
    if type and type in CONTEXT_TYPES:
        query["type"] = type
    convs = await db.conversations.find(query).sort("last_message_at", -1).to_list(500)

    member_map = {m["conversation_id"]: m for m in memberships}
    out = []
    for c in convs:
        item = _ser(c)
        mem = member_map.get(item["id"]) or {}
        item["last_read_at"] = mem.get("last_read_at")
        item["muted"] = bool(mem.get("muted"))
        # unread count
        unread = 0
        try:
            unread = await db.messages.count_documents({
                "conversation_id": item["id"],
                "sender_id": {"$ne": user["id"]},
                "created_at": {"$gt": mem.get("last_read_at") or ""},
            })
        except Exception:
            unread = 0
        item["unread"] = unread
        # presentation: for direct, surface the other user
        if c["type"] == "direct":
            other = await db.conversation_members.find_one({
                "conversation_id": item["id"], "user_id": {"$ne": user["id"]}
            })
            if other:
                ou = await db.users.find_one({"_id": ObjectId(other["user_id"])})
                if ou:
                    item["other_user"] = {
                        "id": str(ou["_id"]), "full_name": ou.get("full_name", ""),
                        "avatar_url": ou.get("avatar_url", ""), "institution": ou.get("institution", ""),
                    }
        # member preview
        member_docs = await db.conversation_members.find({"conversation_id": item["id"]}).limit(10).to_list(10)
        mids = []
        for md in member_docs:
            try:
                mids.append(ObjectId(md["user_id"]))
            except Exception:
                pass
        users = await db.users.find({"_id": {"$in": mids}}).to_list(10)
        item["members_preview"] = [
            {"id": str(u["_id"]), "full_name": u.get("full_name", ""), "avatar_url": u.get("avatar_url", "")}
            for u in users
        ]
        if q:
            blob = f"{item.get('title','')} {(item.get('other_user') or {}).get('full_name','')} {item.get('last_message_preview','')}".lower()
            if q.lower() not in blob:
                continue
        out.append(item)
    return out


@router.post("/conversations")
async def create_or_get_conversation(payload: CreateConversationIn, user: dict = Depends(get_current_user)):
    if payload.type not in CONTEXT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid conversation type")
    if payload.type == "direct":
        if not payload.other_user_id:
            raise HTTPException(status_code=400, detail="other_user_id required for direct")
        try:
            ObjectId(payload.other_user_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid other_user_id")
        conv = await _get_or_create_direct(user["id"], payload.other_user_id)
    else:
        if not payload.context_id:
            raise HTTPException(status_code=400, detail="context_id required for non-direct")
        conv = await _get_or_create_context(payload.type, payload.context_id, user["id"])
    return _ser(conv)


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    try:
        conv = await db.conversations.find_one({"_id": ObjectId(conv_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    item = _ser(conv)
    members = await db.conversation_members.find({"conversation_id": conv_id}).to_list(50)
    mids = []
    for m in members:
        try:
            mids.append(ObjectId(m["user_id"]))
        except Exception:
            pass
    users = await db.users.find({"_id": {"$in": mids}}).to_list(50)
    user_map = {str(u["_id"]): u for u in users}
    item["members"] = []
    for m in members:
        u = user_map.get(m["user_id"])
        if not u:
            continue
        item["members"].append({
            "id": m["user_id"], "full_name": u.get("full_name", ""), "avatar_url": u.get("avatar_url", ""),
            "institution": u.get("institution", ""), "role": m.get("role", "member"),
        })
    if conv["type"] == "direct":
        other = next((m for m in members if m["user_id"] != user["id"]), None)
        if other:
            u = user_map.get(other["user_id"])
            if u:
                item["other_user"] = {
                    "id": str(u["_id"]), "full_name": u.get("full_name", ""),
                    "avatar_url": u.get("avatar_url", ""), "institution": u.get("institution", ""),
                }
    return item


# ============== Messages ==============
MENTION_RE = re.compile(r"@([a-zA-Z0-9._-]{2,})")


async def _extract_mentions(content: str, conv_id: str) -> list:
    if not content:
        return []
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    handles = MENTION_RE.findall(content)
    if not handles:
        return []
    member_docs = await db.conversation_members.find({"conversation_id": conv_id}).to_list(200)
    mids = []
    for m in member_docs:
        try:
            mids.append(ObjectId(m["user_id"]))
        except Exception:
            pass
    members = await db.users.find({"_id": {"$in": mids}}).to_list(200)
    out = []
    for u in members:
        local = (u.get("email") or "").split("@")[0]
        fn = (u.get("full_name") or "").lower()
        for h in handles:
            hl = h.lower()
            if hl == local.lower() or hl in fn.replace(" ", ".").replace(" ", ""):
                out.append(str(u["_id"]))
                break
    return list(set(out))


@router.get("/conversations/{conv_id}/messages")
async def list_messages(conv_id: str, limit: int = 100, before: Optional[str] = None, q: Optional[str] = None, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    query: dict = {"conversation_id": conv_id, "deleted": {"$ne": True}}
    if before:
        query["created_at"] = {"$lt": before}
    if q:
        query["content"] = {"$regex": q, "$options": "i"}
    docs = await db.messages.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    docs.reverse()
    # Batch-load reactions to avoid N+1 (one query for all messages in the page)
    msg_ids = [str(d["_id"]) for d in docs]
    r_docs = await db.message_reactions.find({"message_id": {"$in": msg_ids}}).to_list(5000) if msg_ids else []
    reactions_map: dict = {}
    for r in r_docs:
        mid = r["message_id"]
        e = r["emoji"]
        if mid not in reactions_map:
            reactions_map[mid] = {}
        if e not in reactions_map[mid]:
            reactions_map[mid][e] = []
        reactions_map[mid][e].append({"user_id": r["user_id"], "full_name": r.get("full_name", "")})
    return [await _enrich_message(d, reactions_map=reactions_map) for d in docs]


@router.post("/conversations/{conv_id}/messages")
async def post_message(conv_id: str, payload: MessageIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    content = (payload.content or "").strip()
    has_attach = bool(payload.attachment_ids)
    has_shares = bool(payload.shared_resources)
    if not content and not has_attach and not has_shares:
        raise HTTPException(status_code=400, detail="Message is empty")

    # Validate shared resources schema
    shares = []
    for s in (payload.shared_resources or []):
        t = (s or {}).get("type")
        if t not in ACADEMIC_TYPES:
            continue
        shares.append({
            "type": t,
            "id": str(s.get("id") or ""),
            "title": (s.get("title") or "")[:200],
            "subtitle": (s.get("subtitle") or "")[:200],
        })

    # Validate attachments belong to sender and exist
    att_ids = []
    if has_attach:
        try:
            oids = [ObjectId(a) for a in payload.attachment_ids]
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid attachment_ids")
        atts = await db.message_attachments.find({"_id": {"$in": oids}, "owner_id": user["id"]}).to_list(20)
        att_ids = [str(a["_id"]) for a in atts]

    mentions = await _extract_mentions(content, conv_id)
    # Validate reply_to belongs to this conversation
    reply_to_id = ""
    if payload.reply_to_id:
        try:
            parent = await db.messages.find_one({"_id": ObjectId(payload.reply_to_id)})
        except Exception:
            parent = None
        if not parent or parent.get("conversation_id") != conv_id:
            raise HTTPException(status_code=400, detail="reply_to_id does not belong to this conversation")
        reply_to_id = payload.reply_to_id
    msg = {
        "conversation_id": conv_id,
        "sender_id": user["id"],
        "content": content,
        "attachment_ids": att_ids,
        "shared_resources": shares,
        "mentions": mentions,
        "reply_to_id": reply_to_id,
        "deleted": False,
        "edited_at": None,
        "edit_history": [],
        "created_at": _now_iso(),
    }
    res = await db.messages.insert_one(msg)
    msg["_id"] = res.inserted_id

    # Preview
    preview = content if content else ("📎 Attachment" if has_attach else "🔗 Shared resource")
    await db.conversations.update_one(
        {"_id": ObjectId(conv_id)},
        {"$set": {"last_message_at": msg["created_at"], "last_message_preview": preview[:140]}},
    )
    # Mark sender as read up to now
    await db.conversation_members.update_one(
        {"conversation_id": conv_id, "user_id": user["id"]},
        {"$set": {"last_read_at": msg["created_at"]}},
    )

    enriched = await _enrich_message(msg)
    # Broadcast over WS
    await manager.broadcast(conv_id, {"type": "message", "message": enriched})

    # Notifications + per-user unread WS push
    from services.notifications_service import dispatch, NotificationEvent
    members = await db.conversation_members.find({"conversation_id": conv_id}).to_list(200)
    conv = await db.conversations.find_one({"_id": ObjectId(conv_id)})
    title = conv.get("title", "") or "New message"
    for m in members:
        if m["user_id"] == user["id"]:
            continue
        is_mention = m["user_id"] in mentions
        await dispatch(NotificationEvent(
            user_id=m["user_id"],
            kind="mention" if is_mention else "message",
            title="You were mentioned" if is_mention else f"New message · {title}",
            body=f"{user.get('full_name','Someone')}: {preview[:80]}",
            link=f"/messages/c/{conv_id}",
            actor_id=user["id"],
            payload={"conversation_id": conv_id, "message_id": str(res.inserted_id)},
        ))
        # Live unread badge push
        await manager.broadcast_user(m["user_id"], {
            "type": "unread", "conversation_id": conv_id, "delta": 1, "preview": preview[:140],
        })

    return enriched


@router.patch("/conversations/{conv_id}/messages/{msg_id}")
async def edit_message(conv_id: str, msg_id: str, payload: MessageEdit, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    try:
        oid = ObjectId(msg_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    msg = await db.messages.find_one({"_id": oid})
    if not msg or msg.get("conversation_id") != conv_id or msg.get("deleted"):
        raise HTTPException(status_code=404, detail="Not found")
    if msg["sender_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the author can edit")
    new_content = (payload.content or "").strip()
    if not new_content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    now = _now_iso()
    history_entry = {"content": msg.get("content", ""), "edited_at": now}
    await db.messages.update_one(
        {"_id": oid},
        {
            "$set": {"content": new_content, "edited_at": now},
            "$push": {"edit_history": history_entry},
        },
    )
    updated = await db.messages.find_one({"_id": oid})
    enriched = await _enrich_message(updated)
    await manager.broadcast(conv_id, {"type": "message_edited", "message": enriched})
    return enriched


@router.get("/conversations/{conv_id}/messages/{msg_id}/history")
async def message_history(conv_id: str, msg_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    try:
        msg = await db.messages.find_one({"_id": ObjectId(msg_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not msg or msg.get("conversation_id") != conv_id:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": str(msg["_id"]),
        "current_content": msg.get("content", ""),
        "current_edited_at": msg.get("edited_at"),
        "history": msg.get("edit_history", []),
        "created_at": msg.get("created_at"),
    }


@router.post("/conversations/{conv_id}/read")
async def mark_read(conv_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    now = _now_iso()
    await db.conversation_members.update_one(
        {"conversation_id": conv_id, "user_id": user["id"]},
        {"$set": {"last_read_at": now}},
    )
    # message_reads marker (per-message read receipts can be reconstructed from this)
    await db.message_reads.update_one(
        {"conversation_id": conv_id, "user_id": user["id"]},
        {"$set": {"last_read_at": now, "updated_at": now}},
        upsert=True,
    )
    await manager.broadcast(conv_id, {"type": "read", "user_id": user["id"], "at": now})
    # Push a "cleared" event to the reader's own user-channel so all their tabs sync
    await manager.broadcast_user(user["id"], {"type": "unread", "conversation_id": conv_id, "reset": True})
    return {"ok": True, "at": now}


@router.post("/conversations/{conv_id}/typing")
async def set_typing(conv_id: str, payload: TypingIn, user: dict = Depends(get_current_user)):
    await _assert_member(conv_id, user["id"])
    await manager.broadcast(conv_id, {
        "type": "typing", "user_id": user["id"],
        "full_name": user.get("full_name", ""),
        "typing": bool(payload.typing),
    })
    return {"ok": True}


@router.get("/conversations/unread/count")
async def total_unread(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Single aggregation replaces N+1 count_documents loop (one round-trip regardless of conversation count)
    pipeline = [
        {"$match": {"user_id": user["id"]}},
        {"$lookup": {
            "from": "messages",
            "let": {
                "conv_id": "$conversation_id",
                "last_read": {"$ifNull": ["$last_read_at", ""]},
            },
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$conversation_id", "$$conv_id"]},
                    {"$ne": ["$sender_id", user["id"]]},
                    {"$gt": ["$created_at", "$$last_read"]},
                ]}}},
                {"$count": "n"},
            ],
            "as": "unread_msgs",
        }},
        {"$project": {"count": {"$ifNull": [{"$arrayElemAt": ["$unread_msgs.n", 0]}, 0]}}},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}},
    ]
    result = await db.conversation_members.aggregate(pipeline).to_list(1)
    return {"unread": result[0]["total"] if result else 0}


# ============== Message delete ==============

@router.delete("/conversations/{conv_id}/messages/{msg_id}", status_code=204)
async def delete_message(conv_id: str, msg_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    try:
        oid = ObjectId(msg_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    msg = await db.messages.find_one({"_id": oid})
    if not msg or msg.get("conversation_id") != conv_id or msg.get("deleted"):
        raise HTTPException(status_code=404, detail="Not found")
    if msg["sender_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the author can delete")
    await db.messages.update_one(
        {"_id": oid},
        {"$set": {"deleted": True, "content": "", "attachment_ids": [], "deleted_at": _now_iso()}},
    )
    await manager.broadcast(conv_id, {"type": "message_deleted", "message_id": msg_id})


# ============== Reactions ==============

@router.post("/conversations/{conv_id}/messages/{msg_id}/reactions")
async def add_reaction(conv_id: str, msg_id: str, payload: ReactionIn, user: dict = Depends(get_current_user)):
    if payload.emoji not in REACTION_EMOJIS:
        raise HTTPException(status_code=400, detail=f"Emoji must be one of: {', '.join(sorted(REACTION_EMOJIS))}")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    try:
        ObjectId(msg_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    await db.message_reactions.update_one(
        {"message_id": msg_id, "user_id": user["id"], "emoji": payload.emoji},
        {"$set": {
            "message_id": msg_id,
            "user_id": user["id"],
            "emoji": payload.emoji,
            "full_name": user.get("full_name", ""),
            "created_at": _now_iso(),
        }},
        upsert=True,
    )
    await manager.broadcast(conv_id, {
        "type": "reaction_added",
        "message_id": msg_id,
        "emoji": payload.emoji,
        "user_id": user["id"],
        "full_name": user.get("full_name", ""),
    })
    return {"ok": True}


@router.delete("/conversations/{conv_id}/messages/{msg_id}/reactions/{emoji}", status_code=204)
async def remove_reaction(conv_id: str, msg_id: str, emoji: str, user: dict = Depends(get_current_user)):
    from urllib.parse import unquote
    emoji = unquote(emoji)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    await db.message_reactions.delete_one({"message_id": msg_id, "user_id": user["id"], "emoji": emoji})
    await manager.broadcast(conv_id, {
        "type": "reaction_removed",
        "message_id": msg_id,
        "emoji": emoji,
        "user_id": user["id"],
    })


# ============== Conversation management ==============

@router.post("/conversations/{conv_id}/leave")
async def leave_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    try:
        conv = await db.conversations.find_one({"_id": ObjectId(conv_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if conv and conv.get("type") == "direct":
        raise HTTPException(status_code=400, detail="Cannot leave a direct message conversation")
    await db.conversation_members.delete_one({"conversation_id": conv_id, "user_id": user["id"]})
    await manager.broadcast(conv_id, {"type": "member_left", "user_id": user["id"]})
    return {"ok": True}


@router.post("/conversations/{conv_id}/mute")
async def toggle_mute(conv_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_member(conv_id, user["id"])
    mem = await db.conversation_members.find_one({"conversation_id": conv_id, "user_id": user["id"]})
    new_muted = not bool((mem or {}).get("muted"))
    await db.conversation_members.update_one(
        {"conversation_id": conv_id, "user_id": user["id"]},
        {"$set": {"muted": new_muted}},
    )
    return {"ok": True, "muted": new_muted}


# ============== Attachments / uploads ==============
@router.post("/uploads")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 25 MB)")
    ext = ALLOWED_MIME[file.content_type]
    path = build_path(user["id"], ext)
    try:
        result = await asyncio.to_thread(put_object, path, data, file.content_type)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {str(e)[:200]}")
    kind = "image" if file.content_type.startswith("image/") else "file"
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "owner_id": user["id"],
        "storage_path": result["path"],
        "original_filename": file.filename or f"upload.{ext}",
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "kind": kind,
        "is_deleted": False,
        "created_at": _now_iso(),
    }
    res = await db.message_attachments.insert_one(doc)
    return {
        "id": str(res.inserted_id),
        "filename": doc["original_filename"],
        "content_type": doc["content_type"],
        "size": doc["size"],
        "kind": kind,
    }


@router.get("/uploads/{attachment_id}")
async def download_file(attachment_id: str, request_user: dict = Depends(get_current_user)):
    from fastapi.responses import Response
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        att = await db.message_attachments.find_one({"_id": ObjectId(attachment_id), "is_deleted": False})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not att:
        raise HTTPException(status_code=404, detail="Not found")
    # Authorisation: owner OR member of any conversation where this attachment is used
    if att["owner_id"] != request_user["id"]:
        msg = await db.messages.find_one({"attachment_ids": attachment_id})
        if not msg:
            raise HTTPException(status_code=403, detail="Forbidden")
        if not await _is_member(msg["conversation_id"], request_user["id"]):
            raise HTTPException(status_code=403, detail="Forbidden")
    try:
        data, ctype = await asyncio.to_thread(get_object, att["storage_path"])
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Storage error: {str(e)[:200]}")
    return Response(content=data, media_type=att.get("content_type", ctype),
                    headers={"Content-Disposition": f'inline; filename="{att.get("original_filename","file")}"'})


# Convenience: GET via query-param auth for <img src>
@router.get("/uploads/{attachment_id}/blob")
async def download_blob(attachment_id: str, token: Optional[str] = Query(None)):
    from fastapi.responses import Response
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        data = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if data.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        uid = data["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        att = await db.message_attachments.find_one({"_id": ObjectId(attachment_id), "is_deleted": False})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not att:
        raise HTTPException(status_code=404, detail="Not found")
    if att["owner_id"] != uid:
        msg = await db.messages.find_one({"attachment_ids": attachment_id})
        if not msg or not await _is_member(msg["conversation_id"], uid):
            raise HTTPException(status_code=403, detail="Forbidden")
    try:
        data, ctype = await asyncio.to_thread(get_object, att["storage_path"])
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Storage error: {str(e)[:200]}")
    from fastapi.responses import Response
    return Response(content=data, media_type=att.get("content_type", ctype))


# ============== WebSocket ==============
def _ws_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        logger.error("JWT_SECRET env var not set — WebSocket auth will fail for all clients")
    return secret


@router.websocket("/ws/conversations/{conv_id}")
async def ws_conversation(websocket: WebSocket, conv_id: str):
    # Accept BEFORE any auth checks — closing before accept causes HTTP 403 (ASGI spec behaviour).
    # Auth failures are communicated via WebSocket close codes after the handshake completes.
    await websocket.accept()

    token = websocket.cookies.get("access_token")
    if not token:
        logger.warning("WS /ws/conversations/%s: no access_token cookie — closing 4401", conv_id)
        await websocket.close(code=4401)
        return

    jwt_secret = _ws_jwt_secret()
    if not jwt_secret:
        await websocket.close(code=1011)  # 1011 = internal server error
        return

    try:
        data = jwt.decode(token, jwt_secret, algorithms=[JWT_ALGORITHM])
        if data.get("type") != "access":
            logger.warning(
                "WS /ws/conversations/%s: wrong token type '%s' — closing 4401",
                conv_id, data.get("type"),
            )
            await websocket.close(code=4401)
            return
        user_id = data["sub"]
    except jwt.ExpiredSignatureError:
        logger.debug("WS /ws/conversations/%s: expired token — closing 4401", conv_id)
        await websocket.close(code=4401)
        return
    except jwt.InvalidTokenError as exc:
        logger.warning(
            "WS /ws/conversations/%s: invalid token (%s) — closing 4401",
            conv_id, type(exc).__name__,
        )
        await websocket.close(code=4401)
        return

    try:
        is_member = await _is_member(conv_id, user_id)
    except Exception as exc:
        logger.error(
            "WS /ws/conversations/%s: DB error during member check: %s — closing 1011",
            conv_id, str(exc)[:120],
        )
        await websocket.close(code=1011)
        return

    if not is_member:
        logger.warning(
            "WS /ws/conversations/%s: user=%s not a member — closing 4403",
            conv_id, user_id[:8],
        )
        await websocket.close(code=4403)
        return

    logger.debug("WS /ws/conversations/%s: user=%s connected", conv_id, user_id[:8])
    await manager.connect(conv_id, user_id, websocket)
    try:
        await manager.broadcast(conv_id, {"type": "presence", "user_id": user_id, "online": True}, exclude_ws=websocket)
        while True:
            payload = await websocket.receive_json()
            kind = payload.get("type")
            if kind == "typing":
                await manager.broadcast(conv_id, {
                    "type": "typing", "user_id": user_id, "typing": bool(payload.get("typing")),
                }, exclude_ws=websocket)
            elif kind == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(conv_id, websocket)
        try:
            await manager.broadcast(conv_id, {"type": "presence", "user_id": user_id, "online": False})
        except Exception:
            pass


@router.websocket("/ws/user")
async def ws_user(websocket: WebSocket):
    """Per-user channel: receives unread-counter deltas + in-app notifications."""
    # Accept BEFORE any auth checks — closing before accept causes HTTP 403 (ASGI spec behaviour).
    await websocket.accept()

    token = websocket.cookies.get("access_token")
    if not token:
        logger.warning("WS /ws/user: no access_token cookie — closing 4401")
        await websocket.close(code=4401)
        return

    jwt_secret = _ws_jwt_secret()
    if not jwt_secret:
        await websocket.close(code=1011)
        return

    try:
        data = jwt.decode(token, jwt_secret, algorithms=[JWT_ALGORITHM])
        if data.get("type") != "access":
            logger.warning("WS /ws/user: wrong token type '%s' — closing 4401", data.get("type"))
            await websocket.close(code=4401)
            return
        user_id = data["sub"]
    except jwt.ExpiredSignatureError:
        logger.debug("WS /ws/user: expired token — closing 4401")
        await websocket.close(code=4401)
        return
    except jwt.InvalidTokenError as exc:
        logger.warning("WS /ws/user: invalid token (%s) — closing 4401", type(exc).__name__)
        await websocket.close(code=4401)
        return

    logger.debug("WS /ws/user: user=%s connected", user_id[:8])
    await manager.connect_user(user_id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            if payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_user(user_id, websocket)


@router.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket):
    """Admin OS live feed: super_admin-only. Receives curated domain events
    (new registrations, payments, security events, job failures, ...) so the
    admin panel updates in real time instead of polling."""
    # Accept BEFORE any auth checks — closing before accept causes HTTP 403 (ASGI spec behaviour).
    await websocket.accept()

    token = websocket.cookies.get("access_token")
    if not token:
        logger.warning("WS /ws/admin: no access_token cookie — closing 4401")
        await websocket.close(code=4401)
        return

    jwt_secret = _ws_jwt_secret()
    if not jwt_secret:
        await websocket.close(code=1011)
        return

    try:
        data = jwt.decode(token, jwt_secret, algorithms=[JWT_ALGORITHM])
        if data.get("type") != "access":
            logger.warning("WS /ws/admin: wrong token type '%s' — closing 4401", data.get("type"))
            await websocket.close(code=4401)
            return
        user_id = data["sub"]
    except jwt.ExpiredSignatureError:
        logger.debug("WS /ws/admin: expired token — closing 4401")
        await websocket.close(code=4401)
        return
    except jwt.InvalidTokenError as exc:
        logger.warning("WS /ws/admin: invalid token (%s) — closing 4401", type(exc).__name__)
        await websocket.close(code=4401)
        return

    try:
        from services.permissions import is_super_admin as _is_super_admin
        db = get_db()
        u = await db.users.find_one({"_id": ObjectId(user_id)}, {"role": 1, "email": 1})
    except Exception as exc:
        logger.error("WS /ws/admin: DB error during admin check: %s — closing 1011", str(exc)[:120])
        await websocket.close(code=1011)
        return

    if not u or not _is_super_admin(u):
        logger.warning("WS /ws/admin: user=%s not a super admin — closing 4403", user_id[:8])
        await websocket.close(code=4403)
        return

    logger.debug("WS /ws/admin: user=%s connected", user_id[:8])
    await manager.connect_admin(websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            if payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_admin(websocket)
