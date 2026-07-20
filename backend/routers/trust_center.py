"""
Trust Center Router — /api/trust prefix

All endpoints are completely isolated from the existing /api/verification system.
New MongoDB collections: trust_verifications, trust_requests, trust_scores,
                         trust_badges, trust_passports, trust_audit.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger("synaptiq.trust")
router = APIRouter(prefix="/api/trust", tags=["trust-center"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_oid(s: str):
    try:
        return ObjectId(s)
    except Exception:
        return s


def _ser(doc: dict) -> dict:
    if not doc:
        return {}
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _ser(v)
        elif isinstance(v, list):
            out[k] = [_ser(i) if isinstance(i, dict) else (str(i) if isinstance(i, ObjectId) else i) for i in v]
        else:
            out[k] = v
    return out


def _uid(user) -> str:
    return str(user.get("_id") or user.get("id") or "")


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class SubmitVerificationRequest(BaseModel):
    verification_type: str
    payload: dict = Field(default_factory=dict)
    notes: Optional[str] = None
    evidence_urls: list[str] = Field(default_factory=list)


class AdminReviewRequest(BaseModel):
    action: str  # approve | reject | request_more_info
    notes: Optional[str] = None
    confidence_override: Optional[int] = None


class FlagIntegrityRequest(BaseModel):
    target_user_id: str
    details: str


class PassportVisibilityRequest(BaseModel):
    is_public: bool


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST SCORE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/score")
async def get_trust_score(
    refresh: bool = Query(False),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Return trust score; refreshes from cache or recomputes."""
    db = make_db_proxy(db, user)
    from services.trust.score_service import compute_trust_score, get_cached_trust_score
    uid = _uid(user)
    if not refresh:
        cached = await get_cached_trust_score(uid, db)
        if cached:
            return cached
    result = await compute_trust_score(uid, db)
    return result


