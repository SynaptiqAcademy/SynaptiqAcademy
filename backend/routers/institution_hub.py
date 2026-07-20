"""Institution Hub — Phase XXIV backend router.

Endpoints:
  Public (no auth):
    GET  /api/institution-hub/directory                            — institution directory
    GET  /api/institution-hub/{iid}/public-profile                 — public profile
    GET  /api/institution-hub/leaderboards                         — global leaderboards

  Authenticated:
    GET  /api/institution-hub/{iid}/impact                         — impact score
    GET  /api/institution-hub/{iid}/publications                   — publications
    GET  /api/institution-hub/{iid}/grants                         — grants
    GET  /api/institution-hub/{iid}/research-directory             — researcher directory
    GET  /api/institution-hub/{iid}/leaderboard                    — internal leaderboard
    GET  /api/institution-hub/{iid}/unit-rankings                  — unit rankings
    GET  /api/institution-hub/{iid}/recommendations                — recommendations
    GET  /api/institution-hub/{iid}/timeline                       — activity timeline
    GET  /api/institution-hub/{iid}/collaboration-hub              — collaborations
    GET  /api/institution-hub/{iid}/verification-status            — verification level
    POST /api/institution-hub/{iid}/verify-request                 — submit verification

  Institution Admin Console:
    GET  /api/institution-hub/{iid}/admin/overview                 — admin overview
    GET  /api/institution-hub/{iid}/admin/pending-members          — pending memberships
    POST /api/institution-hub/{iid}/admin/bulk-invite              — bulk invite by email
    GET  /api/institution-hub/{iid}/admin/settings                 — institution settings
    PUT  /api/institution-hub/{iid}/admin/settings                 — update settings
    GET  /api/institution-hub/{iid}/admin/export                   — export data package

  Platform Admin:
    GET  /api/institution-hub/admin/all-institutions               — all institutions with stats
    POST /api/institution-hub/admin/verify/{iid}                   — direct verification
    GET  /api/institution-hub/admin/verification-requests          — pending requests
    POST /api/institution-hub/admin/verification-requests/{rid}/decide — approve/reject
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger("synaptiq.institution_hub")

router = APIRouter(prefix="/api/institution-hub", tags=["institution-hub"])


# ─────────────────────────── helpers ─────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_str(v):
    return str(v) if v is not None else None


def _serialize(doc: dict) -> dict:
    """Recursively convert ObjectId / datetime to JSON-safe types."""
    if not isinstance(doc, dict):
        return doc
    out: dict = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _serialize(v)
        elif isinstance(v, list):
            out[k] = [_serialize(i) if isinstance(i, dict) else (str(i) if isinstance(i, ObjectId) else i) for i in v]
        else:
            out[k] = v
    return out


def _require_platform_admin(user: dict) -> None:
    zt_check(user, "admin", "admin")


async def _require_institution_admin(iid: str, user: dict) -> None:
    """Raise 403 unless user is institution owner/admin or platform admin."""
    if zt_is_admin(user):
        return
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    membership = await db.institution_memberships.find_one({
        "institution_id": iid,
        "user_id": user["id"],
        "role": {"$in": ["owner", "admin"]},
        "status": "active",
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Institution admin access required")


async def _get_institution_or_404(iid: str):
    """Return the institution document or raise 404."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(iid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid institution ID")
    institution = await db.institutions.find_one({"_id": oid})
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


async def _audit_log(iid: str, actor_id: str, action: str, metadata: Optional[dict] = None):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.institution_audit.insert_one({
        "institution_id": iid,
        "actor_id": actor_id,
        "action": action,
        "metadata": metadata or {},
        "created_at": _now(),
    })


# ─────────────────────────── Pydantic models ─────────────────────────────────

class VerifyRequestBody(BaseModel):
    level: int
    evidence_urls: List[str] = []


class BulkInviteBody(BaseModel):
    emails: List[str]
    role: str = "member"


class UpdateSettingsBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None
    contact_email: Optional[str] = None


class PlatformVerifyBody(BaseModel):
    level: int
    note: str = ""


class VerificationDecisionBody(BaseModel):
    decision: str  # "approved" or "rejected"
    note: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS (no auth required)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/directory")
