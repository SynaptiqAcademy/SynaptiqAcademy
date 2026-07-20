"""Department Management router — institutional subscribers only.

Departments are units with type="department" in the existing `units` collection.
This router provides richer, department-specific endpoints on top of the existing
units system: member roster, linked projects, aggregated metrics, and rankings.

Gate: Institution must have a paid institution plan. Individual user's plan_code
is NOT checked — access is determined by institution subscription + membership.

Read endpoints  → approved institution member required
Write endpoints → department admin or institution admin required

Routes:
  GET  /api/institutions/{iid}/departments             — list departments
  POST /api/institutions/{iid}/departments             — create department

  GET    /api/departments/{did}                        — department overview
  PATCH  /api/departments/{did}                        — update metadata
  DELETE /api/departments/{did}                        — delete (inst admin only)

  GET  /api/departments/{did}/members                  — faculty & staff
  POST /api/departments/{did}/members                  — add/remove members
  PATCH /api/departments/{did}/members/{uid}/role      — assign role

  GET    /api/departments/{did}/projects               — linked projects
  POST   /api/departments/{did}/projects               — link a project
  DELETE /api/departments/{did}/projects/{pid}         — unlink project

  GET  /api/departments/{did}/metrics                  — research output KPIs
  GET  /api/departments/{did}/rankings                 — dept ranks in institution
  GET  /api/departments/{did}/collaboration            — collaboration network
  GET  /api/departments/{did}/publications             — publication statistics
  GET  /api/departments/{did}/funding                  — funding breakdown
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.institutions.department_service import (
    assert_institution_plan,
    assert_dept_membership,
    assert_dept_admin,
    get_dept_user_ids,
    get_dept_members_enriched,
    get_dept_projects,
    get_cached_metrics,
    compute_dept_metrics,
    rank_departments,
    get_dept_collaboration,
)
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(tags=["departments"])

DEPT_ROLES = ["unit_admin", "research_lead", "researcher"]
DEPT_ROLE_LABEL = {
    "unit_admin":    "Department Admin",
    "research_lead": "Research Coordinator",
    "researcher":    "Faculty Member",
    "admin":         "Institution Admin",
    "owner":         "Institution Owner",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _audit(institution_id: str, actor_id: str, action: str,
                  target_kind: Optional[str] = None, target_id: Optional[str] = None,
                  metadata: Optional[dict] = None):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.institution_audit.insert_one({
        "institution_id": institution_id, "actor_id": actor_id, "action": action,
        "target_kind": target_kind or "department", "target_id": target_id,
        "metadata": metadata or {}, "created_at": _now(),
    })


async def _get_dept_iid(department_id: str) -> str:
    """Return institution_id for the given department (unit) id."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    d = await db.units.find_one({"_id": ObjectId(department_id)}, {"institution_id": 1})
    if not d:
        raise HTTPException(404, "Department not found")
    if d.get("type") and d.get("type") != "department":
        # Allow any unit type — type filter is soft
        pass
    return d["institution_id"]


# ─────────────────────────── models ──────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name:          str            = Field(..., min_length=2, max_length=200)
    description:   Optional[str] = None
    research_areas: list[str]    = []
    head_id:       Optional[str] = None
    parent_id:     Optional[str] = None


class DepartmentUpdate(BaseModel):
    name:          Optional[str]       = None
    description:   Optional[str]       = None
    research_areas: Optional[list[str]] = None
    head_id:       Optional[str]       = None
    admin_ids:     Optional[list[str]] = None


class MembersIn(BaseModel):
    user_ids: list[str]
    action:   Literal["add", "remove"] = "add"


class RoleIn(BaseModel):
    role: Literal["unit_admin", "research_lead", "researcher"]


class ProjectLinkIn(BaseModel):
    project_id: str


# ─────────────────────────── department list / create ─────────────────────────

