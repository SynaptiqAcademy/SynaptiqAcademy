"""Teaching Hub API — Lesson Planner, Assessment Builder, Portfolio, Workspaces, AI Teaching Assistant.

Phase 8: Full collaborative workspace model with roles, invitations, activity, comments, version history.

Collections:
  teaching_lessons               — structured lesson plans
  teaching_assessments           — assessments, quizzes, rubrics
  teaching_portfolio_items       — portfolio evidence items
  teaching_workspaces            — course-level collaborative spaces (Phase 8: multi-member, role-based)
  teaching_chat_messages         — AI assistant message history per workspace/user
  teaching_workspace_invitations — pending/accepted/declined workspace invitations
  teaching_workspace_activity    — workspace activity feed
  teaching_workspace_comments    — threaded comments on workspace/lessons/assessments
  teaching_lesson_versions       — version history snapshots for lessons
  teaching_assessment_versions   — version history snapshots for assessments

Roles (workspace_owner > course_lead > co_instructor > teaching_assistant > reviewer > observer)
Permissions enforced per endpoint via _assert_perm().
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.ai.llm import call_llm
from services.credits_service import consume_credits, refund_credits
from services.notifications_service import dispatch, NotificationEvent, register_default_providers
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.teaching")
router = APIRouter(prefix="/api/teaching", tags=["teaching"])

def _emit_rep(user_id, event_type, entity_id, description=None):
    async def _task():
        try:
            from services.reputation.events import emit_reputation_event
            await emit_reputation_event(user_id, event_type, "teaching", entity_id, description)
        except Exception:
            pass
    try:
        asyncio.ensure_future(_task())
    except RuntimeError:
        pass

LEVEL_OPTIONS = ["secondary", "undergraduate", "graduate", "professional", "adult", "other"]
ASSESSMENT_TYPES = ["quiz", "exam", "rubric", "assignment", "reflection", "presentation"]
QUESTION_TYPES   = ["multiple_choice", "short_answer", "essay", "true_false"]
PORTFOLIO_TYPES  = ["lesson", "course", "assessment", "achievement", "award", "reflection", "resource", "publication"]


# ──────────────────────────────── helpers ─────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


def _oid(raw: str) -> ObjectId:
    try:
        return ObjectId(raw)
    except Exception:
        raise HTTPException(404, "Not found")


# ────────────────────────────── roles & permissions ───────────────────────────

ROLES = ["workspace_owner", "course_lead", "co_instructor", "teaching_assistant", "reviewer", "observer"]

_PERMS: dict[str, set[str]] = {
    "delete_workspace":   {"workspace_owner"},
    "update_settings":    {"workspace_owner"},
    "manage_roles":       {"workspace_owner"},
    "invite_member":      {"workspace_owner", "course_lead"},
    "remove_member":      {"workspace_owner", "course_lead"},
    "manage_lessons":     {"workspace_owner", "course_lead"},
    "manage_assessments": {"workspace_owner", "course_lead"},
    "create_lesson":      {"workspace_owner", "course_lead", "co_instructor"},
    "edit_lesson":        {"workspace_owner", "course_lead", "co_instructor"},
    "create_assessment":  {"workspace_owner", "course_lead", "co_instructor"},
    "edit_assessment":    {"workspace_owner", "course_lead", "co_instructor"},
    "contribute":         {"workspace_owner", "course_lead", "co_instructor", "teaching_assistant"},
    "comment":            {"workspace_owner", "course_lead", "co_instructor", "teaching_assistant", "reviewer"},
    "use_ai":             {"workspace_owner", "course_lead", "co_instructor", "teaching_assistant"},
    "view":               {"workspace_owner", "course_lead", "co_instructor", "teaching_assistant", "reviewer", "observer"},
}


def _role(ws: dict, uid: str) -> str:
    """Return uid's role in ws, or '' if not a member."""
    roles: dict = ws.get("member_roles") or {}
    if uid in roles:
        return roles[uid]
    if uid == ws.get("owner_id"):
        return "workspace_owner"
    if uid in (ws.get("member_ids") or []):
        return "observer"
    return ""


def _can(ws: dict, uid: str, perm: str) -> bool:
    return _role(ws, uid) in _PERMS.get(perm, set())


def _assert_perm(ws: dict, uid: str, perm: str) -> None:
    if not _can(ws, uid, perm):
        raise HTTPException(403, "Insufficient permissions for this action")


def _assert_member(ws: dict, uid: str) -> None:
    if not _can(ws, uid, "view"):
        raise HTTPException(403, "Not a workspace member")


async def _log_activity(
    db, workspace_id: str, actor: dict, kind: str, message: str,
    entity_id: str | None = None, entity_type: str | None = None,
) -> None:
    try:
        await db.teaching_workspace_activity.insert_one({
            "workspace_id": workspace_id,
            "actor_id":     actor["id"],
            "actor_name":   actor.get("full_name") or "Someone",
            "kind":         kind,
            "message":      message,
            "entity_id":    entity_id,
            "entity_type":  entity_type,
            "created_at":   _now(),
        })
    except Exception as exc:
        log.warning("activity log failed: %s", exc)