@router.get("/score/{user_id}")
async def get_trust_score_for_user(
    user_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: get trust score for any user."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    from services.trust.score_service import compute_trust_score
    return await compute_trust_score(user_id, db)


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/verifications")
async def list_my_verifications(
    status: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    query: dict = {"user_id": uid}
    if status:
        query["status"] = status
    docs = await db.trust_verifications.find(query).sort("updated_at", -1).to_list(length=200)
    return [_ser(d) for d in docs]


@router.get("/verifications/types")
async def list_verification_types(user=Depends(get_current_user)):
    """Return the full catalogue of 22 verification types."""
    from services.trust.verification_engine import VERIFICATION_TYPES
    return [{"id": k, **v} for k, v in VERIFICATION_TYPES.items()]


@router.get("/verifications/{verification_id}")
async def get_verification(
    verification_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    doc = await db.trust_verifications.find_one({"_id": _safe_oid(verification_id)})
    if not doc:
        raise HTTPException(404, "Verification not found.")
    is_admin = zt_is_admin(user)
    if not is_admin and doc["user_id"] != uid:
        raise HTTPException(403, "Access denied.")
    return _ser(doc)


@router.post("/verifications/run")
async def run_auto_verification(
    body: SubmitVerificationRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Run automated AI verification for a given type.
    Creates or updates a trust_verifications record.
    """
    db = make_db_proxy(db, user)
    from services.trust.verification_engine import run_ai_validation, VERIFICATION_TYPES
    uid = _uid(user)
    vtype = body.verification_type

    if vtype not in VERIFICATION_TYPES:
        raise HTTPException(400, f"Unknown verification type: {vtype}")

    result = await run_ai_validation(vtype, uid, body.payload, db)
    now = datetime.now(timezone.utc)

    conf = result["confidence"]
    auto_status = "verified" if conf >= 70 else ("pending" if conf >= 30 else "failed")

    doc = {
        "user_id":           uid,
        "verification_type": vtype,
        "label":             VERIFICATION_TYPES[vtype]["label"],
        "status":            auto_status,
        "confidence":        conf,
        "source":            result.get("source", "ai"),
        "notes":             result.get("notes", ""),
        "payload":           body.payload,
        "evidence_urls":     body.evidence_urls,
        "extra":             result.get("extra", {}),
        "auto_reviewed":     True,
        "created_at":        now,
        "updated_at":        now,
        "validated_at":      result.get("validated_at"),
    }

    existing = await db.trust_verifications.find_one({"user_id": uid, "verification_type": vtype})
    if existing:
        await db.trust_verifications.update_one(
            {"_id": existing["_id"]},
            {"$set": {**doc, "created_at": existing["created_at"]}},
        )
        doc["_id"] = str(existing["_id"])
    else:
        ins = await db.trust_verifications.insert_one(doc)
        doc["_id"] = str(ins.inserted_id)

    await _audit(uid, "verification_run", {"type": vtype, "status": auto_status, "confidence": conf}, db)
    return _ser(doc)


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION REQUESTS (submit evidence for manual review)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/requests")
async def submit_verification_request(
    body: SubmitVerificationRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Submit a manual verification request with uploaded evidence."""
    db = make_db_proxy(db, user)
    from services.trust.verification_engine import VERIFICATION_TYPES
    uid = _uid(user)
    vtype = body.verification_type

    if vtype not in VERIFICATION_TYPES:
        raise HTTPException(400, f"Unknown verification type: {vtype}")

    # Try automated first
    from services.trust.verification_engine import run_ai_validation
    result = await run_ai_validation(vtype, uid, body.payload, db)
    conf = result["confidence"]

    now = datetime.now(timezone.utc)
    needs_manual = conf < 70 or body.evidence_urls

    req_doc = {
        "user_id":           uid,
        "verification_type": vtype,
        "label":             VERIFICATION_TYPES[vtype]["label"],
        "status":            "pending_review" if needs_manual else "auto_approved",
        "ai_confidence":     conf,
        "ai_source":         result.get("source"),
        "ai_notes":          result.get("notes"),
        "payload":           body.payload,
        "evidence_urls":     body.evidence_urls,
        "user_notes":        body.notes,
        "submitted_at":      now,
        "updated_at":        now,
    }
    ins = await db.trust_requests.insert_one(req_doc)
    req_doc["_id"] = str(ins.inserted_id)

    if not needs_manual:
        # Auto-approve
        await _upsert_verification(uid, vtype, conf, "ai", result.get("notes", ""), {}, db)

    await _audit(uid, "request_submitted", {"type": vtype, "request_id": req_doc["_id"]}, db)
    return _ser(req_doc)


@router.get("/requests")
async def list_my_requests(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    docs = await db.trust_requests.find({"user_id": uid}).sort("submitted_at", -1).to_list(length=100)
    return [_ser(d) for d in docs]


@router.get("/requests/pending")
async def list_pending_requests(
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: list all pending verification requests."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    docs = await db.trust_requests.find({"status": "pending_review"}).sort("submitted_at", 1).to_list(length=limit)
    return [_ser(d) for d in docs]


@router.post("/requests/{request_id}/review")
async def admin_review_request(
    request_id: str,
    body: AdminReviewRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: approve, reject or request more info for a verification request."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    req = await db.trust_requests.find_one({"_id": _safe_oid(request_id)})
    if not req:
        raise HTTPException(404, "Request not found.")

    now = datetime.now(timezone.utc)
    action = body.action
    if action not in ("approve", "reject", "request_more_info"):
        raise HTTPException(400, "Invalid action.")

    new_status = {
        "approve": "approved",
        "reject": "rejected",
        "request_more_info": "more_info_needed",
    }[action]

    await db.trust_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {
            "status": new_status,
            "admin_notes": body.notes,
            "reviewed_by": _uid(user),
            "reviewed_at": now,
            "updated_at": now,
        }},
    )

    if action == "approve":
        conf = body.confidence_override or req.get("ai_confidence", 80)
        await _upsert_verification(
            req["user_id"], req["verification_type"],
            conf, "admin_manual", body.notes or "", {}, db,
        )

    await _audit(req["user_id"], f"request_{action}d", {"request_id": request_id, "by": _uid(user)}, db)
    return {"status": new_status, "request_id": request_id}


@router.post("/requests/{request_id}/appeal")
async def appeal_rejection(
    request_id: str,
    notes: str = Body(..., embed=True),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    req = await db.trust_requests.find_one({"_id": _safe_oid(request_id)})
    if not req or req["user_id"] != uid:
        raise HTTPException(404, "Request not found.")
    if req.get("status") != "rejected":
        raise HTTPException(400, "Only rejected requests can be appealed.")

    now = datetime.now(timezone.utc)
    await db.trust_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {"status": "pending_review", "appeal_notes": notes, "appealed_at": now, "updated_at": now}},
    )
    await _audit(uid, "request_appealed", {"request_id": request_id}, db)
    return {"status": "pending_review", "request_id": request_id}


# ═══════════════════════════════════════════════════════════════════════════════
# ACADEMIC PASSPORT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/passport")
async def get_my_passport(
    refresh: bool = Query(False),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.trust.passport_service import build_passport
    uid = _uid(user)
    if not refresh:
        existing = await db.trust_passports.find_one({"user_id": uid})
        if existing:
            return _ser(existing)
    return await build_passport(uid, db)


@router.post("/passport/refresh")
async def refresh_passport(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.trust.passport_service import build_passport
    return await build_passport(_uid(user), db)


@router.patch("/passport/visibility")
async def set_passport_visibility(
    body: PassportVisibilityRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    await db.trust_passports.update_one(
        {"user_id": uid},
        {"$set": {"is_public": body.is_public, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"is_public": body.is_public}


@router.get("/passport/public/{token}")
async def get_public_passport(
    token: str,
    db=Depends(get_db),
):
    """Public endpoint — no auth. Returns a passport if is_public=True."""
    db = make_db_proxy(db, system=True)
    from services.trust.passport_service import get_passport_by_token
    doc = await get_passport_by_token(token, db)
    if not doc:
        raise HTTPException(404, "Passport not found.")
    if not doc.get("is_public", False):
        raise HTTPException(403, "This passport is private.")
    private_fields = {"user_id", "share_token"}
    return {k: v for k, v in doc.items() if k not in private_fields}


# ═══════════════════════════════════════════════════════════════════════════════
# BADGES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/badges")
async def get_my_badges(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.trust.badge_system import get_user_badges, evaluate_badges
    uid = _uid(user)
    await evaluate_badges(uid, db)
    return await get_user_badges(uid, db)


@router.get("/badges/catalogue")
async def get_badge_catalogue(user=Depends(get_current_user)):
    from services.trust.badge_system import BADGE_CATALOGUE
    return [{"id": k, **v} for k, v in BADGE_CATALOGUE.items()]


@router.get("/badges/{user_id}")
async def get_badges_for_user(
    user_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Public-facing — returns badges for any user's profile."""
    db = make_db_proxy(db, user)
    from services.trust.badge_system import get_user_badges
    return await get_user_badges(user_id, db)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRITY REPORT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/integrity")
async def get_integrity_report(
    refresh: bool = Query(False),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    from services.trust.integrity_service import generate_integrity_report, get_cached_integrity_report
    uid = _uid(user)
    if not refresh:
        cached = await get_cached_integrity_report(uid, db)
        if cached:
            return cached
    return await generate_integrity_report(uid, db)


@router.get("/integrity/{user_id}")
async def get_integrity_report_for_user(
    user_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: generate integrity report for any user."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    from services.trust.integrity_service import generate_integrity_report
    return await generate_integrity_report(user_id, db)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/audit")
async def get_audit_history(
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    docs = await db.trust_audit.find({"user_id": uid}).sort("created_at", -1).to_list(length=limit)
    return [_ser(d) for d in docs]


@router.get("/audit/admin")
async def get_all_audit_history(
    limit: int = Query(100, le=500),
    user_id: Optional[str] = Query(None),
    event: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: full audit log with optional filters."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    query: dict = {}
    if user_id:
        query["user_id"] = user_id
    if event:
        query["event"] = event
    docs = await db.trust_audit.find(query).sort("created_at", -1).to_list(length=limit)
    return [_ser(d) for d in docs]


# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW / DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/overview")
async def get_trust_overview(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Returns aggregated trust overview for the dashboard page."""
    db = make_db_proxy(db, user)
    from services.trust.score_service import get_cached_trust_score, compute_trust_score
    from services.trust.badge_system import get_user_badges, evaluate_badges

    uid = _uid(user)
    score_doc = await get_cached_trust_score(uid, db)
    if not score_doc:
        score_doc = await compute_trust_score(uid, db)

    await evaluate_badges(uid, db)
    badges = await get_user_badges(uid, db)

    verif_total = await db.trust_verifications.count_documents({"user_id": uid})
    verif_verified = await db.trust_verifications.count_documents({"user_id": uid, "status": "verified"})
    req_pending = await db.trust_requests.count_documents({"user_id": uid, "status": "pending_review"})

    recent_audit = await db.trust_audit.find({"user_id": uid}).sort("created_at", -1).to_list(length=5)

    return {
        "trust_score": score_doc.get("score", 0),
        "trust_level": score_doc.get("level", "Unverified"),
        "trust_advice": score_doc.get("level_advice", ""),
        "verifications_total":    verif_total,
        "verifications_verified": verif_verified,
        "requests_pending":       req_pending,
        "badges":                 badges[:6],
        "badge_count":            len(badges),
        "recent_activity":        [_ser(e) for e in recent_audit],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/settings")
async def get_trust_settings(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    doc = await db.trust_passports.find_one({"user_id": uid}) or {}
    return {
        "is_public":                doc.get("is_public", False),
        "notify_verification":      doc.get("notify_verification", True),
        "notify_badge":             doc.get("notify_badge", True),
        "notify_score_change":      doc.get("notify_score_change", True),
        "notify_request_reviewed":  doc.get("notify_request_reviewed", True),
    }


@router.patch("/settings")
async def update_trust_settings(
    body: dict = Body(...),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    allowed = {
        "is_public", "notify_verification", "notify_badge",
        "notify_score_change", "notify_request_reviewed",
    }
    update = {k: v for k, v in body.items() if k in allowed}
    await db.trust_passports.update_one(
        {"user_id": uid},
        {"$set": {**update, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return update


# ═══════════════════════════════════════════════════════════════════════════════
# INSTITUTION / PUBLICATION / REVIEWER / GRANT VERIFICATION SHORTCUTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/verify/institution")
async def verify_institution(
    payload: dict = Body(...),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    body = SubmitVerificationRequest(
        verification_type="institution_affiliation", payload=payload,
        evidence_urls=payload.pop("evidence_urls", []),
    )
    return await submit_verification_request(body, user, db)


@router.post("/verify/publication")
async def verify_publication(
    payload: dict = Body(...),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    body = SubmitVerificationRequest(
        verification_type="doi",
        payload=payload,
        evidence_urls=payload.pop("evidence_urls", []),
    )
    return await run_auto_verification(body, user, db)


@router.post("/verify/reviewer")
async def verify_reviewer(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    body = SubmitVerificationRequest(verification_type="reviewer_activity", payload={})
    return await run_auto_verification(body, user, db)


@router.post("/verify/grant")
async def verify_grant(
    payload: dict = Body(...),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    body = SubmitVerificationRequest(
        verification_type="grant_participation", payload=payload,
        evidence_urls=payload.pop("evidence_urls", []),
    )
    return await submit_verification_request(body, user, db)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN CENTER
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/stats")
async def admin_trust_stats(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    total_users   = await db.users.count_documents({})
    v_total       = await db.trust_verifications.count_documents({})
    v_verified    = await db.trust_verifications.count_documents({"status": "verified"})
    req_pending   = await db.trust_requests.count_documents({"status": "pending_review"})
    req_total     = await db.trust_requests.count_documents({})
    badge_total   = await db.trust_badges.count_documents({"status": "active"})
    passport_total= await db.trust_passports.count_documents({})
    audit_total   = await db.trust_audit.count_documents({})

    return {
        "total_users":         total_users,
        "verifications_total": v_total,
        "verifications_verified": v_verified,
        "verification_rate":   round(v_verified / v_total * 100, 1) if v_total else 0,
        "requests_pending":    req_pending,
        "requests_total":      req_total,
        "badges_awarded":      badge_total,
        "passports_generated": passport_total,
        "audit_events":        audit_total,
    }


@router.get("/admin/users")
async def admin_list_users_trust(
    limit: int = Query(50, le=200),
    skip: int = Query(0),
    search: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: list users with their trust scores."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    query: dict = {}
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
        ]
    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    result = []
    for u in users:
        uid = str(u["_id"])
        score_doc = await db.trust_scores.find_one({"user_id": uid})
        result.append({
            "user_id":    uid,
            "email":      u.get("email"),
            "full_name":  u.get("full_name"),
            "trust_score":  (score_doc or {}).get("score", 0),
            "trust_level":  (score_doc or {}).get("level", "Unverified"),
        })
    return result


@router.post("/admin/flag")
async def admin_flag_integrity(
    body: FlagIntegrityRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: raise an integrity flag for a user."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    now = datetime.now(timezone.utc)
    await db.trust_audit.insert_one({
        "user_id":    body.target_user_id,
        "event":      "fraud_flag",
        "details":    body.details,
        "raised_by":  _uid(user),
        "created_at": now,
    })
    # Invalidate cached score
    await db.trust_scores.update_one(
        {"user_id": body.target_user_id},
        {"$set": {"integrity_updated_at": None}},
    )
    return {"flagged": True, "target": body.target_user_id}


@router.delete("/admin/flag/{user_id}")
async def admin_remove_integrity_flag(
    user_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: remove the most recent fraud flag for a user."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    res = await db.trust_audit.delete_one({"user_id": user_id, "event": "fraud_flag"})
    if res.deleted_count == 0:
        raise HTTPException(404, "No integrity flags found for this user.")
    return {"cleared": True, "user_id": user_id}


@router.post("/admin/override/{user_id}/{verification_type}")
async def admin_override_verification(
    user_id: str,
    verification_type: str,
    body: AdminReviewRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Admin: manually set a verification status."""
    db = make_db_proxy(db, user)
    _require_admin(user)
    from services.trust.verification_engine import VERIFICATION_TYPES
    if verification_type not in VERIFICATION_TYPES:
        raise HTTPException(400, f"Unknown type: {verification_type}")
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be approve or reject")

    status = "verified" if body.action == "approve" else "rejected"
    conf = body.confidence_override or (90 if body.action == "approve" else 0)
    await _upsert_verification(user_id, verification_type, conf, "admin_override", body.notes or "", {}, db)
    await _audit(user_id, "admin_override", {
        "type": verification_type, "status": status, "by": _uid(user)
    }, db)
    return {"status": status, "verification_type": verification_type, "user_id": user_id}


# ═══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _require_admin(user):
    zt_check(user, "admin", "admin")


async def _audit(user_id: str, event: str, data: dict, db) -> None:
    await db.trust_audit.insert_one({
        "user_id":    user_id,
        "event":      event,
        "data":       data,
        "created_at": datetime.now(timezone.utc),
    })


async def _upsert_verification(
    user_id: str,
    v_type: str,
    confidence: int,
    source: str,
    notes: str,
    extra: dict,
    db,
) -> None:
    from services.trust.verification_engine import VERIFICATION_TYPES
    defn = VERIFICATION_TYPES.get(v_type, {})
    now = datetime.now(timezone.utc)
    expiry_days = defn.get("expiry_days", 365)

    doc = {
        "user_id":           user_id,
        "verification_type": v_type,
        "label":             defn.get("label", v_type),
        "status":            "verified" if confidence >= 70 else ("failed" if confidence == 0 else "pending"),
        "confidence":        confidence,
        "source":            source,
        "notes":             notes,
        "extra":             extra,
        "auto_reviewed":     source not in ("admin_manual", "admin_override"),
        "verified_at":       now if confidence >= 70 else None,
        "expires_at":        (now + timedelta(days=expiry_days)) if confidence >= 70 else None,
        "updated_at":        now,
    }
    existing = await db.trust_verifications.find_one({"user_id": user_id, "verification_type": v_type})
    if existing:
        await db.trust_verifications.update_one(
            {"_id": existing["_id"]},
            {"$set": {**doc, "created_at": existing.get("created_at", now)}},
        )
    else:
        doc["created_at"] = now
        await db.trust_verifications.insert_one(doc)