@router.get("/api/institutions/{iid}/departments")
async def list_departments(
    iid: str,
    q: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List all departments for an institution. Requires approved membership."""
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    qf: dict = {"institution_id": iid, "type": "department"}
    if q:
        qf["$or"] = [{"name": {"$regex": q, "$options": "i"}},
                     {"research_areas": {"$regex": q, "$options": "i"}}]
    docs = await db.units.find(qf).sort("name", 1).to_list(200)
    out = []
    for d in docs:
        did = str(d["_id"])
        member_count = await db.institution_memberships.count_documents(
            {"institution_id": iid, "status": "approved", "unit_ids": did})
        head_name = None
        if d.get("head_id"):
            hd = await db.users.find_one({"_id": ObjectId(d["head_id"])}, {"full_name": 1})
            head_name = (hd or {}).get("full_name")
        dept_proj_count = await db.department_projects.count_documents(
            {"department_id": did})
        out.append({
            "id":              did,
            "name":            d.get("name"),
            "description":     d.get("description"),
            "research_areas":  d.get("research_areas") or [],
            "head_id":         d.get("head_id"),
            "head_name":       head_name,
            "member_count":    member_count,
            "project_count":   dept_proj_count,
            "institution_id":  iid,
            "created_at":      d.get("created_at"),
        })
    return out


@router.post("/api/institutions/{iid}/departments")
async def create_department(
    iid: str,
    payload: DepartmentCreate,
    user: dict = Depends(get_current_user),
):
    """Create a new department. Requires institution admin role + institution plan."""
    await assert_institution_plan(iid)
    # Must be institution admin
    from services.institutions.department_service import assert_dept_membership
    m = await assert_dept_membership(iid, user["id"])
    from routers.institutions import ADMIN_ROLES
    platform_admin = zt_is_admin(user)
    if not platform_admin and m.get("role") not in ADMIN_ROLES:
        raise HTTPException(403, "Institution admin role required to create departments")

    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = payload.model_dump()
    doc.update({
        "institution_id": iid,
        "type":           "department",
        "admin_ids":      [user["id"]],
        "created_at":     _now(),
        "updated_at":     _now(),
    })
    r   = await db.units.insert_one(doc)
    did = str(r.inserted_id)
    await _audit(iid, user["id"], "department_created",
                 target_kind="department", target_id=did,
                 metadata={"name": doc["name"]})
    doc["_id"] = r.inserted_id
    doc["id"]  = did
    doc.pop("_id")
    doc["member_count"]  = 0
    doc["project_count"] = 0
    return doc


# ─────────────────────────── department detail ────────────────────────────────

@router.get("/api/departments/{did}")
async def get_department(did: str, user: dict = Depends(get_current_user)):
    """Full department overview with head info and quick counts."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(did)
    except Exception:
        raise HTTPException(404, "Not found")
    d = await db.units.find_one({"_id": oid})
    if not d or d.get("type") not in {None, "department"}:
        d = await db.units.find_one({"_id": oid})
        if not d:
            raise HTTPException(404, "Not found")
    iid = d["institution_id"]
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])

    # Membership check: is the user in this department?
    m = await db.institution_memberships.find_one(
        {"institution_id": iid, "user_id": user["id"], "status": "approved"})
    is_dept_member = did in (m.get("unit_ids") or []) if m else False
    is_admin = (zt_is_admin(user) or
                (m and m.get("role") in {"owner", "admin"}) or
                user["id"] in (d.get("admin_ids") or []) or
                d.get("head_id") == user["id"])

    member_count = await db.institution_memberships.count_documents(
        {"institution_id": iid, "status": "approved", "unit_ids": did})
    proj_count = await db.department_projects.count_documents({"department_id": did})

    head_doc = None
    if d.get("head_id"):
        hd = await db.users.find_one(
            {"_id": ObjectId(d["head_id"])},
            {"full_name": 1, "academic_role": 1, "avatar_url": 1})
        if hd:
            head_doc = {"id": str(hd["_id"]), "full_name": hd.get("full_name"),
                        "role": hd.get("academic_role"), "avatar_url": hd.get("avatar_url")}

    inst = await db.institutions.find_one({"_id": ObjectId(iid)},
                                           {"name": 1, "logo_url": 1})
    return {
        "id":             did,
        "name":           d.get("name"),
        "description":    d.get("description"),
        "research_areas": d.get("research_areas") or [],
        "head":           head_doc,
        "head_id":        d.get("head_id"),
        "admin_ids":      d.get("admin_ids") or [],
        "parent_id":      d.get("parent_id"),
        "institution_id": iid,
        "institution":    {"id": iid, "name": (inst or {}).get("name"),
                           "logo_url": (inst or {}).get("logo_url")},
        "member_count":   member_count,
        "project_count":  proj_count,
        "is_dept_member": is_dept_member,
        "is_admin":       is_admin,
        "created_at":     d.get("created_at"),
        "updated_at":     d.get("updated_at"),
    }


