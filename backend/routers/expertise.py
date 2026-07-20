"""Expertise Requests router — researchers post requests for specific expertise
(co-author, statistician, methodology expert, reviewer, AI specialist, etc.)
optionally linked to a workspace, project, or manuscript.

Endpoints:
  POST  /api/expertise           — create
  GET   /api/expertise           — list (faceted)
  GET   /api/expertise/mine      — my own requests
  GET   /api/expertise/matching  — requests matching my profile (alias of /marketplace/reverse subset)
  GET   /api/expertise/{id}      — detail
  PATCH /api/expertise/{id}      — update
  DELETE /api/expertise/{id}     — delete
  POST  /api/expertise/{id}/apply
  POST  /api/expertise/{id}/applications/{aid}/decide
  POST  /api/expertise/{id}/close
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/expertise", tags=["expertise"])

KINDS = ["co_author", "statistician", "methodology", "reviewer",
         "ai_specialist", "data_scientist", "editor", "sme"]


# ============================== SCHEMAS =====================================
class ExpertiseRequestCreate(BaseModel):
    kind: Literal["co_author", "statistician", "methodology", "reviewer",
                  "ai_specialist", "data_scientist", "editor", "sme"]
    title: str = Field(..., min_length=4, max_length=200)
    description: str = Field(..., max_length=4000)
    required_skills: list[str] = []
    research_areas: list[str] = []
    entity_kind: Optional[Literal["workspace", "project", "manuscript"]] = None
    entity_id: Optional[str] = None
    duration: Optional[str] = None
    compensation: Optional[str] = None    # e.g., "authorship", "paid", "credit"
    deadline: Optional[str] = None        # ISO date


class ExpertiseRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list[str]] = None
    research_areas: Optional[list[str]] = None
    duration: Optional[str] = None
    compensation: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[Literal["open", "filled", "closed"]] = None


class ApplyIn(BaseModel):
    message: str = Field(..., min_length=10, max_length=2000)


class DecisionIn(BaseModel):
    decision: Literal["accepted", "rejected"]


# ============================== HELPERS =====================================
def _now() -> str: return datetime.now(timezone.utc).isoformat()


async def _enrich(doc: dict, *, db=None) -> dict:
    if db is None: db = DBProxy(get_db(), SecurityContext.system())
    doc["id"] = str(doc.pop("_id"))
    # Owner card
    try:
        owner = await db.users.find_one(
            {"_id": ObjectId(doc["owner_id"])},
            {"full_name": 1, "academic_role": 1, "institution": 1, "avatar_url": 1, "country": 1})
        if owner:
            owner_id = str(owner.pop("_id"))
            doc["owner"] = {**owner, "id": owner_id}
    except Exception: pass
    # Entity context (best-effort)
    if doc.get("entity_kind") and doc.get("entity_id"):
        try:
            coll = {"workspace": "workspaces", "project": "projects",
                    "manuscript": "manuscripts"}[doc["entity_kind"]]
            ent = await db[coll].find_one({"_id": ObjectId(doc["entity_id"])},
                                            {"title": 1, "name": 1})
            if ent:
                doc["entity"] = {"id": str(ent["_id"]),
                                 "title": ent.get("title") or ent.get("name")}
        except Exception: pass
    return doc


# ============================== CRUD ========================================
@router.post("")
async def create_request(payload: ExpertiseRequestCreate,
                          user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = payload.model_dump()
    doc.update({
        "owner_id": user["id"], "status": "open",
        "applicants": [], "invitations": [],
        "created_at": _now(), "updated_at": _now(),
    })
    # If entity linked, verify ownership/membership.
    if doc.get("entity_kind") and doc.get("entity_id"):
        try:
            coll = {"workspace": "workspaces", "project": "projects",
                    "manuscript": "manuscripts"}[doc["entity_kind"]]
            ent = await db[coll].find_one({"_id": ObjectId(doc["entity_id"])})
            if not ent: raise HTTPException(404, "Linked entity not found")
            # membership check (best-effort across schemas)
            members = (ent.get("member_ids") or ent.get("team") or
                       ent.get("author_ids") or [])
            owner_id = ent.get("owner_id") or ent.get("created_by")
            if user["id"] not in members and user["id"] != owner_id and not zt_is_admin(user):
                raise HTTPException(403, "You are not a member of the linked entity")
        except HTTPException: raise
        except Exception: raise HTTPException(400, "Invalid linked entity")
    r = await db.expertise_requests.insert_one(doc)
    doc["_id"] = r.inserted_id
    return await _enrich(doc)


@router.get("")
async def list_requests(
    kind: Optional[str] = None,
    area: Optional[str] = None,
    skill: Optional[str] = None,
    q: Optional[str] = None,
    status: Optional[Literal["open", "filled", "closed"]] = "open",
    limit: int = 50, skip: int = 0,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    qf: dict = {}
    if status: qf["status"] = status
    if kind:   qf["kind"] = kind
    if area:   qf["research_areas"] = area
    if skill:  qf["required_skills"] = skill
    if q:
        qf["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"required_skills": {"$regex": q, "$options": "i"}},
            {"research_areas": {"$regex": q, "$options": "i"}},
        ]
    total = await db.expertise_requests.count_documents(qf)
    docs = await db.expertise_requests.find(qf).sort("created_at", -1) \
                                       .skip(skip).limit(limit).to_list(limit)
    out = [await _enrich(d, db=db) for d in docs]
    # Facets
    facets = await db.expertise_requests.aggregate([
        {"$match": {"status": "open"}},
        {"$facet": {
            "by_kind": [{"$group": {"_id": "$kind", "n": {"$sum": 1}}},
                        {"$sort": {"n": -1}}],
            "by_area": [{"$unwind": "$research_areas"},
                        {"$group": {"_id": "$research_areas", "n": {"$sum": 1}}},
                        {"$sort": {"n": -1}}, {"$limit": 20}],
        }},
    ]).to_list(1)
    return {"results": out, "total": total, "facets": (facets[0] if facets else {})}


@router.get("/mine")
async def my_requests(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.expertise_requests.find({"owner_id": user["id"]}) \
                                       .sort("created_at", -1).to_list(200)
    return [await _enrich(d, db=db) for d in docs]


@router.get("/matching")
async def matching_for_me(limit: int = 20, user: dict = Depends(get_current_user)):
    """Open requests aligned with my role tags, areas, skills."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    me = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not me: raise HTTPException(404, "User not found")
    my_roles = me.get("expertise_role_tags") or []
    my_areas = me.get("research_areas") or []
    my_kws   = (me.get("research_keywords") or []) + (me.get("research_interests") or [])
    my_skills = me.get("skills") or []
    or_clauses: list = []
    if my_roles:  or_clauses.append({"kind": {"$in": my_roles}})
    if my_areas:  or_clauses.append({"research_areas": {"$in": my_areas}})
    if my_skills: or_clauses.append({"required_skills": {"$in": my_skills}})
    if my_kws:    or_clauses.append({"required_skills": {"$in": my_kws}})
    if not or_clauses: return []
    qf = {"status": "open", "owner_id": {"$ne": user["id"]}, "$or": or_clauses}
    docs = await db.expertise_requests.find(qf).sort("created_at", -1).limit(limit).to_list(limit)
    return [await _enrich(d, db=db) for d in docs]


