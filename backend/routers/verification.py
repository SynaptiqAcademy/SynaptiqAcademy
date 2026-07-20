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
    institution_id: str
    department: str = ""
    role: str = ""


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
    profile = await profile_service.get_or_create_verification_profile(user["id"], db)
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
    db = make_db_proxy(db, user)
    now = datetime.now(timezone.utc)
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
                await db.verification_profiles.update_one(
                    {"user_id": uid},
                    {"$set": {"institution_verified": True, "updated_at": now}},
                    upsert=True,
                )
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