@router.patch("/api/departments/{did}")
async def update_department(
    did: str,
    payload: DepartmentUpdate,
    user: dict = Depends(get_current_user),
):
    """Update department metadata. Requires department admin or institution admin."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_admin(iid, did, user["id"])
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    upd = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    upd["updated_at"] = _now()
    await db.units.update_one({"_id": ObjectId(did)}, {"$set": upd})
    # Invalidate metrics cache
    await db.department_metrics.delete_one({"department_id": did})
    await _audit(iid, user["id"], "department_updated",
                 target_id=did, metadata={"fields": list(upd.keys())})
    return await get_department(did, user=user)


@router.delete("/api/departments/{did}")
async def delete_department(did: str, user: dict = Depends(get_current_user)):
    """Delete department. Requires institution admin (not just dept admin)."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    # Only institution admin or platform admin may delete
    platform_admin = zt_is_admin(user)
    if not platform_admin:
        m = await db_check_inst_admin(iid, user["id"])
        if not m:
            raise HTTPException(403, "Institution admin required to delete departments")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.units.delete_one({"_id": ObjectId(did)})
    await db.institution_memberships.update_many(
        {"institution_id": iid, "unit_ids": did},
        {"$pull": {"unit_ids": did}})
    await db.department_projects.delete_many({"department_id": did})
    await db.department_metrics.delete_one({"department_id": did})
    await _audit(iid, user["id"], "department_deleted", target_id=did)
    return {"ok": True}


async def db_check_inst_admin(iid: str, user_id: str) -> Optional[dict]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    m = await db.institution_memberships.find_one(
        {"institution_id": iid, "user_id": user_id, "status": "approved"})
    if not m or m.get("role") not in {"owner", "admin"}:
        raise HTTPException(403, "Institution admin required")
    return m


# ─────────────────────────── members ─────────────────────────────────────────

@router.get("/api/departments/{did}/members")
async def list_dept_members(did: str, user: dict = Depends(get_current_user)):
    """List all faculty and staff in this department."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])
    members = await get_dept_members_enriched(iid, did)
    # Enrich role labels
    for m in members:
        m["role_label"] = DEPT_ROLE_LABEL.get(m.get("role"), m.get("role", ""))
    return members


@router.post("/api/departments/{did}/members")
async def manage_dept_members(
    did: str,
    payload: MembersIn,
    user: dict = Depends(get_current_user),
):
    """Add or remove members from this department."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_admin(iid, did, user["id"])
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    op  = "$addToSet" if payload.action == "add" else "$pull"
    for uid in payload.user_ids:
        await db.institution_memberships.update_one(
            {"institution_id": iid, "user_id": uid, "status": "approved"},
            {op: {"unit_ids": did}},
        )
    await db.department_metrics.delete_one({"department_id": did})
    await _audit(iid, user["id"], f"dept_members_{payload.action}",
                 target_id=did, metadata={"user_ids": payload.user_ids})
    return {"ok": True}


@router.patch("/api/departments/{did}/members/{uid}/role")
async def update_member_role(
    did: str,
    uid: str,
    payload: RoleIn,
    user: dict = Depends(get_current_user),
):
    """Update a member's role within the institution (dept-scoped)."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_admin(iid, did, user["id"])
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.institution_memberships.update_one(
        {"institution_id": iid, "user_id": uid, "status": "approved"},
        {"$set": {"role": payload.role, "updated_at": _now()}},
    )
    await _audit(iid, user["id"], "dept_role_assigned",
                 target_kind="user", target_id=uid,
                 metadata={"role": payload.role, "department_id": did})
    return {"ok": True}


# ─────────────────────────── projects ────────────────────────────────────────

@router.get("/api/departments/{did}/projects")
async def list_dept_projects(did: str, user: dict = Depends(get_current_user)):
    """List projects linked to this department."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])
    return await get_dept_projects(did)


@router.post("/api/departments/{did}/projects")
async def link_project(
    did: str,
    payload: ProjectLinkIn,
    user: dict = Depends(get_current_user),
):
    """Link an existing project to this department."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_admin(iid, did, user["id"])
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Validate project exists
    try:
        proj = await db.projects.find_one({"_id": ObjectId(payload.project_id)}, {"title": 1})
    except Exception:
        proj = None
    if not proj:
        raise HTTPException(404, "Project not found")
    # Upsert link (prevent duplicates)
    await db.department_projects.update_one(
        {"department_id": did, "project_id": payload.project_id},
        {"$setOnInsert": {
            "department_id":  did,
            "project_id":     payload.project_id,
            "institution_id": iid,
            "linked_by":      user["id"],
            "linked_at":      _now(),
        }},
        upsert=True,
    )
    await db.department_metrics.delete_one({"department_id": did})
    await _audit(iid, user["id"], "dept_project_linked",
                 target_id=did, metadata={"project_id": payload.project_id})
    return {"ok": True}


@router.delete("/api/departments/{did}/projects/{pid}")
async def unlink_project(
    did: str,
    pid: str,
    user: dict = Depends(get_current_user),
):
    """Remove a project link from this department."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_admin(iid, did, user["id"])
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.department_projects.delete_one({"department_id": did, "project_id": pid})
    await db.department_metrics.delete_one({"department_id": did})
    await _audit(iid, user["id"], "dept_project_unlinked",
                 target_id=did, metadata={"project_id": pid})
    return {"ok": True}


