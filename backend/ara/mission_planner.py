"""
Mission Planner — converts a mission description into an executable workflow plan.

Steps:
  1. Extract intent from description (keyword + optional LLM)
  2. Select recommended agents via agent_registry
  3. Build step sequence with dependencies
  4. Estimate total credits
  5. Persist plan + transition mission to "plan_review"
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from .agent_registry import agents_for_mission_type, get_agent
from .models import StepType
from .safe_autonomy import classify_step
from . import mission_store

logger = logging.getLogger("ara.planner")

# ── Intent extraction ──────────────────────────────────────────────────────────

_INTENT_KEYWORDS: dict[str, str] = {
    "manuscript":    "manuscript",
    "paper":         "manuscript",
    "article":       "manuscript",
    "submit":        "manuscript",
    "write":         "manuscript",
    "literature":    "literature",
    "review":        "review",
    "funding":       "funding",
    "grant":         "funding",
    "monitor":       "monitor",
    "watch":         "monitor",
    "collaborat":    "collaboration",
    "colleague":     "collaboration",
    "career":        "career",
    "teach":         "teaching",
    "lesson":        "teaching",
    "repository":    "repository",
    "organize":      "repository",
    "institution":   "institution",
    "department":    "institution",
    "discover":      "literature",
    "analysis":      "review",
    "statistic":     "review",
}


def _detect_intent(description: str, mission_type: str) -> str:
    """Return a mission_type keyword used by agents_for_mission_type."""
    if mission_type and mission_type != "general":
        return mission_type
    lower = description.lower()
    for keyword, mtype in _INTENT_KEYWORDS.items():
        if keyword in lower:
            return mtype
    return "literature"


# ── Step builder ───────────────────────────────────────────────────────────────

def _build_steps(mission_id: str, agent_names: list[str],
                 params: dict, description: str) -> list[dict]:
    steps = []
    prev_step_id: str | None = None

    for i, agent_name in enumerate(agent_names):
        agent = get_agent(agent_name)
        if not agent:
            continue

        step_id   = f"step_{i+1}_{agent_name}"
        action    = (agent["safe_actions"] + agent.get("approval_required_actions", []))
        action    = action[0] if action else "document_quality_check"
        step_type = classify_step(action)

        step = {
            "step_id":       step_id,
            "mission_id":    mission_id,
            "step_number":   i + 1,
            "name":          agent["label"],
            "description":   agent["mission"],
            "agent_name":    agent_name,
            "action":        action,
            "step_type":     step_type.value,
            "inputs":        {k: params.get(k, "") for k in agent["inputs"]},
            "outputs":       {},
            "status":        "pending",
            "depends_on":    [prev_step_id] if prev_step_id else [],
            "parallel_with": [],
            "evidence":      [],
            "confidence":    "not_run",
            "error":         None,
            "started_at":    None,
            "completed_at":  None,
            "estimated_duration_s": agent.get("estimated_duration_s", 30),
        }
        steps.append(step)
        prev_step_id = step_id

    # Always end with validation step
    val_agent = get_agent("validation")
    if val_agent:
        val_id = f"step_{len(steps)+1}_validation"
        steps.append({
            "step_id":       val_id,
            "mission_id":    mission_id,
            "step_number":   len(steps) + 1,
            "name":          "Validation",
            "description":   "Quality-check all outputs for evidence compliance and consistency",
            "agent_name":    "validation",
            "action":        "document_quality_check",
            "step_type":     StepType.SAFE.value,
            "inputs":        {},
            "outputs":       {},
            "status":        "pending",
            "depends_on":    [prev_step_id] if prev_step_id else [],
            "parallel_with": [],
            "evidence":      [],
            "confidence":    "not_run",
            "error":         None,
            "started_at":    None,
            "completed_at":  None,
            "estimated_duration_s": val_agent.get("estimated_duration_s", 15),
        })

    return steps


def _estimate_credits(agent_names: list[str]) -> int:
    total = 1  # validation
    for name in agent_names:
        agent = get_agent(name)
        if agent:
            total += agent.get("cost_estimate_credits", 2)
    return total


# ── Public API ─────────────────────────────────────────────────────────────────

async def generate_plan(db, mission_id: str, description: str,
                        mission_type: str, params: dict,
                        user_context: dict | None = None) -> list[dict]:
    """
    Generate an execution plan for a mission.
    Stores plan in ara_missions (status → plan_review) and ara_steps.
    Returns the step list.
    """
    await mission_store.update_mission(db, mission_id, {"status": "planning"})

    intent      = _detect_intent(description, mission_type)
    agent_names = agents_for_mission_type(intent)

    logger.info("Mission %s: intent=%s agents=%s", mission_id, intent, agent_names)

    steps            = _build_steps(mission_id, agent_names, params, description)
    estimated_credits = _estimate_credits(agent_names)

    # Persist steps
    for step in steps:
        await mission_store.upsert_step(db, step)

    # Persist plan summary + transition to plan_review
    plan_summary = [
        {
            "step_number": s["step_number"],
            "step_id":     s["step_id"],
            "name":        s["name"],
            "agent_name":  s["agent_name"],
            "step_type":   s["step_type"],
            "action":      s["action"],
            "depends_on":  s["depends_on"],
            "estimated_duration_s": s["estimated_duration_s"],
        }
        for s in steps
    ]
    await mission_store.set_plan(db, mission_id, plan_summary, estimated_credits)
    await mission_store.append_log(db, mission_id, "planner", "plan_generated",
                                   f"Generated {len(steps)} steps for intent '{intent}'",
                                   {"intent": intent, "agents": agent_names})

    return steps


async def refine_plan(db, mission_id: str, approved_agents: list[str],
                      params: dict) -> list[dict]:
    """
    Regenerate plan with a user-curated agent list (e.g. after plan_review).
    """
    mission = await mission_store.get_mission(db, mission_id)
    if not mission:
        raise ValueError("Mission not found")

    steps            = _build_steps(mission_id, approved_agents, params, mission.get("description", ""))
    estimated_credits = _estimate_credits(approved_agents)

    for step in steps:
        await mission_store.upsert_step(db, step)

    plan_summary = [
        {k: s[k] for k in ("step_number","step_id","name","agent_name","step_type",
                            "action","depends_on","estimated_duration_s")}
        for s in steps
    ]
    await mission_store.set_plan(db, mission_id, plan_summary, estimated_credits)
    return steps
