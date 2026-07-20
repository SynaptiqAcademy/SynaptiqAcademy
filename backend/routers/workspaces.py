"""Research Workspaces — full production router.

Collections:
  workspaces               core documents
  workspace_activity       activity/notes feed
  workspace_invitations    pending/accepted/declined invitations
  workspace_tasks          workspace-level tasks (separate from project tasks)
  conversations            auto-created group chat per workspace
  conversation_members     chat membership

New endpoints added vs. original (6):
  GET    /api/workspaces/{id}/dashboard
  GET    /api/workspaces/{id}/analytics
  GET    /api/workspaces/{id}/activity
  GET    /api/workspaces/{id}/search
  POST   /api/workspaces/{id}/invitations
  GET    /api/workspaces/invitations/mine
  POST   /api/workspaces/invitations/{inv_id}/respond
  PATCH  /api/workspaces/{id}/members/{uid}/role
  DELETE /api/workspaces/{id}/members/{uid}
  POST   /api/workspaces/{id}/leave
  POST   /api/workspaces/{id}/transfer
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from models import WorkspaceCreate, WorkspaceUpdate
from services.permissions import assert_quota
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.workspaces")
router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

# ── constants ──────────────────────────────────────────────────────────────────

WORKSPACE_TYPES = {
    "Research Project", "Manuscript", "Grant Proposal", "Conference Paper",
    "Doctoral Thesis", "Research Group", "Institutional Research Team",
    "Consulting Project", "Systematic Review", "Custom Workspace",
}

WS_ROLES = [
    "Owner", "Administrator", "Lead Researcher", "Co-Author", "Reviewer",
    "Research Assistant", "Statistician", "Observer",
]

ADMIN_ROLES = {"Owner", "Administrator"}

# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


def _role_of(doc: dict, user_id: str) -> str:
    roles = doc.get("member_roles") or {}
    if user_id in roles:
        return roles[user_id]
    if doc.get("owner_id") == user_id:
        return "Owner"
    return "Observer"


def _assert_member(doc: dict, user_id: str) -> None:
    if user_id not in (doc.get("members") or []) and doc.get("owner_id") != user_id:
        raise HTTPException(403, "Not a member of this workspace")


def _assert_admin(doc: dict, user_id: str) -> None:
    if _role_of(doc, user_id) not in ADMIN_ROLES:
        raise HTTPException(403, "Owner or Administrator role required")


async def _log_activity(db, workspace_id: str, actor_id: str, actor_name: str,
                        message: str, kind: str = "system") -> None:
    try:
        await db.workspace_activity.insert_one({
            "workspace_id": workspace_id,
            "actor_id":     actor_id,
            "actor_name":   actor_name,
            "message":      message,
            "kind":         kind,
            "created_at":   _now(),
        })
    except Exception as exc:
        log.warning("activity insert failed: %s", exc)


async def _notify(user_id: str, kind: str, title: str, body: str,
                  link: str, actor_id: str, payload: dict) -> None:
    try:
        from services.notifications_service import dispatch as _d, NotificationEvent as _NE
        await _d(_NE(user_id=user_id, kind=kind, title=title, body=body,
                     link=link, actor_id=actor_id, payload=payload))
    except Exception:
        pass


async def _enrich(doc: dict, db) -> dict:
    ws = _ser(doc)
    ws_id = ws["id"]
    member_ids = ws.get("members") or []
    proj_ids   = ws.get("project_ids") or []

    member_oids = [ObjectId(m) for m in member_ids if ObjectId.is_valid(m)]
    proj_oids   = [ObjectId(p) for p in proj_ids   if ObjectId.is_valid(p)]

    members_raw, projects_raw, activity_raw, docs_raw, manuscripts_raw = await asyncio.gather(
        db.users.find({"_id": {"$in": member_oids}},
                      {"full_name": 1, "academic_role": 1, "user_type": 1,
                       "primary_domain": 1, "institution": 1, "avatar_url": 1}).to_list(100),
        db.projects.find({"_id": {"$in": proj_oids}}).to_list(50) if proj_oids else asyncio.sleep(0),
        db.workspace_activity.find({"workspace_id": ws_id}).sort("created_at", -1).limit(20).to_list(20),
        db.repository_items.find({"workspace_id": ws_id}).sort("created_at", -1).limit(50).to_list(50),
        db.manuscripts.find({"workspace_id": ws_id}).sort("updated_at", -1).to_list(30),
    )

    roles = ws.get("member_roles") or {}
    ws["members_info"] = [
        {
            "id":           str(m["_id"]),
            "full_name":    m.get("full_name", ""),
            "academic_role": m.get("academic_role", ""),
            "user_type":    m.get("user_type"),
            "primary_domain": m.get("primary_domain"),
            "institution":  m.get("institution", ""),
            "avatar_url":   m.get("avatar_url"),
            "workspace_role": roles.get(str(m["_id"])) or ("Owner" if str(m["_id"]) == ws.get("owner_id") else "Researcher"),
        }
        for m in members_raw
    ]
    ws["projects"]    = [_ser(p) for p in (projects_raw or [])]
    ws["activity"]    = [_ser(a) for a in activity_raw]
    ws["documents"]   = [_ser(d) for d in docs_raw]
    ws["manuscripts"] = [_ser(m) for m in manuscripts_raw]
    return ws


# ── pydantic bodies ────────────────────────────────────────────────────────────

class InviteBody(BaseModel):
    user_id: str = Field(..., min_length=1)
    role:    str = Field("Researcher")
    message: Optional[str] = Field(None, max_length=500)


class RespondBody(BaseModel):
    decision: str  # "accept" | "decline"


class RoleBody(BaseModel):
    role: str


class TransferBody(BaseModel):
    new_owner_id: str


# ══════════════════════════════════════════════════════════════════════════════
# INVITATION ENDPOINTS — must be registered before /{workspace_id} to avoid clash
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/invitations/mine")
async def list_my_invitations(user: dict = Depends(get_current_user)):
    """Return pending workspace invitations addressed to the current user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    invs = await db.workspace_invitations.find(
        {"user_id": user["id"], "status": "pending"}
    ).sort("created_at", -1).to_list(50)

    ws_ids     = list({ObjectId(inv["workspace_id"]) for inv in invs if ObjectId.is_valid(inv.get("workspace_id", ""))})
    inviter_ids = list({ObjectId(inv["invited_by"]) for inv in invs if ObjectId.is_valid(inv.get("invited_by", ""))})

    ws_docs, inviter_docs = await asyncio.gather(
        db.workspaces.find({"_id": {"$in": ws_ids}}, {"name": 1, "description": 1, "workspace_type": 1}).to_list(50) if ws_ids else asyncio.sleep(0),
        db.users.find({"_id": {"$in": inviter_ids}}, {"full_name": 1, "institution": 1, "avatar_url": 1}).to_list(50) if inviter_ids else asyncio.sleep(0),
    )

    ws_map      = {str(d["_id"]): {"name": d.get("name",""), "description": d.get("description",""), "workspace_type": d.get("workspace_type","")} for d in (ws_docs or [])}
    inviter_map = {str(d["_id"]): {"id": str(d["_id"]), "full_name": d.get("full_name",""), "institution": d.get("institution",""), "avatar_url": d.get("avatar_url")} for d in (inviter_docs or [])}

    out = []
    for inv in invs:
        item = _ser(inv)
        item["workspace"] = ws_map.get(inv.get("workspace_id"), {})
        item["inviter"]   = inviter_map.get(inv.get("invited_by"), {})
        out.append(item)
    return out


