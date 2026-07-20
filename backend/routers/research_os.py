"""Research OS extensions — workspace roles & invitations, manuscript versions / comments /
contributions / authorship, workspace + manuscript dashboards. Bolts onto existing
workspaces/projects/manuscripts collections without breaking earlier endpoints."""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from services.notifications_service import dispatch, NotificationEvent
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.research_os")
router = APIRouter(prefix="/api", tags=["research-os"])

WS_ROLES = ["Owner", "Principal Investigator", "Co-Investigator", "Researcher", "Reviewer", "Observer"]
WS_WRITE_ROLES = {"Owner", "Principal Investigator", "Co-Investigator", "Researcher"}
MS_STATUSES = ["draft", "internal_review", "ready_for_submission", "submitted",
               "revision_requested", "accepted", "published", "rejected"]
TASK_STATUSES = ["backlog", "planned", "in_progress", "review", "completed"]


def _now(): return datetime.now(timezone.utc).isoformat()
def _ser(d):
    if not d: return None
    x = dict(d); x["id"] = str(x.pop("_id")); return x


async def _ws_role(ws_id: str, uid: str) -> Optional[str]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try: w = await db.workspaces.find_one({"_id": ObjectId(ws_id)})
    except Exception: return None
    if not w: return None
    if w.get("owner_id") == uid: return "Owner"
    roles = w.get("member_roles", {})
    if uid in w.get("members", []): return roles.get(uid, "Researcher")
    return None


async def _assert_ws_role(ws_id: str, uid: str, allowed: set):
    role = await _ws_role(ws_id, uid)
    if not role or role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient workspace role")


# ============== Workspace roles & invitations ==============
class RoleUpdate(BaseModel):
    role: str

class WorkspaceInviteIn(BaseModel):
    user_id: str
    role: str = "Researcher"

class WorkspaceUpdateMeta(BaseModel):
    research_domain: Optional[str] = None
    status: Optional[str] = None  # active | archived
    description: Optional[str] = None

class InviteRespondIn(BaseModel):
    decision: str  # "accept" | "decline"


@router.patch("/workspaces/{ws_id}/meta")
async def update_workspace_meta(ws_id: str, body: WorkspaceUpdateMeta, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_ws_role(ws_id, user["id"], {"Owner", "Principal Investigator"})
    upd = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if upd: await db.workspaces.update_one({"_id": ObjectId(ws_id)}, {"$set": upd})
    return _ser(await db.workspaces.find_one({"_id": ObjectId(ws_id)}))


INVITATION_EXPIRY_DAYS = 7


@router.post("/workspaces/{ws_id}/invitations")
async def invite(ws_id: str, body: WorkspaceInviteIn, user: dict = Depends(get_current_user)):
    if body.role not in WS_ROLES or body.role == "Owner":
        raise HTTPException(status_code=400, detail="Invalid role")
    if body.user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")
    await _assert_ws_role(ws_id, user["id"], {"Owner", "Principal Investigator"})
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Update or return existing pending non-expired invitation (role may have changed)
    now_iso = _now()
    expires_at_new = (datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)).isoformat()
    existing = await db.workspace_invitations.find_one({
        "workspace_id": ws_id, "user_id": body.user_id, "status": "pending",
        "$or": [{"expires_at": {"$exists": False}}, {"expires_at": {"$gt": now_iso}}],
    })
    if existing:
        if existing.get("role") != body.role:
            await db.workspace_invitations.update_one(
                {"_id": existing["_id"]},
                {"$set": {"role": body.role, "expires_at": expires_at_new, "invited_by": user["id"]}},
            )
            updated = await db.workspace_invitations.find_one({"_id": existing["_id"]})
            return _ser(updated)
        return _ser(existing)
    doc = {
        "workspace_id": ws_id, "user_id": body.user_id, "role": body.role,
        "invited_by": user["id"], "status": "pending",
        "created_at": now_iso, "expires_at": expires_at_new,
    }
    try:
        r = await db.workspace_invitations.insert_one(doc)
    except Exception as dup_err:
        if "duplicate key" in str(dup_err).lower() or "E11000" in str(dup_err):
            # Race: another concurrent request already inserted a pending invitation
            existing_race = await db.workspace_invitations.find_one({
                "workspace_id": ws_id, "user_id": body.user_id, "status": "pending"})
            if existing_race:
                return _ser(existing_race)
        raise dup_err
    doc["_id"] = r.inserted_id
    ws = await db.workspaces.find_one({"_id": ObjectId(ws_id)})
    await dispatch(NotificationEvent(
        user_id=body.user_id, kind="workspace_invitation",
        title=f"Invitation: {ws.get('name','Workspace')}",
        body=f"{user.get('full_name','Someone')} invited you as {body.role}",
        link=f"/workspaces/{ws_id}", actor_id=user["id"],
        payload={"workspace_id": ws_id, "workspace_name": ws.get("name",""), "role": body.role,
                 "invitation_id": str(r.inserted_id), "actor_name": user.get("full_name","")}))
    try:
        from services.email_service import send_workspace_invitation
        await send_workspace_invitation(
            recipient_user_id=body.user_id, workspace_id=ws_id,
            workspace_name=ws.get("name",""), role=body.role,
            inviter_name=user.get("full_name",""))
    except Exception as _email_exc:
        logger.warning("workspace_invitation email failed ws=%s user=%s err=%s",
                       ws_id, body.user_id, _email_exc)
    return _ser(doc)


