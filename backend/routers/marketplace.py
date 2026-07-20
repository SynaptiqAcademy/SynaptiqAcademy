"""Marketplace router — people-first discovery, match scoring, reverse matching,
invitations, and analytics."""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from repo.shim import DBProxy
from repo.security_context import SecurityContext

_log = logging.getLogger("synaptiq.marketplace")
from typing import Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.marketplace import matching as M
from services.permissions import require_feature

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

ROLES = ["co_author", "statistician", "methodology", "reviewer", "ai_specialist",
         "data_scientist", "editor", "sme"]


# ============================== SEARCH =====================================
class SearchIn(BaseModel):
    role: Optional[str] = None
    q: Optional[str] = None
    areas: list[str] = []
    skills: list[str] = []
    country: Optional[str] = None
    institution: Optional[str] = None
    availability: Optional[str] = None
    limit: int = Field(50, ge=1, le=100)
    context_entity_kind: Optional[Literal["workspace", "project", "manuscript"]] = None
    context_entity_id: Optional[str] = None


async def _entity_context_tokens(kind: str, eid: str) -> dict:
    """Pull keywords/areas from a workspace/project/manuscript to seed matching."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try: oid = ObjectId(eid)
    except Exception: return {}
    if kind == "workspace":
        d = await db.workspaces.find_one({"_id": oid})
        if not d: return {}
        return {"areas": d.get("research_areas") or [],
                "keywords": (d.get("keywords") or []) + (d.get("research_topics") or [])}
    if kind == "project":
        d = await db.projects.find_one({"_id": oid})
        if not d: return {}
        return {"areas": [d.get("research_area")] if d.get("research_area") else [],
                "keywords": (d.get("research_questions") or [])[:5]}
    if kind == "manuscript":
        d = await db.manuscripts.find_one({"_id": oid})
        if not d: return {}
        sections = d.get("sections") or {}
        abstract = (sections.get("abstract") or "")[:400]
        return {"keywords": (d.get("keywords") or [])[:8] + ([abstract] if abstract else []),
                "areas": d.get("research_areas") or []}
    return {}


@router.post("/search")
async def search(payload: SearchIn, user: dict = Depends(get_current_user)):
    ctx_tokens = {}
    if payload.context_entity_kind and payload.context_entity_id:
        ctx_tokens = await _entity_context_tokens(payload.context_entity_kind, payload.context_entity_id)
    ranked = await M.deterministic_rank(
        requester_id=user["id"], role=payload.role, q=payload.q,
        areas=payload.areas or None, skills=payload.skills or None,
        country=payload.country, institution=payload.institution,
        availability=payload.availability, limit=payload.limit,
        context_tokens=ctx_tokens or None,
    )
    # Decorate with cached reputation (best-effort, no recompute).
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if ranked:
        uids = [r["user"]["id"] for r in ranked]
        reps = {r["user_id"]: r async for r in
                db.reputation_scores.find({"user_id": {"$in": uids}})}
        for r in ranked:
            rep = reps.get(r["user"]["id"])
            if rep:
                r["reputation"] = {
                    "overall": rep.get("overall"),
                    "collaboration": rep.get("collaboration", {}).get("score"),
                    "publication":   rep.get("publication", {}).get("score"),
                    "reviewer":      rep.get("reviewer", {}).get("score"),
                    "funding":       rep.get("funding", {}).get("score"),
                    "activity":      rep.get("activity", {}).get("score"),
                }
    return {"results": ranked, "role": payload.role, "count": len(ranked)}


# ============================== RERANK =====================================
class RerankIn(BaseModel):
    candidates: list[dict]  # output of /search
    role: Optional[str] = None
    context: Optional[str] = None
    top_n: int = Field(10, ge=1, le=15)


@router.post("/rerank", dependencies=[Depends(require_feature("ai_assistant"))])
async def rerank(payload: RerankIn, user: dict = Depends(get_current_user)):
    return await M.llm_rerank(
        requester_id=user["id"], candidates=payload.candidates,
        role=payload.role, context=payload.context, top_n=payload.top_n,
    )


# ============================== REVERSE ====================================
@router.get("/reverse")
async def reverse_matches(user: dict = Depends(get_current_user), limit: int = 20):
    """Who/what is looking for me?

    Returns three sections:
      - researchers: users whose recent searches/saved searches overlap with me
        (proxy via expertise_requests that filter on my role tags / areas).
      - projects/manuscripts/workspaces: indirectly suggested via open requests.
      - expertise_requests: open requests where my profile matches the role.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    me = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not me: raise HTTPException(404, "User not found")

    my_roles = set((me.get("expertise_role_tags") or []))
    my_areas = set((me.get("research_areas") or []))
    my_kws   = set((me.get("research_keywords") or []) + (me.get("research_interests") or []))

    # Open expertise_requests matching my tags or overlapping in areas/skills.
    or_clauses: list = []
    if my_roles: or_clauses.append({"kind": {"$in": list(my_roles)}})
    if my_areas: or_clauses.append({"research_areas": {"$in": list(my_areas)}})
    if my_kws:   or_clauses.append({"required_skills": {"$in": list(my_kws)}})
    requests_for_me: list[dict] = []
    if or_clauses:
        q = {"status": "open", "owner_id": {"$ne": user["id"]}, "$or": or_clauses}
        docs = await db.expertise_requests.find(q).sort("created_at", -1).limit(limit).to_list(limit)
        for d in docs:
            d["id"] = str(d.pop("_id"))
            requests_for_me.append(d)

    # Pending invitations on expertise_requests where I'm invited
    invited = await db.expertise_requests.find(
        {"invitations.user_id": user["id"], "status": "open"}
    ).limit(20).to_list(20)
    invitations: list[dict] = []
    for d in invited:
        d["id"] = str(d.pop("_id"))
        invitations.append(d)

    # Reviewer assignments pending
    review_assignments_docs = await db.review_requests.find(
        {"reviewer_id": user["id"], "status": "invited"}).limit(10).to_list(10) \
        if "review_requests" in await db.list_collection_names() else []
    review_assignments = []
    for r in review_assignments_docs:
        rid = str(r.pop("_id"))
        review_assignments.append({**r, "id": rid})

    # Suggested workspaces (open, public, overlapping areas — best effort)
    suggested_ws: list[dict] = []
    if my_areas:
        ws_docs = await db.workspaces.find({
            "member_ids": {"$ne": user["id"]},
            "visibility": {"$in": ["public", "discoverable"]},
            "research_areas": {"$in": list(my_areas)},
        }).limit(5).to_list(5)
        for w in ws_docs:
            w["id"] = str(w.pop("_id"))
            suggested_ws.append(w)

    return {
        "expertise_requests": requests_for_me,
        "invitations": invitations,
        "review_assignments": review_assignments,
        "suggested_workspaces": suggested_ws,
    }