@router.post("/invitations/{inv_id}/respond")
async def respond_invitation(inv_id: str, body: RespondBody, user: dict = Depends(get_current_user)):
    """Accept or decline a pending workspace invitation."""
    if body.decision not in ("accept", "decline"):
        raise HTTPException(400, "decision must be 'accept' or 'decline'")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(inv_id)
    except Exception:
        raise HTTPException(404, "Invitation not found")
    inv = await db.workspace_invitations.find_one({"_id": oid})
    if not inv or inv.get("user_id") != user["id"]:
        raise HTTPException(404, "Invitation not found")
    if inv.get("status") != "pending":
        raise HTTPException(409, f"Invitation is already {inv.get('status')}")

    status_new = "accepted" if body.decision == "accept" else "declined"
    now = _now()
    await db.workspace_invitations.update_one(
        {"_id": oid}, {"$set": {"status": status_new, "responded_at": now}}
    )

    if body.decision == "accept":
        ws_id = inv["workspace_id"]
        role  = inv.get("role", "Researcher")
        try:
            ws_oid = ObjectId(ws_id)
        except Exception:
            raise HTTPException(404, "Workspace not found")
        ws = await db.workspaces.find_one({"_id": ws_oid})
        if not ws:
            raise HTTPException(404, "Workspace not found")

        await db.workspaces.update_one(
            {"_id": ws_oid},
            {"$addToSet": {"members": user["id"]},
             "$set": {f"member_roles.{user['id']}": role, "updated_at": now}},
        )
        await _log_activity(db, ws_id, user["id"], user.get("full_name", "Someone"),
                            f"{user.get('full_name','Someone')} joined as {role}", kind="member_join")

        # Add to workspace group conversation
        try:
            conv_key = f"workspace:{ws_id}"
            conv = await db.conversations.find_one({"context_key": conv_key})
            if not conv:
                r = await db.conversations.insert_one({
                    "type": "workspace", "context_id": ws_id, "context_key": conv_key,
                    "title": ws.get("name", "Workspace"), "created_by": user["id"],
                    "created_at": now, "last_message_at": now, "last_message_preview": "",
                })
                conv_id = str(r.inserted_id)
                for mid in list({*(ws.get("members") or []), user["id"]}):
                    await db.conversation_members.update_one(
                        {"conversation_id": conv_id, "user_id": mid},
                        {"$setOnInsert": {"conversation_id": conv_id, "user_id": mid,
                                          "role": "member", "joined_at": now,
                                          "last_read_at": now, "muted": False}},
                        upsert=True,
                    )
            else:
                conv_id = str(conv["_id"])
                await db.conversation_members.update_one(
                    {"conversation_id": conv_id, "user_id": user["id"]},
                    {"$setOnInsert": {"conversation_id": conv_id, "user_id": user["id"],
                                      "role": "member", "joined_at": now,
                                      "last_read_at": now, "muted": False}},
                    upsert=True,
                )
        except Exception as exc:
            log.warning("workspace conv membership failed: %s", exc)

        await _notify(
            user_id=inv["invited_by"], kind="workspace_invitation_accepted",
            title=f"{user.get('full_name','Someone')} accepted your workspace invitation",
            body=f"They joined '{ws.get('name','')}' as {role}",
            link=f"/workspaces/{ws_id}", actor_id=user["id"],
            payload={"workspace_id": ws_id},
        )

    return {"ok": True, "decision": body.decision}


