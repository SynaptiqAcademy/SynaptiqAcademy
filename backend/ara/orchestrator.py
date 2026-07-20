"""
Mission Orchestrator — thin coordination layer.

Phase XXXV.2 change: execution is now handled by the durable MissionWorker.
This module keeps the AI execution logic (unchanged) and becomes the
coordination point between the router and the engine.

Public API (called by routers/ara.py — UNCHANGED):
  run_mission(db, mission_id, user_id, user, autonomy_level)
  resume_after_approval(db, mission_id, user_id, user, autonomy_level)

Internal helpers (imported by engine/worker.py — UNCHANGED behavior):
  _execute_step(db, step, memory, user)
  _create_approval_gate(db, step, user_id)
  _extract_section(text, section)
  _extract_confidence(text)
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from services.ai.llm import call_llm

from .agent_registry import get_agent
from .models import AutonomyLevel, StepStatus, StepType
from .safe_autonomy import can_auto_execute
from . import mission_memory as mem_store
from . import mission_store
from . import validation_agent

logger = logging.getLogger("ara.orchestrator")


# ── Public API (router interface — identical signatures to before) ─────────────

async def run_mission(db, mission_id: str, user_id: str, user: dict,
                      autonomy_level: int) -> None:
    """
    Enqueue mission for durable execution by the MissionWorker.

    Previously: executed inline as a BackgroundTask (lost on restart).
    Now: enqueues to ExecutionQueue → Worker picks up → checkpoints every step.
    The router calls this exactly as before (BackgroundTask); behavior is identical
    from the caller's perspective, but execution is now crash-safe.
    """
    from ara.engine import get_queue
    await mission_store.mark_queued(db, mission_id)
    await mission_store.append_log(db, mission_id, "orchestrator", "queued",
                                   f"Mission enqueued for execution (autonomy_level={autonomy_level})")
    await get_queue().enqueue(mission_id, priority=5)
    logger.info("Mission %s enqueued by orchestrator", mission_id)


async def resume_after_approval(db, mission_id: str, user_id: str,
                                user: dict, autonomy_level: int) -> None:
    """
    Resume execution after a human approval is granted.
    Marks the approved step and requeues at HIGH priority.
    """
    from ara.engine import get_queue

    steps = await mission_store.get_steps(db, mission_id)
    for step in steps:
        if step.get("status") == StepStatus.AWAITING_APPROVAL.value:
            await mission_store.update_step(db, mission_id, step["step_id"], {
                "status":     StepStatus.APPROVED.value,
                "started_at": datetime.now(timezone.utc).isoformat(),
            })

    await mission_store.update_mission(db, mission_id, {"status": "queued"})
    await mission_store.append_log(db, mission_id, "orchestrator", "resumed",
                                   "Mission requeued after human approval")
    # HIGH priority: was already in progress before the approval gate
    await get_queue().enqueue(mission_id, priority=2)
    logger.info("Mission %s requeued after approval", mission_id)


# ── Step execution (AI behavior — UNCHANGED from Phase XXXIV) ─────────────────
# These are imported by engine/worker.py; modifying them changes AI behavior.

async def _execute_step(db, step: dict, memory: mem_store.MissionMemory,
                        user: dict) -> dict:
    """
    Execute a single step. Returns updated step dict.
    All outputs go into mission memory for downstream agents.
    AI prompting behavior is identical to Phase XXXIV.
    """
    step_id  = step["step_id"]
    agent    = get_agent(step["agent_name"])
    if not agent:
        raise RuntimeError(f"Unknown agent: {step['agent_name']}")

    # Collect inputs from memory (previous step outputs)
    resolved_inputs = dict(step.get("inputs") or {})
    for dep_id in step.get("depends_on") or []:
        dep_out = memory.get_step_output(dep_id)
        if dep_out:
            resolved_inputs.update(dep_out)

    system = (
        f"You are the {agent['label']} operating as part of an autonomous research workflow. "
        f"Mission: {agent['mission']}\n\n"
        "CRITICAL EVIDENCE POLICY: You must NEVER invent statistics, percentages, probabilities, "
        "or benchmark numbers. You MUST trace every claim to verified data from the inputs provided. "
        "If you have insufficient data, explicitly state: "
        "'Insufficient data to provide a reliable answer for this step.' "
        "Label all outputs with confidence: high (3+ sources), medium (2 sources), "
        "low (1 source), or insufficient (0 sources). "
        "NEVER output confidence as a percentage."
    )

    user_msg = (
        f"Execute this research workflow step:\n"
        f"Step: {step['name']}\n"
        f"Description: {step['description']}\n\n"
        f"Researcher context: name={user.get('name','')}, "
        f"institution={user.get('institution','')}, "
        f"research_interests={user.get('research_interests','')}\n\n"
        f"Available inputs:\n{resolved_inputs}\n\n"
        "Provide a structured analysis with: "
        "summary (what was done), findings (list of specific results with evidence), "
        "confidence (high/medium/low/insufficient), "
        "limitations (what could not be verified), "
        "next_steps (recommended follow-up)."
    )

    try:
        response = await call_llm(
            system=system,
            user_msg=user_msg,
            feature=f"ara_{step['agent_name']}",
            user_id=str(user.get("_id") or user.get("user_id") or ""),
            mission_id=step.get("mission_id", ""),
            db=db,
        )
        outputs = {
            "summary":     _extract_section(response, "summary"),
            "findings":    _extract_section(response, "findings"),
            "confidence":  _extract_confidence(response),
            "limitations": _extract_section(response, "limitations"),
            "next_steps":  _extract_section(response, "next_steps"),
            "raw":         response[:2000],
        }
        evidence = [{"source": agent["evidence_sources"][0], "type": "ai_analysis",
                     "note": "Derived from available platform data"}]
        status    = StepStatus.COMPLETED.value
        error     = None
        confidence = outputs["confidence"]
    except Exception as exc:
        logger.error("Step %s failed: %s", step_id, exc)
        outputs    = {}
        evidence   = []
        status     = StepStatus.FAILED.value
        error      = str(exc)
        confidence = "not_run"

    now = datetime.now(timezone.utc).isoformat()
    memory.set_step_output(step_id, outputs)

    return {
        **step,
        "status":       status,
        "outputs":      outputs,
        "evidence":     evidence,
        "confidence":   confidence,
        "error":        error,
        "completed_at": now,
    }


def _extract_section(text: str, section: str) -> str:
    import re
    pattern = re.compile(
        rf"(?i){re.escape(section)}\s*[:\-]?\s*(.*?)(?=\n[A-Z][a-z]|\Z)", re.DOTALL
    )
    m = pattern.search(text)
    if m:
        return m.group(1).strip()[:1500]
    return ""


def _extract_confidence(text: str) -> str:
    import re
    m = re.search(r"(?i)confidence\s*[:\-]\s*(high|medium|low|insufficient)", text)
    if m:
        return m.group(1).lower()
    return "low"


# ── Approval gate (imported by engine/worker.py) ───────────────────────────────

async def _create_approval_gate(db, step: dict, user_id: str) -> str:
    """Insert an approval request and pause step execution."""
    approval_id = str(uuid.uuid4())
    agent = get_agent(step["agent_name"])
    await mission_store.create_approval(db, {
        "approval_id":  approval_id,
        "mission_id":   step["mission_id"],
        "step_id":      step["step_id"],
        "user_id":      user_id,
        "action":       step["action"],
        "description":  step["description"],
        "proposed_by":  step["agent_name"],
        "data":         {"inputs": step.get("inputs", {}), "step_name": step["name"]},
        "evidence":     [],
        "status":       "pending",
    })
    await mission_store.update_step(db, step["mission_id"], step["step_id"], {
        "status":      StepStatus.AWAITING_APPROVAL.value,
        "approval_id": approval_id,
    })
    return approval_id