@router.delete("/workspaces/invitations/{inv_id}")
async def cancel_invitation(inv_id: str, user: dict = Depends(get_current_user)):
    """Cancel a pending workspace invitation (only the inviter or workspace Owner/PI may cancel)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(inv_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    inv = await db.workspace_invitations.find_one({"_id": oid, "status": "pending"})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found or already resolved")
    # Allow: the original inviter OR a workspace Owner/PI
    if inv.get("invited_by") != user["id"]:
        await _assert_ws_role(inv["workspace_id"], user["id"], {"Owner", "Principal Investigator"})
    result = await db.workspace_invitations.update_one(
        {"_id": oid, "status": "pending"},
        {"$set": {"status": "cancelled", "cancelled_by": user["id"], "cancelled_at": _now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=409, detail="Invitation was already resolved by a concurrent action")
    return {"ok": True}


@router.patch("/workspaces/{ws_id}/members/{uid}/role")
async def change_role(ws_id: str, uid: str, body: RoleUpdate, user: dict = Depends(get_current_user)):
    if body.role not in WS_ROLES or body.role == "Owner": raise HTTPException(400, "Invalid role")
    await _assert_ws_role(ws_id, user["id"], {"Owner", "Principal Investigator"})
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws = await db.workspaces.find_one({"_id": ObjectId(ws_id)})
    if not ws or uid not in ws.get("members", []):
        raise HTTPException(400, "User is not a workspace member")
    await db.workspaces.update_one({"_id": ObjectId(ws_id)}, {"$set": {f"member_roles.{uid}": body.role}})
    return {"ok": True}


@router.delete("/workspaces/{ws_id}/members/{uid}")
async def remove_member(ws_id: str, uid: str, user: dict = Depends(get_current_user)):
    await _assert_ws_role(ws_id, user["id"], {"Owner", "Principal Investigator"})
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws = await db.workspaces.find_one({"_id": ObjectId(ws_id)})
    if ws and ws["owner_id"] == uid: raise HTTPException(400, "Cannot remove owner")
    await db.workspaces.update_one({"_id": ObjectId(ws_id)}, {"$pull": {"members": uid}, "$unset": {f"member_roles.{uid}": ""}})
    return {"ok": True}


# ============== Workspace dashboard ==============
@router.get("/workspaces/{ws_id}/dashboard")
async def workspace_dashboard(ws_id: str, user: dict = Depends(get_current_user)):
    role = await _ws_role(ws_id, user["id"])
    if not role: raise HTTPException(403, "Forbidden")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws = await db.workspaces.find_one({"_id": ObjectId(ws_id)})
    project_ids = ws.get("project_ids", [])
    poids = [ObjectId(p) for p in project_ids if _safe_oid(p)]
    projects = await db.projects.find({"_id": {"$in": poids}}).to_list(100)
    manuscripts = await db.manuscripts.find({"workspace_id": ws_id}).to_list(100)
    tasks = await db.tasks.find({"project_id": {"$in": project_ids}}).to_list(500)
    milestones = await db.milestones.find({"project_id": {"$in": project_ids}}).to_list(200)
    activity = await db.workspace_activity.find({"workspace_id": ws_id}).sort("created_at", -1).limit(20).to_list(20)
    # upcoming milestones: not completed, sorted by target_date when present
    upcoming = [m for m in milestones if not m.get("completed")]
    upcoming.sort(key=lambda m: (m.get("target_date") or "9999"))
    tasks_total = len(tasks)
    tasks_completed = sum(1 for t in tasks if t.get("status") == "completed")
    ms_total = len(milestones); ms_completed = sum(1 for m in milestones if m.get("completed"))
    health_t = (tasks_completed / tasks_total * 100) if tasks_total else 0
    health_m = (ms_completed / ms_total * 100) if ms_total else 0
    health_p = sum(1 for p in projects if p.get("status","active") != "archived")
    research_health = round(0.5 * health_t + 0.4 * health_m + 0.1 * min(100, health_p * 25))
    return {
        "workspace": _ser(ws),
        "your_role": role,
        "counts": {
            "members": len(ws.get("members", [])),
            "active_projects": sum(1 for p in projects if p.get("status","active") != "archived"),
            "active_manuscripts": sum(1 for m in manuscripts if m.get("status") not in ("published","rejected")),
            "tasks_completed": tasks_completed,
            "tasks_total": tasks_total,
            "milestones_completed": ms_completed,
            "milestones_total": ms_total,
        },
        "research_health": research_health,
        "projects": [_ser(p) for p in projects[:10]],
        "manuscripts": [_ser(m) for m in manuscripts[:10]],
        "upcoming_milestones": [_ser(m) for m in upcoming[:5]],
        "upcoming_deadlines": await _ws_upcoming_deadlines(ws_id, user["id"]),
        "recent_activity": [_ser(a) for a in activity],
    }


async def _ws_upcoming_deadlines(ws_id: str, user_id: str) -> list[dict]:
    """Inline reuse of matching.py deadline aggregator so workspace dashboards
    surface conference/journal/grant/revision deadlines without an extra call."""
    try:
        from routers.matching import _user_deadlines
        items = await _user_deadlines(user_id, workspace_id=ws_id)
        return items[:6]
    except Exception:
        return []


def _safe_oid(s):
    try: ObjectId(s); return True
    except Exception: return False


# ============== Manuscript: versions, comments, contributions, authors ==============
class VersionCreate(BaseModel):
    summary: Optional[str] = ""

class CommentCreate(BaseModel):
    section: str
    body: str
    anchor: Optional[str] = ""  # optional text snippet the comment is anchored to

class ReviewRequestIn(BaseModel):
    reviewer_id: str
    section: Optional[str] = ""
    note: Optional[str] = ""

class AuthorOrderIn(BaseModel):
    order: List[str]  # user_ids in order
    corresponding_author_id: Optional[str] = None

class ManuscriptMetaIn(BaseModel):
    keywords: Optional[List[str]] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    target_journal_id: Optional[str] = None


async def _can_edit_manuscript(mid: str, uid: str) -> bool:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try: m = await db.manuscripts.find_one({"_id": ObjectId(mid)})
    except Exception: return False
    if not m: return False
    if uid in (m.get("authors") or []): return True
    ws_id = m.get("workspace_id")
    if ws_id:
        role = await _ws_role(ws_id, uid)
        if role in WS_WRITE_ROLES: return True
    return False


@router.post("/manuscripts/{mid}/versions")
async def snapshot_version(mid: str, body: VersionCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    m = await db.manuscripts.find_one({"_id": ObjectId(mid)})
    last = await db.manuscript_versions.find({"manuscript_id": mid}).sort("version", -1).limit(1).to_list(1)
    next_v = (last[0]["version"] + 1) if last else 1
    doc = {
        "manuscript_id": mid, "version": next_v, "summary": body.summary or "",
        "snapshot": {"title": m.get("title"), "sections": m.get("sections", {}),
                     "keywords": m.get("keywords", []), "status": m.get("status"),
                     "authors": m.get("authors", []), "target_journal_id": m.get("target_journal_id","")},
        "author_id": user["id"], "author_name": user.get("full_name",""),
        "created_at": _now(),
    }
    r = await db.manuscript_versions.insert_one(doc); doc["_id"] = r.inserted_id
    await db.manuscripts.update_one({"_id": ObjectId(mid)}, {"$set": {"current_version": next_v, "updated_at": _now()}})
    return _ser(doc)


@router.get("/manuscripts/{mid}/versions")
async def list_versions(mid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    docs = await db.manuscript_versions.find({"manuscript_id": mid}).sort("version", -1).to_list(200)
    return [{**_ser(d), "snapshot": None} for d in docs]  # list omits payload


@router.get("/manuscripts/{mid}/versions/{version}")
async def get_version(mid: str, version: int, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    v = await db.manuscript_versions.find_one({"manuscript_id": mid, "version": version})
    if not v: raise HTTPException(404, "Not found")
    return _ser(v)


@router.post("/manuscripts/{mid}/versions/{version}/restore")
async def restore_version(mid: str, version: int, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    v = await db.manuscript_versions.find_one({"manuscript_id": mid, "version": version})
    if not v: raise HTTPException(404, "Not found")
    # Snapshot CURRENT before overwriting (so restore is itself reversible)
    cur = await db.manuscripts.find_one({"_id": ObjectId(mid)})
    last = await db.manuscript_versions.find({"manuscript_id": mid}).sort("version", -1).limit(1).to_list(1)
    next_v = (last[0]["version"] + 1) if last else 1
    await db.manuscript_versions.insert_one({
        "manuscript_id": mid, "version": next_v,
        "summary": f"Auto-snapshot before restore of v{version}",
        "snapshot": {"title": cur.get("title"), "sections": cur.get("sections", {}),
                     "keywords": cur.get("keywords", []), "status": cur.get("status"),
                     "authors": cur.get("authors", []), "target_journal_id": cur.get("target_journal_id","")},
        "author_id": user["id"], "author_name": user.get("full_name",""), "created_at": _now(),
    })
    snap = v["snapshot"]
    await db.manuscripts.update_one({"_id": ObjectId(mid)}, {"$set": {
        "sections": snap.get("sections", {}),
        "title": snap.get("title", cur.get("title")),
        "keywords": snap.get("keywords", []),
        "current_version": next_v + 1,
        "updated_at": _now(),
    }})
    nv = next_v + 1
    await db.manuscript_versions.insert_one({
        "manuscript_id": mid, "version": nv,
        "summary": f"Restored to v{version}",
        "snapshot": snap, "author_id": user["id"], "author_name": user.get("full_name",""), "created_at": _now(),
    })
    return {"ok": True, "current_version": nv}


@router.post("/manuscripts/{mid}/comments")
async def add_comment(mid: str, body: CommentCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    doc = {"manuscript_id": mid, "section": body.section, "body": body.body, "anchor": body.anchor,
           "author_id": user["id"], "author_name": user.get("full_name",""), "resolved": False, "created_at": _now()}
    r = await db.manuscript_comments.insert_one(doc); doc["_id"] = r.inserted_id
    m = await db.manuscripts.find_one({"_id": ObjectId(mid)})
    for uid in (m.get("authors") or []):
        if uid == user["id"]: continue
        await dispatch(NotificationEvent(
            user_id=uid, kind="manuscript_comment", title=f"New comment on {m.get('title','')[:40]}",
            body=f"{user.get('full_name','')} on {body.section}: {body.body[:80]}",
            link=f"/manuscripts/{mid}", actor_id=user["id"], payload={"manuscript_id": mid}))
    return _ser(doc)


@router.get("/manuscripts/{mid}/comments")
async def list_comments(mid: str, section: Optional[str] = None, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    q = {"manuscript_id": mid}
    if section: q["section"] = section
    docs = await db.manuscript_comments.find(q).sort("created_at", -1).to_list(300)
    return [_ser(d) for d in docs]


@router.post("/manuscripts/comments/{cid}/resolve")
async def resolve_comment(cid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    c = await db.manuscript_comments.find_one({"_id": ObjectId(cid)})
    if not c: raise HTTPException(404, "Not found")
    if not await _can_edit_manuscript(c["manuscript_id"], user["id"]): raise HTTPException(403, "Forbidden")
    await db.manuscript_comments.update_one({"_id": ObjectId(cid)}, {"$set": {"resolved": True, "resolved_by": user["id"], "resolved_at": _now()}})
    return {"ok": True}


@router.post("/manuscripts/{mid}/review-requests")
async def request_review(mid: str, body: ReviewRequestIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    # Validate reviewer exists
    try:
        reviewer_doc = await db.users.find_one({"_id": ObjectId(body.reviewer_id)}, {"_id": 1})
    except Exception:
        reviewer_doc = None
    if not reviewer_doc:
        raise HTTPException(404, "Reviewer not found")
    doc = {"manuscript_id": mid, "reviewer_id": body.reviewer_id, "section": body.section,
           "note": body.note, "requested_by": user["id"], "status": "pending", "created_at": _now()}
    r = await db.review_requests.insert_one(doc); doc["_id"] = r.inserted_id
    m = await db.manuscripts.find_one({"_id": ObjectId(mid)})
    await dispatch(NotificationEvent(
        user_id=body.reviewer_id, kind="review_request",
        title=f"Review requested: {m.get('title','')[:60]}",
        body=f"{user.get('full_name','')} asked you to review {body.section or 'this manuscript'}",
        link=f"/manuscripts/{mid}", actor_id=user["id"],
        payload={"manuscript_id": mid, "manuscript_title": m.get("title",""),
                 "section": body.section or "", "note": body.note or "",
                 "actor_name": user.get("full_name","")}))
    # Email trigger (dry-run-safe)
    try:
        from services.email_service import send_review_request
        await send_review_request(
            reviewer_user_id=body.reviewer_id, manuscript_id=mid,
            manuscript_title=m.get("title",""), requester_name=user.get("full_name",""),
            section=body.section or "", note=body.note or "")
    except Exception as _email_exc:
        logger.warning("review_request email failed manuscript=%s reviewer=%s err=%s",
                       mid, body.reviewer_id, _email_exc)
    return _ser(doc)


@router.post("/manuscripts/{mid}/contributions")
async def log_contribution(mid: str, body: dict, user: dict = Depends(get_current_user)):
    """Called by frontend on every save: {section, char_delta}. Aggregated per-user per-section."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    section = body.get("section",""); delta = int(body.get("char_delta", 0))
    await db.manuscript_contributions.update_one(
        {"manuscript_id": mid, "user_id": user["id"], "section": section},
        {"$inc": {"chars_changed": delta, "edits": 1},
         "$set": {"last_edit": _now(), "user_name": user.get("full_name","")},
         "$setOnInsert": {"first_edit": _now()}},
        upsert=True,
    )
    return {"ok": True}