@router.get("/{rid}")
async def get_request(rid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    enriched = await _enrich(d, db=db)
    # Decorate applicants/invitations with user cards.
    user_ids: set = set()
    for a in enriched.get("applicants", []) or []: user_ids.add(a.get("user_id"))
    for inv in enriched.get("invitations", []) or []: user_ids.add(inv.get("user_id"))
    if user_ids:
        ids_oid = [ObjectId(x) for x in user_ids if x]
        users_docs = await db.users.find(
            {"_id": {"$in": ids_oid}},
            {"full_name": 1, "institution": 1, "academic_role": 1, "avatar_url": 1, "country": 1}
        ).to_list(len(ids_oid))
        users = {}
        for u in users_docs:
            uid = str(u.pop("_id"))
            users[uid] = {**u, "id": uid}
        for a in enriched.get("applicants", []) or []:
            u = users.get(a.get("user_id"))
            if u: a["user"] = u
        for inv in enriched.get("invitations", []) or []:
            u = users.get(inv.get("user_id"))
            if u: inv["user"] = u
    enriched["i_am_owner"] = (enriched["owner_id"] == user["id"])
    enriched["i_have_applied"] = any(
        (a.get("user_id") == user["id"]) for a in (enriched.get("applicants") or []))
    return enriched


@router.patch("/{rid}")
async def update_request(rid: str, payload: ExpertiseRequestUpdate,
                          user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    if d["owner_id"] != user["id"] and not zt_is_admin(user):
        raise HTTPException(403, "Forbidden")
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    update["updated_at"] = _now()
    await db.expertise_requests.update_one({"_id": oid}, {"$set": update})
    d2 = await db.expertise_requests.find_one({"_id": oid})
    return await _enrich(d2, db=db)


@router.delete("/{rid}")
async def delete_request(rid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    if d["owner_id"] != user["id"] and not zt_is_admin(user):
        raise HTTPException(403, "Forbidden")
    await db.expertise_requests.delete_one({"_id": oid})
    return {"ok": True}


# ============================== APPLY =======================================
@router.post("/{rid}/apply")
async def apply(rid: str, payload: ApplyIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    if d["owner_id"] == user["id"]: raise HTTPException(400, "Cannot apply to your own request")
    if d.get("status") != "open": raise HTTPException(400, "Request is not open")
    if any((a.get("user_id") == user["id"]) for a in (d.get("applicants") or [])):
        raise HTTPException(400, "You already applied")
    application = {
        "user_id": user["id"], "message": payload.message,
        "status": "pending", "applied_at": _now(),
    }
    await db.expertise_requests.update_one(
        {"_id": oid}, {"$push": {"applicants": application}})
    # Notify owner.
    try:
        await db.notifications.insert_one({
            "user_id": d["owner_id"], "kind": "expertise_application",
            "actor_id": user["id"],
            "title": f"New application on '{d.get('title')}'",
            "body": payload.message[:200],
            "entity_kind": "expertise_request", "entity_id": str(oid),
            "read": False, "created_at": _now(),
        })
    except Exception: pass
    return {"ok": True}


@router.post("/{rid}/applications/{applicant_user_id}/decide")
async def decide_application(rid: str, applicant_user_id: str,
                              payload: DecisionIn,
                              user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    if d["owner_id"] != user["id"] and not zt_is_admin(user):
        raise HTTPException(403, "Forbidden")
    await db.expertise_requests.update_one(
        {"_id": oid, "applicants.user_id": applicant_user_id},
        {"$set": {"applicants.$.status": payload.decision,
                  "applicants.$.decided_at": _now()}}
    )
    # If accepted, mark request as filled.
    if payload.decision == "accepted":
        await db.expertise_requests.update_one(
            {"_id": oid}, {"$set": {"status": "filled", "filled_by": applicant_user_id,
                                     "filled_at": _now()}})
    # Notify applicant
    try:
        await db.notifications.insert_one({
            "user_id": applicant_user_id, "kind": "expertise_decision",
            "actor_id": user["id"],
            "title": f"Your application was {payload.decision}",
            "body": d.get("title", ""),
            "entity_kind": "expertise_request", "entity_id": str(oid),
            "read": False, "created_at": _now(),
        })
    except Exception: pass
    return {"ok": True, "status": payload.decision}


@router.post("/{rid}/close")
async def close_request(rid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    if d["owner_id"] != user["id"] and not zt_is_admin(user):
        raise HTTPException(403, "Forbidden")
    await db.expertise_requests.update_one(
        {"_id": oid}, {"$set": {"status": "closed", "updated_at": _now()}})
    return {"ok": True}


# ============================== ATTACHMENTS =================================
class AttachmentIn(BaseModel):
    file_id: str


@router.post("/{rid}/attachments")
async def attach_file(rid: str, payload: AttachmentIn,
                       user: dict = Depends(get_current_user)):
    """Owner attaches one of their own uploaded files to this expertise request."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid); fid_oid = ObjectId(payload.file_id)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Request not found")
    if d["owner_id"] != user["id"] and not zt_is_admin(user):
        raise HTTPException(403, "Only the owner can attach files")
    f = await db.files.find_one({"_id": fid_oid})
    if not f: raise HTTPException(404, "File not found")
    if f["owner_id"] != user["id"] and not zt_is_admin(user):
        raise HTTPException(403, "You can only attach files you uploaded")
    await db.expertise_requests.update_one(
        {"_id": oid}, {"$addToSet": {"attached_file_ids": payload.file_id},
                       "$set": {"updated_at": _now()}})
    return {"ok": True}


@router.delete("/{rid}/attachments/{fid}")
async def detach_file(rid: str, fid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Request not found")
    if d["owner_id"] != user["id"] and not zt_is_admin(user):
        raise HTTPException(403, "Forbidden")
    await db.expertise_requests.update_one(
        {"_id": oid}, {"$pull": {"attached_file_ids": fid},
                       "$set": {"updated_at": _now()}})
    return {"ok": True}


@router.get("/{rid}/attachments")
async def list_attachments(rid: str, user: dict = Depends(get_current_user)):
    """Anyone who can view the request can see the attached files (read-only)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(rid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.expertise_requests.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Request not found")
    fids = d.get("attached_file_ids") or []
    if not fids: return []
    try: fid_oids = [ObjectId(x) for x in fids]
    except Exception: fid_oids = []
    docs = await db.files.find({"_id": {"$in": fid_oids}, "is_latest": True}) \
        .to_list(len(fid_oids))
    out = []
    for f in docs:
        f["id"] = str(f.pop("_id"))
        # Strip storage_path for non-owners (defense in depth — preview/download remain auth-gated)
        f.pop("storage_path", None); f.pop("sha256", None)
        out.append(f)
    return out
