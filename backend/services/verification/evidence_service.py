"""Evidence Service — handles submission and admin review of verification evidence.

Evidence is submitted by users and reviewed by admins. Approval triggers
a recomputation of the user's verification profile.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId

logger = logging.getLogger("synaptiq.verification.evidence")

EVIDENCE_TYPES: list[str] = [
    "employment_letter",
    "institution_document",
    "certificate",
    "academic_credential",
    "research_contract",
    "grant_document",
    "reviewer_invitation",
    "teaching_document",
    "publication_record",
    "orcid_export",
    "custom",
]


def _serialize(doc: dict) -> dict:
    """Convert ObjectId and datetime fields to str."""
    if not doc:
        return {}
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def submit_evidence(
    user_id: str,
    evidence_type: str,
    description: str,
    db,
) -> dict:
    """Submit a new piece of verification evidence for admin review."""
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(
            f"Invalid evidence_type '{evidence_type}'. "
            f"Must be one of: {', '.join(EVIDENCE_TYPES)}"
        )

    now = datetime.now(timezone.utc)

    evidence_doc = {
        "user_id": user_id,
        "evidence_type": evidence_type,
        "description": description,
        "status": "pending",
        "reviewed_by": None,
        "review_notes": None,
        "reviewed_at": None,
        "created_at": now,
    }
    result = await db.verification_evidence.insert_one(evidence_doc)
    evidence_id = str(result.inserted_id)
    evidence_doc["_id"] = evidence_id

    # Audit log
    audit_doc = {
        "user_id": user_id,
        "action": "evidence_submitted",
        "actor_id": user_id,
        "details": evidence_type,
        "evidence_id": evidence_id,
        "created_at": now,
    }
    await db.verification_audits.insert_one(audit_doc)

    return _serialize(evidence_doc)


async def get_user_evidence(user_id: str, db) -> list:
    """Return all evidence submissions for a user."""
    cursor = db.verification_evidence.find({"user_id": user_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=200)
    return [_serialize(d) for d in docs]


async def admin_review_evidence(
    evidence_id: str,
    decision: str,
    notes: str,
    reviewer_id: str,
    db,
) -> dict:
    """Admin approves or rejects a piece of evidence."""
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")

    now = datetime.now(timezone.utc)

    # Fetch evidence doc first to get user_id
    existing = await db.verification_evidence.find_one(
        {"_id": ObjectId(evidence_id)}
    )
    if not existing:
        raise ValueError(f"Evidence {evidence_id} not found")

    evidence_user_id = existing.get("user_id")

    # Update evidence
    update = {
        "status": decision,
        "reviewed_by": reviewer_id,
        "review_notes": notes,
        "reviewed_at": now,
    }
    await db.verification_evidence.update_one(
        {"_id": ObjectId(evidence_id)},
        {"$set": update},
    )

    # Audit log
    audit_doc = {
        "user_id": evidence_user_id,
        "action": f"evidence_{decision}",
        "actor_id": reviewer_id,
        "details": {
            "evidence_id": evidence_id,
            "decision": decision,
            "notes": notes,
        },
        "created_at": now,
    }
    await db.verification_audits.insert_one(audit_doc)

    # Recompute profile if evidence was approved
    if decision == "approved":
        from services.verification.profile_service import compute_verification_profile
        await compute_verification_profile(evidence_user_id, db)

    updated = await db.verification_evidence.find_one(
        {"_id": ObjectId(evidence_id)}
    )
    return _serialize(updated or {**existing, **update})