def _ser_act(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


async def _capture_lesson_version(db, lesson: dict, author: dict) -> None:
    """Snapshot lesson before an update."""
    try:
        snap = dict(lesson)
        snap.pop("_id", None)
        await db.teaching_lesson_versions.insert_one({
            "lesson_id":   str(lesson["_id"]),
            "snapshot":    snap,
            "author_id":   author["id"],
            "author_name": author.get("full_name") or "Someone",
            "created_at":  _now(),
        })
    except Exception as exc:
        log.warning("lesson version capture failed: %s", exc)


async def _capture_assessment_version(db, assessment: dict, author: dict) -> None:
    """Snapshot assessment before an update."""
    try:
        snap = dict(assessment)
        snap.pop("_id", None)
        await db.teaching_assessment_versions.insert_one({
            "assessment_id": str(assessment["_id"]),
            "snapshot":      snap,
            "author_id":     author["id"],
            "author_name":   author.get("full_name") or "Someone",
            "created_at":    _now(),
        })
    except Exception as exc:
        log.warning("assessment version capture failed: %s", exc)


def _parse_llm_json(raw: str, context: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```", 2)
        inner = parts[1] if len(parts) >= 2 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
        if "```" in text:
            text = text.split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        log.error("%s JSON parse failed: %s | raw[:400]=%s", context, exc, text[:400])
        raise HTTPException(502, f"{context} returned malformed output. Please try again.")


# ──────────────────────────────── request models ──────────────────────────────

class LessonCreate(BaseModel):
    title:             str              = Field(..., min_length=3, max_length=300)
    subject:           str              = Field(..., max_length=100)
    audience:          Optional[str]    = Field(None, max_length=200)
    level:             Optional[str]    = Field(None)
    duration_minutes:  int              = Field(60, ge=5, le=480)
    learning_objectives: List[str]      = Field(default_factory=list)
    materials:         List[str]        = Field(default_factory=list)
    outline:           List[Dict]       = Field(default_factory=list)
    assessment_strategy: Optional[str] = Field(None, max_length=2000)
    differentiation_strategies: List[str] = Field(default_factory=list)
    teacher_notes:     Optional[str]    = Field(None, max_length=3000)
    tags:              List[str]        = Field(default_factory=list)
    status:            str              = Field("draft")


class LessonGenerateRequest(BaseModel):
    topic:            str           = Field(..., min_length=3, max_length=300)
    subject:          str           = Field(..., max_length=100)
    audience:         str           = Field(..., max_length=200)
    level:            str           = Field("undergraduate")
    duration_minutes: int           = Field(60, ge=15, le=480)
    objectives_count: int           = Field(4, ge=2, le=8)
    tags:             List[str]     = Field(default_factory=list)


class AssessmentCreate(BaseModel):
    title:               str           = Field(..., min_length=3, max_length=300)
    subject:             str           = Field(..., max_length=100)
    assessment_type:     str           = Field("quiz")
    learning_objectives: List[str]     = Field(default_factory=list)
    total_marks:         int           = Field(100, ge=1, le=1000)
    duration_minutes:    Optional[int] = Field(None, ge=5, le=480)
    instructions:        Optional[str] = Field(None, max_length=3000)
    questions:           List[Dict]    = Field(default_factory=list)
    rubric_criteria:     List[Dict]    = Field(default_factory=list)
    teacher_notes:       Optional[str] = Field(None, max_length=3000)
    tags:                List[str]     = Field(default_factory=list)
    status:              str           = Field("draft")


class AssessmentGenerateRequest(BaseModel):
    title:               str        = Field(..., min_length=3, max_length=300)
    subject:             str        = Field(..., max_length=100)
    assessment_type:     str        = Field("quiz")
    learning_objectives: List[str]  = Field(..., min_length=1)
    level:               str        = Field("undergraduate")
    question_count:      int        = Field(10, ge=3, le=40)
    question_types:      List[str]  = Field(default_factory=lambda: ["multiple_choice"])
    total_marks:         int        = Field(100, ge=10, le=500)
    tags:                List[str]  = Field(default_factory=list)


class PortfolioCreate(BaseModel):
    title:       str           = Field(..., min_length=2, max_length=300)
    item_type:   str           = Field("lesson")
    description: Optional[str] = Field(None, max_length=3000)
    subject:     Optional[str] = Field(None, max_length=100)
    audience:    Optional[str] = Field(None, max_length=200)
    date:        Optional[str] = Field(None)
    evidence_url: Optional[str] = Field(None, max_length=500)
    tags:        List[str]     = Field(default_factory=list)
    featured:    bool          = Field(False)


class WorkspaceCreate(BaseModel):
    title:                str           = Field(..., min_length=3, max_length=300)
    course_code:          Optional[str] = Field(None, max_length=50)
    description:          Optional[str] = Field(None, max_length=2000)
    subject:              Optional[str] = Field(None, max_length=100)
    level:                Optional[str] = Field(None)
    semester:             Optional[str] = Field(None, max_length=100)
    teaching_objectives:  List[str]     = Field(default_factory=list)


class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


class InviteMemberRequest(BaseModel):
    user_id: Optional[str] = None
    email:   Optional[str] = Field(None, max_length=320)
    role:    str            = Field("co_instructor")

    def validate_role(self) -> None:
        if self.role not in ROLES or self.role == "workspace_owner":
            raise HTTPException(400, f"Role must be one of: {', '.join(ROLES[1:])}")

    def validate_target(self) -> None:
        if not self.user_id and not self.email:
            raise HTTPException(400, "Provide user_id or email")


class ChangeRoleRequest(BaseModel):
    role: str


class CommentCreate(BaseModel):
    content:   str           = Field(..., min_length=1, max_length=3000)
    parent_id: Optional[str] = None
    mentions:  List[str]     = Field(default_factory=list)


# ──────────────────────────────── AI prompts ──────────────────────────────────

# ──────────────────────────────── AI logic ────────────────────────────────────

async def _generate_lesson(
    req: LessonGenerateRequest,
    *,
    user_id: str | None = None,
    db=None,
) -> dict:
    raw = await call_llm(
        prompt_id="teaching.lesson_plan",
        variables={
            "topic":            req.topic,
            "subject":          req.subject,
            "audience":         req.audience,
            "level":            req.level,
            "duration_minutes": req.duration_minutes,
            "objectives_count": req.objectives_count,
        },
        feature="teaching.lesson_plan",
        user_id=user_id,
        db=db,
        max_tokens=4000,
    )
    return _parse_llm_json(raw, "Lesson generation")


async def _generate_assessment(
    req: AssessmentGenerateRequest,
    *,
    user_id: str | None = None,
    db=None,
) -> dict:
    raw = await call_llm(
        prompt_id="teaching.assessment",
        variables={
            "title":               req.title,
            "subject":             req.subject,
            "assessment_type":     req.assessment_type,
            "level":               req.level,
            "learning_objectives": "\n".join(f"- {o}" for o in req.learning_objectives),
            "question_count":      req.question_count,
            "question_types":      ", ".join(req.question_types),
            "total_marks":         req.total_marks,
        },
        feature="teaching.assessment",
        user_id=user_id,
        db=db,
        max_tokens=6000,
    )
    return _parse_llm_json(raw, "Assessment generation")


async def _chat_with_assistant(
    workspace: dict,
    history: list[dict],
    message: str,
    members_info: list[dict] | None = None,
    lesson_count: int = 0,
    assessment_count: int = 0,
    *,
    user_id: str | None = None,
    db=None,
) -> str:
    context_lines = [
        f"Course: {workspace.get('title', 'Untitled')}",
        f"Subject: {workspace.get('subject') or 'Not specified'}",
        f"Level: {workspace.get('level') or 'Not specified'}",
        f"Semester: {workspace.get('semester') or 'Not specified'}",
        f"Description: {workspace.get('description') or 'No description provided'}",
        f"Lessons in workspace: {lesson_count}",
        f"Assessments in workspace: {assessment_count}",
    ]
    objectives = workspace.get("teaching_objectives") or []
    if objectives:
        context_lines.append("Teaching objectives:\n" + "\n".join(f"  - {o}" for o in objectives))
    if members_info:
        roles_summary = ", ".join(
            f"{m.get('full_name', 'Unknown')} ({m.get('role', 'member')})"
            for m in members_info[:8]
        )
        context_lines.append(f"Team members: {roles_summary}")
    context_block = "\n".join(context_lines)

    history_tail = history[-20:] if len(history) > 20 else history
    history_str = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in history_tail
    )

    user_message = (
        f"COURSE CONTEXT:\n{context_block}\n\n"
        f"CONVERSATION HISTORY:\n{history_str if history_str else '(New conversation)'}\n\n"
        f"User: {message}\n\n"
        "Respond as the AI Teaching Assistant. Be specific, practical, and pedagogically grounded."
    )

    return await call_llm(
        prompt_id="teaching.assistant",
        variables={"user_message": user_message},
        feature="teaching.assistant",
        user_id=user_id,
        db=db,
        max_tokens=1500,
    )


# ──────────────────────────────── stats ───────────────────────────────────────

@router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    """Hub stats: counts of lessons, assessments, portfolio items, workspaces."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    lessons, assessments, portfolio, workspaces = await asyncio.gather(
        db.teaching_lessons.count_documents({"owner_id": uid}),
        db.teaching_assessments.count_documents({"owner_id": uid}),
        db.teaching_portfolio_items.count_documents({"owner_id": uid}),
        db.teaching_workspaces.count_documents({"$or": [{"owner_id": uid}, {"member_ids": uid}]}),
    )
    return {
        "lessons": lessons,
        "assessments": assessments,
        "portfolio_items": portfolio,
        "workspaces": workspaces,
    }


# ──────────────────────────────── lessons ─────────────────────────────────────

@router.get("/lessons")
async def list_lessons(
    status: Optional[str] = None,
    subject: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    query: dict = {"owner_id": user["id"]}
    if status:
        query["status"] = status
    if subject:
        query["subject"] = {"$regex": subject, "$options": "i"}
    docs = await db.teaching_lessons.find(query, {"outline": 0}).sort("created_at", -1).to_list(100)
    return [_ser(d) for d in docs]


@router.post("/lessons")
async def create_lesson(body: LessonCreate, workspace_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    doc: dict = {
        "owner_id":       uid,
        "ai_generated":   False,
        **body.model_dump(),
        "created_at":     _now(),
        "updated_at":     _now(),
    }
    if workspace_id:
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if ws and _can(ws, uid, "create_lesson"):
            doc["workspace_id"] = workspace_id
    result = await db.teaching_lessons.insert_one(doc)
    lesson_id = str(result.inserted_id)
    doc["_id"] = result.inserted_id
    _emit_rep(uid, "teaching_lesson_published", lesson_id)
    if workspace_id and doc.get("workspace_id"):
        await db.teaching_workspaces.update_one(
            {"_id": _oid(workspace_id)},
            {"$addToSet": {"linked_lesson_ids": lesson_id}, "$set": {"updated_at": _now()}},
        )
        ws_doc = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if ws_doc:
            await _log_activity(db, workspace_id, user, "lesson_created",
                                f'Created lesson "{body.title}"',
                                entity_id=lesson_id, entity_type="lesson")
    return _ser(doc)


@router.post("/lessons/generate")
async def generate_lesson(body: LessonGenerateRequest, user: dict = Depends(get_current_user)):
    """AI-generate a complete lesson plan. Costs 10 credits."""
    charged = await consume_credits(
        user["id"], "ai_lesson_plan_generate",
        metadata={"topic": body.topic[:100]},
    )
    credits_used = charged.get("consumed", 10)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    started = time.monotonic()
    try:
        generated = await _generate_lesson(body, user_id=user["id"], db=db)
    except HTTPException:
        await refund_credits(user["id"], "ai_lesson_plan_generate", reason="Generation error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_lesson_plan_generate", reason="Unexpected error")
        log.error("Lesson generation failed: %s", exc)
        raise HTTPException(503, "Lesson generation failed. Credits refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    doc = {
        "owner_id":       user["id"],
        "title":          generated.get("title", body.topic),
        "subject":        body.subject,
        "audience":       body.audience,
        "level":          body.level,
        "duration_minutes": body.duration_minutes,
        "learning_objectives": generated.get("learning_objectives", []),
        "materials":      generated.get("materials", []),
        "outline":        generated.get("outline", []),
        "assessment_strategy": generated.get("assessment_strategy", ""),
        "differentiation_strategies": generated.get("differentiation_strategies", []),
        "teacher_notes":  generated.get("teacher_notes", ""),
        "tags":           body.tags,
        "status":         "draft",
        "ai_generated":   True,
        "credits_used":   credits_used,
        "created_at":     _now(),
        "updated_at":     _now(),
    }
    result = await db.teaching_lessons.insert_one(doc)
    doc["_id"] = result.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id": user["id"], "feature": "ai_lesson_plan_generate",
            "credits": credits_used, "duration_ms": duration_ms,
            "success": True, "ref_id": str(result.inserted_id), "created_at": _now(),
        })
    except Exception:
        pass

    return _ser(doc)


@router.get("/lessons/{lesson_id}")
async def get_lesson(lesson_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.teaching_lessons.find_one({"_id": _oid(lesson_id), "owner_id": user["id"]})
    if not doc:
        raise HTTPException(404, "Lesson not found")
    return _ser(doc)


@router.patch("/lessons/{lesson_id}")
async def update_lesson(lesson_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    doc = await db.teaching_lessons.find_one({"_id": _oid(lesson_id)})
    if not doc:
        raise HTTPException(404, "Lesson not found")

    # Owner always can edit. Workspace members with edit_lesson perm can edit too.
    workspace_id = doc.get("workspace_id")
    is_owner = doc.get("owner_id") == uid
    has_ws_perm = False
    if workspace_id and not is_owner:
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if ws and _can(ws, uid, "edit_lesson"):
            has_ws_perm = True
    if not is_owner and not has_ws_perm:
        raise HTTPException(403, "Cannot edit this lesson")

    allowed = {
        "title", "subject", "audience", "level", "duration_minutes",
        "learning_objectives", "materials", "outline", "assessment_strategy",
        "differentiation_strategies", "teacher_notes", "tags", "status",
    }
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        return _ser(doc)

    await _capture_lesson_version(db, doc, user)
    update["updated_at"] = _now()
    update["updated_by"] = uid
    await db.teaching_lessons.update_one({"_id": _oid(lesson_id)}, {"$set": update})
    if workspace_id:
        await _log_activity(db, workspace_id, user, "lesson_edited",
                            f'Edited lesson "{doc.get("title", "")}"',
                            entity_id=lesson_id, entity_type="lesson")
    updated = await db.teaching_lessons.find_one({"_id": _oid(lesson_id)})
    return _ser(updated)


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(lesson_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await db.teaching_lessons.delete_one({"_id": _oid(lesson_id), "owner_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Lesson not found")
    return {"ok": True}


# ──────────────────────────────── assessments ─────────────────────────────────

@router.get("/assessments")
async def list_assessments(
    assessment_type: Optional[str] = None,
    subject: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    query: dict = {"owner_id": user["id"]}
    if assessment_type:
        query["assessment_type"] = assessment_type
    if subject:
        query["subject"] = {"$regex": subject, "$options": "i"}
    docs = await db.teaching_assessments.find(query, {"questions": 0}).sort("created_at", -1).to_list(100)
    return [_ser(d) for d in docs]


@router.post("/assessments")
async def create_assessment(body: AssessmentCreate, workspace_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    doc: dict = {
        "owner_id":     uid,
        "ai_generated": False,
        **body.model_dump(),
        "created_at":   _now(),
        "updated_at":   _now(),
    }
    if workspace_id:
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if ws and _can(ws, uid, "create_assessment"):
            doc["workspace_id"] = workspace_id
    result = await db.teaching_assessments.insert_one(doc)
    assessment_id = str(result.inserted_id)
    doc["_id"] = result.inserted_id
    if workspace_id and doc.get("workspace_id"):
        await db.teaching_workspaces.update_one(
            {"_id": _oid(workspace_id)},
            {"$addToSet": {"linked_assessment_ids": assessment_id}, "$set": {"updated_at": _now()}},
        )
        ws_doc = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if ws_doc:
            await _log_activity(db, workspace_id, user, "assessment_created",
                                f'Created assessment "{body.title}"',
                                entity_id=assessment_id, entity_type="assessment")
    return _ser(doc)


@router.post("/assessments/generate")
async def generate_assessment(body: AssessmentGenerateRequest, user: dict = Depends(get_current_user)):
    """AI-generate a complete assessment. Costs 10 credits."""
    charged = await consume_credits(
        user["id"], "ai_assessment_generate",
        metadata={"title": body.title[:100]},
    )
    credits_used = charged.get("consumed", 10)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    started = time.monotonic()
    try:
        generated = await _generate_assessment(body, user_id=user["id"], db=db)
    except HTTPException:
        await refund_credits(user["id"], "ai_assessment_generate", reason="Generation error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_assessment_generate", reason="Unexpected error")
        log.error("Assessment generation failed: %s", exc)
        raise HTTPException(503, "Assessment generation failed. Credits refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    doc = {
        "owner_id":            user["id"],
        "title":               body.title,
        "subject":             body.subject,
        "assessment_type":     body.assessment_type,
        "learning_objectives": body.learning_objectives,
        "total_marks":         body.total_marks,
        "duration_minutes":    None,
        "instructions":        generated.get("instructions", ""),
        "questions":           generated.get("questions", []),
        "rubric_criteria":     generated.get("rubric_criteria", []),
        "teacher_notes":       generated.get("teacher_notes", ""),
        "tags":                body.tags,
        "status":              "draft",
        "ai_generated":        True,
        "credits_used":        credits_used,
        "created_at":          _now(),
        "updated_at":          _now(),
    }
    result = await db.teaching_assessments.insert_one(doc)
    doc["_id"] = result.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id": user["id"], "feature": "ai_assessment_generate",
            "credits": credits_used, "duration_ms": duration_ms,
            "success": True, "ref_id": str(result.inserted_id), "created_at": _now(),
        })
    except Exception:
        pass

    return _ser(doc)


@router.get("/assessments/{assessment_id}")
async def get_assessment(assessment_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.teaching_assessments.find_one({"_id": _oid(assessment_id), "owner_id": user["id"]})
    if not doc:
        raise HTTPException(404, "Assessment not found")
    return _ser(doc)


@router.patch("/assessments/{assessment_id}")
async def update_assessment(assessment_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    doc = await db.teaching_assessments.find_one({"_id": _oid(assessment_id)})
    if not doc:
        raise HTTPException(404, "Assessment not found")

    workspace_id = doc.get("workspace_id")
    is_owner = doc.get("owner_id") == uid
    has_ws_perm = False
    if workspace_id and not is_owner:
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if ws and _can(ws, uid, "edit_assessment"):
            has_ws_perm = True
    if not is_owner and not has_ws_perm:
        raise HTTPException(403, "Cannot edit this assessment")

    allowed = {
        "title", "subject", "assessment_type", "learning_objectives", "total_marks",
        "duration_minutes", "instructions", "questions", "rubric_criteria", "teacher_notes",
        "tags", "status",
    }
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        return _ser(doc)

    await _capture_assessment_version(db, doc, user)
    update["updated_at"] = _now()
    update["updated_by"] = uid
    await db.teaching_assessments.update_one({"_id": _oid(assessment_id)}, {"$set": update})
    if workspace_id:
        await _log_activity(db, workspace_id, user, "assessment_edited",
                            f'Edited assessment "{doc.get("title", "")}"',
                            entity_id=assessment_id, entity_type="assessment")
    updated = await db.teaching_assessments.find_one({"_id": _oid(assessment_id)})
    return _ser(updated)


@router.delete("/assessments/{assessment_id}")
async def delete_assessment(assessment_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await db.teaching_assessments.delete_one({"_id": _oid(assessment_id), "owner_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Assessment not found")
    return {"ok": True}


# ──────────────────────────────── portfolio ───────────────────────────────────

@router.get("/portfolio")
async def list_portfolio(
    item_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    query: dict = {"owner_id": user["id"]}
    if item_type:
        query["item_type"] = item_type
    docs = await db.teaching_portfolio_items.find(query).sort([("featured", -1), ("date", -1)]).to_list(200)
    return [_ser(d) for d in docs]


@router.post("/portfolio")
async def create_portfolio_item(body: PortfolioCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "owner_id": user["id"],
        **body.model_dump(),
        "created_at": _now(),
        "updated_at": _now(),
    }
    result = await db.teaching_portfolio_items.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _ser(doc)


@router.get("/portfolio/{item_id}")
async def get_portfolio_item(item_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.teaching_portfolio_items.find_one({"_id": _oid(item_id), "owner_id": user["id"]})
    if not doc:
        raise HTTPException(404, "Portfolio item not found")
    return _ser(doc)


@router.patch("/portfolio/{item_id}")
async def update_portfolio_item(item_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.teaching_portfolio_items.find_one({"_id": _oid(item_id), "owner_id": user["id"]})
    if not doc:
        raise HTTPException(404, "Portfolio item not found")
    allowed = {"title", "item_type", "description", "subject", "audience", "date", "evidence_url", "tags", "featured"}
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        return _ser(doc)
    update["updated_at"] = _now()
    await db.teaching_portfolio_items.update_one({"_id": _oid(item_id)}, {"$set": update})
    updated = await db.teaching_portfolio_items.find_one({"_id": _oid(item_id)})
    return _ser(updated)


@router.delete("/portfolio/{item_id}")
async def delete_portfolio_item(item_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await db.teaching_portfolio_items.delete_one({"_id": _oid(item_id), "owner_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Portfolio item not found")
    return {"ok": True}


# ──────────────────────────────── workspaces ──────────────────────────────────

@router.get("/workspaces")
async def list_workspaces(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    docs = await db.teaching_workspaces.find(
        {"$or": [{"owner_id": uid}, {"member_ids": uid}]}
    ).sort("updated_at", -1).to_list(50)
    result = []
    for d in docs:
        ws = _ser(d)
        ws["member_count"] = len(ws.get("member_ids") or [])
        ws["my_role"] = _role(d, uid)
        result.append(ws)
    return result


@router.post("/workspaces")
async def create_workspace(body: WorkspaceCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    doc = {
        "owner_id":              uid,
        "member_ids":            [uid],
        "member_roles":          {uid: "workspace_owner"},
        "status":                "active",
        "linked_lesson_ids":     [],
        "linked_assessment_ids": [],
        **body.model_dump(),
        "created_at":            _now(),
        "updated_at":            _now(),
    }
    result = await db.teaching_workspaces.insert_one(doc)
    doc["_id"] = result.inserted_id
    wid = str(result.inserted_id)
    await _log_activity(db, wid, user, "workspace_created", f'Created workspace "{body.title}"')
    return _ser(doc)


@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    doc = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not doc:
        raise HTTPException(404, "Workspace not found")
    _assert_member(doc, uid)
    ws = _ser(doc)

    # Enrich member list with user info + roles
    member_ids = ws.get("member_ids") or []
    member_roles = ws.get("member_roles") or {}
    if member_ids:
        oids = []
        for mid in member_ids:
            try:
                oids.append(ObjectId(mid))
            except Exception:
                pass
        members_docs = await db.users.find({"_id": {"$in": oids}}).to_list(100)
        ws["members_info"] = [
            {
                "id":           str(m["_id"]),
                "full_name":    m.get("full_name"),
                "institution":  m.get("institution"),
                "user_type":    m.get("user_type"),
                "primary_domain": m.get("primary_domain"),
                "avatar_url":   m.get("avatar_url"),
                "role":         member_roles.get(str(m["_id"]), "observer"),
            }
            for m in members_docs
        ]
    else:
        ws["members_info"] = []

    ws["my_role"] = _role(doc, uid)
    return ws


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    doc = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not doc:
        raise HTTPException(404, "Workspace not found")
    _assert_member(doc, uid)

    # Owner-only fields
    owner_only = {"status", "teaching_objectives"}
    # Fields editable by course_lead+
    lead_fields = {"title", "course_code", "description", "subject", "level", "semester",
                   "linked_lesson_ids", "linked_assessment_ids"}

    update: dict = {}
    for k, v in body.items():
        if k in owner_only:
            if _can(doc, uid, "update_settings"):
                update[k] = v
        elif k in lead_fields:
            if _can(doc, uid, "manage_lessons"):
                update[k] = v

    if not update:
        return _ser(doc)
    update["updated_at"] = _now()
    await db.teaching_workspaces.update_one({"_id": _oid(workspace_id)}, {"$set": update})
    await _log_activity(db, workspace_id, user, "settings_updated", "Updated workspace settings")
    updated = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    return _ser(updated)


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not doc:
        raise HTTPException(404, "Workspace not found")
    _assert_perm(doc, user["id"], "delete_workspace")
    await asyncio.gather(
        db.teaching_chat_messages.delete_many({"workspace_id": workspace_id}),
        db.teaching_workspace_activity.delete_many({"workspace_id": workspace_id}),
        db.teaching_workspace_invitations.delete_many({"workspace_id": workspace_id}),
        db.teaching_workspace_comments.delete_many({"workspace_id": workspace_id}),
    )
    await db.teaching_workspaces.delete_one({"_id": _oid(workspace_id)})
    return {"ok": True}


# ──────────────────────────────── AI teaching assistant ───────────────────────

@router.get("/workspaces/{workspace_id}/chat")
async def get_chat_history(workspace_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    workspace = await db.teaching_workspaces.find_one({
        "_id": _oid(workspace_id),
        "$or": [{"owner_id": uid}, {"member_ids": uid}],
    })
    if not workspace:
        raise HTTPException(404, "Workspace not found")
    docs = await db.teaching_chat_messages.find(
        {"workspace_id": workspace_id, "owner_id": uid}
    ).sort("created_at", 1).to_list(100)
    return [_ser(d) for d in docs]


@router.post("/workspaces/{workspace_id}/chat")
async def send_chat_message(
    workspace_id: str,
    body: ChatMessage,
    user: dict = Depends(get_current_user),
):
    """Send a message to the AI Teaching Assistant. Costs 2 credits."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    workspace = await db.teaching_workspaces.find_one({
        "_id": _oid(workspace_id),
        "$or": [{"owner_id": uid}, {"member_ids": uid}],
    })
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    charged = await consume_credits(
        uid, "ai_teaching_assistant",
        metadata={"workspace_id": workspace_id},
    )
    credits_used = charged.get("consumed", 2)

    # Fetch recent history for context
    history_docs = await db.teaching_chat_messages.find(
        {"workspace_id": workspace_id, "owner_id": uid}
    ).sort("created_at", 1).to_list(40)
    history = [{"role": d["role"], "content": d["content"]} for d in history_docs]

    # Fetch member info for AI context
    member_ids = workspace.get("member_ids") or []
    member_roles = workspace.get("member_roles") or {}
    members_info: list[dict] = []
    if member_ids:
        try:
            oids = [ObjectId(mid) for mid in member_ids if ObjectId.is_valid(mid)]
            mdocs = await db.users.find({"_id": {"$in": oids}}, {"full_name": 1}).to_list(20)
            members_info = [
                {"full_name": m.get("full_name"), "role": member_roles.get(str(m["_id"]), "member")}
                for m in mdocs
            ]
        except Exception:
            pass

    lesson_count = len(workspace.get("linked_lesson_ids") or [])
    assessment_count = len(workspace.get("linked_assessment_ids") or [])

    started = time.monotonic()
    try:
        reply = await _chat_with_assistant(
            workspace, history, body.content,
            members_info=members_info,
            lesson_count=lesson_count,
            assessment_count=assessment_count,
            user_id=uid,
            db=db,
        )
    except Exception as exc:
        await refund_credits(uid, "ai_teaching_assistant", reason="Assistant error")
        log.error("Teaching assistant error: %s", exc)
        raise HTTPException(503, "Teaching assistant unavailable. Credits refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    user_msg_doc  = {"workspace_id": workspace_id, "owner_id": uid, "role": "user",      "content": body.content, "created_at": _now()}
    assistant_doc = {"workspace_id": workspace_id, "owner_id": uid, "role": "assistant",  "content": reply,        "created_at": _now(), "credits_used": credits_used}

    await db.teaching_chat_messages.insert_many([user_msg_doc, assistant_doc])
    await _log_activity(db, workspace_id, user, "ai_session", "Used AI Teaching Assistant")

    try:
        await db.ai_requests.insert_one({
            "user_id": uid, "feature": "ai_teaching_assistant",
            "credits": credits_used, "duration_ms": duration_ms,
            "success": True, "ref_id": workspace_id, "created_at": _now(),
        })
    except Exception:
        pass

    return {"role": "assistant", "content": reply, "credits_used": credits_used}


# ──────────────────────────────── member management ───────────────────────────

@router.get("/workspaces/{workspace_id}/members")
async def list_members(workspace_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    _assert_member(ws, uid)

    member_ids = ws.get("member_ids") or []
    member_roles = ws.get("member_roles") or {}
    if not member_ids:
        return []

    oids = [ObjectId(mid) for mid in member_ids if ObjectId.is_valid(mid)]
    users = await db.users.find({"_id": {"$in": oids}}).to_list(100)
    return [
        {
            "id":             str(u["_id"]),
            "full_name":      u.get("full_name"),
            "institution":    u.get("institution"),
            "user_type":      u.get("user_type"),
            "primary_domain": u.get("primary_domain"),
            "avatar_url":     u.get("avatar_url"),
            "role":           member_roles.get(str(u["_id"]), "observer"),
        }
        for u in users
    ]


@router.post("/workspaces/{workspace_id}/members/invite")
async def invite_member(
    workspace_id: str,
    body: InviteMemberRequest,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    _assert_perm(ws, uid, "invite_member")
    body.validate_role()
    body.validate_target()

    # Resolve invitee
    invitee_id: str | None = None
    invitee_name: str | None = None
    invitee_email: str | None = body.email

    if body.user_id:
        invitee_doc = await db.users.find_one({"_id": _oid(body.user_id)})
        if not invitee_doc:
            raise HTTPException(404, "User not found")
        invitee_id = str(invitee_doc["_id"])
        invitee_name = invitee_doc.get("full_name")
        invitee_email = invitee_doc.get("email") or body.email
    elif body.email:
        invitee_doc = await db.users.find_one({"email": body.email.lower()})
        if invitee_doc:
            invitee_id = str(invitee_doc["_id"])
            invitee_name = invitee_doc.get("full_name")

    # Don't invite existing members
    if invitee_id and invitee_id in (ws.get("member_ids") or []):
        raise HTTPException(409, "User is already a member of this workspace")

    # Don't duplicate pending invitations
    existing = await db.teaching_workspace_invitations.find_one({
        "workspace_id": workspace_id,
        "status": "pending",
        **({"invitee_id": invitee_id} if invitee_id else {"invitee_email": invitee_email}),
    })
    if existing:
        raise HTTPException(409, "An invitation is already pending for this user")

    from datetime import timedelta
    inv_doc = {
        "workspace_id":    workspace_id,
        "workspace_title": ws.get("title", ""),
        "inviter_id":      uid,
        "inviter_name":    user.get("full_name", "Someone"),
        "invitee_id":      invitee_id,
        "invitee_name":    invitee_name,
        "invitee_email":   invitee_email,
        "role":            body.role,
        "status":          "pending",
        "created_at":      _now(),
        "expires_at":      (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }
    result = await db.teaching_workspace_invitations.insert_one(inv_doc)
    inv_doc["_id"] = result.inserted_id

    # Notify invitee (in-app) if they exist on the platform
    if invitee_id:
        register_default_providers()
        await dispatch(NotificationEvent(
            user_id=invitee_id,
            kind="workspace_invitation",
            title="Teaching workspace invitation",
            body=f'{user.get("full_name", "Someone")} invited you to join "{ws.get("title", "a workspace")}" as {body.role.replace("_", " ")}.',
            link=f"/teaching/workspaces/{workspace_id}",
            actor_id=uid,
            payload={"invitation_id": str(result.inserted_id), "workspace_id": workspace_id},
        ))
    await _log_activity(db, workspace_id, user, "member_invited",
                        f"Invited {invitee_name or invitee_email or 'someone'} as {body.role.replace('_', ' ')}")
    return _ser(inv_doc)


@router.patch("/workspaces/{workspace_id}/members/{member_uid}/role")
async def change_member_role(
    workspace_id: str,
    member_uid: str,
    body: ChangeRoleRequest,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    _assert_perm(ws, uid, "manage_roles")

    if body.role not in ROLES or body.role == "workspace_owner":
        raise HTTPException(400, f"Role must be one of: {', '.join(ROLES[1:])}")
    if member_uid == (ws.get("owner_id") or uid):
        raise HTTPException(400, "Cannot change the workspace owner's role")
    if member_uid not in (ws.get("member_ids") or []):
        raise HTTPException(404, "User is not a member of this workspace")

    await db.teaching_workspaces.update_one(
        {"_id": _oid(workspace_id)},
        {"$set": {f"member_roles.{member_uid}": body.role, "updated_at": _now()}},
    )
    member_doc = await db.users.find_one({"_id": _oid(member_uid)})
    member_name = (member_doc or {}).get("full_name", "Member")
    await _log_activity(db, workspace_id, user, "role_changed",
                        f"Changed {member_name}'s role to {body.role.replace('_', ' ')}")
    return {"ok": True, "member_id": member_uid, "role": body.role}


@router.delete("/workspaces/{workspace_id}/members/{member_uid}")
async def remove_member(
    workspace_id: str,
    member_uid: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not ws:
        raise HTTPException(404, "Workspace not found")

    # Members can leave; owners/course_leads can remove others
    is_self = member_uid == uid
    if not is_self:
        _assert_perm(ws, uid, "remove_member")
    if member_uid == ws.get("owner_id"):
        raise HTTPException(400, "Cannot remove the workspace owner")
    if member_uid not in (ws.get("member_ids") or []):
        raise HTTPException(404, "User is not a member of this workspace")

    await db.teaching_workspaces.update_one(
        {"_id": _oid(workspace_id)},
        {
            "$pull": {"member_ids": member_uid},
            "$unset": {f"member_roles.{member_uid}": ""},
            "$set": {"updated_at": _now()},
        },
    )
    member_doc = await db.users.find_one({"_id": _oid(member_uid)})
    member_name = (member_doc or {}).get("full_name", "A member")
    await _log_activity(
        db, workspace_id, user, "member_removed",
        f"{member_name} left the workspace" if is_self else f"Removed {member_name} from workspace",
    )
    return {"ok": True}


# ──────────────────────────────── invitations ─────────────────────────────────

@router.get("/workspace-invitations")
async def list_my_invitations(user: dict = Depends(get_current_user)):
    """List pending workspace invitations sent to the current user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    docs = await db.teaching_workspace_invitations.find({
        "$or": [{"invitee_id": uid}, {"invitee_email": user.get("email", "")}],
        "status": "pending",
    }).sort("created_at", -1).to_list(50)
    return [_ser(d) for d in docs]


@router.post("/workspace-invitations/{inv_id}/accept")
async def accept_invitation(inv_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    inv = await db.teaching_workspace_invitations.find_one({"_id": _oid(inv_id), "status": "pending"})
    if not inv:
        raise HTTPException(404, "Invitation not found or already processed")

    # Verify this invitation is for the current user
    if inv.get("invitee_id") and inv["invitee_id"] != uid:
        raise HTTPException(403, "This invitation is not for you")
    if not inv.get("invitee_id") and inv.get("invitee_email") != (user.get("email") or "").lower():
        raise HTTPException(403, "This invitation is not for you")

    workspace_id = inv["workspace_id"]
    role = inv.get("role", "observer")

    await db.teaching_workspace_invitations.update_one(
        {"_id": _oid(inv_id)},
        {"$set": {"status": "accepted", "accepted_at": _now()}},
    )
    await db.teaching_workspaces.update_one(
        {"_id": _oid(workspace_id)},
        {
            "$addToSet": {"member_ids": uid},
            "$set": {f"member_roles.{uid}": role, "updated_at": _now()},
        },
    )
    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    await _log_activity(
        db, workspace_id, user, "member_joined",
        f"{user.get('full_name', 'Someone')} joined the workspace as {role.replace('_', ' ')}",
    )
    # Notify workspace owner
    if ws and ws.get("owner_id") and ws["owner_id"] != uid:
        register_default_providers()
        await dispatch(NotificationEvent(
            user_id=ws["owner_id"],
            kind="workspace_member_joined",
            title="Member joined workspace",
            body=f'{user.get("full_name", "Someone")} accepted your invitation to join "{ws.get("title", "your workspace")}".',
            link=f"/teaching/workspaces/{workspace_id}",
            actor_id=uid,
            payload={"workspace_id": workspace_id},
        ))
    return {"ok": True, "workspace_id": workspace_id, "role": role}


@router.post("/workspace-invitations/{inv_id}/decline")
async def decline_invitation(inv_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    inv = await db.teaching_workspace_invitations.find_one({"_id": _oid(inv_id), "status": "pending"})
    if not inv:
        raise HTTPException(404, "Invitation not found or already processed")
    if inv.get("invitee_id") and inv["invitee_id"] != uid:
        raise HTTPException(403, "This invitation is not for you")
    await db.teaching_workspace_invitations.update_one(
        {"_id": _oid(inv_id)},
        {"$set": {"status": "declined", "declined_at": _now()}},
    )
    return {"ok": True}


# ──────────────────────────────── activity feed ───────────────────────────────

@router.get("/workspaces/{workspace_id}/activity")
async def get_activity(
    workspace_id: str,
    limit: int = 30,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    _assert_member(ws, uid)
    docs = await db.teaching_workspace_activity.find(
        {"workspace_id": workspace_id}
    ).sort("created_at", -1).limit(min(limit, 100)).to_list(100)
    return [_ser_act(d) for d in docs]


# ──────────────────────────────── comments ────────────────────────────────────

def _ser_comment(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


async def _get_ws_for_entity(db, entity_type: str, entity_id: str, uid: str) -> dict:
    """Resolve the workspace a lesson/assessment belongs to and verify membership."""
    if entity_type == "lesson":
        entity = await db.teaching_lessons.find_one({"_id": _oid(entity_id)})
    elif entity_type == "assessment":
        entity = await db.teaching_assessments.find_one({"_id": _oid(entity_id)})
    else:
        raise HTTPException(400, "Unknown entity type")
    if not entity:
        raise HTTPException(404, "Entity not found")
    workspace_id = entity.get("workspace_id")
    if not workspace_id:
        # Standalone lesson — only owner can comment
        if entity.get("owner_id") != uid:
            raise HTTPException(403, "No workspace context — only owner can comment")
        return {"_standalone": True, "workspace_id": None}
    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    _assert_perm(ws, uid, "comment")
    return ws


@router.get("/workspaces/{workspace_id}/comments")
async def get_workspace_comments(workspace_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    _assert_perm(ws, user["id"], "comment")
    docs = await db.teaching_workspace_comments.find(
        {"workspace_id": workspace_id, "entity_type": "workspace"}
    ).sort("created_at", 1).to_list(200)
    return [_ser_comment(d) for d in docs]


@router.post("/workspaces/{workspace_id}/comments")
async def post_workspace_comment(workspace_id: str, body: CommentCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    _assert_perm(ws, uid, "comment")
    doc = {
        "workspace_id": workspace_id,
        "entity_type":  "workspace",
        "entity_id":    workspace_id,
        "parent_id":    body.parent_id,
        "author_id":    uid,
        "author_name":  user.get("full_name", "Someone"),
        "content":      body.content,
        "mentions":     body.mentions,
        "created_at":   _now(),
        "updated_at":   _now(),
    }
    result = await db.teaching_workspace_comments.insert_one(doc)
    doc["_id"] = result.inserted_id
    await _log_activity(db, workspace_id, user, "comment_added", "Added a workspace comment")
    # Notify mentioned users
    for mentioned_uid in (body.mentions or []):
        if mentioned_uid != uid:
            register_default_providers()
            await dispatch(NotificationEvent(
                user_id=mentioned_uid,
                kind="mention",
                title="You were mentioned",
                body=f'{user.get("full_name", "Someone")} mentioned you in "{ws.get("title", "a workspace")}".',
                link=f"/teaching/workspaces/{workspace_id}",
                actor_id=uid,
            ))
    return _ser_comment(doc)


@router.get("/lessons/{lesson_id}/comments")
async def get_lesson_comments(lesson_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    lesson = await db.teaching_lessons.find_one({"_id": _oid(lesson_id)})
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    # Owner or workspace member with comment perm
    if lesson.get("owner_id") != uid:
        workspace_id = lesson.get("workspace_id")
        if not workspace_id:
            raise HTTPException(403, "Forbidden")
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if not ws or not _can(ws, uid, "comment"):
            raise HTTPException(403, "Forbidden")
    docs = await db.teaching_workspace_comments.find(
        {"entity_type": "lesson", "entity_id": lesson_id}
    ).sort("created_at", 1).to_list(200)
    return [_ser_comment(d) for d in docs]


@router.post("/lessons/{lesson_id}/comments")
async def post_lesson_comment(lesson_id: str, body: CommentCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    lesson = await db.teaching_lessons.find_one({"_id": _oid(lesson_id)})
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    workspace_id = lesson.get("workspace_id")
    if lesson.get("owner_id") != uid:
        if not workspace_id:
            raise HTTPException(403, "Forbidden")
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if not ws or not _can(ws, uid, "comment"):
            raise HTTPException(403, "Forbidden")
    doc = {
        "workspace_id": workspace_id or "",
        "entity_type":  "lesson",
        "entity_id":    lesson_id,
        "parent_id":    body.parent_id,
        "author_id":    uid,
        "author_name":  user.get("full_name", "Someone"),
        "content":      body.content,
        "mentions":     body.mentions,
        "created_at":   _now(),
        "updated_at":   _now(),
    }
    result = await db.teaching_workspace_comments.insert_one(doc)
    doc["_id"] = result.inserted_id
    if workspace_id:
        await _log_activity(db, workspace_id, user, "comment_added",
                            f'Commented on lesson "{lesson.get("title", "")}"',
                            entity_id=lesson_id, entity_type="lesson")
    return _ser_comment(doc)


@router.get("/assessments/{assessment_id}/comments")
async def get_assessment_comments(assessment_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    assessment = await db.teaching_assessments.find_one({"_id": _oid(assessment_id)})
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    if assessment.get("owner_id") != uid:
        workspace_id = assessment.get("workspace_id")
        if not workspace_id:
            raise HTTPException(403, "Forbidden")
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if not ws or not _can(ws, uid, "comment"):
            raise HTTPException(403, "Forbidden")
    docs = await db.teaching_workspace_comments.find(
        {"entity_type": "assessment", "entity_id": assessment_id}
    ).sort("created_at", 1).to_list(200)
    return [_ser_comment(d) for d in docs]


@router.post("/assessments/{assessment_id}/comments")
async def post_assessment_comment(assessment_id: str, body: CommentCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    assessment = await db.teaching_assessments.find_one({"_id": _oid(assessment_id)})
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    workspace_id = assessment.get("workspace_id")
    if assessment.get("owner_id") != uid:
        if not workspace_id:
            raise HTTPException(403, "Forbidden")
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if not ws or not _can(ws, uid, "comment"):
            raise HTTPException(403, "Forbidden")
    doc = {
        "workspace_id": workspace_id or "",
        "entity_type":  "assessment",
        "entity_id":    assessment_id,
        "parent_id":    body.parent_id,
        "author_id":    uid,
        "author_name":  user.get("full_name", "Someone"),
        "content":      body.content,
        "mentions":     body.mentions,
        "created_at":   _now(),
        "updated_at":   _now(),
    }
    result = await db.teaching_workspace_comments.insert_one(doc)
    doc["_id"] = result.inserted_id
    if workspace_id:
        await _log_activity(db, workspace_id, user, "comment_added",
                            f'Commented on assessment "{assessment.get("title", "")}"',
                            entity_id=assessment_id, entity_type="assessment")
    return _ser_comment(doc)


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    doc = await db.teaching_workspace_comments.find_one({"_id": _oid(comment_id)})
    if not doc:
        raise HTTPException(404, "Comment not found")
    # Only author or workspace owner can delete
    is_author = doc.get("author_id") == uid
    workspace_id = doc.get("workspace_id")
    is_ws_owner = False
    if workspace_id:
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if ws and _can(ws, uid, "manage_lessons"):
            is_ws_owner = True
    if not is_author and not is_ws_owner:
        raise HTTPException(403, "Cannot delete this comment")
    await db.teaching_workspace_comments.delete_one({"_id": _oid(comment_id)})
    return {"ok": True}


# ──────────────────────────────── version history ─────────────────────────────

@router.get("/lessons/{lesson_id}/versions")
async def list_lesson_versions(lesson_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    lesson = await db.teaching_lessons.find_one({"_id": _oid(lesson_id)})
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    # Owner or workspace member can view versions
    if lesson.get("owner_id") != uid:
        workspace_id = lesson.get("workspace_id")
        if not workspace_id:
            raise HTTPException(403, "Forbidden")
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if not ws or not _can(ws, uid, "view"):
            raise HTTPException(403, "Forbidden")
    docs = await db.teaching_lesson_versions.find(
        {"lesson_id": lesson_id}
    ).sort("created_at", -1).to_list(50)
    result = []
    for d in docs:
        d = dict(d)
        d["id"] = str(d.pop("_id"))
        d.pop("snapshot", None)  # exclude full snapshot from list
        result.append(d)
    return result


@router.post("/lessons/{lesson_id}/versions/{version_id}/restore")
async def restore_lesson_version(lesson_id: str, version_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    lesson = await db.teaching_lessons.find_one({"_id": _oid(lesson_id)})
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    # Only owner or editor can restore
    workspace_id = lesson.get("workspace_id")
    if lesson.get("owner_id") != uid:
        if not workspace_id:
            raise HTTPException(403, "Forbidden")
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if not ws or not _can(ws, uid, "edit_lesson"):
            raise HTTPException(403, "Forbidden")

    version = await db.teaching_lesson_versions.find_one({"_id": _oid(version_id), "lesson_id": lesson_id})
    if not version:
        raise HTTPException(404, "Version not found")

    snap = version.get("snapshot") or {}
    allowed = {
        "title", "subject", "audience", "level", "duration_minutes",
        "learning_objectives", "materials", "outline", "assessment_strategy",
        "differentiation_strategies", "teacher_notes", "tags", "status",
    }
    restore_data = {k: v for k, v in snap.items() if k in allowed}
    restore_data["updated_at"] = _now()
    restore_data["updated_by"] = uid

    await _capture_lesson_version(db, lesson, user)  # snapshot current before overwriting
    await db.teaching_lessons.update_one({"_id": _oid(lesson_id)}, {"$set": restore_data})
    if workspace_id:
        await _log_activity(db, workspace_id, user, "lesson_restored",
                            f'Restored lesson "{lesson.get("title", "")}" to an earlier version',
                            entity_id=lesson_id, entity_type="lesson")
    updated = await db.teaching_lessons.find_one({"_id": _oid(lesson_id)})
    return _ser(updated)


@router.get("/assessments/{assessment_id}/versions")
async def list_assessment_versions(assessment_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    assessment = await db.teaching_assessments.find_one({"_id": _oid(assessment_id)})
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    if assessment.get("owner_id") != uid:
        workspace_id = assessment.get("workspace_id")
        if not workspace_id:
            raise HTTPException(403, "Forbidden")
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if not ws or not _can(ws, uid, "view"):
            raise HTTPException(403, "Forbidden")
    docs = await db.teaching_assessment_versions.find(
        {"assessment_id": assessment_id}
    ).sort("created_at", -1).to_list(50)
    result = []
    for d in docs:
        d = dict(d)
        d["id"] = str(d.pop("_id"))
        d.pop("snapshot", None)
        result.append(d)
    return result


@router.post("/assessments/{assessment_id}/versions/{version_id}/restore")
async def restore_assessment_version(assessment_id: str, version_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    assessment = await db.teaching_assessments.find_one({"_id": _oid(assessment_id)})
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    workspace_id = assessment.get("workspace_id")
    if assessment.get("owner_id") != uid:
        if not workspace_id:
            raise HTTPException(403, "Forbidden")
        ws = await db.teaching_workspaces.find_one({"_id": _oid(workspace_id)})
        if not ws or not _can(ws, uid, "edit_assessment"):
            raise HTTPException(403, "Forbidden")

    version = await db.teaching_assessment_versions.find_one(
        {"_id": _oid(version_id), "assessment_id": assessment_id}
    )
    if not version:
        raise HTTPException(404, "Version not found")

    snap = version.get("snapshot") or {}
    allowed = {
        "title", "subject", "assessment_type", "learning_objectives", "total_marks",
        "duration_minutes", "instructions", "questions", "rubric_criteria", "teacher_notes",
        "tags", "status",
    }
    restore_data = {k: v for k, v in snap.items() if k in allowed}
    restore_data["updated_at"] = _now()
    restore_data["updated_by"] = uid

    await _capture_assessment_version(db, assessment, user)
    await db.teaching_assessments.update_one({"_id": _oid(assessment_id)}, {"$set": restore_data})
    if workspace_id:
        await _log_activity(db, workspace_id, user, "assessment_restored",
                            f'Restored assessment "{assessment.get("title", "")}" to an earlier version',
                            entity_id=assessment_id, entity_type="assessment")
    updated = await db.teaching_assessments.find_one({"_id": _oid(assessment_id)})
    return _ser(updated)
