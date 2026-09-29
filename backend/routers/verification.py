from __future__ import annotations
import asyncio
import logging
import re
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from auth_utils import get_current_user
from db import get_db
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin
from repo.shim import make_db_proxy

logger = logging.getLogger("synaptiq")
router = APIRouter(prefix="/api/verification", tags=["verification"])


def _s(v):
    return str(v) if v is not None else None


# ──────────────────────────────────────────────
# Request / Response bodies
# ──────────────────────────────────────────────

class OrcidBody(BaseModel):
    orcid: str


class EvidenceBody(BaseModel):
    evidence_type: str
    description: str = ""


class InstitutionVerifyBody(BaseModel):
    # institution_id is set when the user selected a real institutions-
    # directory entry (P1 Phase 7C4.4 Method 2, institution known);
    # institution_name is the free-text fallback when their institution
    # isn't in the directory yet — at least one is required. evidence_kind/
    # evidence_url capture the affiliation evidence an admin reviews (a
    # staff/directory page URL, an appointment letter link, etc.) — never a
    # file upload (no such infra exists here, and inventing one is out of
    # scope), never automatically trusted.
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    department: str = ""
    role: str = ""
    evidence_kind: Optional[str] = None
    evidence_url: Optional[str] = None
    notes: str = ""


class EvidenceReviewBody(BaseModel):
    decision: str
    notes: str = ""


class SetLevelBody(BaseModel):
    level: int
    reason: str = ""


class RequestDecideBody(BaseModel):
    decision: str
    notes: str = ""


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _require_admin(user: dict):
    zt_check(user, "admin", "admin")


# ──────────────────────────────────────────────
# /me  static routes
# ──────────────────────────────────────────────

