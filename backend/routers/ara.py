"""
Autonomous Research Agents router.

Prefix: /api/ara

Endpoints:
  POST   /missions                      — create & plan a mission
  GET    /missions                      — list missions
  GET    /missions/{id}                 — mission detail
  POST   /missions/{id}/approve-plan    — approve plan → start execution
  POST   /missions/{id}/refine-plan     — adjust agent list before execution
  POST   /missions/{id}/pause           — pause running mission
  POST   /missions/{id}/cancel          — cancel mission
  DELETE /missions/{id}                 — delete draft/cancelled mission
  GET    /missions/{id}/steps           — execution steps
  GET    /missions/{id}/logs            — audit log
  GET    /missions/{id}/approvals       — approval requests for this mission
  GET    /approvals/pending             — all pending approvals for user
  POST   /approvals/{aid}/approve       — grant approval → resume execution
  POST   /approvals/{aid}/reject        — reject approval → fail step
  GET    /agents                        — agent registry
  GET    /agents/{name}                 — single agent metadata
  GET    /schedules                     — user schedules
  POST   /schedules                     — create recurring schedule
  DELETE /schedules/{id}                — delete schedule
  POST   /monitors/run                  — run background monitors now
  GET    /monitors/alerts               — recent monitor alerts from ara_logs
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from worker import enqueue_job
from worker.models import Job, Priority
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db

from ara import mission_planner, mission_store, orchestrator, scheduler, background_agents
from ara.agent_registry import list_agents, get_agent
from ara.safe_autonomy import safety_policy_note, autonomy_level_label
from repo.shim import make_db_proxy

logger = logging.getLogger("ara.router")
router = APIRouter(prefix="/api/ara", tags=["ara"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateMissionRequest(BaseModel):
    title:          str
    description:    str
    mission_type:   str  = "general"
    autonomy_level: int  = Field(1, ge=0, le=3)
    params:         dict = Field(default_factory=dict)


class RefinePlanRequest(BaseModel):
    agents: list[str]
    params: dict = Field(default_factory=dict)


class CreateScheduleRequest(BaseModel):
    title:          str
    description:    str
    mission_type:   str
    autonomy_level: int     = Field(1, ge=0, le=3)
    interval:       str     = "weekly"
    params:         dict    = Field(default_factory=dict)


class RejectRequest(BaseModel):
    reason: str = ""


# ── Missions ──────────────────────────────────────────────────────────────────

@router.post("/missions")
async def create_mission(
    body: CreateMissionRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    user_id    = str(user["_id"])
    mission_id = await mission_store.create_mission(
        db, user_id, body.title, body.description,
        body.autonomy_level, body.mission_type, body.params,
    )
    # Generate plan immediately (transitions to plan_review)
    steps = await mission_planner.generate_plan(
        db, mission_id, body.description,
        body.mission_type, body.params,
    )
    return {
        "mission_id":    mission_id,
        "status":        "plan_review",
        "steps":         steps,
        "safety_policy": safety_policy_note(),
    }


@router.get("/missions")
async def list_missions(
    status: Optional[str] = Query(None),
    limit:  int           = Query(20, ge=1, le=50),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await mission_store.list_missions(db, str(user["_id"]), status, limit)


@router.get("/missions/{mission_id}")
async def get_mission(
    mission_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    mission = await mission_store.get_mission(db, mission_id, str(user["_id"]))
    if not mission:
        raise HTTPException(404, "Mission not found")
    return mission


@router.post("/missions/{mission_id}/approve-plan")
async def approve_plan(
    mission_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    mission = await mission_store.get_mission(db, mission_id, user_id)
    if not mission:
        raise HTTPException(404, "Mission not found")
    if mission["status"] != "plan_review":
        raise HTTPException(400, f"Cannot start mission in status '{mission['status']}'")

    autonomy_level = mission["autonomy_level"]
    if autonomy_level == 0:
        return {"status": "plan_approved", "message": "Manual mode: execute steps yourself using the plan."}

    user_doc = {k: str(v) if hasattr(v, "__str__") and not isinstance(v, (str, int, float, bool, type(None), dict, list)) else v
                for k, v in user.items()}
    await enqueue_job(
        Job(job_type="mission.run",
            payload={"mission_id": mission_id, "user_id": user_id,
                     "autonomy_level": autonomy_level, "user": user_doc},
            user_id=user_id, priority=Priority.HIGH),
        db,
    )
    return {"status": "running", "message": "Mission execution started in background."}


@router.post("/missions/{mission_id}/refine-plan")
async def refine_plan(
    mission_id: str,
    body:       RefinePlanRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    mission = await mission_store.get_mission(db, mission_id, user_id)
    if not mission:
        raise HTTPException(404, "Mission not found")
    if mission["status"] not in ("plan_review", "draft"):
        raise HTTPException(400, "Can only refine plan in plan_review or draft status")

    # Validate agents
    invalid = [a for a in body.agents if not get_agent(a)]
    if invalid:
        raise HTTPException(400, f"Unknown agents: {invalid}")

    steps = await mission_planner.refine_plan(db, mission_id, body.agents, body.params)
    return {"status": "plan_review", "steps": steps}


@router.post("/missions/{mission_id}/pause")
async def pause_mission(
    mission_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    mission = await mission_store.get_mission(db, mission_id, str(user["_id"]))
    if not mission:
        raise HTTPException(404, "Mission not found")
    if mission["status"] not in ("running", "awaiting_human"):
        raise HTTPException(400, "Can only pause running missions")
    await mission_store.update_mission(db, mission_id, {"status": "paused"})
    return {"status": "paused"}


@router.post("/missions/{mission_id}/cancel")
async def cancel_mission(
    mission_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    mission = await mission_store.get_mission(db, mission_id, str(user["_id"]))
    if not mission:
        raise HTTPException(404, "Mission not found")
    if mission["status"] == "completed":
        raise HTTPException(400, "Cannot cancel completed mission")
    await mission_store.update_mission(db, mission_id, {"status": "cancelled"})
    return {"status": "cancelled"}


@router.delete("/missions/{mission_id}")
async def delete_mission(
    mission_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    mission = await mission_store.get_mission(db, mission_id, str(user["_id"]))
    if not mission:
        raise HTTPException(404, "Mission not found")
    if mission["status"] in ("running", "awaiting_human"):
        raise HTTPException(400, "Cannot delete a running mission — cancel it first")
    deleted = await mission_store.delete_mission(db, mission_id, str(user["_id"]))
    return {"deleted": deleted}


@router.get("/missions/{mission_id}/steps")
async def get_steps(
    mission_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    mission = await mission_store.get_mission(db, mission_id, str(user["_id"]))
    if not mission:
        raise HTTPException(404, "Mission not found")
    return await mission_store.get_steps(db, mission_id)


@router.get("/missions/{mission_id}/logs")
async def get_logs(
    mission_id: str,
    limit:      int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    mission = await mission_store.get_mission(db, mission_id, str(user["_id"]))
    if not mission:
        raise HTTPException(404, "Mission not found")
    return await mission_store.get_logs(db, mission_id, limit)


@router.get("/missions/{mission_id}/approvals")
async def get_mission_approvals(
    mission_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    mission = await mission_store.get_mission(db, mission_id, str(user["_id"]))
    if not mission:
        raise HTTPException(404, "Mission not found")
    return await mission_store.get_mission_approvals(db, mission_id)


# ── Approvals ─────────────────────────────────────────────────────────────────

@router.get("/approvals/pending")
async def pending_approvals(
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await mission_store.list_pending_approvals(db, str(user["_id"]))


@router.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    user_id  = str(user["_id"])
    approval = await mission_store.get_approval(db, approval_id, user_id)
    if not approval:
        raise HTTPException(404, "Approval request not found")
    if approval["status"] != "pending":
        raise HTTPException(400, f"Approval already {approval['status']}")

    await mission_store.resolve_approval(db, approval_id, "approved", user_id)
    await mission_store.append_log(
        db, approval["mission_id"], "researcher", "step_approved",
        f"Action '{approval['action']}' approved by researcher",
    )

    # Resume mission execution
    mission = await mission_store.get_mission(db, approval["mission_id"], user_id)
    if mission and mission["status"] == "awaiting_human":
        user_doc = {k: str(v) if hasattr(v, "__str__") and not isinstance(v, (str, int, float, bool, type(None), dict, list)) else v
                    for k, v in user.items()}
        await enqueue_job(
            Job(job_type="mission.resume",
                payload={"mission_id": approval["mission_id"], "user_id": user_id,
                         "autonomy_level": mission["autonomy_level"], "user": user_doc},
                user_id=user_id, priority=Priority.CRITICAL),
            db,
        )

    return {"status": "approved", "message": "Execution will resume momentarily."}


@router.post("/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    body:        RejectRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    user_id  = str(user["_id"])
    approval = await mission_store.get_approval(db, approval_id, user_id)
    if not approval:
        raise HTTPException(404, "Approval request not found")
    if approval["status"] != "pending":
        raise HTTPException(400, f"Approval already {approval['status']}")

    await mission_store.resolve_approval(db, approval_id, "rejected", user_id, body.reason)
    await mission_store.update_step(db, approval["mission_id"], approval["step_id"],
                                    {"status": "rejected", "error": body.reason or "Rejected by researcher"})
    await mission_store.update_mission(db, approval["mission_id"],
                                       {"status": "failed",
                                        "error": f"Step rejected: {body.reason or 'No reason given'}"})
    await mission_store.append_log(
        db, approval["mission_id"], "researcher", "step_rejected",
        f"Action '{approval['action']}' rejected by researcher",
        {"reason": body.reason},
    )
    return {"status": "rejected"}


# ── Agent registry ────────────────────────────────────────────────────────────

@router.get("/agents")
async def get_agents(user=Depends(get_current_user)):
    agents = list_agents(include_internal=False)
    return {
        "agents": agents,
        "total":  len(agents),
        "safety_policy": safety_policy_note(),
    }


@router.get("/agents/{agent_name}")
async def get_agent_detail(agent_name: str, user=Depends(get_current_user)):
    agent = get_agent(agent_name)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


# ── Schedules ─────────────────────────────────────────────────────────────────

@router.get("/schedules")
async def list_schedules(
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await mission_store.list_schedules(db, str(user["_id"]))


@router.post("/schedules")
async def create_schedule(
    body: CreateScheduleRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    if body.interval not in ("daily", "weekly", "monthly"):
        raise HTTPException(400, "interval must be daily, weekly, or monthly")
    schedule_id = await scheduler.create_schedule(
        db, str(user["_id"]), body.title, body.description,
        body.mission_type, body.autonomy_level, body.interval, body.params,
    )
    return {"schedule_id": schedule_id}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    deleted = await mission_store.delete_schedule(db, schedule_id, str(user["_id"]))
    return {"deleted": deleted}


# ── Background monitors ───────────────────────────────────────────────────────

@router.post("/monitors/run")
async def run_monitors(
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Trigger all background monitors for the current user."""
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    user_doc = {k: str(v) if hasattr(v, "__str__") and not isinstance(v, (str, int, float, bool, type(None), dict, list)) else v
                for k, v in user.items()}
    await enqueue_job(
        Job(job_type="mission.monitors",
            payload={"user_id": user_id, "user": user_doc},
            user_id=user_id, priority=Priority.NORMAL),
        db,
    )
    return {"status": "monitors_started", "message": "Background monitors running."}


@router.get("/monitors/alerts")
async def get_monitor_alerts(
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Get recent monitor alerts from ara_logs (mission_id='background')."""
    db = make_db_proxy(db, user)
    docs = await db["ara_logs"].find(
        {"mission_id": "background"},
        {"_id": 0},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return docs


# ── Autonomy info ─────────────────────────────────────────────────────────────

@router.get("/autonomy-levels")
async def get_autonomy_levels(user=Depends(get_current_user)):
    return {
        "levels": [
            {"level": i, "label": autonomy_level_label(i)}
            for i in range(4)
        ],
        "safety_policy": safety_policy_note(),
    }