# ============================== INVITES ====================================
INVITE_KINDS = Literal[
    "collaboration", "workspace", "project", "manuscript", "expertise_request",
    "grant_team", "conference_team", "reviewer", "mentorship", "institutional_collaboration",
]

INVITE_EXPIRY_DAYS = 30


class InviteIn(BaseModel):
    target_user_id:        str
    kind:                  INVITE_KINDS = "collaboration"
    entity_id:             Optional[str] = None
    role:                  Optional[str] = None
    message:               Optional[str] = None
    expected_contribution: Optional[str] = Field(None, max_length=500)
    estimated_duration:    Optional[str] = Field(None, max_length=100)


@router.post("/invite")
async def invite(payload: InviteIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if payload.target_user_id == user["id"]:
        raise HTTPException(400, "Cannot invite yourself")
    target = await db.users.find_one({"_id": ObjectId(payload.target_user_id)},
                                      {"full_name": 1, "email": 1})
    if not target:
        raise HTTPException(404, "User not found")

    # Ownership check: sender must be a member/owner of the entity they're inviting to
    if payload.entity_id and payload.kind in ("workspace", "project", "manuscript"):
        try:
            oid = ObjectId(payload.entity_id)
            if payload.kind == "workspace":
                ent = await db.workspaces.find_one({"_id": oid}, {"members": 1, "owner_id": 1})
                if ent and user["id"] not in ent.get("members", []) and ent.get("owner_id") != user["id"]:
                    raise HTTPException(403, "You are not a member of this workspace")
            elif payload.kind == "project":
                ent = await db.projects.find_one({"_id": oid}, {"members": 1, "owner_id": 1})
                if ent and user["id"] not in ent.get("members", []) and ent.get("owner_id") != user["id"]:
                    raise HTTPException(403, "You are not a member of this project")
            elif payload.kind == "manuscript":
                ent = await db.manuscripts.find_one({"_id": oid}, {"authors": 1, "owner_id": 1})
                if ent and user["id"] not in ent.get("authors", []) and ent.get("owner_id") != user["id"]:
                    raise HTTPException(403, "You are not an author of this manuscript")
        except HTTPException:
            raise
        except Exception:
            pass  # entity not found — allow invite anyway

    # Prevent duplicate pending invitation
    existing = await db.marketplace_invitations.find_one({
        "from_user_id": user["id"],
        "to_user_id": payload.target_user_id,
        "kind": payload.kind,
        "entity_id": payload.entity_id,
        "status": "pending",
    })
    if existing:
        raise HTTPException(409, "You already have a pending invitation of this type to this user.")

    now = datetime.now(timezone.utc).isoformat()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)).isoformat()
    doc = {
        "from_user_id":        user["id"],
        "to_user_id":          payload.target_user_id,
        "kind":                payload.kind,
        "entity_id":           payload.entity_id,
        "role":                payload.role,
        "message":             payload.message,
        "expected_contribution": payload.expected_contribution,
        "estimated_duration":  payload.estimated_duration,
        "status":              "pending",
        "viewed_at":           None,
        "responded_at":        None,
        "decline_reason":      None,
        "created_at":          now,
        "expires_at":          expires_at,
    }
    r = await db.marketplace_invitations.insert_one(doc)
    inv_id = str(r.inserted_id)

    # Link to expertise_request if relevant
    if payload.kind == "expertise_request" and payload.entity_id:
        try:
            await db.expertise_requests.update_one(
                {"_id": ObjectId(payload.entity_id)},
                {"$push": {"invitations": {
                    "user_id": payload.target_user_id, "from_user_id": user["id"],
                    "invitation_id": inv_id,
                    "status": "pending", "invited_at": now,
                }}},
            )
        except Exception:
            pass

    # Notify recipient
    from services.notifications_service import dispatch as _dispatch, NotificationEvent as _NE
    try:
        await _dispatch(_NE(
            user_id=payload.target_user_id,
            kind="marketplace_invitation",
            title=f"{user.get('full_name','Someone')} invited you to collaborate",
            body=payload.message or "Open the marketplace to respond.",
            link="/invitations",
            actor_id=user["id"],
            payload={"invitation_id": inv_id, "kind": payload.kind, "entity_id": payload.entity_id},
        ))
    except Exception:
        pass

    return {"id": inv_id, "ok": True}