@router.get("/manuscripts/{mid}/contributions")
async def list_contributions(mid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    docs = await db.manuscript_contributions.find({"manuscript_id": mid}).to_list(500)
    return [_ser(d) for d in docs]


@router.patch("/manuscripts/{mid}/authors")
async def reorder_authors(mid: str, body: AuthorOrderIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    m = await db.manuscripts.find_one({"_id": ObjectId(mid)})
    if not m: raise HTTPException(404, "Not found")
    if m.get("lead_author_id") != user["id"]:
        raise HTTPException(403, "Only the lead author can reorder authors")
    upd = {"authors": body.order, "updated_at": _now()}
    if body.corresponding_author_id and body.corresponding_author_id in body.order:
        upd["corresponding_author_id"] = body.corresponding_author_id
    await db.manuscripts.update_one({"_id": ObjectId(mid)}, {"$set": upd})
    return _ser(await db.manuscripts.find_one({"_id": ObjectId(mid)}))


@router.patch("/manuscripts/{mid}/meta")
async def update_meta(mid: str, body: ManuscriptMetaIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    upd = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if upd:
        upd["updated_at"] = _now()
        await db.manuscripts.update_one({"_id": ObjectId(mid)}, {"$set": upd})
    return _ser(await db.manuscripts.find_one({"_id": ObjectId(mid)}))


@router.get("/manuscripts/{mid}/dashboard")
async def manuscript_dashboard(mid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    m = await db.manuscripts.find_one({"_id": ObjectId(mid)})
    versions = await db.manuscript_versions.count_documents({"manuscript_id": mid})
    comments_open = await db.manuscript_comments.count_documents({"manuscript_id": mid, "resolved": False})
    comments_total = await db.manuscript_comments.count_documents({"manuscript_id": mid})
    reviews = await db.review_requests.count_documents({"manuscript_id": mid, "status": "pending"})
    contribs = await db.manuscript_contributions.find({"manuscript_id": mid}).to_list(500)
    sections = m.get("sections", {})
    filled = sum(1 for v in sections.values() if (v or "").strip())
    progress = round(100 * filled / max(1, len(sections)))
    # submission readiness: progress + has target journal + draft-not-empty
    ready = progress >= 80 and bool(m.get("target_journal_id")) and bool((sections.get("abstract") or "").strip())
    return {
        "manuscript_id": mid,
        "status": m.get("status"),
        "current_version": m.get("current_version", 0),
        "versions_count": versions,
        "comments_open": comments_open,
        "comments_total": comments_total,
        "review_requests_pending": reviews,
        "progress_pct": progress,
        "ready_for_submission": ready,
        "contributions": [_ser(c) for c in contribs],
        # Publication-pipeline integration hooks (filled by future modules)
        "pipeline_hooks": {
            "journal_finder": {"endpoint": "/api/ai/journal-matching", "credits": 5, "wired": False},
            "conference_finder": {"endpoint": "/api/ai/conference-matching", "credits": 5, "wired": False},
            "grant_finder": {"endpoint": "/api/ai/grant-matching", "credits": 5, "wired": False},
            "publication_hub": {"endpoint": "/api/publication-hub/pipeline", "wired": True},
        },
    }


# ============== Tasks — extend status vocabulary ==============
@router.get("/research-os/task-statuses")
async def task_statuses(): return TASK_STATUSES

@router.get("/research-os/manuscript-statuses")
async def manuscript_statuses(): return MS_STATUSES

@router.get("/research-os/workspace-roles")
async def workspace_roles_list(): return WS_ROLES


# ============== Workspace task aggregation (Kanban) ==============
@router.get("/workspaces/{ws_id}/tasks")
async def workspace_tasks(ws_id: str, user: dict = Depends(get_current_user)):
    """Aggregate all tasks across the workspace's projects, with project + assignee enrichment."""
    role = await _ws_role(ws_id, user["id"])
    if not role: raise HTTPException(403, "Forbidden")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws = await db.workspaces.find_one({"_id": ObjectId(ws_id)})
    project_ids = ws.get("project_ids", []) if ws else []
    if not project_ids:
        return {"projects": [], "tasks": []}
    poids = [ObjectId(p) for p in project_ids if _safe_oid(p)]
    projects = await db.projects.find({"_id": {"$in": poids}}).to_list(100)
    project_meta = {str(p["_id"]): {"id": str(p["_id"]), "title": p.get("title", "")} for p in projects}
    tasks = await db.tasks.find({"project_id": {"$in": project_ids}}).sort("created_at", -1).to_list(500)
    # enrich assignees
    assignee_ids = list({t.get("assignee_id") for t in tasks if t.get("assignee_id")})
    aoids = [ObjectId(a) for a in assignee_ids if _safe_oid(a)]
    users = await db.users.find({"_id": {"$in": aoids}}).to_list(100) if aoids else []
    user_meta = {str(u["_id"]): {"id": str(u["_id"]), "full_name": u.get("full_name", ""), "avatar_url": u.get("avatar_url")} for u in users}
    out_tasks = []
    for t in tasks:
        x = _ser(t)
        x["project"] = project_meta.get(x.get("project_id"))
        x["assignee"] = user_meta.get(x.get("assignee_id")) if x.get("assignee_id") else None
        # Normalize legacy status "todo" → "backlog"
        if x.get("status") == "todo": x["status"] = "backlog"
        out_tasks.append(x)
    return {"projects": list(project_meta.values()), "tasks": out_tasks}


# ============== Manuscript Review Workflow ==============
REVIEW_VERDICTS = ["accepted", "minor_revision", "major_revision", "rejected"]


class ReviewRespondIn(BaseModel):
    decision: str  # "accept" | "decline"


class ReviewVerdictIn(BaseModel):
    verdict: str  # accepted | minor_revision | major_revision | rejected
    comment: Optional[str] = ""


def _ms_status_for_verdict(v: str) -> Optional[str]:
    return {
        "accepted": "accepted",
        "rejected": "rejected",
        "minor_revision": "revision_requested",
        "major_revision": "revision_requested",
    }.get(v)


@router.get("/manuscripts/{mid}/review-requests")
async def list_manuscript_reviews(mid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    docs = await db.review_requests.find({"manuscript_id": mid}).sort("created_at", -1).to_list(100)
    # Enrich reviewer + requester
    uids = list({d.get("reviewer_id") for d in docs} | {d.get("requested_by") for d in docs})
    oids = [ObjectId(u) for u in uids if _safe_oid(u)]
    users = await db.users.find({"_id": {"$in": oids}}).to_list(200) if oids else []
    umap = {str(u["_id"]): {"id": str(u["_id"]), "full_name": u.get("full_name",""), "avatar_url": u.get("avatar_url")} for u in users}
    out = []
    for d in docs:
        x = _ser(d)
        x["reviewer"] = umap.get(x.get("reviewer_id"))
        x["requester"] = umap.get(x.get("requested_by"))
        out.append(x)
    return out


@router.get("/review-requests/mine")
async def my_reviews(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    """All review requests where the current user is the reviewer."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    q = {"reviewer_id": user["id"]}
    if status: q["status"] = status
    docs = await db.review_requests.find(q).sort("created_at", -1).to_list(200)
    # Enrich with manuscript title + requester
    mids = list({d.get("manuscript_id") for d in docs})
    moids = [ObjectId(m) for m in mids if _safe_oid(m)]
    ms = await db.manuscripts.find({"_id": {"$in": moids}}).to_list(200) if moids else []
    mmap = {str(m["_id"]): {"id": str(m["_id"]), "title": m.get("title",""), "manuscript_type": m.get("manuscript_type","")} for m in ms}
    req_ids = list({d.get("requested_by") for d in docs})
    roids = [ObjectId(r) for r in req_ids if _safe_oid(r)]
    users = await db.users.find({"_id": {"$in": roids}}).to_list(200) if roids else []
    umap = {str(u["_id"]): {"id": str(u["_id"]), "full_name": u.get("full_name",""), "avatar_url": u.get("avatar_url"), "institution": u.get("institution","")} for u in users}
    out = []
    for d in docs:
        x = _ser(d)
        x["manuscript"] = mmap.get(x.get("manuscript_id"))
        x["requester"] = umap.get(x.get("requested_by"))
        out.append(x)
    return out


@router.post("/review-requests/{rid}/respond")
async def respond_review(rid: str, body: ReviewRespondIn, user: dict = Depends(get_current_user)):
    if body.decision not in {"accept", "decline"}: raise HTTPException(400, "Invalid decision")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    r = await db.review_requests.find_one({"_id": ObjectId(rid)})
    if not r: raise HTTPException(404, "Not found")
    if r.get("reviewer_id") != user["id"]: raise HTTPException(403, "Forbidden")
    if r.get("status") != "pending": raise HTTPException(400, "Already responded")
    new_status = "accepted" if body.decision == "accept" else "declined"
    await db.review_requests.update_one({"_id": ObjectId(rid)}, {"$set": {"status": new_status, "responded_at": _now()}})
    # Notify requester
    m = await db.manuscripts.find_one({"_id": ObjectId(r["manuscript_id"])}) if _safe_oid(r["manuscript_id"]) else None
    await dispatch(NotificationEvent(
        user_id=r["requested_by"], kind="review_response",
        title=f"Review {'accepted' if new_status=='accepted' else 'declined'}: {((m or {}).get('title') or '')[:50]}",
        body=f"{user.get('full_name','')} {'accepted' if new_status=='accepted' else 'declined'} your review request",
        link=f"/manuscripts/{r['manuscript_id']}", actor_id=user["id"],
        payload={"manuscript_id": r["manuscript_id"], "review_request_id": rid}))
    return {"ok": True, "status": new_status}


@router.post("/review-requests/{rid}/verdict")
async def submit_verdict(rid: str, body: ReviewVerdictIn, user: dict = Depends(get_current_user)):
    if body.verdict not in REVIEW_VERDICTS: raise HTTPException(400, "Invalid verdict")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    r = await db.review_requests.find_one({"_id": ObjectId(rid)})
    if not r: raise HTTPException(404, "Not found")
    if r.get("reviewer_id") != user["id"]: raise HTTPException(403, "Forbidden")
    if r.get("status") not in {"accepted"}: raise HTTPException(400, "Must accept the review before submitting a verdict")
    await db.review_requests.update_one({"_id": ObjectId(rid)}, {"$set": {
        "verdict": body.verdict, "verdict_comment": body.comment or "",
        "status": "completed", "verdict_at": _now()}})
    # Cascade manuscript status when appropriate
    new_ms_status = _ms_status_for_verdict(body.verdict)
    if new_ms_status and _safe_oid(r["manuscript_id"]):
        await db.manuscripts.update_one({"_id": ObjectId(r["manuscript_id"])}, {"$set": {"status": new_ms_status, "updated_at": _now()}})
    # Notify requester + manuscript authors
    m = await db.manuscripts.find_one({"_id": ObjectId(r["manuscript_id"])}) if _safe_oid(r["manuscript_id"]) else None
    notify_uids = set([r["requested_by"]] + list((m or {}).get("authors", [])))
    notify_uids.discard(user["id"])
    for uid in notify_uids:
        await dispatch(NotificationEvent(
            user_id=uid, kind="review_verdict",
            title=f"Verdict: {body.verdict.replace('_',' ').title()} — {((m or {}).get('title') or '')[:40]}",
            body=f"{user.get('full_name','')} returned a verdict of {body.verdict.replace('_',' ')}",
            link=f"/manuscripts/{r['manuscript_id']}", actor_id=user["id"],
            payload={"manuscript_id": r["manuscript_id"], "review_request_id": rid, "verdict": body.verdict}))
    return {"ok": True, "verdict": body.verdict, "manuscript_status": new_ms_status}


@router.get("/manuscripts/{mid}/review-history")
async def review_history(mid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if not await _can_edit_manuscript(mid, user["id"]): raise HTTPException(403, "Forbidden")
    docs = await db.review_requests.find({"manuscript_id": mid, "status": {"$in": ["completed", "declined"]}}).sort("created_at", -1).to_list(200)
    uids = list({d.get("reviewer_id") for d in docs})
    oids = [ObjectId(u) for u in uids if _safe_oid(u)]
    users = await db.users.find({"_id": {"$in": oids}}).to_list(200) if oids else []
    umap = {str(u["_id"]): {"id": str(u["_id"]), "full_name": u.get("full_name",""), "avatar_url": u.get("avatar_url")} for u in users}
    out = []
    for d in docs:
        x = _ser(d); x["reviewer"] = umap.get(x.get("reviewer_id")); out.append(x)
    return out


@router.get("/research-os/review-verdicts")
async def review_verdicts(): return REVIEW_VERDICTS

