"""Grant Collaboration Hub — Phase XXV router.

Collections used:
  grant_collaborations              — collaboration workspaces
  grant_collab_team_members         — team members per collaboration
  grant_collab_positions            — open positions per collaboration
  grant_team_invitations            — invitations sent/received
  grant_consortiums                 — consortium per collaboration
  grant_collab_work_packages        — work packages per collaboration
  grant_collab_proposal_sections    — proposal sections per collaboration

Prefix: /api/grant-hub
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from auth_utils import get_current_user
from db import get_db
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin
from repo.shim import make_db_proxy

logger = logging.getLogger("synaptiq")
router = APIRouter(prefix="/api/grant-hub", tags=["grant-hub"])


def _s(v):
    return str(v) if v is not None else None


# ── Pydantic Models ─────────────────────────────────────────────────────────────

class CreateCollaborationBody(BaseModel):
    title: str
    description: str = ""
    grant_id: Optional[str] = None
    research_areas: List[str] = []
    countries_required: List[str] = []
    funding_source: str = ""
    deadline: Optional[str] = None
    budget_total: float = 0.0
    visibility: str = "public"
    lead_institution_id: Optional[str] = None


class UpdateCollaborationBody(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    research_areas: Optional[List[str]] = None
    countries_required: Optional[List[str]] = None
    funding_source: Optional[str] = None
    deadline: Optional[str] = None
    budget_total: Optional[float] = None
    status: Optional[str] = None
    visibility: Optional[str] = None


class CreatePositionBody(BaseModel):
    role_title: str
    description: str = ""
    required_expertise: List[str] = []
    required_publications: int = 0
    required_experience_years: int = 0
    availability_required: str = ""
    contribution: str = ""


class SendInvitationBody(BaseModel):
    to_user_id: str
    role: str
    message: str = ""
    position_id: Optional[str] = None


class InvitationResponseBody(BaseModel):
    response: str  # "accepted" or "rejected"


class AddPartnerBody(BaseModel):
    institution_id: str
    role: str = "partner"
    budget_share: float = 0.0


class CreateWorkPackageBody(BaseModel):
    title: str
    description: str = ""
    lead_user_id: Optional[str] = None
    budget: float = 0.0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    deliverables: List[str] = []


class AddTaskBody(BaseModel):
    title: str
    assignee_user_id: Optional[str] = None
    due_date: Optional[str] = None


class CreateProposalSectionBody(BaseModel):
    section_title: str
    content: str = ""
    assigned_to_user_id: Optional[str] = None


class UpdateProposalSectionBody(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None
    assigned_to_user_id: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_doc(doc: dict) -> dict:
    """Convert ObjectId fields to strings in a MongoDB document."""
    if doc is None:
        return {}
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, list):
            result[k] = [str(i) if isinstance(i, ObjectId) else i for i in v]
        elif isinstance(v, dict):
            result[k] = _serialize_doc(v)
        else:
            result[k] = v
    return result


# ══════════════════════════════════════════════════════════════════════════════
# STATIC / FIXED-PATH ROUTES  (must come before /{cid})
# ══════════════════════════════════════════════════════════════════════════════

# ── Analytics: /analytics/me ──────────────────────────────────────────────────

@router.get("/analytics/me")
async def my_hub_analytics(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """My hub analytics."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.analytics_service import get_hub_analytics
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await get_hub_analytics(user["id"], db)


# ── Admin: /admin/stats ───────────────────────────────────────────────────────