@router.get("/invitations")
async def my_invitations(direction: Literal["sent", "received"] = "received",
                         user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    field = "to_user_id" if direction == "received" else "from_user_id"
    docs = await db.marketplace_invitations.find({field: user["id"]}).sort(
        "created_at", -1).limit(100).to_list(100)

    now = datetime.now(timezone.utc).isoformat()

    # Mark pending received invitations as viewed (first time they see them)
    if direction == "received":
        from services.notifications_service import dispatch as _dispatch, NotificationEvent as _NE
        unviewed = [d for d in docs if d.get("status") == "pending" and not d.get("viewed_at")]
        if unviewed:
            unviewed_ids = [d["_id"] for d in unviewed]
            await db.marketplace_invitations.update_many(
                {"_id": {"$in": unviewed_ids}},
                {"$set": {"viewed_at": now}},
            )
            for d in unviewed:
                try:
                    await _dispatch(_NE(
                        user_id=d["from_user_id"],
                        kind="invitation_viewed",
                        title=f"{user.get('full_name','Someone')} viewed your invitation",
                        body="They've seen your collaboration invitation.",
                        link="/invitations",
                        actor_id=user["id"],
                        payload={"invitation_id": str(d["_id"])},
                    ))
                except Exception:
                    pass

    # Decorate with counterpart profile
    other_field = "from_user_id" if direction == "received" else "to_user_id"
    ids = list({ObjectId(d[other_field]) for d in docs if d.get(other_field)})
    users_docs = await db.users.find(
        {"_id": {"$in": ids}},
        {"full_name": 1, "academic_role": 1, "user_type": 1, "institution": 1, "avatar_url": 1},
    ).to_list(len(ids)) if ids else []
    users_map = {}
    for u in users_docs:
        uid = str(u.pop("_id"))
        users_map[uid] = {**u, "id": uid}

    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        counterpart = users_map.get(d.get(other_field))
        if counterpart:
            d["counterpart"] = counterpart
        out.append(d)
    return out


@router.delete("/invitations/{inv_id}", status_code=204)
async def withdraw_invitation(inv_id: str, user: dict = Depends(get_current_user)):
    """Sender can withdraw (cancel) a pending invitation."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(inv_id)
    except Exception:
        raise HTTPException(404, "Not found")
    inv = await db.marketplace_invitations.find_one({"_id": oid})
    if not inv:
        raise HTTPException(404, "Not found")
    if inv["from_user_id"] != user["id"]:
        raise HTTPException(403, "Only the sender can withdraw")
    if inv["status"] not in ("pending",):
        raise HTTPException(409, f"Cannot withdraw a {inv['status']} invitation")
    await db.marketplace_invitations.update_one(
        {"_id": oid},
        {"$set": {"status": "withdrawn", "responded_at": datetime.now(timezone.utc).isoformat()}},
    )


class InviteDecision(BaseModel):
    decision:       Literal["accepted", "declined"]
    decline_reason: Optional[str] = Field(None, max_length=500)


@router.post("/invitations/{inv_id}/decide")
async def decide_invitation(inv_id: str, payload: InviteDecision,
                             user: dict = Depends(get_current_user)):
    from services.notifications_service import dispatch as _dispatch, NotificationEvent as _NE
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(inv_id)
    except Exception:
        raise HTTPException(404, "Not found")
    inv = await db.marketplace_invitations.find_one({"_id": oid})
    if not inv:
        raise HTTPException(404, "Not found")
    if inv["to_user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    if inv["status"] not in ("pending",):
        raise HTTPException(409, f"Invitation is already {inv['status']}")

    # Check expiry
    expires_at = inv.get("expires_at")
    if expires_at and inv["status"] == "pending":
        try:
            if datetime.fromisoformat(expires_at.replace("Z", "+00:00")) < datetime.now(timezone.utc):
                await db.marketplace_invitations.update_one({"_id": oid}, {"$set": {"status": "expired"}})
                raise HTTPException(410, "This invitation has expired.")
        except HTTPException:
            raise
        except Exception:
            pass

    now = datetime.now(timezone.utc).isoformat()
    update: dict = {
        "status": payload.decision,
        "responded_at": now,
        "decided_at": now,
    }
    if payload.decision == "declined" and payload.decline_reason:
        update["decline_reason"] = payload.decline_reason.strip()

    await db.marketplace_invitations.update_one({"_id": oid}, {"$set": update})

    # Accept side effects: add user to entity members
    if payload.decision == "accepted" and inv.get("entity_id"):
        kind = inv.get("kind")
        try:
            ent_oid = ObjectId(inv["entity_id"])
            if kind == "workspace":
                await db.workspaces.update_one({"_id": ent_oid}, {"$addToSet": {"members": user["id"]}})
            elif kind == "project":
                await db.projects.update_one({"_id": ent_oid}, {"$addToSet": {"members": user["id"]}})
            elif kind == "manuscript":
                await db.manuscripts.update_one({"_id": ent_oid}, {"$addToSet": {"authors": user["id"]}})
        except Exception as exc:
            _log.warning("Entity membership on invite accept failed: %s", exc)

        # Record team membership
        try:
            await db.team_memberships.insert_one({
                "user_id":         user["id"],
                "inviter_id":      inv["from_user_id"],
                "invitation_id":   inv_id,
                "invitation_type": inv.get("kind", "collaboration"),
                "entity_type":     inv.get("kind"),
                "entity_id":       inv.get("entity_id"),
                "role":            inv.get("role") or "member",
                "joined_at":       now,
                "created_at":      now,
            })
        except Exception as exc:
            _log.warning("team_memberships insert on marketplace accept failed: %s", exc)

        # Auto-create DM conversation
        try:
            sorted_ids = sorted([inv["from_user_id"], user["id"]])
            conv_key = f"direct:{sorted_ids[0]}:{sorted_ids[1]}"
            existing = await db.conversations.find_one({"context_key": conv_key})
            if not existing:
                conv_doc = {
                    "type": "direct", "context_id": "", "context_key": conv_key, "title": "",
                    "created_by": user["id"],
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
            _log.warning("DM creation after marketplace accept failed: %s", exc)

    # Notify sender
    try:
        status_label = "accepted" if payload.decision == "accepted" else "declined"
        notif_body = payload.decline_reason or f"Invitation {payload.decision}"
        await _dispatch(_NE(
            user_id=inv["from_user_id"],
            kind="invitation_decision",
            title=f"{user.get('full_name','Someone')} {status_label} your invitation",
            body=notif_body[:200],
            link="/invitations",
            actor_id=user["id"],
            payload={"invitation_id": inv_id, "decision": payload.decision},
        ))
    except Exception:
        pass

    return {"ok": True, "status": payload.decision}


# ============================== ANALYTICS ==================================
@router.get("/analytics")
async def my_analytics(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    sent       = await db.marketplace_invitations.count_documents({"from_user_id": user["id"]})
    accepted   = await db.marketplace_invitations.count_documents(
        {"from_user_id": user["id"], "status": "accepted"})
    received   = await db.marketplace_invitations.count_documents({"to_user_id": user["id"]})
    rec_accept = await db.marketplace_invitations.count_documents(
        {"to_user_id": user["id"], "status": "accepted"})
    reviews_done = await db.reviews.count_documents(
        {"reviewer_id": user["id"], "status": {"$in": ["completed", "submitted"]}})
    req_fulfilled = await db.expertise_requests.count_documents(
        {"owner_id": user["id"], "status": "filled"})
    return {
        "invitations_sent": sent,
        "invitations_accepted": accepted,
        "invitations_received": received,
        "invitations_received_accepted": rec_accept,
        "collaboration_success_rate": round((accepted / sent) if sent else 0.0, 2),
        "reviews_completed": reviews_done,
        "expertise_requests_fulfilled": req_fulfilled,
    }


# ============================== ROLES META =================================
@router.get("/roles")
async def list_roles():
    return {"roles": ROLES}
