"""Autonomous Research Agents Platform — Router (Phase XIII).

User routes:   /api/agents/*
Admin routes:  /api/admin/agents/*
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.credits_service import consume_credits
from services.agents import get_agent_engine
from services.agents.models import AgentType, WorkflowType
from services.agents.telemetry import get_telemetry
from repo.shim import make_db_proxy

router       = APIRouter(prefix="/api/agents", tags=["agents"])
admin_router = APIRouter(prefix="/api/admin/agents", tags=["admin-agents"])


# ── Request schemas ───────────────────────────────────────────────────────────

class WorkflowRunRequest(BaseModel):
    workflow_type: str
    content: str = Field(..., min_length=10)
    metadata: Optional[dict] = None


class TaskRequest(BaseModel):
    message: str = Field(..., min_length=3)
    content: str = Field(..., min_length=10)
    metadata: Optional[dict] = None


class AgentRunRequest(BaseModel):
    agent_type: str
    content: str = Field(..., min_length=5)
    metadata: Optional[dict] = None


class ParallelAgentRequest(BaseModel):
    agent_types: list[str] = Field(..., min_items=1, max_items=10)
    content: str = Field(..., min_length=5)
    metadata: Optional[dict] = None


class ComposeWorkflowRequest(BaseModel):
    agent_sequence: list[str] = Field(..., min_items=1, max_items=20)
    content: str = Field(..., min_length=10)
    metadata: Optional[dict] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _deduct(user: dict, key: str, db) -> None:
    await consume_credits(str(user.get("_id") or user.get("id", "")), key)


def _ok(data) -> dict:
    return {"status": "success", "data": data}


# ── User endpoints ────────────────────────────────────────────────────────────

@router.post("/workflow/run")
async def run_workflow(
    body: WorkflowRunRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Execute a named multi-agent workflow end-to-end."""
    db = make_db_proxy(db, user)
    try:
        wf_type = WorkflowType(body.workflow_type)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Unknown workflow_type: {body.workflow_type}")
    try:
        await _deduct(user, "agents_workflow_run", db)
        engine = await get_agent_engine()
        response = await engine.run_workflow(
            wf_type, body.content, str(user["_id"]), body.metadata
        )
        return _ok(response.to_dict())
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/task")
async def run_task(
    body: TaskRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Auto-detect the best workflow for a free-text request and execute it."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "agents_task_run", db)
        engine = await get_agent_engine()
        response = await engine.run_task(
            body.message, body.content, str(user["_id"]), body.metadata
        )
        return _ok(response.to_dict())
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/run")
async def run_single_agent(
    body: AgentRunRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Execute a single named agent."""
    db = make_db_proxy(db, user)
    try:
        agent_type = AgentType(body.agent_type)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Unknown agent_type: {body.agent_type}")
    try:
        await _deduct(user, "agents_single_run", db)
        engine = await get_agent_engine()
        result = await engine.run_agent(agent_type, body.content, str(user["_id"]), body.metadata)
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/run/parallel")
async def run_parallel_agents(
    body: ParallelAgentRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Execute multiple agents in parallel and return all results."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "agents_parallel_run", db)
        engine = await get_agent_engine()
        results = await engine.run_agents_parallel(
            body.agent_types, body.content, str(user["_id"]), body.metadata
        )
        return _ok(results)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/compose")
async def compose_workflow(
    body: ComposeWorkflowRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Compose and execute a custom agent sequence."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "agents_workflow_run", db)
        engine = await get_agent_engine()
        results = await engine.run_agents_parallel(
            body.agent_sequence, body.content, str(user["_id"]), body.metadata
        )
        return _ok(results)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get("/list")
async def list_agents(user: dict = Depends(get_current_user)):
    """List all registered agents and their capabilities."""
    engine = await get_agent_engine()
    return _ok(engine.list_agents())


@router.get("/workflow/templates")
async def list_workflow_templates(user: dict = Depends(get_current_user)):
    """List all available workflow templates."""
    engine = await get_agent_engine()
    return _ok(engine.list_workflows())


@router.get("/{agent_type}/info")
async def get_agent_info(
    agent_type: str,
    user: dict = Depends(get_current_user),
):
    """Get capabilities and metadata for a specific agent."""
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown agent: {agent_type}")
    try:
        engine = await get_agent_engine()
        return _ok(engine.agent_info(at))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.get("/operations")
async def admin_operations(user: dict = Depends(get_current_user)):
    snap = get_telemetry().snapshot()
    return {
        "status": "success",
        "total_runs": snap["workflow_runs"] + snap["ad_hoc_runs"],
        "total_agent_invocations": snap["total_agent_invocations"],
        "errors": snap["errors"],
        "latency_avg_s": snap["latency_avg_s"],
        "breakdown": snap,
    }


@admin_router.get("/telemetry")
async def admin_telemetry(user: dict = Depends(get_current_user)):
    return {"status": "success", "telemetry": get_telemetry().snapshot()}


@admin_router.post("/telemetry/reset")
async def reset_telemetry(user: dict = Depends(get_current_user)):
    get_telemetry().reset()
    return {"status": "success", "message": "Agent platform telemetry reset."}