@router.get("/me")
async def get_my_verification_profile(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.verification import profile_service
    # Recomputes on every read rather than returning a possibly-stale (or
    # never-computed) default — compute_verification_profile() is
    # idempotent and skips the write when nothing actually changed.
    profile = await profile_service.compute_verification_profile(user["id"], db)
    return profile


@router.post("/me/compute")
async def compute_my_verification_profile(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.verification import profile_service
    profile = await profile_service.compute_verification_profile(user["id"], db)
    return profile


@router.get("/me/badges")
async def get_my_badges(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.verification import badge_service
    badges = await badge_service.get_user_badges(user["id"], db)
    return badges


@router.get("/me/history")
async def get_my_verification_history(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.verification import profile_service
    history = await profile_service.get_verification_history(user["id"], db)
    return history


@router.get("/me/trust-breakdown")
async def get_my_trust_breakdown(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.verification import trust_score_engine
    breakdown = await trust_score_engine.compute_trust_breakdown(user["id"], db)
    return breakdown


@router.post("/me/orcid")
async def link_orcid(
    body: OrcidBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    orcid_pattern = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
    if not orcid_pattern.match(body.orcid) or len(body.orcid) != 19:
        raise HTTPException(status_code=400, detail="Invalid ORCID format. Expected XXXX-XXXX-XXXX-XXXX")

    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"orcid": body.orcid, "orcid_verified": True}},
    )

    from services.verification import profile_service
    await profile_service.compute_verification_profile(user["id"], db)

    return {"orcid": body.orcid, "orcid_verified": True}


@router.get("/me/evidence")
async def get_my_evidence(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.verification import evidence_service
    evidence = await evidence_service.get_user_evidence(user["id"], db)
    return evidence


@router.post("/me/evidence")
async def submit_my_evidence(
    body: EvidenceBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.verification import evidence_service
    doc = await evidence_service.submit_evidence(
        user["id"], body.evidence_type, body.description, db
    )
    return doc


@router.post("/me/institution")
async def request_institution_verification(
    body: InstitutionVerifyBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Method 2 fallback for an institution not (yet) in the institutions
    directory — see routers/institutions.py's claim() for the preferred
    path when the institution IS in the directory. Creates a pending
    request for an authorized admin to review (P1 Phase 7C4.4 §D Method 2).
    """
    db = make_db_proxy(db, user)
    if not (body.institution_id or (body.institution_name or "").strip()):
        raise HTTPException(400, "institution_id or institution_name is required")

    now = datetime.now(timezone.utc)

    # Don't let repeated clicks pile up duplicate pending requests — surface
    # the existing one instead of creating another the admin queue would
    # have to de-duplicate by hand.
    existing = await db.verification_requests.find_one(
        {"user_id": user["id"], "request_type": "institution", "status": "pending"}
    )
    if existing:
        existing["_id"] = _s(existing.get("_id"))
        return existing

    request_doc = {
        "user_id": user["id"],
        "request_type": "institution",
        "status": "pending",
        "details": body.dict(),
        "created_at": now,
    }
    result = await db.verification_requests.insert_one(request_doc)
    request_doc["_id"] = _s(result.inserted_id)
    return request_doc


@router.get("/me/institution-status")
async def get_my_institution_status(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Read-only aggregation over the real institution-verification state —
    verification_profiles.institution_verified plus whichever of the two
    request-shaped collections (institution_memberships for a known
    institution, verification_requests for a not-yet-catalogued one) is
    actually in flight. P1 Phase 7C4.4 §E: the Passport previously only had
    a bare boolean, which can only ever render "Verified" or a meaningless
    "Pending" — this exists so the UI can show the real state (not verified /
    in progress / verified / action required / rejected) instead. No new
    verification model — every field here already exists somewhere.
    """
    db = make_db_proxy(db, user)
    uid = user["id"]

    u = await db.users.find_one({"_id": ObjectId(uid)}, {"institution_id": 1, "institution": 1})
    inst_id = (u or {}).get("institution_id")

    if inst_id:
        inst = await db.institutions.find_one({"_id": ObjectId(inst_id)}, {"name": 1})
        membership = await db.institution_memberships.find_one({"institution_id": inst_id, "user_id": uid})
        if membership and membership.get("status") == "approved":
            return {
                "state": "verified",
                "institution_name": (inst or {}).get("name") or (u or {}).get("institution"),
                "verified_via": membership.get("verified_via"),
                "verified_at": _iso(membership.get("joined_at")),
            }

    # Not (yet) linked to an approved institution_memberships row — check
    # both request-shaped paths for anything in flight, most recent first.
    membership_req = await db.institution_memberships.find_one(
        {"user_id": uid}, sort=[("joined_at", -1)]
    ) if not inst_id else await db.institution_memberships.find_one({"institution_id": inst_id, "user_id": uid})
    legacy_req = await db.verification_requests.find_one(
        {"user_id": uid, "request_type": "institution"}, sort=[("created_at", -1)]
    )

    # Prefer whichever request is newer when both exist.
    def _ts(doc, key):
        if not doc:
            return None
        v = doc.get(key)
        return v if isinstance(v, str) else (v.isoformat() if v else None)

    m_time = _ts(membership_req, "joined_at")
    r_time = _ts(legacy_req, "created_at")
    use_membership = bool(membership_req) and (not legacy_req or (m_time or "") >= (r_time or ""))

    if use_membership and membership_req:
        status = membership_req.get("status")
        inst = await db.institutions.find_one({"_id": ObjectId(membership_req["institution_id"])}, {"name": 1})
        name = (inst or {}).get("name")
        if status == "pending":
            return {"state": "in_progress", "institution_name": name, "submitted_at": m_time}
        if status == "denied":
            return {"state": "rejected", "institution_name": name, "decided_at": _iso(membership_req.get("decided_at"))}

    if legacy_req:
        status = legacy_req.get("status")
        name = (legacy_req.get("details") or {}).get("institution_name") or (legacy_req.get("details") or {}).get("institution_id")
        if status == "pending":
            return {"state": "in_progress", "institution_name": name, "submitted_at": r_time}
        if status == "rejected":
            return {
                "state": "rejected", "institution_name": name,
                "decided_at": _iso(legacy_req.get("reviewed_at")), "notes": legacy_req.get("review_notes"),
            }

    return {"state": "not_verified", "institution_name": (u or {}).get("institution")}


def _iso(v):
    if v is None:
        return None
    return v if isinstance(v, str) else v.isoformat()


# ──────────────────────────────────────────────
# /directory  static route
# ──────────────────────────────────────────────

@router.get("/directory")
async def get_verification_directory(
    min_level: int = Query(0),
    verified_only: bool = Query(False),
    limit: int = Query(50),
    page: int = Query(1),
    db=Depends(get_db),
):
    db = make_db_proxy(db, system=True)
    query: dict = {"verification_level": {"$gte": min_level}}
    if verified_only:
        query["verification_level"] = {"$gte": 1}
        if min_level > 1:
            query["verification_level"] = {"$gte": min_level}

    skip = (page - 1) * limit
    total = await db.verification_profiles.count_documents(query)
    cursor = (
        db.verification_profiles.find(query)
        .sort("verification_score", -1)
        .skip(skip)
        .limit(limit)
    )
    profiles = await cursor.to_list(length=limit)

    # Join users for display fields
    items = []
    for p in profiles:
        uid = p.get("user_id")
        user_doc = None
        if uid:
            try:
                user_doc = await db.users.find_one({"_id": ObjectId(uid)})
            except Exception:
                pass
        item = {k: _s(v) if isinstance(v, ObjectId) else v for k, v in p.items()}
        item["_id"] = _s(p.get("_id"))
        if user_doc:
            item["full_name"] = user_doc.get("full_name") or user_doc.get("name", "")
            item["institution"] = user_doc.get("institution", "")
            item["country"] = user_doc.get("country", "")
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),  # ceiling division
    }


# ──────────────────────────────────────────────
# /admin  static routes
# ──────────────────────────────────────────────

@router.get("/admin/queue")
async def get_admin_queue(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    cursor = (
        db.verification_requests.find({"status": "pending"})
        .sort("created_at", 1)
        .limit(50)
    )
    requests = await cursor.to_list(length=50)
    items = []
    for r in requests:
        uid = r.get("user_id")
        user_doc = None
        if uid:
            try:
                user_doc = await db.users.find_one({"_id": ObjectId(uid)})
            except Exception:
                pass
        item = {k: _s(v) if isinstance(v, ObjectId) else v for k, v in r.items()}
        item["_id"] = _s(r.get("_id"))
        if user_doc:
            item["full_name"] = user_doc.get("full_name") or user_doc.get("name", "")
        items.append(item)
    return items


@router.get("/admin/evidence-queue")
async def get_admin_evidence_queue(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    cursor = (
        db.verification_evidence.find({"status": "pending"})
        .sort("created_at", 1)
        .limit(50)
    )
    evidence_list = await cursor.to_list(length=50)
    items = []
    for e in evidence_list:
        uid = e.get("user_id")
        user_doc = None
        if uid:
            try:
                user_doc = await db.users.find_one({"_id": ObjectId(uid)})
            except Exception:
                pass
        item = {k: _s(v) if isinstance(v, ObjectId) else v for k, v in e.items()}
        item["_id"] = _s(e.get("_id"))
        if user_doc:
            item["full_name"] = user_doc.get("full_name") or user_doc.get("name", "")
        items.append(item)
    return items


@router.post("/admin/evidence/{evidence_id}/review")
async def admin_review_evidence(
    evidence_id: str,
    body: EvidenceReviewBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    from services.verification import evidence_service
    result = await evidence_service.admin_review_evidence(
        evidence_id, body.decision, body.notes, user["id"], db
    )
    return result


@router.get("/admin/stats")
async def get_admin_stats(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    from services.verification import trust_score_engine, fraud_detection

    trust_stats, fraud_overview = await asyncio.gather(
        trust_score_engine.get_platform_trust_stats(db),
        fraud_detection.get_platform_fraud_overview(db),
    )
    return {**trust_stats, "fraud_overview": fraud_overview}


@router.get("/admin/fraud-overview")
async def get_admin_fraud_overview(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    from services.verification import fraud_detection
    overview = await fraud_detection.get_platform_fraud_overview(db)
    return overview


@router.post("/admin/set-level/{uid}")
async def admin_set_verification_level(
    uid: str,
    body: SetLevelBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    if body.level < 0 or body.level > 4:
        raise HTTPException(status_code=400, detail="Level must be between 0 and 4")

    now = datetime.now(timezone.utc)

    await db.verification_profiles.update_one(
        {"user_id": uid},
        {"$set": {"verification_level": body.level, "updated_at": now}},
        upsert=True,
    )

    history_doc = {
        "user_id": uid,
        "event": "level_set",
        "new_level": body.level,
        "reason": body.reason,
        "set_by": user["id"],
        "created_at": now,
    }
    audit_doc = {
        "user_id": uid,
        "action": "admin_set_level",
        "new_level": body.level,
        "reason": body.reason,
        "performed_by": user["id"],
        "created_at": now,
    }
    await asyncio.gather(
        db.verification_history.insert_one(history_doc),
        db.verification_audits.insert_one(audit_doc),
    )

    return {"user_id": uid, "new_level": body.level}


@router.post("/admin/request/{rid}/decide")
async def admin_decide_request(
    rid: str,
    body: RequestDecideBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    now = datetime.now(timezone.utc)

    try:
        request_oid = ObjectId(rid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request ID")

    await db.verification_requests.update_one(
        {"_id": request_oid},
        {
            "$set": {
                "status": body.decision,
                "reviewed_by": user["id"],
                "review_notes": body.notes,
                "reviewed_at": now,
            }
        },
    )

    if body.decision == "approved":
        req_doc = await db.verification_requests.find_one({"_id": request_oid})
        if req_doc:
            uid = req_doc.get("user_id")
            if uid:
                # compute_verification_profile() now itself checks for an
                # approved request_type="institution" verification_requests
                # doc (see services/verification/profile_service.py) — no
                # separate direct field write needed here. The previous
                # direct update_one(institution_verified=True) was silently
                # discarded by this very recompute call overwriting it back
                # to False on the next line, since the compute function had
                # no way to know about the approval (P1 Phase 7C4.4 — the
                # confirmed root cause of admin approval having no effect).
                from services.verification import profile_service
                await profile_service.compute_verification_profile(uid, db)

    audit_doc = {
        "action": "admin_decide_request",
        "request_id": rid,
        "decision": body.decision,
        "notes": body.notes,
        "performed_by": user["id"],
        "created_at": now,
    }
    await db.verification_audits.insert_one(audit_doc)

    updated = await db.verification_requests.find_one({"_id": request_oid})
    if updated:
        result = {k: _s(v) if isinstance(v, ObjectId) else v for k, v in updated.items()}
        result["_id"] = _s(updated.get("_id"))
        return result

    return {"_id": rid, "status": body.decision}


# ──────────────────────────────────────────────
# Parameterized /{uid} routes  (MUST come last)
# ──────────────────────────────────────────────

@router.get("/{uid}")
async def get_public_verification_profile(
    uid: str,
    db=Depends(get_db),
):
    db = make_db_proxy(db, system=True)
    from services.verification import profile_service
    profile = await profile_service.get_public_verification_profile(uid, db)
    return profile


@router.get("/{uid}/badges")
async def get_user_badges_public(
    uid: str,
    db=Depends(get_db),
):
    db = make_db_proxy(db, system=True)
    from services.verification import badge_service
    badges = await badge_service.get_user_badges(uid, db)
    return badges


@router.post("/{uid}/check-fraud")
async def check_user_fraud(
    uid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    from services.verification import fraud_detection
    result = await fraud_detection.check_for_anomalies(uid, db)
    return result
