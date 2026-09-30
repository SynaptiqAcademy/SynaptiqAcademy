"""P1 Phase 8F — Interdisciplinary Research Team Builder.

Research Need -> Team Blueprint -> real Synaptiq candidates per role ->
user-selected team -> individual Phase 8E collaboration requests. Every
invitation is sent by calling routers.collaboration_requests.send_request()
directly — this router never writes to the collaboration_requests
collection itself, so every Phase 8E protection (authorization, blocking,
demo rejection, context-scoped deduplication, rate limiting, notifications)
applies with zero duplication.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy, DBProxy
from repo.security_context import SecurityContext
from plans_catalogue import CREDIT_COSTS
from services.credits_service import consume_credits, refund_credits
from services.research_need.models import ResearchNeed
from services.research_need.relevance import find_relevant_people
from services.team_builder.blueprint_generator import generate_blueprint_roles, CREDIT_ACTION
from services.team_builder.models import TeamRole, PRIORITIES, CATEGORIES
from routers.collaboration_requests import send_request as _send_collab_request, SendRequestBody

router = APIRouter(prefix="/api/team-builder", tags=["team-builder"])


def _uid(user) -> str:
    return str(user["id"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(doc: dict) -> dict:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    return d


class CreateBlueprintRequest(BaseModel):
    need: ResearchNeed
    use_ai: bool = True


class RoleEdit(BaseModel):
    role_id: Optional[str] = None  # omitted/None = add a new role
    label: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    required_expertise: Optional[list[str]] = None
    useful_methods: Optional[list[str]] = None
    useful_tools: Optional[list[str]] = None
    relevant_disciplines: Optional[list[str]] = None
    why_needed: Optional[str] = None
    priority: Optional[str] = None
    self_covers: Optional[bool] = None


class PatchBlueprintRequest(BaseModel):
    role_edits: list[RoleEdit] = Field(default_factory=list)
    remove_role_ids: list[str] = Field(default_factory=list)


class InviteCandidateRequest(BaseModel):
    collaboration_purpose: Optional[str] = None
    expected_contribution: Optional[str] = None
    message: str = ""


async def _get_owned_blueprint(db, blueprint_id: str, uid: str) -> dict:
    try:
        oid = ObjectId(blueprint_id)
    except Exception:
        raise HTTPException(404, "Team blueprint not found.")
    bp = await db.team_blueprints.find_one({"_id": oid})
    if not bp:
        raise HTTPException(404, "Team blueprint not found.")
    if bp["owner_id"] != uid:
        raise HTTPException(403, "Forbidden.")
    return bp


_CROSS_ROLE_FIELDS = (
    "research_areas", "research_interests", "research_keywords",
    "methods", "software_skills", "professional_expertise", "professional_role",
)


def _term_matches(term: str, value: str) -> bool:
    t, v = term.strip().lower(), (value or "").strip().lower()
    return bool(t) and bool(v) and (t in v or v in t)


def _candidate_field_values(card: dict) -> set[str]:
    """Raw profile field values for cross-role hinting (§13) — deliberately
    NOT card['evidence'], which only reflects the terms of the ONE role
    find_relevant_people was scoped to; a cross-role check needs the
    candidate's actual profile, not another role's narrower evidence list."""
    values: set[str] = set()
    for field in _CROSS_ROLE_FIELDS:
        v = card.get(field)
        if isinstance(v, list):
            values.update(x.lower() for x in v if x)
        elif v:
            values.add(str(v).lower())
    return values


def _role_pseudo_need(role: dict, original_query: str) -> ResearchNeed:
    """A role's own expertise fields, reframed as a ResearchNeed so
    services/research_need/relevance.py's retrieval+evidence+grouping logic
    can be reused verbatim per role — no second matching engine (§9/§16/§17)."""
    return ResearchNeed(
        original_query=original_query,
        required_expertise=role.get("required_expertise") or [],
        complementary_expertise=role.get("relevant_disciplines") or [],
        useful_methods=role.get("useful_methods") or [],
        useful_software_or_tools=role.get("useful_tools") or [],
    )


async def _live_candidate_statuses(db, request_ids: list[str]) -> dict:
    """One batched query for every collaboration_request referenced across
    all roles — never one lookup per candidate (§46)."""
    if not request_ids:
        return {}
    oids = [ObjectId(r) for r in request_ids if ObjectId.is_valid(r)]
    if not oids:
        return {}
    docs = await db.collaboration_requests.find(
        {"_id": {"$in": oids}}, {"status": 1}
    ).to_list(len(oids))
    return {str(d["_id"]): d.get("status") for d in docs}


_STATUS_MAP = {
    None: "proposed",
    "pending": "invitation_pending",
    "viewed": "invitation_pending",
    "accepted": "accepted",
    "declined": "declined",
    "withdrawn": "withdrawn",
    "cancelled": "withdrawn",
    "expired": "withdrawn",
}


async def _enrich_blueprint(db, bp: dict) -> dict:
    """Live-syncs every selected candidate's status from the canonical
    collaboration_requests collection (§24/§25/§28) — never stale, never a
    duplicated status field trusted on its own."""
    request_ids = [
        c.get("collaboration_request_id")
        for role in bp.get("roles", [])
        for c in role.get("selected_candidates", [])
        if c.get("collaboration_request_id")
    ]
    statuses = await _live_candidate_statuses(db, request_ids)

    # One batched name/avatar lookup for every distinct candidate across all
    # roles — never one query per candidate. Only the same safe fields
    # discovery already serializes publicly (§38).
    candidate_ids = {
        c["candidate_id"]
        for role in bp.get("roles", []) for c in role.get("selected_candidates", [])
    }
    names: dict = {}
    if candidate_ids:
        oids = [ObjectId(i) for i in candidate_ids if ObjectId.is_valid(i)]
        docs = await db.users.find({"_id": {"$in": oids}}, {"full_name": 1, "avatar_url": 1}).to_list(len(oids))
        names = {str(d["_id"]): {"full_name": d.get("full_name") or "", "avatar_url": d.get("avatar_url")} for d in docs}

    out = _ser(bp)
    for role in out.get("roles", []):
        for c in role.get("selected_candidates", []):
            rid = c.get("collaboration_request_id")
            c["status"] = _STATUS_MAP.get(statuses.get(rid), "proposed") if rid else "proposed"
            info = names.get(c["candidate_id"], {})
            c["candidate_name"] = info.get("full_name", "")
            c["candidate_avatar_url"] = info.get("avatar_url")
    return out


@router.get("/cost")
async def blueprint_cost():
    """Cost shown BEFORE the user commits to AI blueprint generation (§36)."""
    return {"action": CREDIT_ACTION, "cost": CREDIT_COSTS.get(CREDIT_ACTION, 0)}


@router.post("/blueprints")
async def create_blueprint(
    payload: CreateBlueprintRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Research Need -> proposed Team Blueprint (§2). Charges credits only
    for a real AI generation attempt, refunded immediately on fallback —
    same pattern as research_need/interpret (§36)."""
    db = make_db_proxy(db, user)
    uid = _uid(user)

    charged = None
    if payload.use_ai:
        charged = await consume_credits(uid, CREDIT_ACTION, metadata={})

    roles, meta = await generate_blueprint_roles(payload.need, use_ai=payload.use_ai, user_id=uid, db=db)

    if payload.use_ai and meta["source"] != "ai":
        await refund_credits(uid, CREDIT_ACTION, reason=meta.get("reason") or "ai_blueprint_fallback")
        charged = None

    now = _now()
    doc = {
        "owner_id": uid,
        "research_need": payload.need.model_dump(),
        "roles": [r.model_dump() for r in roles],
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.team_blueprints.insert_one(doc)
    doc["_id"] = result.inserted_id

    return {
        "blueprint": await _enrich_blueprint(db, doc),
        "source": meta["source"],
        "credits_consumed": charged["consumed"] if charged else 0,
    }


@router.get("/blueprints")
async def list_blueprints(db=Depends(get_db), user=Depends(get_current_user)):
    """Sent-view-style list — lightweight, no per-role candidate retrieval."""
    db = make_db_proxy(db, user)
    uid = _uid(user)
    docs = await db.team_blueprints.find({"owner_id": uid}).sort("updated_at", -1).to_list(100)
    return [
        {
            "id": str(d["_id"]),
            "status": d.get("status"),
            "original_query": (d.get("research_need") or {}).get("original_query", ""),
            "role_count": len(d.get("roles", [])),
            "created_at": d.get("created_at"),
            "updated_at": d.get("updated_at"),
        }
        for d in docs
    ]


@router.get("/blueprints/{blueprint_id}")
async def get_blueprint(blueprint_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    bp = await _get_owned_blueprint(db, blueprint_id, _uid(user))
    return await _enrich_blueprint(db, bp)


@router.delete("/blueprints/{blueprint_id}")
async def delete_blueprint(blueprint_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    """Deletes the draft only — never touches any collaboration_requests
    already sent from it; those remain visible/actionable in
    CollaborationRequests.jsx regardless (§29 — IDs, not duplicated state)."""
    db = make_db_proxy(db, user)
    uid = _uid(user)
    bp = await _get_owned_blueprint(db, blueprint_id, uid)
    await db.team_blueprints.delete_one({"_id": bp["_id"]})
    return {"ok": True}


@router.patch("/blueprints/{blueprint_id}")
async def patch_blueprint(
    blueprint_id: str, payload: PatchBlueprintRequest,
    db=Depends(get_db), user=Depends(get_current_user),
):
    """Add/remove/rename/re-prioritize roles, edit expertise/methods, and
    toggle 'I can cover this role' (§6/§7). Never touches
    selected_candidates — that has its own dedicated endpoints so an edit
    here can never accidentally clobber a live invitation reference."""
    db = make_db_proxy(db, user)
    uid = _uid(user)
    bp = await _get_owned_blueprint(db, blueprint_id, uid)

    roles = bp.get("roles", [])
    by_id = {r["role_id"]: r for r in roles}

    for rid in payload.remove_role_ids:
        by_id.pop(rid, None)

    import uuid
    for edit in payload.role_edits:
        if edit.priority is not None and edit.priority not in PRIORITIES:
            raise HTTPException(400, f"Invalid priority. Must be one of: {', '.join(sorted(PRIORITIES))}")
        if edit.category is not None and edit.category not in CATEGORIES:
            raise HTTPException(400, f"Invalid category. Must be one of: {', '.join(sorted(CATEGORIES))}")

        if edit.role_id and edit.role_id in by_id:
            role = by_id[edit.role_id]
            for field in ("label", "category", "description", "required_expertise",
                          "useful_methods", "useful_tools", "relevant_disciplines",
                          "why_needed", "priority", "self_covers"):
                v = getattr(edit, field)
                if v is not None:
                    role[field] = v
        else:
            if not edit.label:
                raise HTTPException(400, "A new role requires a label.")
            role = TeamRole(
                role_id=uuid.uuid4().hex[:12], label=edit.label,
                category=edit.category or "other", description=edit.description or "",
                required_expertise=edit.required_expertise or [],
                useful_methods=edit.useful_methods or [],
                useful_tools=edit.useful_tools or [],
                relevant_disciplines=edit.relevant_disciplines or [],
                why_needed=edit.why_needed or "", priority=edit.priority or "useful",
                self_covers=bool(edit.self_covers),
            ).model_dump()
            by_id[role["role_id"]] = role

    new_roles = list(by_id.values())
    await db.team_blueprints.update_one(
        {"_id": bp["_id"]}, {"$set": {"roles": new_roles, "updated_at": _now()}},
    )
    bp["roles"] = new_roles
    return await _enrich_blueprint(db, bp)


@router.get("/blueprints/{blueprint_id}/roles/{role_id}/candidates")
async def get_role_candidates(
    blueprint_id: str, role_id: str,
    db=Depends(get_db), user=Depends(get_current_user),
):
    """Real, eligible Synaptiq candidates for one role (§9/§10/§11) — lazy,
    on-demand per role, never fetched for every role up front (§47)."""
    db = make_db_proxy(db, user)
    uid = _uid(user)
    bp = await _get_owned_blueprint(db, blueprint_id, uid)
    role = next((r for r in bp["roles"] if r["role_id"] == role_id), None)
    if not role:
        raise HTTPException(404, "Role not found.")

    pseudo_need = _role_pseudo_need(role, bp.get("research_need", {}).get("original_query", ""))
    result = await find_relevant_people(db, pseudo_need, viewer_id=uid)

    already_selected = {c["candidate_id"] for c in role.get("selected_candidates", [])}
    candidates = []
    for group_name, group in (
        ("directly_relevant", result["similar"]), ("complementary_expertise", result["complementary"]),
        ("methods_specialist", result["methods_specialists"]), ("context_specialist", result["context_specialists"]),
    ):
        for c in group:
            card = dict(c)
            card["already_selected"] = card["id"] in already_selected
            # §13 — cross-role hint: does this same candidate's actual
            # profile also match a DIFFERENT role's terms?
            candidate_values = _candidate_field_values(card)
            also_relevant_to = []
            for other in bp["roles"]:
                if other["role_id"] == role_id:
                    continue
                other_terms = (
                    other.get("required_expertise", []) + other.get("useful_methods", [])
                    + other.get("relevant_disciplines", []) + other.get("useful_tools", [])
                )
                if any(_term_matches(t, v) for t in other_terms for v in candidate_values):
                    also_relevant_to.append(other["label"])
            card["also_relevant_to"] = also_relevant_to
            candidates.append(card)

    return {
        "role_id": role_id, "candidates": candidates,
        "missing_expertise": result["missing_expertise"],
    }


@router.post("/blueprints/{blueprint_id}/roles/{role_id}/candidates/{candidate_id}/select")
async def select_candidate(
    blueprint_id: str, role_id: str, candidate_id: str,
    db=Depends(get_db), user=Depends(get_current_user),
):
    """'Add to proposed team' (§9) — selection is NOT outreach; no
    invitation is sent here. Re-verifies eligibility/evidence at selection
    time by re-running the same real retrieval, rather than trusting a
    client-supplied id blindly."""
    db = make_db_proxy(db, user)
    uid = _uid(user)
    bp = await _get_owned_blueprint(db, blueprint_id, uid)
    role = next((r for r in bp["roles"] if r["role_id"] == role_id), None)
    if not role:
        raise HTTPException(404, "Role not found.")
    if candidate_id == uid:
        raise HTTPException(400, "Use 'I can cover this role' instead of selecting yourself as a candidate.")
    if any(c["candidate_id"] == candidate_id for c in role.get("selected_candidates", [])):
        return await _enrich_blueprint(db, bp)  # idempotent — already selected

    pseudo_need = _role_pseudo_need(role, bp.get("research_need", {}).get("original_query", ""))
    result = await find_relevant_people(db, pseudo_need, viewer_id=uid)
    all_candidates = result["similar"] + result["complementary"] + result["methods_specialists"] + result["context_specialists"]
    match = next((c for c in all_candidates if c["id"] == candidate_id), None)
    if not match:
        raise HTTPException(404, "This candidate is not currently eligible or relevant for this role.")

    selected = {
        "candidate_id": candidate_id,
        "evidence": match.get("evidence", []),
        "contribution": match.get("contribution", []),
        "explanation": match.get("explanation", ""),
        "selected_at": _now(),
        "collaboration_request_id": None,
    }
    role.setdefault("selected_candidates", []).append(selected)
    await db.team_blueprints.update_one(
        {"_id": bp["_id"], "roles.role_id": role_id},
        {"$set": {"roles.$.selected_candidates": role["selected_candidates"], "updated_at": _now()}},
    )
    return await _enrich_blueprint(db, bp)


@router.delete("/blueprints/{blueprint_id}/roles/{role_id}/candidates/{candidate_id}")
async def unselect_candidate(
    blueprint_id: str, role_id: str, candidate_id: str,
    db=Depends(get_db), user=Depends(get_current_user),
):
    """Remove a proposed (not-yet-invited) candidate, or clear a
    declined/withdrawn one to make room for 'Find another collaborator'
    (§26). Does not touch an already-sent Phase 8E request — withdrawing an
    actual invitation is Phase 8E's own action (Cancel/Withdraw in
    CollaborationRequests.jsx), not duplicated here."""
    db = make_db_proxy(db, user)
    uid = _uid(user)
    bp = await _get_owned_blueprint(db, blueprint_id, uid)
    role = next((r for r in bp["roles"] if r["role_id"] == role_id), None)
    if not role:
        raise HTTPException(404, "Role not found.")

    target = next((c for c in role.get("selected_candidates", []) if c["candidate_id"] == candidate_id), None)
    if target and target.get("collaboration_request_id"):
        raise HTTPException(
            409,
            "This candidate already has a pending or resolved invitation. "
            "Cancel or withdraw it from Collaboration Requests first.",
        )
    role["selected_candidates"] = [c for c in role.get("selected_candidates", []) if c["candidate_id"] != candidate_id]
    await db.team_blueprints.update_one(
        {"_id": bp["_id"], "roles.role_id": role_id},
        {"$set": {"roles.$.selected_candidates": role["selected_candidates"], "updated_at": _now()}},
    )
    return await _enrich_blueprint(db, bp)


@router.post("/blueprints/{blueprint_id}/roles/{role_id}/candidates/{candidate_id}/invite")
async def invite_candidate(
    blueprint_id: str, role_id: str, candidate_id: str,
    payload: InviteCandidateRequest,
    db=Depends(get_db), user=Depends(get_current_user),
):
    """Send ONE Phase 8E collaboration request for this candidate (§21/§22/
    §23). Reuses routers.collaboration_requests.send_request() directly —
    every authorization/blocking/demo-rejection/dedup/rate-limit/
    notification rule in Phase 8E applies unmodified. Each call is one
    individual, explicitly user-approved invitation — there is no bulk-send
    endpoint anywhere in this router."""
    uid = _uid(user)
    bp = await _get_owned_blueprint(make_db_proxy(db, user), blueprint_id, uid)
    role = next((r for r in bp["roles"] if r["role_id"] == role_id), None)
    if not role:
        raise HTTPException(404, "Role not found.")
    selected = next((c for c in role.get("selected_candidates", []) if c["candidate_id"] == candidate_id), None)
    if not selected:
        raise HTTPException(404, "This candidate has not been selected for this role yet.")
    if selected.get("collaboration_request_id"):
        raise HTTPException(409, "An invitation has already been sent to this candidate for this role.")

    topic = (bp.get("research_need") or {}).get("concise_problem_statement") or (bp.get("research_need") or {}).get("original_query") or ""
    req = await _send_collab_request(
        SendRequestBody(
            receiver_id=candidate_id,
            message=payload.message,
            source="team_builder",
            invitation_type="research_collaboration",
            collaboration_purpose=payload.collaboration_purpose,
            expected_contribution=payload.expected_contribution or (selected.get("contribution") or [None])[0],
            context={"research_need_topic": topic, "team_role": role["label"]} if topic else {"team_role": role["label"]},
        ),
        user=user,
    )

    selected["collaboration_request_id"] = req["id"]
    dbp = make_db_proxy(db, user)
    await dbp.team_blueprints.update_one(
        {"_id": bp["_id"], "roles.role_id": role_id},
        {"$set": {"roles.$.selected_candidates": role["selected_candidates"], "status": "inviting", "updated_at": _now()}},
    )
    bp["status"] = "inviting"
    return await _enrich_blueprint(dbp, bp)
