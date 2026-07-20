"""Academic Copilot — Domain models (Phase XI)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class IntentType(str, Enum):
    MANUSCRIPT_REVIEW   = "manuscript_review"
    LITERATURE_REVIEW   = "literature_review"
    GAP_ANALYSIS        = "gap_analysis"
    STATISTICAL_REVIEW  = "statistical_review"
    JOURNAL_REC         = "journal_recommendation"
    GRANT_GUIDANCE      = "grant_guidance"
    CONFERENCE_GUIDANCE = "conference_guidance"
    METHODOLOGY_ADVICE  = "methodology_advice"
    CAREER_PLANNING     = "career_planning"
    WRITING_COACHING    = "writing_coaching"
    ROADMAP_REQUEST     = "roadmap_request"
    PROJECT_PLANNING    = "project_planning"
    GENERAL_CHAT        = "general_chat"


class RoadmapType(str, Enum):
    RESEARCH    = "research"
    PUBLICATION = "publication"
    GRANT       = "grant"
    CONFERENCE  = "conference"
    CAREER      = "career"
    DOCTORAL    = "doctoral"
    INSTITUTION = "institution"


class SuggestionCategory(str, Enum):
    CITATION      = "citation"
    GRANT         = "grant"
    CONFERENCE    = "conference"
    METHODOLOGY   = "methodology"
    JOURNAL       = "journal"
    COLLABORATION = "collaboration"
    MANUSCRIPT    = "manuscript"
    STATISTICS    = "statistics"
    DEADLINE      = "deadline"
    CAREER        = "career"


class Urgency(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class WorkflowStatus(str, Enum):
    PLANNED   = "planned"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    PARTIAL   = "partial"


# ── Core dataclasses ──────────────────────────────────────────────────────────

@dataclass
class DetectedIntent:
    intent_type: IntentType
    confidence: float          # 0.0–1.0
    signals: list[str] = field(default_factory=list)
    requires_engines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "intent_type": self.intent_type.value,
            "confidence": round(self.confidence, 3),
            "signals": self.signals,
            "requires_engines": self.requires_engines,
        }


@dataclass
class WorkflowStep:
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    engine: str = ""           # e.g., "manuscript", "literature", "gap", "statistical"
    title: str = ""
    description: str = ""
    status: str = "pending"    # pending | running | completed | failed | skipped
    result: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    is_parallel: bool = False
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "engine": self.engine,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "is_parallel": self.is_parallel,
            "result_preview": {k: v for k, v in self.result.items() if k != "raw_output"}
            if self.result else {},
        }


@dataclass
class CopilotWorkflow:
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    trigger_message: str = ""
    intents: list[DetectedIntent] = field(default_factory=list)
    steps: list[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PLANNED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    total_credits: int = 0

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "trigger_message": self.trigger_message[:200],
            "intents": [i.to_dict() for i in self.intents],
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_credits": self.total_credits,
        }


@dataclass
class ProactiveSuggestion:
    suggestion_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    category: SuggestionCategory = SuggestionCategory.MANUSCRIPT
    title: str = ""
    description: str = ""
    urgency: Urgency = Urgency.LOW
    confidence: float = 0.5
    action_type: str = ""          # e.g., "open_manuscript", "submit_grant"
    action_params: dict = field(default_factory=dict)
    source_engine: str = "rule"
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "suggestion_id": self.suggestion_id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "urgency": self.urgency.value,
            "confidence": round(self.confidence, 3),
            "action_type": self.action_type,
            "action_params": self.action_params,
            "source_engine": self.source_engine,
            "rationale": self.rationale,
        }


@dataclass
class RoadmapMilestone:
    week: int
    title: str
    deliverable: str
    is_critical: bool = False

    def to_dict(self) -> dict:
        return {
            "week": self.week,
            "title": self.title,
            "deliverable": self.deliverable,
            "is_critical": self.is_critical,
        }


@dataclass
class RoadmapPhase:
    phase: int
    title: str
    duration_weeks: int
    objectives: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    milestones: list[RoadmapMilestone] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "title": self.title,
            "duration_weeks": self.duration_weeks,
            "objectives": self.objectives,
            "tasks": self.tasks,
            "milestones": [m.to_dict() for m in self.milestones],
            "risks": self.risks,
        }


@dataclass
class AcademicRoadmap:
    roadmap_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    roadmap_type: RoadmapType = RoadmapType.RESEARCH
    title: str = ""
    description: str = ""
    phases: list[RoadmapPhase] = field(default_factory=list)
    total_weeks: int = 0
    key_milestones: list[str] = field(default_factory=list)
    success_indicators: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    ai_narrative: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "roadmap_id": self.roadmap_id,
            "roadmap_type": self.roadmap_type.value,
            "title": self.title,
            "description": self.description,
            "phases": [p.to_dict() for p in self.phases],
            "total_weeks": self.total_weeks,
            "key_milestones": self.key_milestones,
            "success_indicators": self.success_indicators,
            "risk_factors": self.risk_factors,
            "ai_narrative": self.ai_narrative,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DashboardWidget:
    widget_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    widget_type: str = ""
    title: str = ""
    data: dict = field(default_factory=dict)
    priority: int = 50
    urgency: Urgency = Urgency.LOW

    def to_dict(self) -> dict:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "title": self.title,
            "data": self.data,
            "priority": self.priority,
            "urgency": self.urgency.value,
        }


@dataclass
class CopilotDashboard:
    user_id: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active_projects: list[dict] = field(default_factory=list)
    upcoming_deadlines: list[dict] = field(default_factory=list)
    publication_readiness: list[dict] = field(default_factory=list)
    grant_opportunities: int = 0
    conference_opportunities: int = 0
    recommended_actions: list[dict] = field(default_factory=list)
    ai_insights: list[str] = field(default_factory=list)
    research_goals: list[str] = field(default_factory=list)
    widgets: list[DashboardWidget] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "generated_at": self.generated_at.isoformat(),
            "active_projects": self.active_projects,
            "upcoming_deadlines": self.upcoming_deadlines,
            "publication_readiness": self.publication_readiness,
            "grant_opportunities": self.grant_opportunities,
            "conference_opportunities": self.conference_opportunities,
            "recommended_actions": self.recommended_actions,
            "ai_insights": self.ai_insights,
            "research_goals": self.research_goals,
            "widgets": [w.to_dict() for w in self.widgets],
        }


@dataclass
class CopilotResponse:
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    message: str = ""
    intents: list[DetectedIntent] = field(default_factory=list)
    workflow: CopilotWorkflow | None = None
    engine_results: dict = field(default_factory=dict)
    suggested_actions: list[dict] = field(default_factory=list)
    proactive_suggestions: list[ProactiveSuggestion] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    agent_type: str = "copilot"
    tokens_used: int = 0
    latency_ms: float = 0.0
    roadmap: AcademicRoadmap | None = None

    def to_dict(self) -> dict:
        return {
            "response_id": self.response_id,
            "message": self.message,
            "intents": [i.to_dict() for i in self.intents],
            "workflow": self.workflow.to_dict() if self.workflow else None,
            "engine_results": self.engine_results,
            "suggested_actions": self.suggested_actions,
            "proactive_suggestions": [s.to_dict() for s in self.proactive_suggestions],
            "sources": self.sources,
            "reasoning": self.reasoning,
            "confidence": round(self.confidence, 3),
            "agent_type": self.agent_type,
            "tokens_used": self.tokens_used,
            "latency_ms": round(self.latency_ms, 1),
            "roadmap": self.roadmap.to_dict() if self.roadmap else None,
        }
