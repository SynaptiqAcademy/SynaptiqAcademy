"""Multi-Agent Research Copilot Router — Phase XXXI.

Endpoints:
  POST /api/copilot/execute           — Stream SSE events from orchestrator
  GET  /api/copilot/agents            — List all registered agents
  GET  /api/copilot/workflows         — List available workflow templates
  POST /api/copilot/workflows/{id}    — Execute a named workflow
  GET  /api/copilot/session/{id}      — Session memory and all outputs
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from agents import orchestrator, REGISTRY
from agents.orchestrator import WORKFLOWS, detect_intent
from repo.shim import make_db_proxy

logger = logging.getLogger("copilot.router")

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


# ── Request / response models ─────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    context:    Optional[dict] = None


class WorkflowExecuteRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None


# ── SSE streaming endpoint ────────────────────────────────────────────────────

@router.post("/execute")
async def execute(
    payload: ExecuteRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Stream multi-agent orchestration results via Server-Sent Events.

    Client reads this as a streaming fetch (not EventSource, since we need POST).
    Each SSE frame is:  data: {json}\n\n
    """
    db = make_db_proxy(db, user)
    async def _stream():
        try:
            async for event in orchestrator.stream_execute(
                user_input = payload.user_input,
                user       = user,
                db         = db,
                session_id = payload.session_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            logger.exception("Stream error: %s", exc)
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(exc)[:200]}})}\n\n"
        finally:
            yield "data: {\"event\": \"done\"}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":      "no-cache",
            "X-Accel-Buffering":  "no",
            "Connection":         "keep-alive",
        },
    )


# ── Non-streaming execute (for environments where SSE isn't practical) ────────

@router.post("/execute/sync")
async def execute_sync(
    payload: ExecuteRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Blocking version — collects all events and returns after completion."""
    db = make_db_proxy(db, user)
    events    = []
    final_evt = None

    async for event in orchestrator.stream_execute(
        user_input = payload.user_input,
        user       = user,
        db         = db,
        session_id = payload.session_id,
    ):
        events.append(event)
        if event.get("event") == "final":
            final_evt = event["data"]

    return {
        "final":  final_evt,
        "events": events,
    }


# ── Agent registry info ───────────────────────────────────────────────────────

@router.get("/agents")
async def list_agents(user=Depends(get_current_user)):
    """Return all registered agents with name, description, mission, capabilities."""
    return {"agents": REGISTRY.info(), "count": len(REGISTRY.names())}


# ── Workflow templates ────────────────────────────────────────────────────────

@router.get("/workflows")
async def list_workflows(user=Depends(get_current_user)):
    """Return all available research workflows."""
    return {
        "workflows": [
            {
                "id":      wid,
                "label":   cfg["label"],
                "stages":  cfg["stages"],
                "phrases": cfg["phrases"][:3],  # sample trigger phrases
            }
            for wid, cfg in WORKFLOWS.items()
            if wid != "general_research"
        ],
        "default_workflow": "general_research",
    }


@router.post("/workflows/{workflow_id}")
async def execute_workflow(
    workflow_id: str,
    payload: WorkflowExecuteRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Execute a specific named workflow (non-streaming).
    Useful for WorkflowLauncher shortcuts.
    """
    db = make_db_proxy(db, user)
    if workflow_id not in WORKFLOWS:
        return {"error": f"Unknown workflow: {workflow_id}"}

    # Override the intent detection by injecting a workflow-specific phrase
    trigger = WORKFLOWS[workflow_id]["phrases"][0] if WORKFLOWS[workflow_id]["phrases"] else ""
    modified_input = f"{trigger}: {payload.user_input}" if trigger else payload.user_input

    events   = []
    final_evt = None
    async for event in orchestrator.stream_execute(
        user_input = modified_input,
        user       = user,
        db         = db,
        session_id = payload.session_id,
    ):
        events.append(event)
        if event.get("event") == "final":
            final_evt = event["data"]

    return {"final": final_evt, "workflow_id": workflow_id}


# ── Intent detection ──────────────────────────────────────────────────────────

@router.post("/detect-intent")
async def detect_intent_endpoint(
    payload: ExecuteRequest,
    user=Depends(get_current_user),
):
    """Preview which workflow would be selected without running it."""
    wid = detect_intent(payload.user_input)
    cfg = WORKFLOWS[wid]
    return {
        "workflow_id":   wid,
        "workflow_label": cfg["label"],
        "agents":        [a for s in cfg["stages"] for a in s],
        "stages":        cfg["stages"],
    }
