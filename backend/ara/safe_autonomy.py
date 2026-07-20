"""
Safe autonomy checker.

Determines whether a step can auto-execute or requires human approval,
based on the action type and the mission's autonomy level.
"""
from __future__ import annotations

from .models import AutonomyLevel, StepType, IRREVERSIBLE_ACTIONS, SAFE_ACTIONS


def can_auto_execute(action: str, autonomy_level: int) -> bool:
    """
    Returns True if this action can run without human approval.

    Rules:
      - L0 (Manual):          Nothing auto-executes.
      - L1 (Assist):          Safe actions only.
      - L2 (Semi-Autonomous): Safe actions only.
      - L3 (Autonomous):      Safe actions only — irreversible NEVER auto-execute.

    Irreversible actions (submit, email, apply, delete, publish, share) ALWAYS
    require human approval regardless of autonomy level.
    """
    if action in IRREVERSIBLE_ACTIONS:
        return False  # NEVER auto-execute — no matter the level

    if autonomy_level == AutonomyLevel.MANUAL:
        return False

    if action in SAFE_ACTIONS:
        return True

    # Unknown action — conservative default: require approval
    return False


def needs_approval(action: str) -> bool:
    """Returns True if this action always needs human sign-off."""
    return action in IRREVERSIBLE_ACTIONS


def classify_step(action: str) -> StepType:
    if action in IRREVERSIBLE_ACTIONS:
        return StepType.APPROVAL_REQUIRED
    if action in SAFE_ACTIONS:
        return StepType.SAFE
    return StepType.APPROVAL_REQUIRED  # unknown → safe choice


def autonomy_level_label(level: int) -> str:
    return {
        0: "Manual — AI answers only, you execute everything",
        1: "Assist — AI proposes actions, you execute",
        2: "Semi-Autonomous — AI executes safe operations, you approve important decisions",
        3: "Autonomous — AI executes complete workflows; irreversible actions still require your approval",
    }.get(level, "Unknown")


def safety_policy_note() -> str:
    return (
        "SAFETY GUARANTEE: Autonomous Agents NEVER submit manuscripts, send emails, "
        "apply for grants, invite collaborators, delete documents, publish reports, "
        "or communicate externally without explicit researcher approval. "
        "The researcher remains solely responsible for all scientific and ethical decisions."
    )