@router.get("/admin/stats")
async def admin_platform_stats(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Platform grant hub stats (admin only)."""
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    try:
        from services.grant_hub.analytics_service import get_platform_grant_analytics
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await get_platform_grant_analytics(db)


# ── Admin: /admin/collaborations ──────────────────────────────────────────────

@router.get("/admin/collaborations")
async def admin_all_collaborations(
    status: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """All collaborations (admin only)."""
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    query: dict = {}
    if status:
        query["status"] = status
    cursor = db["grant_collaborations"].find(query).sort("created_at", -1)
    docs = []
    async for doc in cursor:
        docs.append(_serialize_doc(doc))
    return {"collaborations": docs, "total": len(docs)}


# ── Invitations: /invitations/my ──────────────────────────────────────────────

@router.get("/invitations/my")
async def my_invitations(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """My received invitations."""
    db = make_db_proxy(db, user)
    cursor = db["grant_team_invitations"].find({"to_user_id": user["id"]}).sort("created_at", -1)
    results = []
    async for inv in cursor:
        inv = _serialize_doc(inv)
        # Enrich with collaboration title
        cid = inv.get("collaboration_id")
        if cid:
            try:
                collab = await db["grant_collaborations"].find_one({"_id": ObjectId(cid)})
                inv["collaboration_title"] = collab.get("title", "") if collab else ""
            except Exception:
                inv["collaboration_title"] = ""
        results.append(inv)
    return {"invitations": results, "total": len(results)}


# ── My collaborations: /my ────────────────────────────────────────────────────

@router.get("/my")
async def my_collaborations(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """My collaborations (auth required)."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.collaboration_service import get_user_collaborations
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await get_user_collaborations(user["id"], db)


# ══════════════════════════════════════════════════════════════════════════════
# COLLABORATION WORKSPACE CRUD  (prefix /)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/")
async def create_grant_collaboration(
    body: CreateCollaborationBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a new collaboration workspace."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.collaboration_service import create_collaboration
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await create_collaboration(user["id"], body.dict(), db)


@router.get("/")
async def list_grant_collaborations(
    status: Optional[str] = Query(None),
    research_area: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    funding_source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """List public collaborations (marketplace)."""
    db = make_db_proxy(db, system=True)
    try:
        from services.grant_hub.collaboration_service import list_collaborations
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    filters: dict = {}
    if status:
        filters["status"] = status
    if research_area:
        filters["research_area"] = research_area
    if country:
        filters["country"] = country
    if funding_source:
        filters["funding_source"] = funding_source
    return await list_collaborations(db, filters, page, limit)


# ══════════════════════════════════════════════════════════════════════════════
# COLLABORATION DETAIL & MANAGEMENT  (prefix /{cid})
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{cid}")
async def get_grant_collaboration(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Collaboration detail."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.collaboration_service import (
            get_collaboration,
            get_collaboration_stats,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    try:
        collab = await get_collaboration(cid, db)
    except KeyError:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    stats = await get_collaboration_stats(cid, db)
    return {**collab, "stats": stats}


@router.patch("/{cid}")
async def update_grant_collaboration(
    cid: str,
    body: UpdateCollaborationBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update collaboration (lead only)."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.collaboration_service import (
            get_collaboration,
            update_collaboration,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    try:
        collab = await get_collaboration(cid, db)
    except KeyError:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    if collab.get("lead_user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the lead can update this collaboration")
    return await update_collaboration(cid, user["id"], body.dict(exclude_none=True), db)


@router.delete("/{cid}")
async def delete_grant_collaboration(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Close/delete collaboration (lead only)."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.collaboration_service import (
            get_collaboration,
            update_collaboration,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    try:
        collab = await get_collaboration(cid, db)
    except KeyError:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    if collab.get("lead_user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the lead can close this collaboration")
    return await update_collaboration(cid, user["id"], {"status": "closed"}, db)


# ══════════════════════════════════════════════════════════════════════════════
# TEAM FORMATION
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{cid}/team")
async def get_team_members(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get team members for a collaboration."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.team_service import get_team_members
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await get_team_members(cid, db)


@router.get("/{cid}/positions")
async def list_positions(
    cid: str,
    status: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """List open positions for a collaboration."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.team_service import list_positions
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await list_positions(cid, db)


@router.post("/{cid}/positions")
async def create_position(
    cid: str,
    body: CreatePositionBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a position in a collaboration (lead or team member)."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.team_service import create_position
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await create_position(cid, user["id"], body.dict(), db)


@router.patch("/{cid}/positions/{pid}")
async def update_position(
    cid: str,
    pid: str,
    body: CreatePositionBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update a position."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.team_service import update_position
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await update_position(pid, user["id"], body.dict(exclude_none=True), db)


@router.post("/{cid}/invite")
async def send_invitation(
    cid: str,
    body: SendInvitationBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Send an invitation to join a collaboration."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.team_service import send_invitation
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    try:
        return await send_invitation(
            cid,
            user["id"],
            body.to_user_id,
            body.role,
            body.message,
            body.position_id or "",
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invitations/{inv_id}/respond")
async def respond_invitation(
    inv_id: str,
    body: InvitationResponseBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Accept or reject an invitation."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.team_service import respond_to_invitation
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await respond_to_invitation(inv_id, user["id"], body.response, db)


@router.delete("/{cid}/team/{uid}")
async def remove_team_member(
    cid: str,
    uid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Remove a team member (lead or self-removal)."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.team_service import remove_team_member
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await remove_team_member(cid, user["id"], uid, db)


# ══════════════════════════════════════════════════════════════════════════════
# CONSORTIUM
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{cid}/consortium")
async def get_consortium(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get or create consortium for a collaboration."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.consortium_service import get_or_create_consortium
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await get_or_create_consortium(cid, user["id"], "", db)


@router.post("/{cid}/consortium/partners")
async def add_partner(
    cid: str,
    body: AddPartnerBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Add a partner institution to the consortium."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.consortium_service import add_partner_institution
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await add_partner_institution(
        cid, user["id"], body.institution_id, body.role, body.budget_share, db
    )


@router.patch("/{cid}/consortium/partners/{iid}")
async def update_partner(
    cid: str,
    iid: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update a partner institution."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.consortium_service import update_partner
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await update_partner(cid, iid, body, db)


@router.delete("/{cid}/consortium/partners/{iid}")
async def remove_partner(
    cid: str,
    iid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Remove a partner institution from the consortium."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.consortium_service import remove_partner
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await remove_partner(cid, iid, user["id"], db)


@router.get("/{cid}/consortium/validate")
async def validate_consortium(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Validate consortium eligibility."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.consortium_service import validate_consortium_eligibility
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await validate_consortium_eligibility(cid, db)


# ══════════════════════════════════════════════════════════════════════════════
# WORK PACKAGES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{cid}/work-packages")
async def list_work_packages(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """List work packages for a collaboration."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.workpackage_service import list_work_packages
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await list_work_packages(cid, db)


@router.post("/{cid}/work-packages")
async def create_work_package(
    cid: str,
    body: CreateWorkPackageBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a work package."""
    db = make_db_proxy(db, user)
    try:
        from services.grant_hub.workpackage_service import create_work_package
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await create_work_package(cid, user["id"], body.dict(), db)


@router.patch("/{cid}/work-packages/{wid}")
async def update_work_package(
    cid: str,
    wid: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Update a work package."""
    try:
        from services.grant_hub.workpackage_service import update_work_package
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await update_work_package(wid, user["id"], body, db)


@router.post("/{cid}/work-packages/{wid}/tasks")
async def add_task(
    cid: str,
    wid: str,
    body: AddTaskBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Add a task to a work package."""
    try:
        from services.grant_hub.workpackage_service import add_task_to_wp
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await add_task_to_wp(wid, user["id"], body.dict(), db)


# ══════════════════════════════════════════════════════════════════════════════
# PARTNER MATCHING
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{cid}/matches")
async def get_matches(
    cid: str,
    force_refresh: bool = Query(False),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Get partner matches for a collaboration."""
    try:
        from services.grant_hub.matching_service import (
            compute_partner_matches,
            get_partner_matches,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    if force_refresh:
        return await compute_partner_matches(cid, db, force_refresh)
    matches = await get_partner_matches(cid, db)
    if not matches:
        return await compute_partner_matches(cid, db, False)
    return matches


@router.post("/{cid}/matches/refresh")
async def refresh_matches(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Force recompute partner matches."""
    try:
        from services.grant_hub.matching_service import compute_partner_matches
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await compute_partner_matches(cid, db, force_refresh=True)


# ══════════════════════════════════════════════════════════════════════════════
# GAP DETECTION & READINESS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{cid}/gaps")
async def get_gaps(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Get expertise gap analysis (cached 2hr)."""
    try:
        from services.grant_hub.gap_service import get_gap_analysis
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await get_gap_analysis(cid, db)


@router.post("/{cid}/gaps/refresh")
async def refresh_gaps(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Refresh gap analysis (force recompute)."""
    try:
        from services.grant_hub.gap_service import analyze_expertise_gaps
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await analyze_expertise_gaps(cid, db)


@router.get("/{cid}/readiness")
async def get_readiness(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Funding readiness score."""
    try:
        from services.grant_hub.gap_service import compute_readiness
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await compute_readiness(cid, db)


# ══════════════════════════════════════════════════════════════════════════════
# PROPOSAL SECTIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{cid}/proposal")
async def list_proposal_sections(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """List proposal sections for a collaboration."""
    cursor = db["grant_collab_proposal_sections"].find(
        {"collaboration_id": cid}
    ).sort("created_at", 1)
    sections = []
    async for doc in cursor:
        sections.append(_serialize_doc(doc))
    return {"sections": sections, "total": len(sections)}


@router.post("/{cid}/proposal")
async def create_proposal_section(
    cid: str,
    body: CreateProposalSectionBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Create a proposal section."""
    now = _now()
    doc = {
        "collaboration_id": cid,
        "section_title": body.section_title,
        "content": body.content,
        "assigned_to_user_id": body.assigned_to_user_id,
        "status": "draft",
        "version": 1,
        "history": [],
        "created_at": now,
        "updated_at": now,
    }
    result = await db["grant_collab_proposal_sections"].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return _serialize_doc(doc)


@router.patch("/{cid}/proposal/{sid}")
async def update_proposal_section(
    cid: str,
    sid: str,
    body: UpdateProposalSectionBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Update a proposal section (increments version on content change)."""
    try:
        existing = await db["grant_collab_proposal_sections"].find_one(
            {"_id": ObjectId(sid), "collaboration_id": cid}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid section ID")
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal section not found")

    updates: dict = {"updated_at": _now()}
    mongo_push: dict = {}

    if body.content is not None:
        # Push old content to history, increment version
        mongo_push["history"] = {
            "content": existing.get("content", ""),
            "version": existing.get("version", 1),
            "updated_at": existing.get("updated_at"),
        }
        updates["content"] = body.content
        updates["version"] = existing.get("version", 1) + 1

    if body.status is not None:
        updates["status"] = body.status

    if body.assigned_to_user_id is not None:
        updates["assigned_to_user_id"] = body.assigned_to_user_id

    mongo_op: dict = {"$set": updates}
    if mongo_push:
        mongo_op["$push"] = mongo_push

    await db["grant_collab_proposal_sections"].update_one(
        {"_id": ObjectId(sid)}, mongo_op
    )
    updated = await db["grant_collab_proposal_sections"].find_one({"_id": ObjectId(sid)})
    return _serialize_doc(updated)


@router.delete("/{cid}/proposal/{sid}")
async def delete_proposal_section(
    cid: str,
    sid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Delete a proposal section."""
    try:
        result = await db["grant_collab_proposal_sections"].delete_one(
            {"_id": ObjectId(sid), "collaboration_id": cid}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid section ID")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposal section not found")
    return {"deleted": True, "id": sid}


# ══════════════════════════════════════════════════════════════════════════════
# COLLABORATION ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{cid}/analytics")
async def collaboration_analytics(
    cid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    """Collaboration analytics."""
    try:
        from services.grant_hub.analytics_service import get_collaboration_analytics
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant Hub services not available")
    return await get_collaboration_analytics(cid, db)
