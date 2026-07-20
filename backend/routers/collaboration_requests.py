"""Collaboration Requests — researcher-to-researcher collaboration invitations.

Connects the Research Gap Finder and Collaboration Intelligence workflows into
a real collaboration pipeline. A request carries an optional project_id so the
receiver knows what they are being invited to.

On accept the sender can then create a Workspace or Project Team.

Endpoints:
  POST /api/collaboration-requests          — send a request
  GET  /api/collaboration-requests          — list mine (sent + received)
  PATCH /api/collaboration-requests/{id}    — update status (accepted/declined/withdrawn)
  GET  /api/collaboration-requests/metrics  — aggregate stats for Feature 10

Activity is written to `collaboration_activity` on every state transition.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.notifications_service import dispatch, NotificationEvent
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.collaboration_requests")
router = APIRouter(prefix="/api/collaboration-requests", tags=["collaboration-requests"])

VALID_STATUSES = {"pending", "viewed", "accepted", "declined", "withdrawn", "expired", "cancelled"}
INVITATION_TYPES = {
    "research_collaboration", "project_invitation", "workspace_invitation",
    "manuscript_invitation", "grant_team", "conference_team",
    "reviewer", "mentorship", "institutional_collaboration",
}
REQUEST_EXPIRY_DAYS = 30


# ──────────────────────────────── models ─────────────────────────────────────

class SendRequestBody(BaseModel):
    receiver_id:           str = Field(..., min_length=1)
    message:               str = Field("", max_length=2000)
    project_id:            Optional[str] = Field(None)
    source:                Optional[str] = Field(None)
    context:               Optional[dict] = Field(None)
    invitation_type:       Optional[str] = Field("research_collaboration")
    role:                  Optional[str] = Field(None, max_length=100)
    expected_contribution: Optional[str] = Field(None, max_length=500)
    estimated_duration:    Optional[str] = Field(None, max_length=100)


class UpdateStatusBody(BaseModel):
    status:         str
    decline_reason: Optional[str] = Field(None, max_length=500)


# ──────────────────────────────── helpers ────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


async def _track(db, user_id: str, action: str, entity_type: str,
                 entity_id: str, metadata: dict | None = None) -> None:
    """Write a lightweight activity record."""
    try:
        await db.collaboration_activity.insert_one({
            "user_id":     user_id,
            "action":      action,
            "entity_type": entity_type,
            "entity_id":   entity_id,
            "metadata":    metadata or {},
            "created_at":  _now(),
        })
    except Exception as exc:
        log.warning("Activity tracking failed: %s", exc)


def _enrich_request(req: dict, users_map: dict) -> dict:
    """Attach sender_profile and receiver_profile to a request dict."""
    req = dict(req)
    req["sender_profile"] = users_map.get(req.get("sender_id"))
    req["receiver_profile"] = users_map.get(req.get("receiver_id"))
    return req


# ──────────────────────────────── endpoints ──────────────────────────────────

@router.post("")
async def send_request(
    body: SendRequestBody,
    user: dict = Depends(get_current_user),
):
    """Send a collaboration request to another researcher."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    sender_id = user["id"]

    if body.receiver_id == sender_id:
        raise HTTPException(400, "Cannot send a collaboration request to yourself.")

    # Verify receiver exists
    try:
        receiver = await db.users.find_one({"_id": ObjectId(body.receiver_id)})
    except Exception:
        raise HTTPException(404, "Receiver not found.")
    if not receiver:
        raise HTTPException(404, "Receiver not found.")

    # Prevent duplicate pending requests
    existing = await db.collaboration_requests.find_one({
        "sender_id":   sender_id,
        "receiver_id": body.receiver_id,
        "status":      "pending",
    })
    if existing:
        raise HTTPException(409, "You already have a pending request to this researcher.")

    # Validate project_id if supplied
    project_title = None
    if body.project_id:
        try:
            proj = await db.projects.find_one({"_id": ObjectId(body.project_id)})
            if proj:
                project_title = proj.get("title")
        except Exception:
            pass

    inv_type = body.invitation_type or "research_collaboration"
    if inv_type not in INVITATION_TYPES:
        inv_type = "research_collaboration"
    expires_at = (datetime.now(timezone.utc) + timedelta(days=REQUEST_EXPIRY_DAYS)).isoformat()
    doc = {
        "sender_id":             sender_id,
        "receiver_id":           body.receiver_id,
        "message":               body.message.strip(),
        "project_id":            body.project_id,
        "project_title":         project_title,
        "source":                body.source or "manual",
        "context":               body.context or {},
        "invitation_type":       inv_type,
        "role":                  body.role or "",
        "expected_contribution": body.expected_contribution or "",
        "estimated_duration":    body.estimated_duration or "",
        "status":                "pending",
        "status_history":        [{"status": "pending", "at": _now(), "by": sender_id}],
        "created_at":            _now(),
        "updated_at":            _now(),
        "expires_at":            expires_at,
        "viewed_at":             None,
        "responded_at":          None,
        "decline_reason":        None,
    }
    result = await db.collaboration_requests.insert_one(doc)
    doc["_id"] = result.inserted_id
    req_id = str(result.inserted_id)

    # Notify receiver
    sender_name = user.get("full_name") or "A researcher"
    notif_body = body.message[:120] if body.message else "Would like to collaborate with you."
    link = "/collaboration-requests"
    await dispatch(NotificationEvent(
        user_id=body.receiver_id,
        kind="collaboration_request",
        title=f"{sender_name} sent you a collaboration request",
        body=notif_body,
        link=link,
        actor_id=sender_id,
        payload={"request_id": req_id, "project_id": body.project_id},
    ))

    # Track activity
    await _track(db, sender_id, "request_sent", "collaboration_request", req_id,
                 {"receiver_id": body.receiver_id, "source": body.source})

    return _ser(doc)


