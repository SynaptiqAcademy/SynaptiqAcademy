"""Institution Hub — Verification Service.

5-level institution verification system backed by real MongoDB collections.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId


# ─── constants ────────────────────────────────────────────────────────────────

VERIFICATION_LEVELS: dict[int, str] = {
    1: "Registered",
    2: "Verified Domain",
    3: "Accredited",
    4: "Research Partner",
    5: "Synaptiq Certified",
}


def _to_str(oid) -> str:
    if oid is None:
        return ""
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


# ─── public functions ─────────────────────────────────────────────────────────

async def get_verification_status(institution_id: str, db) -> dict:
    """Return current verification level and pending requests for an institution."""
    ver_coro = db.institution_verifications.find_one({"institution_id": institution_id})
    req_coro = db.institution_verifications_requests.find(
        {"institution_id": institution_id, "status": "pending"},
        {"_id": 1, "requested_level": 1, "created_at": 1, "evidence_urls": 1},
    ).to_list(50)

    ver_doc, pending_raw = await asyncio.gather(ver_coro, req_coro)

    current_level = int((ver_doc or {}).get("current_level") or 1)
    verified_at = None
    if ver_doc:
        va = ver_doc.get("verified_at")
        if isinstance(va, datetime):
            verified_at = va.isoformat()
        elif isinstance(va, str):
            verified_at = va

    pending_requests = []
    for req in pending_raw:
        requested_level = int(req.get("requested_level") or 0)
        created_at = req.get("created_at")
        pending_requests.append({
            "request_id": _to_str(req.get("_id")),
            "requested_level": requested_level,
            "requested_level_name": VERIFICATION_LEVELS.get(requested_level, "Unknown"),
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or ""),
            "evidence_urls": req.get("evidence_urls") or [],
        })

    return {
        "institution_id": institution_id,
        "current_level": current_level,
        "current_level_name": VERIFICATION_LEVELS.get(current_level, "Registered"),
        "verified_at": verified_at,
        "pending_requests": pending_requests,
    }


async def request_verification(
    institution_id: str,
    user_id: str,
    level: int,
    evidence_urls: list,
    db,
) -> dict:
    """Submit a verification request for an institution."""
    # Check current verification level
    ver_doc = await db.institution_verifications.find_one(
        {"institution_id": institution_id},
        {"current_level": 1},
    )
    current_level = int((ver_doc or {}).get("current_level") or 1)

    if current_level >= level:
        return {
            "request_id": None,
            "status": "already_verified",
            "message": f"Institution is already at level {current_level} ({VERIFICATION_LEVELS.get(current_level, '')}).",
        }

    now = _now()
    doc = {
        "institution_id": institution_id,
        "user_id": user_id,
        "requested_level": level,
        "requested_level_name": VERIFICATION_LEVELS.get(level, "Unknown"),
        "evidence_urls": evidence_urls or [],
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }

    insert_result = await db.institution_verifications_requests.insert_one(doc)
    return {
        "request_id": _to_str(insert_result.inserted_id),
        "status": "pending",
    }


async def process_verification_decision(
    request_id: str,
    decision: str,
    admin_note: str,
    admin_id: str,
    db,
) -> dict:
    """Approve or reject a verification request. Updates collections and logs audit."""
    try:
        req_oid = ObjectId(request_id)
    except Exception:
        return {"success": False, "error": "Invalid request_id"}

    req_doc = await db.institution_verifications_requests.find_one({"_id": req_oid})
    if not req_doc:
        return {"success": False, "error": "Request not found"}

    now = _now()
    await db.institution_verifications_requests.update_one(
        {"_id": req_oid},
        {"$set": {
            "status": decision,
            "admin_note": admin_note,
            "admin_id": admin_id,
            "decided_at": now,
            "updated_at": now,
        }},
    )

    institution_id = req_doc.get("institution_id") or ""
    requested_level = int(req_doc.get("requested_level") or 0)

    if decision == "approved" and requested_level > 0:
        await db.institution_verifications.update_one(
            {"institution_id": institution_id},
            {"$set": {
                "institution_id": institution_id,
                "current_level": requested_level,
                "current_level_name": VERIFICATION_LEVELS.get(requested_level, "Unknown"),
                "verified_at": now,
                "verified_by": admin_id,
                "updated_at": now,
            }},
            upsert=True,
        )

    # Audit log
    audit_doc = {
        "institution_id": institution_id,
        "action": f"verification_{decision}",
        "actor_id": admin_id,
        "details": {
            "request_id": request_id,
            "requested_level": requested_level,
            "decision": decision,
            "admin_note": admin_note,
        },
        "created_at": now,
    }
    await db.institution_audit.insert_one(audit_doc)

    return {
        "success": True,
        "institution_id": institution_id,
        "decision": decision,
        "new_level": requested_level if decision == "approved" else None,
        "new_level_name": VERIFICATION_LEVELS.get(requested_level, "") if decision == "approved" else None,
    }


async def auto_verify_domain(institution_id: str, domain: str, db) -> bool:
    """Auto-verify an institution at Level 2 if domain matches contact email."""
    inst_doc = await db.institutions.find_one(
        {"_id": ObjectId(institution_id) if len(institution_id) == 24 else institution_id},
        {"contact_email": 1, "domain": 1, "email": 1},
    )
    if not inst_doc:
        return False

    # Derive institution domain from contact_email or explicit domain field
    inst_domain: str = ""
    explicit_domain = inst_doc.get("domain") or ""
    if explicit_domain:
        inst_domain = explicit_domain.lower().strip()
    else:
        contact_email = inst_doc.get("contact_email") or inst_doc.get("email") or ""
        if "@" in contact_email:
            inst_domain = contact_email.split("@", 1)[1].lower().strip()

    if not inst_domain:
        return False

    provided_domain = domain.lower().strip().lstrip("@")

    if inst_domain != provided_domain:
        return False

    # Upsert level 2 verification
    now = _now()
    await db.institution_verifications.update_one(
        {"institution_id": institution_id},
        {"$set": {
            "institution_id": institution_id,
            "current_level": 2,
            "current_level_name": VERIFICATION_LEVELS[2],
            "verified_at": now,
            "verified_by": "auto_domain",
            "domain_verified": provided_domain,
            "updated_at": now,
        },
        "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return True
