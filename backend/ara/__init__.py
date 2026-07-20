"""
Autonomous Research Agents (ARA) — Phase XXXIV.

An autonomous academic execution layer built ON TOP of the existing AI architecture.

  Level 0 — Manual:          AI answers only
  Level 1 — Assist:          AI proposes, human executes
  Level 2 — Semi-Autonomous: AI executes safe actions, human approves gates
  Level 3 — Autonomous:      AI executes complete workflows within permissions

SAFETY GUARANTEE: Agents NEVER submit, publish, email, apply, or share without
explicit human approval — regardless of autonomy level.

Extends, does NOT replace:
  - Multi-Agent Research Copilot (Phase XXXI)
  - All existing AI tools
  - All existing routes and APIs

MongoDB collections:
  ara_missions    — mission documents (persistent across sessions)
  ara_steps       — per-step records for each mission
  ara_approvals   — pending + resolved human approval requests
  ara_logs        — append-only execution audit log
  ara_schedules   — recurring scheduled mission templates
"""
from . import (
    models,
    mission_store,
    agent_registry,
    mission_planner,
    orchestrator,
    safe_autonomy,
    validation_agent,
    scheduler,
    background_agents,
    mission_memory,
)

__all__ = [
    "models", "mission_store", "agent_registry", "mission_planner",
    "orchestrator", "safe_autonomy", "validation_agent",
    "scheduler", "background_agents", "mission_memory",
]
