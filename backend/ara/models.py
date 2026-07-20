"""Data models for the Autonomous Research Agent system."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class AutonomyLevel(int, Enum):
    MANUAL          = 0   # AI answers only
    ASSIST          = 1   # AI proposes, human executes
    SEMI_AUTONOMOUS = 2   # AI executes safe ops, human approves gates
    AUTONOMOUS      = 3   # AI executes full workflow within permissions


class MissionStatus(str, Enum):
    # Legacy states (kept for backward compat — existing missions use these)
    DRAFT            = "draft"
    PLANNING         = "planning"
    PLAN_REVIEW      = "plan_review"    # awaiting user approval of plan
    AWAITING_HUMAN   = "awaiting_human" # approval gate hit
    # Enterprise lifecycle (new)
    CREATED          = "created"        # alias for draft
    QUEUED           = "queued"         # in execution queue, waiting for worker
    PLANNED          = "planned"        # alias for plan_review
    RUNNING          = "running"
    WAITING          = "waiting"        # alias for awaiting_human
    PAUSED           = "paused"
    RETRYING         = "retrying"       # scheduled for retry with backoff
    COMPLETED        = "completed"
    FAILED           = "failed"
    CANCELLED        = "cancelled"
    ARCHIVED         = "archived"       # retained for history, not active


class MissionPriority(int, Enum):
    EMERGENCY  = 1
    HIGH       = 2
    NORMAL     = 5
    LOW        = 7
    BACKGROUND = 9


# Status groups for UI filtering (frontend tabs)
ACTIVE_STATUSES: frozenset[str] = frozenset({
    "draft", "created", "planning", "queued", "planned", "plan_review",
    "running", "waiting", "awaiting_human", "paused", "retrying",
})
TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed", "cancelled", "archived"})


class StepStatus(str, Enum):
    PENDING          = "pending"
    RUNNING          = "running"
    COMPLETED        = "completed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED         = "approved"
    REJECTED         = "rejected"
    SKIPPED          = "skipped"
    FAILED           = "failed"


class StepType(str, Enum):
    SAFE             = "safe"       # can auto-execute at any level >= 1
    APPROVAL_REQUIRED = "approval"  # always needs human sign-off
    INFORMATIONAL    = "info"       # no side effects, always runs


# ── Actions that ALWAYS require human approval ─────────────────────────────────

IRREVERSIBLE_ACTIONS: set[str] = {
    "submit_manuscript",
    "send_email",
    "apply_for_grant",
    "invite_collaborator",
    "delete_document",
    "publish_report",
    "edit_institution_record",
    "share_private_information",
    "accept_reviewer_invitation",
    "reject_reviewer_comments",
    "modify_verified_record",
    "external_communication",
}

# ── Safe actions (no approval needed) ────────────────────────────────────────

SAFE_ACTIONS: set[str] = {
    "literature_search",
    "citation_analysis",
    "knowledge_graph_update",
    "recommendation_generation",
    "repository_organization",
    "reference_formatting",
    "document_quality_check",
    "trend_monitoring",
    "background_sync",
    "draft_generation",
    "statistical_analysis",
    "reviewer_simulation",
    "journal_search",
    "gap_analysis",
    "teaching_analysis",
    "career_analysis",
    "funding_search",
    "collaboration_suggestions",
}


# ── Step dataclass ─────────────────────────────────────────────────────────────

@dataclass
class MissionStep:
    step_id:       str
    mission_id:    str
    name:          str
    description:   str
    agent_name:    str
    action:        str              # from SAFE_ACTIONS or IRREVERSIBLE_ACTIONS
    step_type:     StepType
    inputs:        dict             # what the step consumes
    outputs:       dict             # what the step produces (filled on completion)
    status:        StepStatus       = StepStatus.PENDING
    depends_on:    list[str]        = field(default_factory=list)  # step_ids
    parallel_with: list[str]        = field(default_factory=list)
    evidence:      list[dict]       = field(default_factory=list)
    confidence:    str              = "not_run"
    error:         Optional[str]    = None
    started_at:    Optional[datetime] = None
    completed_at:  Optional[datetime] = None
    estimated_duration_s: int       = 30

    def to_dict(self) -> dict:
        return {
            "step_id":       self.step_id,
            "mission_id":    self.mission_id,
            "name":          self.name,
            "description":   self.description,
            "agent_name":    self.agent_name,
            "action":        self.action,
            "step_type":     self.step_type.value,
            "inputs":        self.inputs,
            "outputs":       self.outputs,
            "status":        self.status.value,
            "depends_on":    self.depends_on,
            "parallel_with": self.parallel_with,
            "evidence":      self.evidence,
            "confidence":    self.confidence,
            "error":         self.error,
            "started_at":    self.started_at.isoformat() if self.started_at else None,
            "completed_at":  self.completed_at.isoformat() if self.completed_at else None,
            "estimated_duration_s": self.estimated_duration_s,
        }


# ── Approval request ───────────────────────────────────────────────────────────

@dataclass
class ApprovalRequest:
    approval_id:  str
    mission_id:   str
    step_id:      str
    user_id:      str
    action:       str
    description:  str
    proposed_by:  str               # agent name
    data:         dict              # what the agent wants to do (for review)
    evidence:     list[dict]        = field(default_factory=list)
    status:       Literal["pending", "approved", "rejected"] = "pending"
    created_at:   datetime          = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at:  Optional[datetime] = None
    resolved_by:  Optional[str]     = None
    reject_reason: Optional[str]    = None

    def to_dict(self) -> dict:
        return {
            "approval_id":  self.approval_id,
            "mission_id":   self.mission_id,
            "step_id":      self.step_id,
            "user_id":      self.user_id,
            "action":       self.action,
            "description":  self.description,
            "proposed_by":  self.proposed_by,
            "data":         self.data,
            "evidence":     self.evidence,
            "status":       self.status,
            "created_at":   self.created_at.isoformat(),
            "resolved_at":  self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by":  self.resolved_by,
            "reject_reason": self.reject_reason,
        }
