"""Autonomous Research Agents Platform — Domain models (Phase XIII)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class AgentType(str, Enum):
    LITERATURE_REVIEW    = "literature_review"
    RESEARCH_GAP         = "research_gap"
    METHODOLOGY          = "methodology"
    STATISTICS           = "statistics"
    ACADEMIC_WRITING     = "academic_writing"
    JOURNAL_INTELLIGENCE = "journal_intelligence"
    CONFERENCE_INTELLIGENCE = "conference_intelligence"
    GRANT_INTELLIGENCE   = "grant_intelligence"
    CITATION_INTELLIGENCE = "citation_intelligence"
    RESEARCH_ETHICS      = "research_ethics"
    DATA_ANALYSIS        = "data_analysis"
    TEACHING             = "teaching"
    CAREER_DEVELOPMENT   = "career_development"
    COLLABORATION        = "collaboration"
    PEER_REVIEW          = "peer_review"
    SUPERVISOR           = "supervisor"
    PUBLICATION_STRATEGY = "publication_strategy"
    RESEARCH_PLANNING    = "research_planning"
    TIMELINE             = "timeline"
    KNOWLEDGE_GRAPH      = "knowledge_graph"


class ExecutionMode(str, Enum):
    PARALLEL   = "parallel"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    DYNAMIC    = "dynamic"


class WorkflowType(str, Enum):
    LITERATURE_REVIEW    = "literature_review_workflow"
    PUBLICATION          = "publication_workflow"
    GRANT                = "grant_workflow"
    DOCTORAL             = "doctoral_workflow"
    JOURNAL_SUBMISSION   = "journal_submission_workflow"
    CONFERENCE           = "conference_workflow"
    RESEARCH_PROPOSAL    = "research_proposal_workflow"
    SYSTEMATIC_REVIEW    = "systematic_review_workflow"
    TEACHING             = "teaching_workflow"
    INSTITUTION          = "institution_workflow"


class AgentStatus(str, Enum):
    IDLE      = "idle"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    RETRYING  = "retrying"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class QualityLevel(str, Enum):
    EXCELLENT    = "excellent"
    GOOD         = "good"
    ACCEPTABLE   = "acceptable"
    POOR         = "poor"
    UNACCEPTABLE = "unacceptable"


class MessageType(str, Enum):
    REQUEST    = "request"
    RESPONSE   = "response"
    VALIDATION = "validation"
    FEEDBACK   = "feedback"
    HANDOFF    = "handoff"


# ── Core task and result ──────────────────────────────────────────────────────

@dataclass
class AgentTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    agent_type: AgentType = AgentType.SUPERVISOR
    content: str = ""
    metadata: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str] = field(default_factory=list)
    timeout_seconds: int = 60
    retry_count: int = 2
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "agent_type": self.agent_type.value,
            "content": self.content[:500],
            "metadata": self.metadata,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
        }


@dataclass
class AgentResult:
    task_id: str = ""
    agent_id: str = ""
    agent_type: AgentType = AgentType.SUPERVISOR
    status: AgentStatus = AgentStatus.COMPLETED
    output: dict = field(default_factory=dict)
    confidence: float = 0.7
    reasoning: str = ""
    evidence: list[str] = field(default_factory=list)
    alternatives: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    latency_seconds: float = 0.0
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "output": self.output,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "evidence": self.evidence[:5],
            "alternatives": self.alternatives[:3],
            "latency_seconds": round(self.latency_seconds, 3),
        }


# ── Inter-agent communication ─────────────────────────────────────────────────

@dataclass
class AgentMessage:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    from_agent: str = ""
    to_agent: str = ""
    content: dict = field(default_factory=dict)
    message_type: MessageType = MessageType.REQUEST
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
        }


# ── Shared context ────────────────────────────────────────────────────────────

@dataclass
class AgentContext:
    user_id: str = ""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    memory: dict = field(default_factory=dict)
    user_profile: dict = field(default_factory=dict)
    project_data: dict = field(default_factory=dict)
    previous_results: dict = field(default_factory=dict)  # agent_type.value → AgentResult

    def add_result(self, result: AgentResult) -> None:
        self.previous_results[result.agent_type.value] = result

    def get_result(self, agent_type: AgentType) -> AgentResult | None:
        return self.previous_results.get(agent_type.value)


# ── Workflow ──────────────────────────────────────────────────────────────────

@dataclass
class WorkflowStep:
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_type: AgentType = AgentType.SUPERVISOR
    name: str = ""
    description: str = ""
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    depends_on: list[str] = field(default_factory=list)   # step_ids
    required: bool = True
    timeout_seconds: int = 60
    retry_count: int = 2
    condition: str = ""  # evaluated expression e.g. "confidence > 0.5"

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "execution_mode": self.execution_mode.value,
            "depends_on": self.depends_on,
            "required": self.required,
        }


@dataclass
class WorkflowTemplate:
    workflow_type: WorkflowType = WorkflowType.PUBLICATION
    name: str = ""
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    estimated_minutes: int = 5

    def to_dict(self) -> dict:
        return {
            "workflow_type": self.workflow_type.value,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_minutes": self.estimated_minutes,
            "agent_count": len(self.steps),
        }


@dataclass
class WorkflowExecution:
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_type: WorkflowType = WorkflowType.PUBLICATION
    user_id: str = ""
    status: AgentStatus = AgentStatus.RUNNING
    steps: list[WorkflowStep] = field(default_factory=list)
    results: dict = field(default_factory=dict)  # step_id → AgentResult
    messages: list[AgentMessage] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "workflow_type": self.workflow_type.value,
            "user_id": self.user_id,
            "status": self.status.value,
            "step_count": len(self.steps),
            "completed_steps": sum(
                1 for r in self.results.values()
                if isinstance(r, AgentResult) and r.status == AgentStatus.COMPLETED
            ),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "results": {k: v.to_dict() for k, v in self.results.items() if isinstance(v, AgentResult)},
        }


# ── Quality control ───────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    agent_type: AgentType = AgentType.SUPERVISOR
    is_valid: bool = True
    quality_level: QualityLevel = QualityLevel.GOOD
    issues: list[str] = field(default_factory=list)
    confidence_after_validation: float = 0.7
    hallucination_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_type": self.agent_type.value,
            "is_valid": self.is_valid,
            "quality_level": self.quality_level.value,
            "issues": self.issues,
            "confidence_after_validation": round(self.confidence_after_validation, 3),
            "hallucination_flags": self.hallucination_flags,
        }


@dataclass
class QualityReport:
    execution_id: str = ""
    overall_quality: QualityLevel = QualityLevel.GOOD
    agent_reports: dict = field(default_factory=dict)  # agent_type → ValidationResult
    inconsistencies: list[str] = field(default_factory=list)
    hallucination_flags: list[str] = field(default_factory=list)
    citation_issues: list[str] = field(default_factory=list)
    methodology_issues: list[str] = field(default_factory=list)
    overall_confidence: float = 0.7
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "overall_quality": self.overall_quality.value,
            "agent_reports": {k: v.to_dict() if isinstance(v, ValidationResult) else v
                              for k, v in self.agent_reports.items()},
            "inconsistencies": self.inconsistencies,
            "hallucination_flags": self.hallucination_flags,
            "citation_issues": self.citation_issues,
            "methodology_issues": self.methodology_issues,
            "overall_confidence": round(self.overall_confidence, 3),
            "recommendations": self.recommendations,
        }


# ── Execution graph (for admin visualisation) ─────────────────────────────────

@dataclass
class GraphNode:
    node_id: str = ""
    agent_type: str = ""
    name: str = ""
    status: str = "idle"
    confidence: float = 0.0
    latency_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "status": self.status,
            "confidence": round(self.confidence, 3),
            "latency_seconds": round(self.latency_seconds, 3),
        }


@dataclass
class ExecutionGraph:
    execution_id: str = ""
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)  # {from, to, label}

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": self.edges,
        }


# ── Final integrated response ─────────────────────────────────────────────────

@dataclass
class AgentPlatformResponse:
    response_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    user_id: str = ""
    workflow_type: WorkflowType | None = None
    execution_id: str = ""
    summary: str = ""
    agent_contributions: list[dict] = field(default_factory=list)
    integrated_output: dict = field(default_factory=dict)
    quality_report: QualityReport | None = None
    execution_graph: ExecutionGraph | None = None
    overall_confidence: float = 0.7
    total_agents_used: int = 0
    total_latency_seconds: float = 0.0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "response_id": self.response_id,
            "user_id": self.user_id,
            "workflow_type": self.workflow_type.value if self.workflow_type else None,
            "execution_id": self.execution_id,
            "summary": self.summary,
            "agent_contributions": self.agent_contributions,
            "integrated_output": self.integrated_output,
            "quality_report": self.quality_report.to_dict() if self.quality_report else None,
            "execution_graph": self.execution_graph.to_dict() if self.execution_graph else None,
            "overall_confidence": round(self.overall_confidence, 3),
            "total_agents_used": self.total_agents_used,
            "total_latency_seconds": round(self.total_latency_seconds, 3),
            "generated_at": self.generated_at.isoformat(),
        }