# ─────────────────────────── analytics endpoints ──────────────────────────────

@router.get("/api/departments/{did}/metrics")
async def dept_metrics(did: str, refresh: bool = False,
                        user: dict = Depends(get_current_user)):
    """Aggregated research output KPIs for this department."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])
    if refresh:
        await db_invalidate_cache(did)
    return await get_cached_metrics(did, iid)


@router.get("/api/departments/{did}/rankings")
async def dept_rankings(did: str, user: dict = Depends(get_current_user)):
    """Rankings of all departments within the institution."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])
    all_ranks = await rank_departments(iid)
    # Mark the requested department
    for r in all_ranks:
        r["is_current"] = r["department_id"] == did
    return {"rankings": all_ranks, "current_dept_id": did}


@router.get("/api/departments/{did}/collaboration")
async def dept_collaboration(did: str, user: dict = Depends(get_current_user)):
    """Collaboration network for department members."""
    iid = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])
    return await get_dept_collaboration(iid, did)


@router.get("/api/departments/{did}/publications")
async def dept_publications(
    did: str,
    limit: int = Query(50, le=200),
    user: dict = Depends(get_current_user),
):
    """Publication list scoped to department members, sorted by citations."""
    iid     = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])
    db      = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uids    = await get_dept_user_ids(iid, did)
    if not uids:
        return {"publications": [], "total": 0}
    pub_docs = await db.publications.find(
        {"owner_id": {"$in": uids}},
        {"title": 1, "year": 1, "journal": 1, "citations": 1,
         "doi": 1, "type": 1, "topics": 1, "owner_id": 1, "coauthors": 1},
    ).sort("citations", -1).limit(limit).to_list(limit)
    total = await db.publications.count_documents({"owner_id": {"$in": uids}})

    # Enrich with author name
    uid_name_map: dict[str, str] = {}
    udocs = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in uids]}},
        {"full_name": 1},
    ).to_list(len(uids))
    for u in udocs:
        uid_name_map[str(u["_id"])] = u.get("full_name") or ""

    out = []
    for p in pub_docs:
        out.append({
            "id":         str(p["_id"]),
            "title":      p.get("title") or "Untitled",
            "year":       p.get("year"),
            "journal":    p.get("journal"),
            "citations":  int(p.get("citations") or 0),
            "doi":        p.get("doi"),
            "type":       p.get("type"),
            "topics":     (p.get("topics") or [])[:3],
            "author_id":  p.get("owner_id"),
            "author":     uid_name_map.get(p.get("owner_id"), ""),
        })
    return {"publications": out, "total": total}


@router.get("/api/departments/{did}/funding")
async def dept_funding(did: str, user: dict = Depends(get_current_user)):
    """Grants and funding breakdown for department members."""
    iid  = await _get_dept_iid(did)
    await assert_institution_plan(iid)
    await assert_dept_membership(iid, user["id"])
    db   = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uids = await get_dept_user_ids(iid, did)
    if not uids:
        return {"total_usd": 0, "by_status": [], "top_grants": []}

    by_status = await db.grant_links.aggregate([
        {"$match": {"user_id": {"$in": uids}}},
        {"$group": {"_id": "$status", "n": {"$sum": 1}, "usd": {"$sum": "$amount_usd"}}},
        {"$sort": {"usd": -1}},
    ]).to_list(20)

    total_usd = sum(int(r.get("usd") or 0) for r in by_status if r.get("_id") == "awarded")

    # Top grants
    top_grant_links = await db.grant_links.find(
        {"user_id": {"$in": uids}, "status": "awarded"},
        {"grant_id": 1, "user_id": 1, "amount_usd": 1, "title": 1, "status": 1},
    ).sort("amount_usd", -1).limit(10).to_list(10)

    uid_name_map: dict[str, str] = {}
    udocs = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in uids]}},
        {"full_name": 1},
    ).to_list(len(uids))
    for u in udocs:
        uid_name_map[str(u["_id"])] = u.get("full_name") or ""

    top_grants = []
    for lk in top_grant_links:
        top_grants.append({
            "id":         str(lk.get("_id", "")),
            "title":      lk.get("title") or "Grant",
            "amount_usd": int(lk.get("amount_usd") or 0),
            "status":     lk.get("status"),
            "researcher": uid_name_map.get(lk.get("user_id"), ""),
        })

    return {
        "total_usd":  total_usd,
        "by_status":  [{"status": r["_id"], "n": r["n"], "usd": int(r.get("usd") or 0)}
                       for r in by_status if r.get("_id")],
        "top_grants": top_grants,
    }


async def db_invalidate_cache(department_id: str) -> None:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.department_metrics.delete_one({"department_id": department_id})