async def list_institutions(
    search: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Public institution directory with basic info and member counts."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    query: dict = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    if country:
        query["country"] = country
    if type:
        query["type"] = type

    skip = (page - 1) * limit
    total = await db.institutions.count_documents(query)
    cursor = db.institutions.find(query, {
        "_id": 1, "name": 1, "country": 1, "type": 1, "logo_url": 1
    }).skip(skip).limit(limit)
    institutions_raw = await cursor.to_list(length=limit)

    results = []
    for inst in institutions_raw:
        iid_str = str(inst["_id"])
        member_count = await db.institution_memberships.count_documents(
            {"institution_id": iid_str, "status": "active"}
        )
        verification_doc = await db.institution_verifications.find_one(
            {"institution_id": iid_str},
            {"verification_level": 1}
        )
        results.append({
            "_id": iid_str,
            "name": inst.get("name"),
            "country": inst.get("country"),
            "type": inst.get("type"),
            "logo_url": inst.get("logo_url"),
            "member_count": member_count,
            "verification_level": verification_doc.get("verification_level", 0) if verification_doc else 0,
        })

    return {"institutions": results, "total": total, "page": page, "limit": limit}


@router.get("/leaderboards")
async def get_leaderboards():
    """Global institution and researcher leaderboards (public)."""
    try:
        from services.institution_hub.leaderboard_engine import (
            get_global_institution_leaderboard,
            get_top_researchers_global,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    institutions, researchers = await asyncio.gather(
        get_global_institution_leaderboard(db),
        get_top_researchers_global(db),
    )
    return {"institutions": institutions, "researchers": researchers}


@router.get("/{iid}/public-profile")
async def get_public_profile(iid: str):
    """Public profile of an institution."""
    institution = await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    member_count = await db.institution_memberships.count_documents(
        {"institution_id": iid, "status": "active"}
    )
    publication_count = await db.publications.count_documents(
        {"institution_id": iid}
    )
    verification_doc = await db.institution_verifications.find_one(
        {"institution_id": iid},
        {"verification_level": 1, "verified_at": 1}
    )

    # Top research areas: aggregate from member users
    member_user_ids_cursor = db.institution_memberships.find(
        {"institution_id": iid, "status": "active"}, {"user_id": 1}
    )
    member_user_ids_raw = await member_user_ids_cursor.to_list(length=500)
    member_user_ids = [m["user_id"] for m in member_user_ids_raw if m.get("user_id")]

    research_areas: list = []
    if member_user_ids:
        pipeline = [
            {"$match": {"_id": {"$in": [ObjectId(uid) for uid in member_user_ids if ObjectId.is_valid(uid)]}}},
            {"$unwind": {"path": "$research_areas", "preserveNullAndEmptyArrays": False}},
            {"$group": {"_id": "$research_areas", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        async for doc in db.users.aggregate(pipeline):
            research_areas.append({"area": doc["_id"], "count": doc["count"]})

    profile = _serialize(institution)
    profile["_id"] = iid
    profile["member_count"] = member_count
    profile["publication_count"] = publication_count
    profile["top_research_areas"] = research_areas
    profile["verification_status"] = _serialize(verification_doc) if verification_doc else None

    return profile


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATED ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{iid}/impact")
async def get_impact(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Institution Impact Score."""
    try:
        from services.institution_hub.impact_engine import get_institution_impact
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await get_institution_impact(iid, db)
    return result


@router.get("/{iid}/publications")
async def get_publications(
    iid: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """Institution publications, stats, and citation trends."""
    try:
        from services.institution_hub.publication_aggregator import (
            get_institution_publications,
            get_institution_publication_stats,
            get_institution_citation_trends,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    publications, stats, citation_trends = await asyncio.gather(
        get_institution_publications(iid, db, page, limit, search),
        get_institution_publication_stats(iid, db),
        get_institution_citation_trends(iid, db),
    )
    return {"publications": publications, "stats": stats, "citation_trends": citation_trends}


@router.get("/{iid}/grants")
async def get_grants(
    iid: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """Institution grants and grant stats."""
    try:
        from services.institution_hub.grant_aggregator import (
            get_institution_grants,
            get_institution_grant_stats,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    grants, stats = await asyncio.gather(
        get_institution_grants(iid, db, page, limit, status),
        get_institution_grant_stats(iid, db),
    )
    return {"grants": grants, "stats": stats}


@router.get("/{iid}/research-directory")
async def get_research_directory(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Researcher directory for institution: top researchers + full member list."""
    try:
        from services.institution_hub.impact_engine import get_top_researchers_in_institution
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    top_researchers_task = get_top_researchers_in_institution(iid, db, limit=100)

    memberships_cursor = db.institution_memberships.find(
        {"institution_id": iid, "status": "active"},
        {"user_id": 1, "role": 1, "joined_at": 1}
    )
    memberships_raw = await memberships_cursor.to_list(length=1000)

    top_researchers, _ = await asyncio.gather(top_researchers_task, asyncio.sleep(0))

    # Enrich members with basic user info
    members = []
    for m in memberships_raw:
        uid = m.get("user_id")
        if uid and ObjectId.is_valid(uid):
            user_doc = await db.users.find_one(
                {"_id": ObjectId(uid)},
                {"name": 1, "email": 1, "avatar_url": 1, "research_areas": 1}
            )
            members.append({
                "user_id": uid,
                "role": m.get("role"),
                "joined_at": m.get("joined_at"),
                "name": user_doc.get("name") if user_doc else None,
                "email": user_doc.get("email") if user_doc else None,
                "avatar_url": user_doc.get("avatar_url") if user_doc else None,
                "research_areas": user_doc.get("research_areas", []) if user_doc else [],
            })

    return {
        "top_researchers": top_researchers,
        "members": members,
        "total_members": len(members),
    }


@router.get("/{iid}/leaderboard")
async def get_internal_leaderboard(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Institution's internal top researchers leaderboard."""
    try:
        from services.institution_hub.impact_engine import get_top_researchers_in_institution
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    top_researchers = await get_top_researchers_in_institution(iid, db, limit=50)
    return {"leaderboard": top_researchers, "institution_id": iid}


@router.get("/{iid}/unit-rankings")
async def get_unit_rankings(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Unit/department rankings within an institution."""
    try:
        from services.institution_hub.leaderboard_engine import get_institution_unit_rankings
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    rankings = await get_institution_unit_rankings(iid, db)
    return {"unit_rankings": rankings, "institution_id": iid}


@router.get("/{iid}/recommendations")
async def get_recommendations(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Recommendations for an institution: collaborators, funding, researchers to recruit."""
    try:
        from services.institution_hub.recommendation_engine import (
            recommend_collaborating_institutions,
            recommend_funding_opportunities,
            recommend_researchers_to_recruit,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    collaborating_institutions, funding_opportunities, researchers_to_recruit = await asyncio.gather(
        recommend_collaborating_institutions(iid, db),
        recommend_funding_opportunities(iid, db),
        recommend_researchers_to_recruit(iid, db),
    )
    return {
        "collaborating_institutions": collaborating_institutions,
        "funding_opportunities": funding_opportunities,
        "researchers_to_recruit": researchers_to_recruit,
    }


@router.get("/{iid}/timeline")
async def get_timeline(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Institution activity timeline — last 50 audit events sorted by created_at desc."""
    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    cursor = db.institution_audit.find(
        {"institution_id": iid}
    ).sort("created_at", -1).limit(50)
    events_raw = await cursor.to_list(length=50)
    events = [_serialize(e) for e in events_raw]
    return {"timeline": events, "total": len(events)}


@router.get("/{iid}/collaboration-hub")
async def get_collaboration_hub(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Active collaborations involving institution members."""
    await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    # Gather member user IDs
    memberships_cursor = db.institution_memberships.find(
        {"institution_id": iid, "status": "active"}, {"user_id": 1}
    )
    memberships_raw = await memberships_cursor.to_list(length=1000)
    member_user_ids = [m["user_id"] for m in memberships_raw if m.get("user_id")]

    if not member_user_ids:
        return {"collaborations": [], "total": 0}

    # Query collaborations where created_by or participant is in member list
    collab_query = {
        "$or": [
            {"created_by": {"$in": member_user_ids}},
            {"participants": {"$in": member_user_ids}},
            {"participant_ids": {"$in": member_user_ids}},
        ]
    }
    cursor = db.collaborations.find(collab_query).sort("created_at", -1).limit(100)
    collabs_raw = await cursor.to_list(length=100)
    collabs = [_serialize(c) for c in collabs_raw]
    return {"collaborations": collabs, "total": len(collabs)}


@router.get("/{iid}/verification-status")
async def get_verification_status_endpoint(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Current verification level for an institution."""
    try:
        from services.institution_hub.verification_service import get_verification_status
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    status = await get_verification_status(iid, db)
    return status


@router.post("/{iid}/verify-request")
async def submit_verification_request(
    iid: str,
    body: VerifyRequestBody,
    user: dict = Depends(get_current_user),
):
    """Submit a verification request for an institution."""
    try:
        from services.institution_hub.verification_service import request_verification
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    await _get_institution_or_404(iid)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await request_verification(iid, user["id"], body.level, body.evidence_urls, db)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  INSTITUTION ADMIN CONSOLE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{iid}/admin/overview")
async def admin_overview(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Admin overview: member stats, publication count, grant count, impact summary."""
    await _require_institution_admin(iid, user)
    await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    member_count, pending_count, publication_count, grant_count = await asyncio.gather(
        db.institution_memberships.count_documents({"institution_id": iid, "status": "active"}),
        db.institution_memberships.count_documents({"institution_id": iid, "status": "pending"}),
        db.publications.count_documents({"institution_id": iid}),
        db.grants.count_documents({"institution_id": iid}),
    )

    # Recent joins (last 5)
    recent_cursor = db.institution_memberships.find(
        {"institution_id": iid, "status": "active"},
        {"user_id": 1, "role": 1, "joined_at": 1}
    ).sort("joined_at", -1).limit(5)
    recent_joins = await recent_cursor.to_list(length=5)

    # Impact score summary
    verification_doc = await db.institution_verifications.find_one(
        {"institution_id": iid}, {"verification_level": 1}
    )
    impact_doc = await db.institution_impact.find_one(
        {"institution_id": iid}, {"impact_score": 1, "computed_at": 1}
    )

    return {
        "institution_id": iid,
        "member_count": member_count,
        "pending_invite_count": pending_count,
        "publication_count": publication_count,
        "grant_count": grant_count,
        "recent_joins": [_serialize(m) for m in recent_joins],
        "verification_level": verification_doc.get("verification_level", 0) if verification_doc else 0,
        "impact_score": impact_doc.get("impact_score") if impact_doc else None,
        "impact_computed_at": impact_doc.get("computed_at") if impact_doc else None,
    }


@router.get("/{iid}/admin/pending-members")
async def admin_pending_members(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Pending membership requests for an institution."""
    await _require_institution_admin(iid, user)
    await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    cursor = db.institution_memberships.find(
        {"institution_id": iid, "status": "pending"}
    ).sort("requested_at", -1)
    pending_raw = await cursor.to_list(length=200)
    pending = [_serialize(m) for m in pending_raw]
    return {"pending_members": pending, "total": len(pending)}


@router.post("/{iid}/admin/bulk-invite")
async def admin_bulk_invite(
    iid: str,
    body: BulkInviteBody,
    user: dict = Depends(get_current_user),
):
    """Bulk invite users by email list."""
    await _require_institution_admin(iid, user)
    await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    invited = 0
    already_members = 0

    for email in body.emails:
        email = email.strip().lower()
        if not email:
            continue

        # Check if already a member via user lookup
        existing_user = await db.users.find_one({"email": email}, {"_id": 1})
        if existing_user:
            uid_str = str(existing_user["_id"])
            existing_membership = await db.institution_memberships.find_one(
                {"institution_id": iid, "user_id": uid_str}
            )
            if existing_membership:
                already_members += 1
                continue

        # Check if already invited
        existing_invite = await db.institution_invites.find_one(
            {"institution_id": iid, "email": email, "status": "pending"}
        )
        if existing_invite:
            already_members += 1
            continue

        # Create invite doc
        await db.institution_invites.insert_one({
            "institution_id": iid,
            "email": email,
            "role": body.role,
            "invited_by": user["id"],
            "status": "pending",
            "created_at": _now(),
        })
        invited += 1

    await _audit_log(iid, user["id"], "bulk_invite", {
        "invited_count": invited,
        "already_members": already_members,
        "role": body.role,
    })

    return {"invited": invited, "already_members": already_members}


@router.get("/{iid}/admin/settings")
async def admin_get_settings(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Institution settings."""
    await _require_institution_admin(iid, user)
    institution = await _get_institution_or_404(iid)
    return _serialize(institution)


@router.put("/{iid}/admin/settings")
async def admin_update_settings(
    iid: str,
    body: UpdateSettingsBody,
    user: dict = Depends(get_current_user),
):
    """Update institution settings."""
    await _require_institution_admin(iid, user)
    await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    update_fields: dict = {}
    if body.name is not None:
        update_fields["name"] = body.name
    if body.description is not None:
        update_fields["description"] = body.description
    if body.website is not None:
        update_fields["website"] = body.website
    if body.country is not None:
        update_fields["country"] = body.country
    if body.type is not None:
        update_fields["type"] = body.type
    if body.contact_email is not None:
        update_fields["contact_email"] = body.contact_email

    if not update_fields:
        raise HTTPException(status_code=400, detail="No updatable fields provided")

    update_fields["updated_at"] = _now()
    await db.institutions.update_one(
        {"_id": ObjectId(iid)},
        {"$set": update_fields}
    )

    await _audit_log(iid, user["id"], "settings_updated", {"fields_changed": list(update_fields.keys())})

    updated = await db.institutions.find_one({"_id": ObjectId(iid)})
    return _serialize(updated)


@router.get("/{iid}/admin/export")
async def admin_export(
    iid: str,
    user: dict = Depends(get_current_user),
):
    """Export institution data package (JSON)."""
    await _require_institution_admin(iid, user)
    institution = await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    member_count, publication_count, grant_count = await asyncio.gather(
        db.institution_memberships.count_documents({"institution_id": iid, "status": "active"}),
        db.publications.count_documents({"institution_id": iid}),
        db.grants.count_documents({"institution_id": iid}),
    )

    impact_doc = await db.institution_impact.find_one(
        {"institution_id": iid}, {"impact_score": 1, "computed_at": 1}
    )

    members_cursor = db.institution_memberships.find(
        {"institution_id": iid, "status": "active"},
        {"user_id": 1, "role": 1, "joined_at": 1, "email": 1}
    )
    members_raw = await members_cursor.to_list(length=5000)

    return {
        "institution": _serialize(institution),
        "exported_at": _now(),
        "member_count": member_count,
        "publication_count": publication_count,
        "grant_count": grant_count,
        "impact_score": impact_doc.get("impact_score") if impact_doc else None,
        "members": [_serialize(m) for m in members_raw],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  PLATFORM ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/all-institutions")
async def platform_admin_all_institutions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """All institutions with member counts, verification levels, and impact scores."""
    _require_platform_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    skip = (page - 1) * limit
    total = await db.institutions.count_documents({})
    cursor = db.institutions.find({}).skip(skip).limit(limit)
    institutions_raw = await cursor.to_list(length=limit)

    results = []
    for inst in institutions_raw:
        iid_str = str(inst["_id"])
        member_count, verification_doc, impact_doc = await asyncio.gather(
            db.institution_memberships.count_documents({"institution_id": iid_str, "status": "active"}),
            db.institution_verifications.find_one(
                {"institution_id": iid_str}, {"verification_level": 1, "verified_at": 1}
            ),
            db.institution_impact.find_one(
                {"institution_id": iid_str}, {"impact_score": 1}
            ),
        )
        serialized = _serialize(inst)
        serialized["member_count"] = member_count
        serialized["verification_level"] = verification_doc.get("verification_level", 0) if verification_doc else 0
        serialized["verified_at"] = verification_doc.get("verified_at") if verification_doc else None
        serialized["impact_score"] = impact_doc.get("impact_score") if impact_doc else None
        results.append(serialized)

    return {"institutions": results, "total": total, "page": page, "limit": limit}


@router.post("/admin/verify/{iid}")
async def platform_admin_verify_institution(
    iid: str,
    body: PlatformVerifyBody,
    user: dict = Depends(get_current_user),
):
    """Platform admin direct verification for an institution."""
    _require_platform_admin(user)
    await _get_institution_or_404(iid)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    now = _now()
    await db.institution_verifications.update_one(
        {"institution_id": iid},
        {"$set": {
            "institution_id": iid,
            "verification_level": body.level,
            "verified_by": user["id"],
            "note": body.note,
            "verified_at": now,
            "updated_at": now,
            "method": "platform_admin_direct",
        }},
        upsert=True,
    )

    await _audit_log(iid, user["id"], "platform_admin_verified", {
        "level": body.level,
        "note": body.note,
    })

    return {
        "institution_id": iid,
        "verification_level": body.level,
        "verified_by": user["id"],
        "verified_at": now,
    }


@router.get("/admin/verification-requests")
async def platform_admin_verification_requests(
    user: dict = Depends(get_current_user),
):
    """All pending verification requests with institution names."""
    _require_platform_admin(user)
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    cursor = db.institution_verifications_requests.find(
        {"status": "pending"}
    ).sort("created_at", -1)
    requests_raw = await cursor.to_list(length=200)

    results = []
    for req in requests_raw:
        iid_str = req.get("institution_id", "")
        inst_name = None
        if iid_str and ObjectId.is_valid(iid_str):
            inst_doc = await db.institutions.find_one(
                {"_id": ObjectId(iid_str)}, {"name": 1}
            )
            if inst_doc:
                inst_name = inst_doc.get("name")
        serialized = _serialize(req)
        serialized["institution_name"] = inst_name
        results.append(serialized)

    return {"verification_requests": results, "total": len(results)}


@router.post("/admin/verification-requests/{request_id}/decide")
async def platform_admin_decide_verification(
    request_id: str,
    body: VerificationDecisionBody,
    user: dict = Depends(get_current_user),
):
    """Approve or reject a verification request."""
    _require_platform_admin(user)

    if body.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")

    try:
        from services.institution_hub.verification_service import process_verification_decision
    except ImportError:
        raise HTTPException(status_code=503, detail="Institution Hub services not available")

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await process_verification_decision(request_id, body.decision, body.note, user["id"], db)
    return result