@router.get("")
async def list_my_requests(
    kind: Optional[str] = Query(None),  # "sent" | "received"
    status: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """Return sent and/or received collaboration requests for the current user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    filt: dict = {}
    if kind == "sent":
        filt["sender_id"] = uid
    elif kind == "received":
        filt["receiver_id"] = uid
    else:
        filt["$or"] = [{"sender_id": uid}, {"receiver_id": uid}]

    if status:
        filt["status"] = status

    docs = await db.collaboration_requests.find(filt).sort("created_at", -1).to_list(200)
    if not docs:
        return []

    # Fetch all involved user profiles in a single query
    user_ids = set()
    for d in docs:
        user_ids.add(d.get("sender_id"))
        user_ids.add(d.get("receiver_id"))
    user_ids.discard(None)

    oid_list = []
    for uid_str in user_ids:
        try:
            oid_list.append(ObjectId(uid_str))
        except Exception:
            pass

    profiles_raw = await db.users.find(
        {"_id": {"$in": oid_list}},
        {"full_name": 1, "academic_role": 1, "user_type": 1, "primary_domain": 1, "institution": 1, "country": 1, "avatar_url": 1, "research_areas": 1},
    ).to_list(200)

    users_map = {}
    for p in profiles_raw:
        users_map[str(p["_id"])] = {
            "id":             str(p["_id"]),
            "full_name":      p.get("full_name") or "",
            "academic_role":  p.get("academic_role") or "",
            "user_type":      p.get("user_type") or None,
            "primary_domain": p.get("primary_domain") or None,
            "institution":    p.get("institution") or "",
            "country":        p.get("country") or "",
            "avatar_url":     p.get("avatar_url"),
            "research_areas": p.get("research_areas") or [],
        }

    return [_enrich_request(_ser(d), users_map) for d in docs]


@router.get("/{request_id}")
async def get_request(request_id: str, user: dict = Depends(get_current_user)):
    """Get a single collaboration request by ID (sender or receiver only)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(request_id)
    except Exception:
        raise HTTPException(404, "Not found")
    req = await db.collaboration_requests.find_one({"_id": oid})
    if not req:
        raise HTTPException(404, "Not found")
    uid = user["id"]
    if req["sender_id"] != uid and req["receiver_id"] != uid:
        raise HTTPException(403, "Forbidden")
    profiles_raw = await db.users.find(
        {"_id": {"$in": [ObjectId(req["sender_id"]), ObjectId(req["receiver_id"])]}},
        {"full_name": 1, "institution": 1, "avatar_url": 1, "research_areas": 1, "user_type": 1, "primary_domain": 1},
    ).to_list(2)
    users_map = {str(p["_id"]): {
        "id": str(p["_id"]), "full_name": p.get("full_name", ""),
        "institution": p.get("institution", ""), "avatar_url": p.get("avatar_url"),
        "research_areas": p.get("research_areas", []),
    } for p in profiles_raw}
    return _enrich_request(_ser(req), users_map)


@router.patch("/{request_id}")
async def update_request_status(
    request_id: str,
    body: UpdateStatusBody,
    user: dict = Depends(get_current_user),
):
    """Accept, decline, withdraw, or mark-viewed a collaboration request."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")

    try:
        oid = ObjectId(request_id)
    except Exception:
        raise HTTPException(404, "Not found")

    req = await db.collaboration_requests.find_one({"_id": oid})
    if not req:
        raise HTTPException(404, "Request not found.")

    uid = user["id"]

    # Check expiry
    expires_at = req.get("expires_at")
    if expires_at and req["status"] == "pending":
        try:
            if datetime.fromisoformat(expires_at.replace("Z", "+00:00")) < datetime.now(timezone.utc):
                await db.collaboration_requests.update_one({"_id": oid}, {"$set": {"status": "expired"}})
                raise HTTPException(410, "This invitation has expired.")
        except HTTPException:
            raise
        except Exception:
            pass

    # Permission gate by action
    if body.status == "withdrawn":
        if req["sender_id"] != uid:
            raise HTTPException(403, "Only the sender can withdraw.")
        if req["status"] not in ("pending", "viewed"):
            raise HTTPException(409, f"Cannot withdraw a {req['status']} request.")
    elif body.status == "cancelled":
        if req["sender_id"] != uid:
            raise HTTPException(403, "Only the sender can cancel.")
    elif body.status == "viewed":
        if req["receiver_id"] != uid:
            raise HTTPException(403, "Only the receiver can mark as viewed.")
        if req["status"] != "pending":
            return {"id": request_id, "status": req["status"]}
    else:
        # accepted / declined
        if req["receiver_id"] != uid:
            raise HTTPException(403, "Only the receiver can accept or decline.")
        if req["status"] not in ("pending", "viewed"):
            raise HTTPException(409, f"Request is already {req['status']}.")

    now = _now()
    update_fields: dict = {"status": body.status, "updated_at": now}
    if body.status == "viewed":
        update_fields["viewed_at"] = now
    if body.status in ("accepted", "declined", "withdrawn", "cancelled"):
        update_fields["responded_at"] = now
    if body.status == "declined" and body.decline_reason:
        update_fields["decline_reason"] = body.decline_reason.strip()

    # Status history entry
    history_entry = {"status": body.status, "at": now, "by": uid}

    match_filter = {"_id": oid}
    if body.status not in ("viewed", "cancelled"):
        match_filter["status"] = {"$in": ["pending", "viewed"]}

    result = await db.collaboration_requests.update_one(
        match_filter,
        {
            "$set": update_fields,
            "$push": {"status_history": history_entry},
        },
    )
    if result.matched_count == 0:
        raise HTTPException(409, "Request was already processed by a concurrent action.")

    # ── Accept side effects ──────────────────────────────────────────────────
    if body.status == "accepted":
        # 1. Add sender to project if receiver has access
        if req.get("project_id"):
            try:
                proj_oid = ObjectId(req["project_id"])
                proj = await db.projects.find_one({"_id": proj_oid})
                if proj and (uid == proj.get("owner_id") or uid in proj.get("members", [])):
                    await db.projects.update_one(
                        {"_id": proj_oid},
                        {"$addToSet": {"members": req["sender_id"]}},
                    )
            except Exception as exc:
                log.warning("Failed to add member to project after accept: %s", exc)

        # 2. Record team membership
        try:
            await db.team_memberships.insert_one({
                "user_id":         req["sender_id"],
                "inviter_id":      uid,
                "invitation_id":   request_id,
                "invitation_type": req.get("invitation_type", "research_collaboration"),
                "entity_type":     "collaboration_request",
                "entity_id":       request_id,
                "project_id":      req.get("project_id"),
                "role":            req.get("role") or "collaborator",
                "joined_at":       now,
                "created_at":      now,
            })
        except Exception as exc:
            log.warning("team_memberships insert failed: %s", exc)

        # 3. Auto-create DM conversation so they can immediately communicate
        try:
            sorted_ids = sorted([req["sender_id"], uid])
            conv_key = f"direct:{sorted_ids[0]}:{sorted_ids[1]}"
            existing = await db.conversations.find_one({"context_key": conv_key})
            if not existing:
                conv_doc = {
                    "type": "direct", "context_id": "", "context_key": conv_key, "title": "",
                    "created_by": uid,
                    "created_at": now, "last_message_at": now, "last_message_preview": "",
                }
                res = await db.conversations.insert_one(conv_doc)
                for mid in sorted_ids:
                    await db.conversation_members.insert_one({
                        "conversation_id": str(res.inserted_id),
                        "user_id": mid, "role": "member",
                        "joined_at": now, "last_read_at": now, "muted": False,
                    })
        except Exception as exc:
            log.warning("DM conversation creation after accept failed: %s", exc)

    # ── Notifications ──────────────────────────────────────────────────────
    if body.status != "viewed":
        notifier_name = user.get("full_name") or "A researcher"
        other_id = req["sender_id"] if uid == req["receiver_id"] else req["receiver_id"]
        status_label = {
            "accepted": "accepted", "declined": "declined",
            "withdrawn": "withdrew", "cancelled": "cancelled",
        }.get(body.status, body.status)
        notif_body = body.decline_reason or f"Request status: {body.status}"
        await dispatch(NotificationEvent(
            user_id=other_id,
            kind="collaboration_request_update",
            title=f"{notifier_name} {status_label} your collaboration request",
            body=notif_body[:200],
            link="/collaboration-requests",
            actor_id=uid,
            payload={"request_id": request_id, "new_status": body.status},
        ))

    # ── Viewed notification (tell sender receiver has looked) ──────────────
    if body.status == "viewed":
        await dispatch(NotificationEvent(
            user_id=req["sender_id"],
            kind="invitation_viewed",
            title=f"{user.get('full_name','Someone')} viewed your collaboration request",
            body="They've seen your invitation.",
            link="/collaboration-requests",
            actor_id=uid,
            payload={"request_id": request_id},
        ))

    action_map = {
        "accepted": "request_accepted", "declined": "request_declined",
        "withdrawn": "request_withdrawn", "cancelled": "request_cancelled",
        "viewed": "request_viewed",
    }
    await _track(db, uid, action_map.get(body.status, "request_updated"),
                 "collaboration_request", request_id,
                 {"status": body.status, "project_id": req.get("project_id")})

    return {"id": request_id, "status": body.status, "updated_at": now}


@router.get("/metrics")
async def get_collab_metrics(user: dict = Depends(get_current_user)):
    """Aggregate collaboration workflow stats for the current user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    sent   = await db.collaboration_requests.count_documents({"sender_id": uid})
    received = await db.collaboration_requests.count_documents({"receiver_id": uid})
    accepted = await db.collaboration_requests.count_documents({
        "$or": [{"sender_id": uid}, {"receiver_id": uid}],
        "status": "accepted",
    })
    pending_received = await db.collaboration_requests.count_documents({
        "receiver_id": uid, "status": "pending",
    })

    gap_runs = await db.research_gap_reviews.count_documents({"user_id": uid})
    collab_runs = await db.collaboration_recommendations.count_documents({"user_id": uid})
    total_recs_cursor = await db.collaboration_recommendations.aggregate([
        {"$match": {"user_id": uid}},
        {"$group": {"_id": None, "total": {"$sum": "$recommendation_count"}}},
    ]).to_list(1)
    total_recs = total_recs_cursor[0]["total"] if total_recs_cursor else 0

    projects_from_gap = await db.projects.count_documents({"owner_id": uid, "source": "gap_finder"})
    projects_from_collab = await db.projects.count_documents({"owner_id": uid, "source": "collab_intel"})
    total_projects = await db.projects.count_documents(
        {"$or": [{"owner_id": uid}, {"members": uid}]}
    )

    recent_gaps = await db.research_gap_reviews.find(
        {"user_id": uid},
        {"topic": 1, "publication_score": 1, "keywords": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(5)

    return {
        "requests_sent":         sent,
        "requests_received":     received,
        "requests_accepted":     accepted,
        "pending_received":      pending_received,
        "gap_analyses":          gap_runs,
        "collab_intel_runs":     collab_runs,
        "total_recommendations": total_recs,
        "projects_from_gap":     projects_from_gap,
        "projects_from_collab":  projects_from_collab,
        "total_projects":        total_projects,
        "recent_gap_analyses": [
            {
                "id":               str(g["_id"]),
                "topic":            g.get("topic", ""),
                "publication_score": g.get("publication_score", 0),
                "keywords":         g.get("keywords", [])[:3],
                "created_at":       g.get("created_at"),
            }
            for g in recent_gaps
        ],
    }