# ══════════════════════════════════════════════════════════════════════════════
# WORKSPACE CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("")
async def list_workspaces(
    status: Optional[str] = None,
    workspace_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    q: dict = {"$or": [{"owner_id": user["id"]}, {"members": user["id"]}]}
    if status:
        q["status"] = status
    if workspace_type:
        q["workspace_type"] = workspace_type
    docs = await db.workspaces.find(q).sort("updated_at", -1).to_list(100)
    return [_ser(d) for d in docs]


@router.post("", status_code=201)
async def create_workspace(payload: WorkspaceCreate, user: dict = Depends(get_current_user)):
    await assert_quota(user, "workspaces")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws_type = payload.workspace_type if payload.workspace_type in WORKSPACE_TYPES else "Research Project"
    now = _now()
    doc = {
        "name":           payload.name.strip(),
        "description":    (payload.description or "").strip(),
        "workspace_type": ws_type,
        "visibility":     payload.visibility or "private",
        "institution":    payload.institution or "",
        "research_area":  payload.research_area or "",
        "keywords":       payload.keywords or [],
        "owner_id":       user["id"],
        "members":        [user["id"]],
        "member_roles":   {user["id"]: "Owner"},
        "project_ids":    [],
        "status":         "active",
        "created_at":     now,
        "updated_at":     now,
    }
    res = await db.workspaces.insert_one(doc)
    doc["_id"] = res.inserted_id
    ws_id = str(res.inserted_id)

    # Auto-create workspace group conversation
    try:
        conv_key = f"workspace:{ws_id}"
        cr = await db.conversations.insert_one({
            "type": "workspace", "context_id": ws_id, "context_key": conv_key,
            "title": doc["name"], "created_by": user["id"],
            "created_at": now, "last_message_at": now, "last_message_preview": "",
        })
        await db.conversation_members.insert_one({
            "conversation_id": str(cr.inserted_id), "user_id": user["id"],
            "role": "owner", "joined_at": now, "last_read_at": now, "muted": False,
        })
    except Exception as exc:
        log.warning("workspace conversation create failed: %s", exc)

    await _log_activity(db, ws_id, user["id"], user.get("full_name", "Someone"),
                        f"Workspace created by {user.get('full_name','Someone')}", kind="workspace_created")
    return _ser(doc)


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"])
    return await _enrich(doc, db)


@router.patch("/{workspace_id}")
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_admin(doc, user["id"])
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "workspace_type" in update and update["workspace_type"] not in WORKSPACE_TYPES:
        del update["workspace_type"]
    if update:
        update["updated_at"] = _now()
        await db.workspaces.update_one({"_id": oid}, {"$set": update})
    return _ser(await db.workspaces.find_one({"_id": oid}))


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(workspace_id: str, user: dict = Depends(get_current_user)):
    """Hard-delete workspace and all sub-resources. Owner only."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["owner_id"] != user["id"]:
        raise HTTPException(403, "Only the workspace owner can delete this workspace")

    ws_id = workspace_id
    project_ids = doc.get("project_ids") or []
    if project_ids:
        await asyncio.gather(*[db.tasks.delete_many({"project_id": pid}) for pid in project_ids]
                             + [db.milestones.delete_many({"project_id": pid}) for pid in project_ids]
                             + [db.literature.delete_many({"project_id": pid}) for pid in project_ids])
        try:
            p_oids = [ObjectId(p) for p in project_ids]
            await db.projects.delete_many({"_id": {"$in": p_oids}})
        except Exception:
            pass

    # Find workspace conversation before deleting
    ws_conv = await db.conversations.find_one({"context_key": f"workspace:{ws_id}"})

    await asyncio.gather(
        db.workspace_invitations.delete_many({"workspace_id": ws_id}),
        db.workspace_activity.delete_many({"workspace_id": ws_id}),
        db.workspace_tasks.delete_many({"workspace_id": ws_id}),
        db.manuscripts.update_many({"workspace_id": ws_id}, {"$unset": {"workspace_id": ""}}),
        db.repository_items.delete_many({"workspace_id": ws_id}),
    )

    if ws_conv:
        conv_id = str(ws_conv["_id"])
        await asyncio.gather(
            db.conversation_members.delete_many({"conversation_id": conv_id}),
            db.messages.delete_many({"conversation_id": conv_id}),
            db.conversations.delete_one({"_id": ws_conv["_id"]}),
        )

    await db.workspaces.delete_one({"_id": oid})


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{workspace_id}/dashboard")
async def workspace_dashboard(workspace_id: str, user: dict = Depends(get_current_user)):
    """KPI dashboard: counts, health score, upcoming milestones, recent activity."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"])

    proj_ids   = doc.get("project_ids") or []
    member_ids = doc.get("members") or []
    your_role  = _role_of(doc, user["id"])

    # Run all counts in parallel
    async def _count(coll, q):
        return await coll.count_documents(q)

    p_oids = [ObjectId(p) for p in proj_ids if ObjectId.is_valid(p)]

    results = await asyncio.gather(
        _count(db.tasks,       {"project_id": {"$in": proj_ids}}) if proj_ids else asyncio.sleep(0),
        _count(db.tasks,       {"project_id": {"$in": proj_ids}, "status": "done"}) if proj_ids else asyncio.sleep(0),
        _count(db.tasks,       {"project_id": {"$in": proj_ids}, "status": "in_progress"}) if proj_ids else asyncio.sleep(0),
        _count(db.milestones,  {"project_id": {"$in": proj_ids}}) if proj_ids else asyncio.sleep(0),
        _count(db.milestones,  {"project_id": {"$in": proj_ids}, "completed": True}) if proj_ids else asyncio.sleep(0),
        db.projects.count_documents({"_id": {"$in": p_oids}, "status": "active"}) if p_oids else asyncio.sleep(0),
        _count(db.manuscripts, {"workspace_id": workspace_id, "status": {"$nin": ["archived"]}}),
        db.workspace_activity.find({"workspace_id": workspace_id}).sort("created_at", -1).limit(10).to_list(10),
        db.milestones.find({"project_id": {"$in": proj_ids}, "completed": {"$ne": True}}).sort("target_date", 1).limit(5).to_list(5) if proj_ids else asyncio.sleep(0),
        db.milestones.find({"workspace_id": workspace_id, "completed": {"$ne": True}}).sort("target_date", 1).limit(8).to_list(8),
        _count(db.repository_items, {"workspace_id": workspace_id}),
        db.manuscripts.find({"workspace_id": workspace_id}).sort("updated_at", -1).limit(10).to_list(10),
    )

    (tasks_total, tasks_done, tasks_ip, ms_total, ms_done,
     active_projects, active_manuscripts, recent_activity,
     upcoming_ms, upcoming_deadlines, files_count, manuscripts_list) = results

    # Coerce None (from sleep(0))
    tasks_total      = tasks_total or 0
    tasks_done       = tasks_done or 0
    tasks_ip         = tasks_ip or 0
    ms_total         = ms_total or 0
    ms_done          = ms_done or 0
    active_projects  = active_projects or 0
    upcoming_ms      = upcoming_ms or []

    # Research health score (0-100)
    task_pct = (tasks_done / tasks_total) if tasks_total else 0
    ms_pct   = (ms_done   / ms_total)    if ms_total   else 0
    health = int(
        task_pct  * 40
        + ms_pct  * 30
        + min(20, len(recent_activity) * 2)
        + min(10, len(member_ids) * 2)
    )

    return {
        "your_role":   your_role,
        "counts": {
            "members":              len(member_ids),
            "active_projects":      active_projects,
            "total_projects":       len(proj_ids),
            "active_manuscripts":   active_manuscripts or 0,
            "tasks_total":          tasks_total,
            "tasks_completed":      tasks_done,
            "tasks_in_progress":    tasks_ip,
            "milestones_total":     ms_total,
            "milestones_completed": ms_done,
            "files_count":          files_count,
        },
        "research_health":    health,
        "recent_activity":    [_ser(a) for a in recent_activity],
        "upcoming_milestones":[_ser(m) for m in upcoming_ms],
        "upcoming_deadlines": [_ser(m) for m in upcoming_deadlines],
        "manuscripts":        [_ser(m) for m in manuscripts_list],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{workspace_id}/analytics")
async def workspace_analytics(
    workspace_id: str,
    days: int = Query(default=30, ge=7, le=365),
    user: dict = Depends(get_current_user),
):
    """Activity analytics for the workspace over the last N days."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"])

    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    base  = {"workspace_id": workspace_id, "created_at": {"$gte": cutoff}}

    by_day_pipeline = [
        {"$match": base},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    by_kind_pipeline = [
        {"$match": base},
        {"$group": {"_id": "$kind", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    contrib_pipeline = [
        {"$match": base},
        {"$group": {"_id": "$actor_id", "name": {"$first": "$actor_name"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]

    by_day, by_kind, contribs = await asyncio.gather(
        db.workspace_activity.aggregate(by_day_pipeline).to_list(366),
        db.workspace_activity.aggregate(by_kind_pipeline).to_list(20),
        db.workspace_activity.aggregate(contrib_pipeline).to_list(10),
    )

    return {
        "period_days":      days,
        "activity_by_day":  [{"date": a["_id"], "count": a["count"]} for a in by_day],
        "activity_by_kind": [{"kind": a["_id"], "count": a["count"]} for a in by_kind],
        "top_contributors": [{"user_id": c["_id"], "name": c["name"], "actions": c["count"]} for c in contribs],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ACTIVITY FEED
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{workspace_id}/activity")
async def list_activity(
    workspace_id: str,
    limit: int = Query(default=30, ge=1, le=100),
    kind: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"])
    q: dict = {"workspace_id": workspace_id}
    if kind:
        q["kind"] = kind
    entries = await db.workspace_activity.find(q).sort("created_at", -1).limit(limit).to_list(limit)
    return [_ser(a) for a in entries]


@router.post("/{workspace_id}/activity")
async def add_activity(workspace_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        ws = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    except Exception:
        raise HTTPException(404, "Not found")
    if not ws:
        raise HTTPException(404, "Not found")
    _assert_member(ws, user["id"])
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "message is required")
    entry = {
        "workspace_id": workspace_id,
        "actor_id":     user["id"],
        "actor_name":   user.get("full_name", "Someone"),
        "message":      message,
        "kind":         body.get("kind", "note"),
        "created_at":   _now(),
    }
    res = await db.workspace_activity.insert_one(entry)
    entry["_id"] = res.inserted_id
    return _ser(entry)


# ══════════════════════════════════════════════════════════════════════════════
# INVITATIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{workspace_id}/invitations", status_code=201)
async def invite_member(workspace_id: str, body: InviteBody, user: dict = Depends(get_current_user)):
    """Invite a user to the workspace. Admin roles only."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_admin(doc, user["id"])

    if body.user_id == user["id"]:
        raise HTTPException(400, "Cannot invite yourself")
    if body.user_id in (doc.get("members") or []):
        raise HTTPException(409, "User is already a member")

    try:
        target = await db.users.find_one({"_id": ObjectId(body.user_id)}, {"full_name": 1})
    except Exception:
        raise HTTPException(404, "User not found")
    if not target:
        raise HTTPException(404, "User not found")

    existing = await db.workspace_invitations.find_one({
        "workspace_id": workspace_id, "user_id": body.user_id, "status": "pending",
    })
    if existing:
        raise HTTPException(409, "A pending invitation already exists for this user")

    role = body.role if body.role in WS_ROLES else "Researcher"
    now = _now()
    inv = {
        "workspace_id": workspace_id,
        "user_id":      body.user_id,
        "invited_by":   user["id"],
        "role":         role,
        "message":      body.message or "",
        "status":       "pending",
        "created_at":   now,
    }
    res = await db.workspace_invitations.insert_one(inv)

    await _notify(
        user_id=body.user_id, kind="workspace_invitation",
        title=f"{user.get('full_name','Someone')} invited you to a workspace",
        body=f"You've been invited to join '{doc.get('name','')}' as {role}",
        link="/workspaces", actor_id=user["id"],
        payload={"invitation_id": str(res.inserted_id), "workspace_id": workspace_id},
    )
    await _log_activity(db, workspace_id, user["id"], user.get("full_name","Someone"),
                        f"{user.get('full_name','Someone')} invited {target.get('full_name','a user')} as {role}",
                        kind="member_invited")

    inv["_id"] = res.inserted_id
    return _ser(inv)


# ══════════════════════════════════════════════════════════════════════════════
# MEMBER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{workspace_id}/members/{member_id}/role")
async def update_member_role(
    workspace_id: str,
    member_id: str,
    body: RoleBody,
    user: dict = Depends(get_current_user),
):
    """Change a member's role. Admin only; cannot change the owner's role."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_admin(doc, user["id"])

    if member_id == doc.get("owner_id"):
        raise HTTPException(400, "Cannot change the owner's role. Use transfer ownership.")
    if member_id not in (doc.get("members") or []):
        raise HTTPException(404, "User is not a member")

    role = body.role if body.role in WS_ROLES else "Researcher"
    if role == "Owner":
        raise HTTPException(400, "Cannot assign Owner directly. Use transfer ownership.")

    now = _now()
    await db.workspaces.update_one(
        {"_id": oid},
        {"$set": {f"member_roles.{member_id}": role, "updated_at": now}},
    )
    try:
        target_name = (await db.users.find_one({"_id": ObjectId(member_id)}, {"full_name": 1}) or {}).get("full_name", "a member")
    except Exception:
        target_name = "a member"
    await _log_activity(db, workspace_id, user["id"], user.get("full_name","Someone"),
                        f"{target_name}'s role changed to {role}", kind="role_changed")
    return {"ok": True, "member_id": member_id, "role": role}


@router.delete("/{workspace_id}/members/{member_id}", status_code=204)
async def remove_member(
    workspace_id: str,
    member_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove a member. Admin only; cannot remove the owner."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_admin(doc, user["id"])

    if member_id == doc.get("owner_id"):
        raise HTTPException(400, "Cannot remove the owner. Transfer ownership first.")
    if member_id not in (doc.get("members") or []):
        raise HTTPException(404, "User is not a member")

    now = _now()
    await db.workspaces.update_one(
        {"_id": oid},
        {"$pull": {"members": member_id},
         "$unset": {f"member_roles.{member_id}": ""},
         "$set": {"updated_at": now}},
    )
    try:
        name = (await db.users.find_one({"_id": ObjectId(member_id)}, {"full_name": 1}) or {}).get("full_name", "a member")
    except Exception:
        name = "a member"
    await _log_activity(db, workspace_id, user["id"], user.get("full_name","Someone"),
                        f"{name} was removed from the workspace", kind="member_removed")

    # Remove from workspace conversation
    try:
        conv = await db.conversations.find_one({"context_key": f"workspace:{workspace_id}"})
        if conv:
            await db.conversation_members.delete_one({"conversation_id": str(conv["_id"]), "user_id": member_id})
    except Exception:
        pass


@router.post("/{workspace_id}/leave", status_code=204)
async def leave_workspace(workspace_id: str, user: dict = Depends(get_current_user)):
    """Leave a workspace. Owners must transfer ownership first."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if user["id"] not in (doc.get("members") or []):
        raise HTTPException(404, "You are not a member of this workspace")
    if doc.get("owner_id") == user["id"]:
        raise HTTPException(400, "Owners cannot leave. Transfer ownership first.")

    now = _now()
    await db.workspaces.update_one(
        {"_id": oid},
        {"$pull": {"members": user["id"]},
         "$unset": {f"member_roles.{user['id']}": ""},
         "$set": {"updated_at": now}},
    )
    await _log_activity(db, workspace_id, user["id"], user.get("full_name","Someone"),
                        f"{user.get('full_name','Someone')} left the workspace", kind="member_left")
    try:
        conv = await db.conversations.find_one({"context_key": f"workspace:{workspace_id}"})
        if conv:
            await db.conversation_members.delete_one({"conversation_id": str(conv["_id"]), "user_id": user["id"]})
    except Exception:
        pass


@router.post("/{workspace_id}/transfer")
async def transfer_ownership(workspace_id: str, body: TransferBody, user: dict = Depends(get_current_user)):
    """Transfer workspace ownership to an existing member. Owner only."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc.get("owner_id") != user["id"]:
        raise HTTPException(403, "Only the owner can transfer ownership")
    if body.new_owner_id == user["id"]:
        raise HTTPException(400, "Already the owner")
    if body.new_owner_id not in (doc.get("members") or []):
        raise HTTPException(400, "New owner must already be a member")

    try:
        new_name = (await db.users.find_one({"_id": ObjectId(body.new_owner_id)}, {"full_name": 1}) or {}).get("full_name", "a member")
    except Exception:
        new_name = "a member"
    now = _now()
    await db.workspaces.update_one(
        {"_id": oid},
        {"$set": {
            "owner_id":                         body.new_owner_id,
            f"member_roles.{body.new_owner_id}": "Owner",
            f"member_roles.{user['id']}":        "Administrator",
            "updated_at":                        now,
        }},
    )
    await _log_activity(db, workspace_id, user["id"], user.get("full_name","Someone"),
                        f"Ownership transferred to {new_name}", kind="ownership_transferred")
    return {"ok": True, "new_owner_id": body.new_owner_id}


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH WITHIN WORKSPACE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{workspace_id}/search")
async def search_workspace(
    workspace_id: str,
    q: str = Query(..., min_length=1, max_length=200),
    user: dict = Depends(get_current_user),
):
    """Full-text search across members, files, tasks, manuscripts, activity notes."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.workspaces.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"])

    rx = {"$regex": q, "$options": "i"}
    proj_ids   = doc.get("project_ids") or []
    member_ids = doc.get("members") or []
    m_oids = [ObjectId(m) for m in member_ids if ObjectId.is_valid(m)]

    tasks_r, manuscripts_r, activity_r, files_r, members_r = await asyncio.gather(
        db.tasks.find({"project_id": {"$in": proj_ids}, "$or": [{"title": rx}, {"description": rx}]}).limit(10).to_list(10) if proj_ids else asyncio.sleep(0),
        db.manuscripts.find({"workspace_id": workspace_id, "$or": [{"title": rx}, {"abstract": rx}]}).limit(10).to_list(10),
        db.workspace_activity.find({"workspace_id": workspace_id, "message": rx}).sort("created_at", -1).limit(10).to_list(10),
        db.repository_items.find({"workspace_id": workspace_id, "$or": [{"title": rx}, {"description": rx}]}).limit(10).to_list(10),
        db.users.find({"_id": {"$in": m_oids}, "$or": [{"full_name": rx}, {"institution": rx}]}).limit(10).to_list(10) if m_oids else asyncio.sleep(0),
    )

    return {
        "query":       q,
        "tasks":       [_ser(t) for t in (tasks_r or [])],
        "manuscripts": [_ser(m) for m in (manuscripts_r or [])],
        "activity":    [_ser(a) for a in (activity_r or [])],
        "files":       [_ser(f) for f in (files_r or [])],
        "members":     [{"id": str(m["_id"]), "full_name": m.get("full_name",""), "institution": m.get("institution","")} for m in (members_r or [])],
    }
