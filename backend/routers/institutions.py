"""Institutions router — directory, profile, governance, multi-seat, units, analytics.

Routes:
  GET    /api/institutions                         — directory (q, country, type)
  POST   /api/institutions                         — create (any user; creator becomes owner)
  GET    /api/institutions/{id}                    — full profile
  PATCH  /api/institutions/{id}                    — admin-only update
  DELETE /api/institutions/{id}                    — owner-only

  GET    /api/institutions/{id}/members            — list memberships
  POST   /api/institutions/{id}/claim              — self-claim (email-domain auto-verify or pending)
  POST   /api/institutions/{id}/invite             — admin invite (auto-approved on accept)
  POST   /api/institutions/{id}/members/{uid}/decide — admin approve/reject
  POST   /api/institutions/{id}/members/{uid}/role  — admin assign role
  POST   /api/institutions/{id}/members/{uid}/seat  — admin set seat type
  POST   /api/institutions/{id}/members/{uid}/revoke — admin remove
  POST   /api/institutions/{id}/seats               — admin update seat capacity

  GET    /api/institutions/{id}/audit              — admin-only audit log

  GET    /api/institutions/{id}/units              — list units (tree)
  POST   /api/institutions/{id}/units              — create
  GET    /api/units/{id}                            — unit detail
  PATCH  /api/units/{id}                            — unit admin update
  DELETE /api/units/{id}                            — institution admin only
  POST   /api/units/{id}/members                    — add/remove members

  GET    /api/institutions/{id}/analytics           — overview KPIs
  GET    /api/institutions/{id}/analytics/publications
  GET    /api/institutions/{id}/analytics/collaboration
  GET    /api/institutions/{id}/analytics/funding
  GET    /api/institutions/{id}/analytics/reputation
  GET    /api/institutions/{id}/analytics/marketplace
  GET    /api/institutions/{id}/analytics/health    — composite Research Health Score
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.institutions import analytics as A
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(tags=["institutions"])

# Allowed roles within an institution
ROLES = ["owner", "admin", "unit_admin", "research_lead", "researcher"]
ADMIN_ROLES = {"owner", "admin"}
SEAT_TYPES = ["personal", "sponsored", "institution_owned", None]


def _now() -> str: return datetime.now(timezone.utc).isoformat()


# ============================= HELPERS ======================================
async def _audit(institution_id: str, actor_id: str, action: str,
                  *, target_kind: Optional[str] = None, target_id: Optional[str] = None,
                  metadata: Optional[dict] = None):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.institution_audit.insert_one({
        "institution_id": institution_id, "actor_id": actor_id, "action": action,
        "target_kind": target_kind, "target_id": target_id,
        "metadata": metadata or {}, "created_at": _now(),
    })


async def _require_admin(institution_id: str, user: dict, *, allow_unit_admin: bool = False):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if zt_is_admin(user):  # platform admin override
        return True
    m = await db.institution_memberships.find_one(
        {"institution_id": institution_id, "user_id": user["id"], "status": "approved"})
    if not m: raise HTTPException(403, "Not a member of this institution")
    allowed = ADMIN_ROLES | ({"unit_admin"} if allow_unit_admin else set())
    if m.get("role") not in allowed: raise HTTPException(403, "Admin role required")
    return True


def _email_domain(email: str) -> Optional[str]:
    if not email or "@" not in email: return None
    return email.split("@", 1)[1].lower().strip()


# ============================= DIRECTORY ====================================
class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    country: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    email_domains: list[str] = []
    research_areas: list[str] = []
    type: Literal["university", "research_institute", "government", "company", "multi_campus", "other"] = "university"


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    email_domains: Optional[list[str]] = None
    research_areas: Optional[list[str]] = None
    type: Optional[str] = None
    plan_code: Optional[str] = None
    seats_total: Optional[int] = None


@router.get("/api/institutions")
async def list_institutions(
    q: Optional[str] = None, country: Optional[str] = None, type: Optional[str] = None,
    limit: int = Query(40, le=100), skip: int = 0,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    import re as _re
    qf: dict = {}
    if q:
        q_safe = _re.escape(q)
        qf["$or"] = [{"name": {"$regex": q_safe, "$options": "i"}},
                     {"description": {"$regex": q_safe, "$options": "i"}},
                     {"research_areas": {"$regex": q_safe, "$options": "i"}}]
    if country: qf["country"] = {"$regex": f"^{_re.escape(country)}$", "$options": "i"}
    if type: qf["type"] = type
    total = await db.institutions.count_documents(qf)
    docs = await db.institutions.find(qf).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        d["member_count"] = await db.institution_memberships.count_documents(
            {"institution_id": d["id"], "status": "approved"})
        out.append(d)
    return {"results": out, "total": total}


@router.post("/api/institutions")
async def create_institution(payload: InstitutionCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = payload.model_dump()
    doc.update({
        "owner_id": user["id"], "admin_ids": [user["id"]],
        "slug": doc["name"].lower().replace(" ", "-")[:80],
        "plan_code": "institution_free",
        "seats": {"total": 5, "assigned": 1, "sponsored": 0},
        "created_at": _now(), "updated_at": _now(),
    })
    r = await db.institutions.insert_one(doc)
    iid = str(r.inserted_id)
    doc.pop("_id", None)
    # Creator becomes owner-member auto-approved.
    await db.institution_memberships.insert_one({
        "institution_id": iid, "user_id": user["id"], "role": "owner",
        "status": "approved", "unit_ids": [], "seat_type": "institution_owned",
        "verified_via": "creator", "joined_at": _now(),
    })
    # Link user.institution_id for backwards-compat aggregations.
    await db.users.update_one({"_id": ObjectId(user["id"])},
                                {"$set": {"institution_id": iid}})
    await _audit(iid, user["id"], "institution_created", target_kind="institution", target_id=iid)
    return {**doc, "id": iid}


@router.get("/api/institutions/{iid}")
async def get_institution(iid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(iid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.institutions.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    d["id"] = str(d.pop("_id"))
    d["member_count"] = await db.institution_memberships.count_documents(
        {"institution_id": iid, "status": "approved"})
    # My membership in this institution (for UI gating)
    me = await db.institution_memberships.find_one(
        {"institution_id": iid, "user_id": user["id"]})
    if me:
        me["id"] = str(me.pop("_id"))
        d["my_membership"] = me
    return d


@router.patch("/api/institutions/{iid}")
async def update_institution(iid: str, payload: InstitutionUpdate,
                              user: dict = Depends(get_current_user)):
    await _require_admin(iid, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "seats_total" in update:
        seats = (await db.institutions.find_one({"_id": ObjectId(iid)}, {"seats": 1})) \
                 .get("seats") or {"total": 0, "assigned": 0, "sponsored": 0}
        seats["total"] = update.pop("seats_total")
        update["seats"] = seats
    update["updated_at"] = _now()
    await db.institutions.update_one({"_id": ObjectId(iid)}, {"$set": update})
    await _audit(iid, user["id"], "institution_updated", metadata={"fields": list(update.keys())})
    return await get_institution(iid, user=user)


@router.delete("/api/institutions/{iid}")
async def delete_institution(iid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    d = await db.institutions.find_one({"_id": ObjectId(iid)})
    if not d: raise HTTPException(404, "Not found")
    if d["owner_id"] != user["id"] and not zt_is_admin(user):
        raise HTTPException(403, "Only the owner can delete")
    await db.institutions.delete_one({"_id": ObjectId(iid)})
    await db.units.delete_many({"institution_id": iid})
    await db.institution_memberships.delete_many({"institution_id": iid})
    return {"ok": True}


# ============================= MEMBERS ======================================
@router.get("/api/institutions/{iid}/members")
async def list_members(iid: str, status: Optional[str] = None,
                        user: dict = Depends(get_current_user), limit: int = 200):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    qf: dict = {"institution_id": iid}
    if status: qf["status"] = status
    rows = await db.institution_memberships.find(qf).sort("joined_at", -1).limit(limit).to_list(limit)
    uids = [r["user_id"] for r in rows]
    udocs = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in uids]}},
        {"full_name": 1, "email": 1, "academic_role": 1, "avatar_url": 1, "institution": 1}
    ).to_list(len(uids)) if uids else []
    umap = {}
    for u in udocs:
        uid_str = str(u.pop("_id"))
        umap[uid_str] = {**u, "id": uid_str}
    out = []
    for r in rows:
        r["id"] = str(r.pop("_id"))
        r["user"] = umap.get(r["user_id"])
        out.append(r)
    return out


class ClaimIn(BaseModel):
    note: Optional[str] = None
    unit_ids: list[str] = []


@router.post("/api/institutions/{iid}/claim")
async def claim_institution(iid: str, payload: ClaimIn,
                             user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    inst = await db.institutions.find_one({"_id": ObjectId(iid)},
                                            {"email_domains": 1, "name": 1, "seats": 1})
    if not inst: raise HTTPException(404, "Not found")
    existing = await db.institution_memberships.find_one(
        {"institution_id": iid, "user_id": user["id"]})
    if existing and existing.get("status") == "approved":
        raise HTTPException(400, "Already a member")
    domain = _email_domain(user.get("email") or "")
    auto = domain in (inst.get("email_domains") or [])
    record = {
        "institution_id": iid, "user_id": user["id"], "role": "researcher",
        "status": "approved" if auto else "pending",
        "unit_ids": payload.unit_ids,
        "seat_type": "personal", "verified_via": "email_domain" if auto else "admin_approval",
        "note": payload.note, "joined_at": _now(),
    }
    if existing:
        await db.institution_memberships.update_one(
            {"_id": existing["_id"]}, {"$set": record})
    else:
        await db.institution_memberships.insert_one(record)
    if auto:
        await db.users.update_one({"_id": ObjectId(user["id"])},
                                    {"$set": {"institution_id": iid}})
        await _audit(iid, user["id"], "member_self_joined_via_email_domain",
                      target_kind="user", target_id=user["id"], metadata={"domain": domain})
    else:
        await _audit(iid, user["id"], "member_claim_pending",
                      target_kind="user", target_id=user["id"])
    return {"status": record["status"], "verified_via": record["verified_via"]}


class MemberDecisionIn(BaseModel):
    decision: Literal["approved", "denied"]


@router.post("/api/institutions/{iid}/members/{uid}/decide")
async def decide_member(iid: str, uid: str, payload: MemberDecisionIn,
                         user: dict = Depends(get_current_user)):
    await _require_admin(iid, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.institution_memberships.update_one(
        {"institution_id": iid, "user_id": uid},
        {"$set": {"status": payload.decision, "decided_by": user["id"], "decided_at": _now()}}
    )
    if payload.decision == "approved":
        await db.users.update_one({"_id": ObjectId(uid)}, {"$set": {"institution_id": iid}})
    await _audit(iid, user["id"], f"member_{payload.decision}", target_kind="user", target_id=uid)
    return {"ok": True}


class RoleIn(BaseModel):
    role: Literal["admin", "unit_admin", "research_lead", "researcher"]


@router.post("/api/institutions/{iid}/members/{uid}/role")
async def assign_role(iid: str, uid: str, payload: RoleIn,
                       user: dict = Depends(get_current_user)):
    await _require_admin(iid, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.institution_memberships.update_one(
        {"institution_id": iid, "user_id": uid},
        {"$set": {"role": payload.role, "updated_at": _now()}}
    )
    await _audit(iid, user["id"], "role_assigned", target_kind="user", target_id=uid,
                  metadata={"role": payload.role})
    return {"ok": True}


class SeatIn(BaseModel):
    seat_type: Literal["personal", "sponsored", "institution_owned"]


@router.post("/api/institutions/{iid}/members/{uid}/seat")
async def set_seat(iid: str, uid: str, payload: SeatIn,
                    user: dict = Depends(get_current_user)):
    await _require_admin(iid, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    inst = await db.institutions.find_one({"_id": ObjectId(iid)}, {"seats": 1})
    if not inst: raise HTTPException(404, "Not found")
    seats = inst.get("seats") or {"total": 0, "assigned": 0, "sponsored": 0}
    if payload.seat_type in {"sponsored", "institution_owned"}:
        # Enforce seat cap
        used = await db.institution_memberships.count_documents({
            "institution_id": iid, "status": "approved",
            "seat_type": {"$in": ["sponsored", "institution_owned"]}})
        # If user is being newly assigned a paid seat, ensure room.
        current = await db.institution_memberships.find_one(
            {"institution_id": iid, "user_id": uid}, {"seat_type": 1})
        is_upgrade = (current or {}).get("seat_type") not in {"sponsored", "institution_owned"}
        if is_upgrade and used >= (seats.get("total") or 0):
            raise HTTPException(400, f"No seats available ({used}/{seats.get('total')})")
    await db.institution_memberships.update_one(
        {"institution_id": iid, "user_id": uid},
        {"$set": {"seat_type": payload.seat_type, "updated_at": _now()}}
    )
    # Recount assigned seats
    assigned = await db.institution_memberships.count_documents({
        "institution_id": iid, "status": "approved",
        "seat_type": {"$in": ["sponsored", "institution_owned"]}})
    seats["assigned"] = assigned
    await db.institutions.update_one({"_id": ObjectId(iid)}, {"$set": {"seats": seats}})
    await _audit(iid, user["id"], "seat_assigned", target_kind="user", target_id=uid,
                  metadata={"seat_type": payload.seat_type})
    return {"ok": True, "seats": seats}


@router.post("/api/institutions/{iid}/members/{uid}/revoke")
async def revoke_member(iid: str, uid: str, user: dict = Depends(get_current_user)):
    await _require_admin(iid, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Owners cannot be revoked
    target = await db.institution_memberships.find_one({"institution_id": iid, "user_id": uid})
    if not target: raise HTTPException(404, "Not found")
    if target.get("role") == "owner":
        raise HTTPException(400, "Cannot revoke owner")
    await db.institution_memberships.update_one(
        {"_id": target["_id"]},
        {"$set": {"status": "revoked", "revoked_at": _now()}}
    )
    await db.users.update_one({"_id": ObjectId(uid)}, {"$unset": {"institution_id": ""}})
    await _audit(iid, user["id"], "member_revoked", target_kind="user", target_id=uid)
    return {"ok": True}


# ============================= INVITE ========================================

class InviteIn(BaseModel):
    email: str
    role: Optional[str] = "researcher"
    message: Optional[str] = ""


@router.post("/api/institutions/{iid}/invite")
async def invite_member(iid: str, payload: InviteIn, user: dict = Depends(get_current_user)):
    """Admin-invite a user by email. If user exists → creates pending_invite membership.
    If user doesn't exist → stores pre-registration invite. Idempotent."""
    await _require_admin(iid, user)
    if payload.role not in ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of {ROLES}")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    inst = await db.institutions.find_one({"_id": ObjectId(iid)}, {"name": 1, "seats": 1})
    if not inst:
        raise HTTPException(404, "Institution not found")

    target_user = await db.users.find_one({"email": payload.email.lower()}, {"_id": 1, "email": 1})

    now = _now()
    if target_user:
        target_uid = str(target_user["_id"])
        existing = await db.institution_memberships.find_one(
            {"institution_id": iid, "user_id": target_uid}
        )
        if existing and existing.get("status") in ("approved", "pending_invite", "pending"):
            return {"ok": True, "user_found": True, "status": existing["status"],
                    "message": "User already has a membership record"}

        await db.institution_memberships.update_one(
            {"institution_id": iid, "user_id": target_uid},
            {"$set": {
                "institution_id": iid, "user_id": target_uid,
                "status": "pending_invite", "role": payload.role,
                "seat_type": "institution_owned", "unit_ids": [],
                "invited_by": user["id"], "invite_message": payload.message or "",
                "invited_at": now, "updated_at": now,
            }},
            upsert=True,
        )
        # Dispatch notification to invited user
        try:
            from services.notifications_service import dispatch as _d, NotificationEvent as _NE
            async def _notify():
                try:
                    await _d(_NE.INSTITUTION_INVITE, actor_id=user["id"],
                             target_user_id=target_uid,
                             payload={"institution_id": iid,
                                      "institution_name": inst.get("name"),
                                      "role": payload.role})
                except Exception:
                    pass
            import asyncio as _asyncio
            _asyncio.create_task(_notify())
        except Exception:
            pass
        await _audit(iid, user["id"], "member_invited",
                     target_kind="user", target_id=target_uid,
                     metadata={"email": payload.email, "role": payload.role})
        return {"ok": True, "user_found": True, "status": "pending_invite",
                "user_id": target_uid}
    else:
        # User not yet registered — store pre-registration invite
        await db.institution_invites.update_one(
            {"institution_id": iid, "email": payload.email.lower()},
            {"$set": {
                "institution_id": iid, "email": payload.email.lower(),
                "role": payload.role, "invited_by": user["id"],
                "invite_message": payload.message or "",
                "status": "pending_registration", "created_at": now, "updated_at": now,
            }},
            upsert=True,
        )
        await _audit(iid, user["id"], "invite_sent_external",
                     metadata={"email": payload.email, "role": payload.role})
        return {"ok": True, "user_found": False, "status": "pending_registration",
                "message": "Invite stored; user will be auto-joined on registration"}


