"""Base types and abstract class for all specialized research agents."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional


# ── Data types ──────────────────────────────────────────────────────────────


@dataclass
class AgentEvidence:
    type: str        # "database_query" | "external_api" | "profile_field" | "platform_count"
    source: str      # Human-readable source name
    detail: str      # Specific detail about what was found
    verified: bool = True
    url: Optional[str] = None

    def to_dict(self) -> dict:
        return {"type": self.type, "source": self.source, "detail": self.detail,
                "verified": self.verified, "url": self.url}


@dataclass
class AgentTask:
    user_input: str
    subtask: str
    context: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


@dataclass
class AgentOutput:
    agent_name: str
    task_id: str
    status: Literal["success", "partial", "insufficient_data", "error"]
    content: str
    structured_data: dict
    evidence: list[AgentEvidence]
    confidence: Literal["high", "medium", "low", "not_applicable"]
    confidence_basis: str
    data_quality: Literal["sufficient", "partial", "insufficient"]
    limitations: list[str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "task_id": self.task_id,
            "status": self.status,
            "content": self.content,
            "structured_data": self.structured_data,
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence,
            "confidence_basis": self.confidence_basis,
            "data_quality": self.data_quality,
            "limitations": self.limitations,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata,
        }


# ── Abstract base ────────────────────────────────────────────────────────────


class BaseAgent(ABC):
    name:         str       = "base"
    description:  str       = ""
    mission:      str       = ""
    capabilities: list[str] = []

    @abstractmethod
    async def execute(
        self,
        task:   AgentTask,
        memory: "SharedMemory",
        db:     Any,
    ) -> AgentOutput:
        """Execute the agent's task with verified evidence. Never fabricate."""

    # ── Helpers ────────────────────────────────────────────────────────────

    def _ev(self, type_: str, source: str, detail: str, **kw) -> AgentEvidence:
        return AgentEvidence(type=type_, source=source, detail=detail, **kw)

    def _insufficient(self, task_id: str, missing: list[str]) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            task_id=task_id,
            status="insufficient_data",
            content=(
                "Not enough verified information is currently available to generate "
                f"a reliable output from the {self.name}. "
                f"Missing: {', '.join(missing)}."
            ),
            structured_data={},
            evidence=[],
            confidence="not_applicable",
            confidence_basis="Cannot produce evidence-based output without required data.",
            data_quality="insufficient",
            limitations=missing,
        )

    def _error(self, task_id: str, message: str) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            task_id=task_id,
            status="error",
            content=f"[{self.name}] Agent error: {message}",
            structured_data={},
            evidence=[],
            confidence="not_applicable",
            confidence_basis="Execution error prevented evidence collection.",
            data_quality="insufficient",
            limitations=[f"Execution error: {message[:120]}"],
        )

    def _conf(self, evidence: list[AgentEvidence]) -> tuple[str, str]:
        n = len([e for e in evidence if e.verified])
        if n >= 3:
            return "high", f"Supported by {n} verified platform data points."
        if n >= 1:
            return "medium", f"Supported by {n} verified data point(s). More context would improve accuracy."
        return "low", "Inferred from limited available data."
