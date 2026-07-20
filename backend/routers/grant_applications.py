"""Grant Applications — complete lifecycle router.

Collections used (all new):
  grant_applications         — one per researcher × grant opportunity
  grant_team_members         — members per application
  grant_budget_items         — budget line-items per application
  grant_deliverables         — milestones / deliverables per application
  grant_proposal_versions    — proposal snapshots

Endpoints:
  GET    /api/grant-applications                     — list user's applications
  POST   /api/grant-applications                     — start an application
  GET    /api/grant-applications/analytics           — funding analytics
  GET    /api/grant-applications/{id}                — detail + enrichment
  PATCH  /api/grant-applications/{id}                — update
  DELETE /api/grant-applications/{id}                — delete (PI only)
  GET    /api/grant-applications/{id}/dashboard      — progress + checklist
  GET    /api/grant-applications/{id}/team           — list team members
  POST   /api/grant-applications/{id}/team           — invite team member
  PATCH  /api/grant-applications/{id}/team/{uid}     — update member role
  DELETE /api/grant-applications/{id}/team/{uid}     — remove member
  GET    /api/grant-applications/{id}/budget         — list budget items
  POST   /api/grant-applications/{id}/budget         — add budget item
  PATCH  /api/grant-applications/{id}/budget/{bid}   — update budget item
  DELETE /api/grant-applications/{id}/budget/{bid}   — delete budget item
  GET    /api/grant-applications/{id}/deliverables   — list deliverables
  POST   /api/grant-applications/{id}/deliverables   — add deliverable
  PATCH  /api/grant-applications/{id}/deliverables/{did} — update deliverable
  DELETE /api/grant-applications/{id}/deliverables/{did} — delete deliverable
  GET    /api/grant-applications/{id}/versions       — proposal version history
  POST   /api/grant-applications/{id}/versions       — snapshot proposal
  POST   /api/grant-applications/{id}/versions/{v}/restore — restore version

  GET    /api/grants/matches                         — AI-powered grant matching
  GET    /api/grants/{id}/applications               — list applications for a grant (admin/PI)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.grant_applications")
router = APIRouter(prefix="/api/grant-applications", tags=["grant-applications"])

def _emit_rep(user_id, event_type, entity_id, description=None):
    async def _task():
        try:
            from services.reputation.events import emit_reputation_event
            await emit_reputation_event(user_id, event_type, "grant_application", entity_id, description)
        except Exception:
            pass
    try:
        asyncio.ensure_future(_task())
    except RuntimeError:
        pass

# ── constants ──────────────────────────────────────────────────────────────────

APPLICATION_STATUSES = [
    "draft", "in_preparation", "internal_review", "ready_for_submission",
    "submitted", "eligible", "under_evaluation", "funded",
    "rejected", "closed", "withdrawn",
]

TEAM_ROLES = [
    "Principal Investigator", "Co-Investigator", "Work Package Lead",
    "Researcher", "Statistician", "Advisor", "Industry Partner",
    "Postdoctoral Researcher", "PhD Student", "Research Engineer",
]

BUDGET_CATEGORIES = [
    "Personnel", "Equipment", "Travel", "Software", "Consumables",
    "Dissemination", "Overheads", "Subcontracting", "Other",
]

DELIVERABLE_TYPES = [
    "Milestone", "Report", "Publication", "Dataset", "Software",
    "Patent", "Workshop", "Deliverable", "Other",
]

PROPOSAL_SECTIONS = {
    "executive_summary": "",
    "introduction":      "",
    "objectives":        "",
    "methodology":       "",
    "work_plan":         "",
    "team_expertise":    "",
    "budget_justification": "",
    "impact":            "",
    "dissemination":     "",
    "ethics":            "",
    "references":        "",
}

# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d: dict) -> dict:
    if not d:
        return {}
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


def _assert_member(doc: dict, user_id: str) -> None:
    members = [m["user_id"] for m in (doc.get("team_members") or [])]
    if doc.get("pi_id") != user_id and user_id not in members:
        raise HTTPException(403, "Only application team members can do this")


def _assert_pi(doc: dict, user_id: str) -> None:
    if doc.get("pi_id") != user_id:
        raise HTTPException(403, "Only the Principal Investigator can do this")


async def _notify(user_id: str, kind: str, title: str, body: str,
                  link: str, actor_id: str, payload: dict = None) -> None:
    try:
        from services.notifications_service import dispatch as _d, NotificationEvent as _NE
        await _d(_NE(user_id=user_id, kind=kind, title=title, body=body,
                     link=link, actor_id=actor_id, payload=payload or {}))
    except Exception:
        pass


async def _enrich_application(doc: dict, db) -> dict:
    app = _ser(doc)
    app_id = app["id"]

    grant, pi_user, team_raw = await asyncio.gather(
        db.grants.find_one({"_id": ObjectId(app["grant_id"])}) if ObjectId.is_valid(app.get("grant_id", "")) else asyncio.sleep(0),
        db.users.find_one({"_id": ObjectId(app["pi_id"])}, {"full_name": 1, "institution": 1, "avatar_url": 1}) if ObjectId.is_valid(app.get("pi_id", "")) else asyncio.sleep(0),
        db.grant_team_members.find({"application_id": app_id}).to_list(30),
    )

    if grant and not isinstance(grant, type(None)):
        app["grant"] = {
            "id": str(grant["_id"]),
            "title": grant.get("title", ""),
            "agency": grant.get("agency") or grant.get("sponsor", ""),
            "deadline": grant.get("deadline"),
            "funding_amount": grant.get("funding_amount"),
        }

    if pi_user and not isinstance(pi_user, type(None)):
        app["pi"] = {
            "id": str(pi_user["_id"]), "full_name": pi_user.get("full_name", ""),
            "institution": pi_user.get("institution", ""), "avatar_url": pi_user.get("avatar_url"),
        }

    # Enrich team members
    member_user_ids = [ObjectId(m["user_id"]) for m in team_raw if ObjectId.is_valid(m.get("user_id", ""))]
    member_users = await db.users.find({"_id": {"$in": member_user_ids}},
                                       {"full_name": 1, "institution": 1, "avatar_url": 1, "department": 1}).to_list(30)
    umap = {str(u["_id"]): u for u in member_users}
    app["team"] = []
    for m in team_raw:
        entry = _ser(m)
        u = umap.get(m.get("user_id", ""))
        if u:
            entry["user"] = {
                "id": str(u["_id"]), "full_name": u.get("full_name", ""),
                "institution": u.get("institution", ""), "avatar_url": u.get("avatar_url"),
                "department": u.get("department", ""),
            }
        app["team"].append(entry)

    return app


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS — before /{id} to prevent path conflict
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics")
async def grant_analytics(user: dict = Depends(get_current_user)):
    """Funding analytics: success rate, funding won, active grants, trends."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    apps = await db.grant_applications.find({"pi_id": uid}).to_list(500)
    team_apps_raw = await db.grant_team_members.find({"user_id": uid}).to_list(200)
    team_app_ids = [ObjectId(m["application_id"]) for m in team_apps_raw if ObjectId.is_valid(m.get("application_id", ""))]
    team_apps = await db.grant_applications.find({"_id": {"$in": team_app_ids}}).to_list(200)
    all_apps = {str(a["_id"]): a for a in apps + team_apps}

    total = len(all_apps)
    by_status: dict = {}
    funding_won: float = 0.0
    currencies: dict = {}
    active_count = 0
    submission_count = 0
    agencies: dict = {}

    for a in all_apps.values():
        st = a.get("status", "draft")
        by_status[st] = by_status.get(st, 0) + 1
        if st == "funded":
            fa = a.get("requested_budget") or 0
            funding_won += float(fa)
        if st in ("submitted", "eligible", "under_evaluation", "funded"):
            submission_count += 1
        if st in ("in_preparation", "internal_review", "ready_for_submission",
                  "submitted", "eligible", "under_evaluation"):
            active_count += 1
        agency = a.get("agency_name") or a.get("grant_title", "Unknown")[:40]
        agencies[agency] = agencies.get(agency, 0) + 1

    funded = by_status.get("funded", 0)
    rejected = by_status.get("rejected", 0)
    closed = by_status.get("closed", 0)
    evaluated = funded + rejected + closed
    success_rate = round(funded / evaluated * 100, 1) if evaluated else None

    # Monthly submission trend (last 12 months)
    from datetime import timedelta
    trend = {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    for a in all_apps.values():
        st_hist = a.get("status_history") or []
        for h in st_hist:
            if h.get("status") == "submitted" and h.get("at", "") > cutoff.isoformat():
                month = h["at"][:7]
                trend[month] = trend.get(month, 0) + 1

    return {
        "total_applications": total,
        "active_applications": active_count,
        "submission_count":   submission_count,
        "funded":             funded,
        "rejected":           rejected,
        "success_rate":       success_rate,
        "funding_won_eur":    funding_won,
        "by_status":          by_status,
        "monthly_submissions": [{"month": k, "count": v} for k, v in sorted(trend.items())],
        "top_agencies":       sorted([{"agency": k, "count": v} for k, v in agencies.items()], key=lambda x: -x["count"])[:10],
    }


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("")
async def list_applications(
    status: Optional[str] = None,
    grant_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List all grant applications where user is PI or team member."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    # PI applications
    q: dict = {"pi_id": uid}
    if status:
        q["status"] = status
    if grant_id:
        q["grant_id"] = grant_id

    pi_apps = await db.grant_applications.find(q).sort("updated_at", -1).to_list(200)

    # Team member applications
    team_entries = await db.grant_team_members.find({"user_id": uid}).to_list(200)
    team_ids = [ObjectId(m["application_id"]) for m in team_entries if ObjectId.is_valid(m.get("application_id", ""))]
    team_apps = await db.grant_applications.find(
        {"_id": {"$in": team_ids}, "pi_id": {"$ne": uid}}
    ).sort("updated_at", -1).to_list(200) if team_ids else []

    # Enrich with grant info
    all_apps = pi_apps + team_apps
    grant_ids = list({a["grant_id"] for a in all_apps if a.get("grant_id") and ObjectId.is_valid(a["grant_id"])})
    g_oids = [ObjectId(g) for g in grant_ids]
    grants_raw = await db.grants.find({"_id": {"$in": g_oids}},
                                      {"title": 1, "sponsor": 1, "agency": 1, "deadline": 1, "funding_amount": 1}).to_list(len(g_oids)) if g_oids else []
    g_map = {str(g["_id"]): g for g in grants_raw}

    out = []
    for a in all_apps:
        item = _ser(a)
        gid = item.get("grant_id", "")
        if gid in g_map:
            g = g_map[gid]
            item["grant"] = {
                "id": str(g["_id"]),
                "title": g.get("title", ""),
                "agency": g.get("agency") or g.get("sponsor", ""),
                "deadline": g.get("deadline"),
                "funding_amount": g.get("funding_amount"),
            }
        item["is_pi"] = a.get("pi_id") == uid
        out.append(item)
    return out


@router.post("", status_code=201)
async def create_application(body: dict, user: dict = Depends(get_current_user)):
    """Start a grant application. grant_id is required; optionally provide consortium_name."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    grant_id = body.get("grant_id", "").strip()
    if not grant_id:
        raise HTTPException(400, "grant_id is required")

    # Validate grant exists
    try:
        grant = await db.grants.find_one({"_id": ObjectId(grant_id)})
    except Exception:
        raise HTTPException(404, "Grant not found")
    if not grant:
        raise HTTPException(404, "Grant not found")

    # Prevent duplicate pending application
    existing = await db.grant_applications.find_one({
        "grant_id": grant_id, "pi_id": user["id"],
        "status": {"$nin": ["withdrawn", "closed", "rejected"]},
    })
    if existing:
        raise HTTPException(409, "You already have an active application for this grant")

    now = _now()
    doc = {
        "grant_id":          grant_id,
        "grant_title":       grant.get("title", ""),
        "agency_name":       grant.get("agency") or grant.get("sponsor", ""),
        "grant_deadline":    grant.get("deadline"),
        "pi_id":             user["id"],
        "consortium_name":   body.get("consortium_name", ""),
        "institution":       body.get("institution") or user.get("institution", ""),
        "status":            "draft",
        "proposal_sections": dict(PROPOSAL_SECTIONS),
        "current_version":   0,
        "requested_budget":  body.get("requested_budget", 0),
        "currency":          body.get("currency", "EUR"),
        "team_members":      [],
        "status_history":    [{"status": "draft", "at": now, "by": user["id"]}],
        "notes":             "",
        "submission_ref":    "",
        "outcome_notes":     "",
        "created_at":        now,
        "updated_at":        now,
        "last_activity":     now,
    }
    res = await db.grant_applications.insert_one(doc)
    doc["_id"] = res.inserted_id
    app_id_str = str(res.inserted_id)
    return _ser(doc)


@router.get("/{app_id}")
async def get_application(app_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None
    return await _enrich_application(doc, db)


@router.patch("/{app_id}")
async def update_application(app_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    allowed = {
        "consortium_name", "institution", "requested_budget", "currency",
        "notes", "submission_ref", "outcome_notes", "proposal_sections",
    }
    update: dict = {k: v for k, v in body.items() if k in allowed}

    if "status" in body:
        new_status = body["status"]
        if new_status not in APPLICATION_STATUSES:
            raise HTTPException(400, f"Invalid status: {new_status}")
        update["status"] = new_status
        await db.grant_applications.update_one(
            {"_id": oid},
            {"$push": {"status_history": {"status": new_status, "at": _now(), "by": user["id"]}}},
        )
        old_status = doc.get("status", "")
        if new_status == "submitted" and old_status != "submitted":
            _emit_rep(user["id"], "grant_application_submitted", app_id)
        elif new_status == "funded" and old_status != "funded":
            _emit_rep(user["id"], "grant_awarded", app_id)

    if update:
        update["updated_at"] = _now()
        update["last_activity"] = _now()
        await db.grant_applications.update_one({"_id": oid}, {"$set": update})

    return _ser(await db.grant_applications.find_one({"_id": oid}))


@router.delete("/{app_id}", status_code=204)
async def delete_application(app_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_pi(doc, user["id"])
    await asyncio.gather(
        db.grant_team_members.delete_many({"application_id": app_id}),
        db.grant_budget_items.delete_many({"application_id": app_id}),
        db.grant_deliverables.delete_many({"application_id": app_id}),
        db.grant_proposal_versions.delete_many({"application_id": app_id}),
        db.grant_applications.delete_one({"_id": oid}),
    )


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{app_id}/dashboard")
async def application_dashboard(app_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    sections = doc.get("proposal_sections") or {}
    filled_sections = sum(1 for v in sections.values() if v.strip())
    total_sections  = len(PROPOSAL_SECTIONS)
    progress_pct = int(filled_sections / total_sections * 100)

    team_count, budget_items, deliverables, version_count = await asyncio.gather(
        db.grant_team_members.count_documents({"application_id": app_id}),
        db.grant_budget_items.find({"application_id": app_id}).to_list(100),
        db.grant_deliverables.find({"application_id": app_id}).sort("due_date", 1).to_list(50),
        db.grant_proposal_versions.count_documents({"application_id": app_id}),
    )

    total_budget = sum(float(b.get("amount", 0)) for b in budget_items)

    # Overdue deliverables
    today = datetime.now(timezone.utc).date().isoformat()
    overdue = [d for d in deliverables if d.get("due_date", "9999") < today and d.get("status") not in ("completed", "submitted")]

    # Readiness checklist
    grant = await db.grants.find_one({"_id": ObjectId(doc["grant_id"])}) if ObjectId.is_valid(doc.get("grant_id", "")) else None
    checklist = [
        {"label": "Proposal sections filled (>60%)", "done": progress_pct >= 60},
        {"label": "Team has at least 2 members",      "done": team_count >= 1},
        {"label": "Budget planned",                   "done": total_budget > 0},
        {"label": "At least 1 deliverable defined",   "done": len(deliverables) > 0},
        {"label": "Consortium/institution set",        "done": bool(doc.get("consortium_name") or doc.get("institution"))},
        {"label": "Submission reference noted" if doc.get("status") in ("submitted",) else "Ready to submit", "done": bool(doc.get("submission_ref")) if doc.get("status") == "submitted" else doc.get("status") in ("ready_for_submission",)},
    ]
    ready = all(c["done"] for c in checklist[:5])

    return {
        "progress_pct":       progress_pct,
        "filled_sections":    filled_sections,
        "total_sections":     total_sections,
        "team_count":         team_count,
        "total_budget":       total_budget,
        "currency":           doc.get("currency", "EUR"),
        "deliverable_count":  len(deliverables),
        "overdue_count":      len(overdue),
        "version_count":      version_count,
        "checklist":          checklist,
        "ready_to_submit":    ready,
        "upcoming_deliverables": [_ser(d) for d in deliverables[:5]],
        "overdue_deliverables":  [_ser(d) for d in overdue[:5]],
        "grant_deadline":     doc.get("grant_deadline"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TEAM MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{app_id}/team")
async def list_team(app_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    members = await db.grant_team_members.find({"application_id": app_id}).to_list(50)
    user_ids = [ObjectId(m["user_id"]) for m in members if ObjectId.is_valid(m.get("user_id", ""))]
    users_raw = await db.users.find({"_id": {"$in": user_ids}},
                                    {"full_name": 1, "institution": 1, "avatar_url": 1, "department": 1, "orcid": 1}).to_list(50)
    umap = {str(u["_id"]): u for u in users_raw}
    out = []
    for m in members:
        item = _ser(m)
        u = umap.get(m.get("user_id", ""))
        if u:
            item["user"] = {
                "id": str(u["_id"]), "full_name": u.get("full_name", ""),
                "institution": u.get("institution", ""), "avatar_url": u.get("avatar_url"),
                "department": u.get("department", ""),
                "orcid_id": (u.get("orcid") or {}).get("orcid_id"),
            }
        out.append(item)
    return out


@router.post("/{app_id}/team")
async def invite_team_member(app_id: str, body: dict, user: dict = Depends(get_current_user)):
    """PI or Co-I invites a collaborator to the grant team."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    invited_id = body.get("user_id", "").strip()
    if not invited_id:
        raise HTTPException(400, "user_id required")
    if invited_id == doc.get("pi_id"):
        raise HTTPException(400, "PI is already the team lead")

    try:
        target = await db.users.find_one({"_id": ObjectId(invited_id)}, {"full_name": 1})
    except Exception:
        raise HTTPException(404, "User not found")
    if not target:
        raise HTTPException(404, "User not found")

    existing = await db.grant_team_members.find_one({"application_id": app_id, "user_id": invited_id})
    if existing:
        raise HTTPException(409, "User is already on the team")

    role = body.get("role", "Co-Investigator")
    if role not in TEAM_ROLES:
        role = "Researcher"

    now = _now()
    member_doc = {
        "application_id":   app_id,
        "user_id":          invited_id,
        "role":             role,
        "work_package":     body.get("work_package", ""),
        "institution":      body.get("institution", target.get("institution", "")),
        "fte_months":       body.get("fte_months", 0),
        "status":           "invited",
        "invited_by":       user["id"],
        "invited_at":       now,
        "joined_at":        None,
    }
    res = await db.grant_team_members.insert_one(member_doc)
    member_doc["_id"] = res.inserted_id

    grant_title = doc.get("grant_title", "a grant")
    await _notify(
        user_id=invited_id, kind="grant_team_invited",
        title=f"Grant team invitation: {grant_title[:60]}",
        body=f"{user.get('full_name','Someone')} invited you to join as {role}",
        link=f"/grant-applications/{app_id}", actor_id=user["id"],
        payload={"application_id": app_id},
    )
    return _ser(member_doc)


@router.patch("/{app_id}/team/{uid}")
async def update_team_member(app_id: str, uid: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_pi(doc, user["id"])

    update: dict = {}
    if "role" in body and body["role"] in TEAM_ROLES:
        update["role"] = body["role"]
    if "work_package" in body:
        update["work_package"] = body["work_package"]
    if "fte_months" in body:
        update["fte_months"] = body["fte_months"]
    if "status" in body and body["status"] in ("invited", "accepted", "declined"):
        update["status"] = body["status"]
        if body["status"] == "accepted":
            update["joined_at"] = _now()
    if update:
        await db.grant_team_members.update_one({"application_id": app_id, "user_id": uid}, {"$set": update})
    return {"ok": True}


@router.delete("/{app_id}/team/{uid}", status_code=204)
async def remove_team_member(app_id: str, uid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    # PI can remove anyone; members can remove themselves
    if user["id"] != doc.get("pi_id") and user["id"] != uid:
        raise HTTPException(403, "Forbidden")
    if uid == doc.get("pi_id"):
        raise HTTPException(400, "Cannot remove the PI")
    await db.grant_team_members.delete_one({"application_id": app_id, "user_id": uid})


# ══════════════════════════════════════════════════════════════════════════════
# BUDGET MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{app_id}/budget")
async def list_budget(app_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None
    items = await db.grant_budget_items.find({"application_id": app_id}).sort("category", 1).to_list(200)
    total = sum(float(b.get("amount", 0)) for b in items)
    by_category: dict = {}
    for b in items:
        cat = b.get("category", "Other")
        by_category[cat] = by_category.get(cat, 0) + float(b.get("amount", 0))
    return {
        "items":       [_ser(b) for b in items],
        "total":       total,
        "by_category": [{"category": k, "amount": v} for k, v in sorted(by_category.items())],
        "currency":    doc.get("currency", "EUR"),
    }


@router.post("/{app_id}/budget", status_code=201)
async def add_budget_item(app_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    category = body.get("category", "Other")
    if category not in BUDGET_CATEGORIES:
        category = "Other"

    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0.0

    now = _now()
    item_doc = {
        "application_id": app_id,
        "category":       category,
        "description":    body.get("description", "").strip()[:500],
        "amount":         amount,
        "unit":           body.get("unit", ""),
        "quantity":       body.get("quantity"),
        "justification":  body.get("justification", "").strip()[:1000],
        "year":           body.get("year"),
        "created_by":     user["id"],
        "created_at":     now,
        "updated_at":     now,
    }
    res = await db.grant_budget_items.insert_one(item_doc)
    item_doc["_id"] = res.inserted_id

    # Update application total
    all_items = await db.grant_budget_items.find({"application_id": app_id}).to_list(200)
    total = sum(float(b.get("amount", 0)) for b in all_items)
    await db.grant_applications.update_one(
        {"_id": oid}, {"$set": {"requested_budget": total, "updated_at": now}},
    )
    return _ser(item_doc)


@router.patch("/{app_id}/budget/{bid}")
async def update_budget_item(app_id: str, bid: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        app_oid = ObjectId(app_id)
        b_oid   = ObjectId(bid)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": app_oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    update: dict = {"updated_at": _now()}
    for field in ("category", "description", "amount", "unit", "quantity", "justification", "year"):
        if field in body:
            update[field] = body[field]
    await db.grant_budget_items.update_one({"_id": b_oid, "application_id": app_id}, {"$set": update})

    # Recompute total
    all_items = await db.grant_budget_items.find({"application_id": app_id}).to_list(200)
    total = sum(float(b.get("amount", 0)) for b in all_items)
    await db.grant_applications.update_one({"_id": app_oid}, {"$set": {"requested_budget": total, "updated_at": _now()}})
    return _ser(await db.grant_budget_items.find_one({"_id": b_oid}))


@router.delete("/{app_id}/budget/{bid}", status_code=204)
async def delete_budget_item(app_id: str, bid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        app_oid = ObjectId(app_id)
        b_oid   = ObjectId(bid)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": app_oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None
    await db.grant_budget_items.delete_one({"_id": b_oid, "application_id": app_id})


# ══════════════════════════════════════════════════════════════════════════════
# DELIVERABLES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{app_id}/deliverables")
async def list_deliverables(app_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None
    items = await db.grant_deliverables.find({"application_id": app_id}).sort("due_date", 1).to_list(100)
    return [_ser(d) for d in items]


@router.post("/{app_id}/deliverables", status_code=201)
async def add_deliverable(app_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    d_type = body.get("type", "Deliverable")
    if d_type not in DELIVERABLE_TYPES:
        d_type = "Deliverable"

    now = _now()
    d_doc = {
        "application_id":  app_id,
        "title":           (body.get("title") or "").strip()[:300],
        "type":            d_type,
        "due_date":        body.get("due_date"),
        "work_package":    body.get("work_package", ""),
        "description":     body.get("description", "").strip()[:1000],
        "status":          "pending",
        "assignee_id":     body.get("assignee_id"),
        "link":            body.get("link", ""),
        "created_by":      user["id"],
        "created_at":      now,
        "updated_at":      now,
        "completed_at":    None,
    }
    if not d_doc["title"]:
        raise HTTPException(400, "title required")
    res = await db.grant_deliverables.insert_one(d_doc)
    d_doc["_id"] = res.inserted_id
    return _ser(d_doc)


@router.patch("/{app_id}/deliverables/{did}")
async def update_deliverable(app_id: str, did: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        app_oid = ObjectId(app_id)
        d_oid   = ObjectId(did)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": app_oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    update: dict = {"updated_at": _now()}
    for field in ("title", "type", "due_date", "work_package", "description", "status", "assignee_id", "link"):
        if field in body:
            update[field] = body[field]
    if body.get("status") == "completed" and not body.get("completed_at"):
        update["completed_at"] = _now()
    await db.grant_deliverables.update_one({"_id": d_oid, "application_id": app_id}, {"$set": update})
    return _ser(await db.grant_deliverables.find_one({"_id": d_oid}))


@router.delete("/{app_id}/deliverables/{did}", status_code=204)
async def delete_deliverable(app_id: str, did: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        app_oid = ObjectId(app_id)
        d_oid   = ObjectId(did)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": app_oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None
    await db.grant_deliverables.delete_one({"_id": d_oid, "application_id": app_id})


# ══════════════════════════════════════════════════════════════════════════════
# PROPOSAL VERSION CONTROL
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{app_id}/versions")
async def list_versions(app_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None
    versions = await db.grant_proposal_versions.find({"application_id": app_id}).sort("version", -1).to_list(50)
    return [_ser(v) for v in versions]


@router.post("/{app_id}/versions")
async def create_version(app_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    version = doc.get("current_version", 0) + 1
    now = _now()
    v_doc = {
        "application_id":   app_id,
        "version":          version,
        "summary":          (body.get("summary") or "").strip()[:500],
        "author_id":        user["id"],
        "author_name":      user.get("full_name", ""),
        "proposal_sections": doc.get("proposal_sections") or {},
        "created_at":       now,
    }
    res = await db.grant_proposal_versions.insert_one(v_doc)
    await db.grant_applications.update_one(
        {"_id": oid}, {"$set": {"current_version": version, "updated_at": now}},
    )
    v_doc["_id"] = res.inserted_id
    return _ser(v_doc)


@router.post("/{app_id}/versions/{version_number}/restore")
async def restore_version(app_id: str, version_number: int, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.grant_applications.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_member(doc, user["id"]) if doc.get("pi_id") != user["id"] else None

    target = await db.grant_proposal_versions.find_one({
        "application_id": app_id, "version": version_number,
    })
    if not target:
        raise HTTPException(404, f"Version {version_number} not found")

    now = _now()
    new_version = doc.get("current_version", 0) + 1

    # Auto-snapshot current state
    await db.grant_proposal_versions.insert_one({
        "application_id":    app_id,
        "version":           new_version,
        "summary":           f"Auto-snapshot before restore to v{version_number}",
        "author_id":         user["id"],
        "author_name":       user.get("full_name", ""),
        "proposal_sections": doc.get("proposal_sections") or {},
        "created_at":        now,
    })

    await db.grant_applications.update_one(
        {"_id": oid},
        {"$set": {
            "proposal_sections": target.get("proposal_sections") or {},
            "current_version":   new_version,
            "updated_at":        now,
        }},
    )
    return {"ok": True, "restored_to": version_number, "new_version": new_version}
