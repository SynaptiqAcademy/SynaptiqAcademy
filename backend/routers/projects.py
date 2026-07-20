import asyncio
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends

from auth_utils import get_current_user
from db import get_db
from models import ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate, MilestoneCreate, LiteratureCreate
from services.permissions import assert_quota
from repo.shim import DBProxy
from repo.security_context import SecurityContext

def _emit_rep(user_id, event_type, entity_id, description=None):
    async def _task():
        try:
            from services.reputation.events import emit_reputation_event
            await emit_reputation_event(user_id, event_type, "project", entity_id, description)
        except Exception:
            pass
    import asyncio as _aio
    try:
        _aio.ensure_future(_task())
    except RuntimeError:
        pass

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


def _now():
    return datetime.now(timezone.utc).isoformat()


async def _assert_project_member(db, project_id: str, user_id: str) -> dict:
    """Raise 403/404 unless user is a member or owner of the project."""
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Project not found")
    doc = await db.projects.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if user_id not in doc.get("members", []) and doc.get("owner_id") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return doc


@router.get("")
async def list_projects(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.projects.find(
        {"$or": [{"owner_id": user["id"]}, {"members": user["id"]}, {"visibility": "public"}],
         "is_demo": {"$ne": True}}
    ).sort("created_at", -1).to_list(200)
    return [_ser(d) for d in docs]


@router.post("")
async def create_project(payload: ProjectCreate, user: dict = Depends(get_current_user)):
    await assert_quota(user, "projects")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "title": payload.title,
        "description": payload.description or "",
        "visibility": payload.visibility,
        "owner_id": user["id"],
        "members": [user["id"]],
        "problem_statement": "",
        "research_gap": payload.research_gap or "",
        "objectives": payload.objectives or [],
        "research_questions": payload.research_questions or [],
        "hypotheses": payload.hypotheses or [],
        "expected_contributions": "",
        "methodology": payload.methodology or "",
        "data_sources": "",
        "sampling": "",
        "analysis_methods": "",
        "ethics": "",
        "keywords": payload.keywords or [],
        "source": payload.source,
        "created_at": _now(),
    }
    result = await db.projects.insert_one(doc)
    doc["_id"] = result.inserted_id
    proj_id = str(result.inserted_id)

    _emit_rep(user["id"], "project_created", proj_id)

    # Auto-send collaboration requests to initial members
    if payload.initial_member_ids:
        from services.notifications_service import dispatch, NotificationEvent
        for mid in (payload.initial_member_ids or []):
            if mid == user["id"]:
                continue
            try:
                await db.collaboration_requests.insert_one({
                    "sender_id":    user["id"],
                    "receiver_id":  mid,
                    "message":      f"You've been invited to join the project: {payload.title}",
                    "project_id":   proj_id,
                    "project_title": payload.title,
                    "source":       payload.source or "manual",
                    "context":      {},
                    "status":       "pending",
                    "created_at":   _now(),
                    "updated_at":   _now(),
                })
                await dispatch(NotificationEvent(
                    user_id=mid,
                    kind="collaboration_request",
                    title=f"{user.get('full_name', 'A researcher')} invited you to a project",
                    body=f"Project: {payload.title}",
                    link="/collaboration-requests",
                    actor_id=user["id"],
                    payload={"project_id": proj_id},
                ))
            except Exception:
                pass

    return _ser(doc)