# ============================= SEATS =========================================

class SeatCapacityIn(BaseModel):
    seats_total: int = Field(..., ge=1, le=10000)


@router.post("/api/institutions/{iid}/seats")
async def update_seat_capacity(iid: str, payload: SeatCapacityIn,
                                user: dict = Depends(get_current_user)):
    """Admin update seat capacity for the institution."""
    await _require_admin(iid, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    inst = await db.institutions.find_one({"_id": ObjectId(iid)}, {"seats": 1})
    if not inst:
        raise HTTPException(404, "Institution not found")
    current_seats = inst.get("seats") or {"total": 0, "assigned": 0, "sponsored": 0}
    current_seats["total"] = payload.seats_total
    await db.institutions.update_one(
        {"_id": ObjectId(iid)},
        {"$set": {"seats": current_seats, "updated_at": _now()}}
    )
    await _audit(iid, user["id"], "seats_updated",
                 metadata={"seats_total": payload.seats_total})
    return {"ok": True, "seats": current_seats}


# ============================= AUDIT LOG ====================================
@router.get("/api/institutions/{iid}/audit")
async def audit_log(iid: str, limit: int = 100, user: dict = Depends(get_current_user)):
    await _require_admin(iid, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    rows = await db.institution_audit.find({"institution_id": iid}) \
        .sort("created_at", -1).limit(limit).to_list(limit)
    actor_ids = list({r.get("actor_id") for r in rows if r.get("actor_id")})
    udocs = await db.users.find({"_id": {"$in": [ObjectId(u) for u in actor_ids]}},
                                  {"full_name": 1}).to_list(len(actor_ids)) if actor_ids else []
    actor_names = {str(u["_id"]): u.get("full_name") for u in udocs}
    out = []
    for r in rows:
        r["id"] = str(r.pop("_id"))
        r["actor_name"] = actor_names.get(r.get("actor_id"))
        out.append(r)
    return out


# ============================= UNITS ========================================
class UnitCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    type: Literal["faculty", "department", "research_center", "lab", "institute", "school", "research_group", "other"] = "department"
    parent_id: Optional[str] = None
    description: Optional[str] = None
    research_areas: list[str] = []
    head_id: Optional[str] = None


class UnitUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[str] = None
    description: Optional[str] = None
    research_areas: Optional[list[str]] = None
    head_id: Optional[str] = None
    admin_ids: Optional[list[str]] = None


async def _enrich_unit(doc: dict) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    doc["id"] = str(doc.pop("_id"))
    # Counts
    doc["member_count"] = await db.institution_memberships.count_documents(
        {"institution_id": doc["institution_id"], "status": "approved",
         "unit_ids": doc["id"]})
    doc["child_count"] = await db.units.count_documents(
        {"institution_id": doc["institution_id"], "parent_id": doc["id"]})
    return doc


@router.get("/api/institutions/{iid}/units")
async def list_units(iid: str, parent_id: Optional[str] = None,
                      user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    qf: dict = {"institution_id": iid}
    if parent_id is not None:
        qf["parent_id"] = parent_id if parent_id else None
    docs = await db.units.find(qf).sort([("type", 1), ("name", 1)]).to_list(500)
    return [await _enrich_unit(d) for d in docs]


@router.post("/api/institutions/{iid}/units")
async def create_unit(iid: str, payload: UnitCreate, user: dict = Depends(get_current_user)):
    await _require_admin(iid, user)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = payload.model_dump()
    doc.update({
        "institution_id": iid, "admin_ids": [user["id"]] if doc.get("head_id") is None else [],
        "created_at": _now(), "updated_at": _now(),
    })
    r = await db.units.insert_one(doc)
    doc["_id"] = r.inserted_id
    await _audit(iid, user["id"], "unit_created", target_kind="unit", target_id=str(r.inserted_id))
    return await _enrich_unit(doc)


@router.get("/api/units/{uid}")
async def get_unit(uid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(uid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.units.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    enriched = await _enrich_unit(d)
    # parent breadcrumb
    breadcrumb = []
    cur = enriched
    safety = 0
    while cur and safety < 10:
        if cur.get("parent_id"):
            par = await db.units.find_one({"_id": ObjectId(cur["parent_id"])}, {"name": 1, "type": 1})
            if not par: break
            par["id"] = str(par["_id"])
            breadcrumb.append({"id": par["id"], "name": par.get("name"), "type": par.get("type")})
            cur = par
        else: break
        safety += 1
    breadcrumb.reverse()
    enriched["breadcrumb"] = breadcrumb
    # institution card
    inst = await db.institutions.find_one({"_id": ObjectId(enriched["institution_id"])},
                                            {"name": 1, "logo_url": 1, "country": 1})
    if inst:
        enriched["institution"] = {"id": str(inst["_id"]), "name": inst.get("name"),
                                    "logo_url": inst.get("logo_url"), "country": inst.get("country")}
    return enriched


@router.patch("/api/units/{uid}")
async def update_unit(uid: str, payload: UnitUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    d = await db.units.find_one({"_id": ObjectId(uid)})
    if not d: raise HTTPException(404, "Not found")
    iid = d["institution_id"]
    # Unit admin or institution admin
    if not zt_is_admin(user) and user["id"] not in (d.get("admin_ids") or []) and (d.get("head_id") != user["id"]):
        await _require_admin(iid, user)
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    update["updated_at"] = _now()
    await db.units.update_one({"_id": ObjectId(uid)}, {"$set": update})
    await _audit(iid, user["id"], "unit_updated", target_kind="unit", target_id=uid,
                  metadata={"fields": list(update.keys())})
    d2 = await db.units.find_one({"_id": ObjectId(uid)})
    return await _enrich_unit(d2)


@router.delete("/api/units/{uid}")
async def delete_unit(uid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    d = await db.units.find_one({"_id": ObjectId(uid)})
    if not d: raise HTTPException(404, "Not found")
    iid = d["institution_id"]
    await _require_admin(iid, user)
    # Move children up to parent
    await db.units.update_many({"institution_id": iid, "parent_id": uid},
                                {"$set": {"parent_id": d.get("parent_id")}})
    # Remove unit reference from memberships
    await db.institution_memberships.update_many(
        {"institution_id": iid, "unit_ids": uid},
        {"$pull": {"unit_ids": uid}})
    await db.units.delete_one({"_id": ObjectId(uid)})
    await _audit(iid, user["id"], "unit_deleted", target_kind="unit", target_id=uid)
    return {"ok": True}


class UnitMembershipIn(BaseModel):
    user_ids: list[str]
    action: Literal["add", "remove"] = "add"


@router.post("/api/units/{uid}/members")
async def unit_members(uid: str, payload: UnitMembershipIn,
                        user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    d = await db.units.find_one({"_id": ObjectId(uid)})
    if not d: raise HTTPException(404, "Not found")
    iid = d["institution_id"]
    if not zt_is_admin(user) and user["id"] not in (d.get("admin_ids") or []) and d.get("head_id") != user["id"]:
        await _require_admin(iid, user)
    op = "$addToSet" if payload.action == "add" else "$pull"
    for uid2 in payload.user_ids:
        await db.institution_memberships.update_one(
            {"institution_id": iid, "user_id": uid2, "status": "approved"},
            {op: {"unit_ids": uid}}
        )
    await _audit(iid, user["id"], f"unit_members_{payload.action}", target_kind="unit", target_id=uid,
                  metadata={"user_ids": payload.user_ids})
    return {"ok": True}


# ============================= ANALYTICS ====================================
@router.get("/api/institutions/{iid}/analytics")
async def analytics_overview(iid: str, user: dict = Depends(get_current_user)):
    return await A.institution_overview(iid)

@router.get("/api/institutions/{iid}/analytics/publications")
async def analytics_publications(iid: str, user: dict = Depends(get_current_user)):
    return await A.publications_breakdown(iid)

@router.get("/api/institutions/{iid}/analytics/collaboration")
async def analytics_collaboration(iid: str, user: dict = Depends(get_current_user)):
    return await A.collaboration_breakdown(iid)

@router.get("/api/institutions/{iid}/analytics/funding")
async def analytics_funding(iid: str, user: dict = Depends(get_current_user)):
    return await A.funding_breakdown(iid)

@router.get("/api/institutions/{iid}/analytics/reputation")
async def analytics_reputation(iid: str, user: dict = Depends(get_current_user)):
    return await A.reputation_top(iid)

@router.get("/api/institutions/{iid}/analytics/marketplace")
async def analytics_marketplace(iid: str, user: dict = Depends(get_current_user)):
    return await A.marketplace_activity(iid)

@router.get("/api/institutions/{iid}/analytics/health")
async def analytics_health(iid: str, user: dict = Depends(get_current_user)):
    return await A.research_health(iid)