@router.get("/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc["visibility"] != "public" and user["id"] not in doc.get("members", []) and doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    project = _ser(doc)
    # enrich members
    member_ids = [ObjectId(m) for m in project.get("members", [])]
    members = await db.users.find({"_id": {"$in": member_ids}}).to_list(50)
    project["members_info"] = [
        {"id": str(m["_id"]), "full_name": m.get("full_name"), "academic_role": m.get("academic_role"),
         "institution": m.get("institution"), "avatar_url": m.get("avatar_url")}
        for m in members
    ]
    return project


@router.patch("/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.projects.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if user["id"] not in doc.get("members", []) and doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    # Only the project owner may change visibility
    if "visibility" in update and doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the project owner can change visibility.")
    if update:
        await db.projects.update_one({"_id": oid}, {"$set": update})
        # Emit project_completed when status transitions to "completed"
        if update.get("status") == "completed" and doc.get("status") != "completed":
            _emit_rep(user["id"], "project_completed", project_id)
    new_doc = await db.projects.find_one({"_id": oid})
    return _ser(new_doc)


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    """Hard-delete a project and all sub-resources. Only the project owner may delete."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.projects.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the project owner can delete this project")

    # Parallel cascade: remove all sub-resources and membership references
    await asyncio.gather(
        db.tasks.delete_many({"project_id": project_id}),
        db.milestones.delete_many({"project_id": project_id}),
        db.literature.delete_many({"project_id": project_id}),
        db.collaboration_requests.delete_many({"project_id": project_id}),
        db.workspace_activity.delete_many({"project_id": project_id}),
        # Remove project from any workspace's project_ids array
        db.workspaces.update_many(
            {"project_ids": project_id},
            {"$pull": {"project_ids": project_id}},
        ),
        # Delete context conversation + members for this project
        db.conversations.delete_many({"context_key": f"project:{project_id}"}),
    )
    # Delete members for those conversations (conversation_id not easy to filter without a lookup,
    # so we target by context_key indirectly — clean up stale membership after conv delete)
    deleted_conv = await db.conversations.find_one({"context_id": project_id, "type": "project"})
    if deleted_conv:
        await db.conversation_members.delete_many({"conversation_id": str(deleted_conv["_id"])})
        await db.messages.delete_many({"conversation_id": str(deleted_conv["_id"])})

    await db.projects.delete_one({"_id": oid})
    return {"ok": True, "deleted": project_id}


# Tasks
@router.get("/{project_id}/tasks")
async def list_tasks(project_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_project_member(db, project_id, user["id"])
    docs = await db.tasks.find({"project_id": project_id}).sort("created_at", -1).to_list(200)
    return [_ser(d) for d in docs]


@router.post("/{project_id}/tasks")
async def create_task(project_id: str, payload: TaskCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_project_member(db, project_id, user["id"])
    doc = payload.model_dump()
    doc.update({"project_id": project_id, "created_by": user["id"], "created_at": _now()})
    result = await db.tasks.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _ser(doc)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    task = await db.tasks.find_one({"_id": oid})
    if not task:
        raise HTTPException(status_code=404, detail="Not found")
    await _assert_project_member(db, task["project_id"], user["id"])
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if update:
        await db.tasks.update_one({"_id": oid}, {"$set": update})
    doc = await db.tasks.find_one({"_id": oid})
    return _ser(doc)


# Milestones
@router.get("/{project_id}/milestones")
async def list_milestones(project_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_project_member(db, project_id, user["id"])
    docs = await db.milestones.find({"project_id": project_id}).sort("due_date", 1).to_list(100)
    return [_ser(d) for d in docs]


@router.post("/{project_id}/milestones")
async def create_milestone(project_id: str, payload: MilestoneCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_project_member(db, project_id, user["id"])
    doc = payload.model_dump()
    doc.update({"project_id": project_id, "completed": False, "created_at": _now()})
    result = await db.milestones.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _ser(doc)


# Literature
@router.get("/{project_id}/literature")
async def list_literature(project_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_project_member(db, project_id, user["id"])
    docs = await db.literature.find({"project_id": project_id}).sort("created_at", -1).to_list(200)
    return [_ser(d) for d in docs]


@router.post("/{project_id}/literature")
async def add_literature(project_id: str, payload: LiteratureCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await _assert_project_member(db, project_id, user["id"])
    doc = payload.model_dump()
    doc.update({"project_id": project_id, "added_by": user["id"], "created_at": _now()})
    result = await db.literature.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _ser(doc)


# ── Team Intelligence ─────────────────────────────────────────────────────────

_ROLE_KEYWORDS = {
    "Principal Investigator": ["professor", "associate professor", "principal investigator", "pi", "director"],
    "Co-Investigator": ["associate professor", "assistant professor", "co-investigator", "senior researcher"],
    "Methodology Lead": ["methodology", "research design", "qualitative", "quantitative", "mixed methods", "sem", "grounded theory"],
    "Data Analysis Lead": ["data analysis", "statistics", "spss", "r software", "stata", "machine learning", "python", "data science", "econometrics"],
    "Literature Review Lead": ["literature review", "systematic review", "meta-analysis", "bibliometrics", "scoping review"],
    "Grant Writing Lead": ["grant writing", "funding", "proposal writing", "research funding", "grant", "horizon europe", "nsf"],
}

_STANDARD_EXPERTISE = [
    "Statistical Analysis",
    "Machine Learning / AI",
    "Research Methodology",
    "Literature Review",
    "Grant Writing",
    "Data Collection",
    "Public Health",
    "Ethics & Compliance",
    "Qualitative Research",
    "Quantitative Research",
]

_EXPERTISE_KEYWORDS = {
    "Statistical Analysis": ["statistics", "data analysis", "spss", "r software", "stata", "quantitative", "regression", "econometrics"],
    "Machine Learning / AI": ["machine learning", "deep learning", "ai", "artificial intelligence", "nlp", "neural network", "python"],
    "Research Methodology": ["methodology", "research design", "sem", "grounded theory", "mixed methods"],
    "Literature Review": ["literature review", "systematic review", "meta-analysis", "scoping"],
    "Grant Writing": ["grant writing", "proposal", "funding", "grant", "horizon"],
    "Data Collection": ["survey", "interview", "data collection", "fieldwork", "ethnography", "questionnaire"],
    "Public Health": ["public health", "epidemiology", "health", "clinical", "medicine", "nursing"],
    "Ethics & Compliance": ["ethics", "irb", "gdpr", "compliance", "bioethics"],
    "Qualitative Research": ["qualitative", "grounded theory", "thematic analysis", "ethnography", "interview"],
    "Quantitative Research": ["quantitative", "statistics", "regression", "experiment", "anova", "sem"],
}


def _member_skill_tokens(member: dict) -> set:
    """Flatten all skill-bearing fields into a lowercase token set."""
    tokens = set()
    for field in ("skills", "research_areas", "research_keywords", "research_interests"):
        for item in (member.get(field) or []):
            tokens.update(t.lower() for t in str(item).split())
    if member.get("academic_role"):
        tokens.update(member["academic_role"].lower().split())
    return tokens


def _assign_roles(members_full: list) -> list:
    """Assign one of the six standard roles to each team member based on profile."""
    assignments = {}
    role_assigned = set()

    # Owner → PI by default if no better signal
    owner_idx = 0

    # Score each member against each role
    member_scores = []
    for idx, m in enumerate(members_full):
        tokens = _member_skill_tokens(m)
        role_scores = {}
        for role, keywords in _ROLE_KEYWORDS.items():
            role_scores[role] = sum(1 for kw in keywords if any(kw in t for t in tokens) or kw in " ".join(tokens))
        member_scores.append((idx, m, role_scores))

    # Greedy assignment: highest score wins each role
    role_order = list(_ROLE_KEYWORDS.keys())
    for role in role_order:
        best_idx = None
        best_score = -1
        for idx, m, scores in member_scores:
            if idx in role_assigned:
                continue
            if scores[role] > best_score:
                best_score = scores[role]
                best_idx = idx
        if best_idx is not None and best_score > 0:
            assignments[best_idx] = role
            role_assigned.add(best_idx)

    # Any unassigned member gets "Team Member"
    result = []
    for idx, m in enumerate(members_full):
        result.append({
            "id":           str(m["_id"]),
            "full_name":    m.get("full_name") or "",
            "academic_role": m.get("academic_role") or "",
            "institution":  m.get("institution") or "",
            "avatar_url":   m.get("avatar_url"),
            "recommended_role": assignments.get(idx, "Team Member"),
            "role_confidence": "high" if idx in assignments else "low",
        })
    return result


def _detect_expertise(members_full: list) -> tuple[list, list]:
    """Return (covered_expertise, missing_expertise)."""
    covered = set()
    all_tokens = set()
    for m in members_full:
        all_tokens.update(_member_skill_tokens(m))

    for expertise, keywords in _EXPERTISE_KEYWORDS.items():
        if any(kw in " ".join(all_tokens) for kw in keywords):
            covered.add(expertise)

    missing = [e for e in _STANDARD_EXPERTISE if e not in covered]
    return list(covered), missing


@router.get("/{project_id}/role-recommendations")
async def get_role_recommendations(project_id: str, user: dict = Depends(get_current_user)):
    """Analyse team profiles and recommend a standard role for each member."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    except Exception:
        raise HTTPException(404, "Not found")
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["visibility"] != "public" and user["id"] not in doc.get("members", []) and doc["owner_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")

    member_ids = [ObjectId(mid) for mid in (doc.get("members") or [])]
    members_full = await db.users.find({"_id": {"$in": member_ids}}).to_list(50)

    return {"roles": _assign_roles(members_full)}


@router.get("/{project_id}/team-analysis")
async def get_team_analysis(project_id: str, user: dict = Depends(get_current_user)):
    """Detect expertise gaps and recommend researchers for missing areas."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    except Exception:
        raise HTTPException(404, "Not found")
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["visibility"] != "public" and user["id"] not in doc.get("members", []) and doc["owner_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")

    member_ids = [ObjectId(mid) for mid in (doc.get("members") or [])]
    members_full = await db.users.find({"_id": {"$in": member_ids}}).to_list(50)

    covered, missing = _detect_expertise(members_full)
    member_id_strs = {str(m["_id"]) for m in members_full}

    # For each missing expertise, find top 3 platform researchers who have it
    suggestions = []
    for expertise in missing[:5]:  # Limit to top 5 gaps
        keywords = _EXPERTISE_KEYWORDS.get(expertise, [])
        if not keywords:
            continue

        # Build a regex-based search across skill fields
        regex_patterns = [{"research_areas": {"$regex": kw, "$options": "i"}} for kw in keywords[:3]]
        skill_patterns = [{"skills": {"$regex": kw, "$options": "i"}} for kw in keywords[:3]]
        kw_patterns = [{"research_keywords": {"$regex": kw, "$options": "i"}} for kw in keywords[:3]]

        candidates = await db.users.find(
            {
                "_id": {"$nin": [ObjectId(mid) for mid in member_id_strs]},
                "onboarding_complete": True,
                "is_demo": {"$ne": True},
                "$or": regex_patterns + skill_patterns + kw_patterns,
            },
            {"full_name": 1, "academic_role": 1, "institution": 1, "avatar_url": 1, "research_areas": 1},
        ).limit(3).to_list(3)

        suggestions.append({
            "expertise":    expertise,
            "researchers":  [
                {
                    "id":           str(c["_id"]),
                    "full_name":    c.get("full_name") or "",
                    "academic_role": c.get("academic_role") or "",
                    "institution":  c.get("institution") or "",
                    "avatar_url":   c.get("avatar_url"),
                    "research_areas": c.get("research_areas") or [],
                }
                for c in candidates
            ],
        })

    return {
        "covered_expertise": covered,
        "missing_expertise": missing,
        "suggestions":       suggestions,
        "team_size":         len(member_ids),
    }
