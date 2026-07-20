"""Autonomous Research Agents — Abstract base + registry framework (Phase XIII).

To add a new agent:
1. Subclass AcademicAgent
2. Set class-level: agent_id, agent_type, name, domain, capabilities
3. Implement execute()
4. Decorate the class with @AgentRegistry.register

That's it — the registry auto-discovers the agent.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import ClassVar

from .models import (
    AgentContext, AgentResult, AgentStatus, AgentTask, AgentType,
    QualityLevel, ValidationResult,
)


class AcademicAgent(ABC):
    """Abstract base class for all academic research agents."""

    # ── Class-level identity (override in each concrete agent) ────────────────
    agent_id: ClassVar[str] = "base"
    agent_type: ClassVar[AgentType] = AgentType.SUPERVISOR
    name: ClassVar[str] = "Base Agent"
    domain: ClassVar[str] = "general"
    capabilities: ClassVar[list[str]] = []
    version: ClassVar[str] = "1.0"

    # ── Core interface ────────────────────────────────────────────────────────

    @abstractmethod
    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        """Execute the agent's task and return a structured result."""

    # ── Default validation (can be overridden) ────────────────────────────────

    def validate(self, result: AgentResult) -> ValidationResult:
        """Validate the agent's output. Override for domain-specific validation."""
        issues: list[str] = []
        flags: list[str] = []

        if result.confidence < 0.2:
            issues.append("Very low confidence — output may be unreliable")
        if not result.output:
            issues.append("Empty output dictionary")
            flags.append("empty_output")
        if not result.reasoning:
            issues.append("No reasoning provided")

        is_valid = len(flags) == 0 and result.confidence >= 0.1

        if result.confidence >= 0.8 and not issues:
            quality = QualityLevel.EXCELLENT
        elif result.confidence >= 0.65 and len(issues) <= 1:
            quality = QualityLevel.GOOD
        elif result.confidence >= 0.4:
            quality = QualityLevel.ACCEPTABLE
        elif result.confidence >= 0.2:
            quality = QualityLevel.POOR
        else:
            quality = QualityLevel.UNACCEPTABLE

        return ValidationResult(
            agent_type=result.agent_type,
            is_valid=is_valid,
            quality_level=quality,
            issues=issues,
            confidence_after_validation=result.confidence * (0.9 if issues else 1.0),
            hallucination_flags=flags,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _timed_result(
        self,
        task: AgentTask,
        output: dict,
        confidence: float,
        reasoning: str,
        evidence: list[str],
        t0: float,
        alternatives: list[dict] | None = None,
    ) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=AgentStatus.COMPLETED,
            output=output,
            confidence=round(min(1.0, max(0.0, confidence)), 3),
            reasoning=reasoning,
            evidence=evidence[:8],
            alternatives=alternatives or [],
            latency_seconds=round(time.monotonic() - t0, 3),
        )

    def _failed_result(self, task: AgentTask, error: str, t0: float) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=AgentStatus.FAILED,
            output={"error": error},
            confidence=0.0,
            reasoning=f"Task failed: {error}",
            latency_seconds=round(time.monotonic() - t0, 3),
        )

    def describe(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "domain": self.domain,
            "capabilities": self.capabilities,
            "version": self.version,
        }


# ── Registry ──────────────────────────────────────────────────────────────────

class AgentRegistry:
    """Maps AgentType → concrete AcademicAgent class. Agents self-register via decorator."""

    _agents: dict[AgentType, type[AcademicAgent]] = {}

    @classmethod
    def register(cls, agent_class: type[AcademicAgent]) -> type[AcademicAgent]:
        """Decorator: @AgentRegistry.register — registers the class by agent_type."""
        cls._agents[agent_class.agent_type] = agent_class
        return agent_class

    @classmethod
    def create(cls, agent_type: AgentType) -> AcademicAgent:
        """Instantiate a registered agent by type. Raises ValueError if not found."""
        klass = cls._agents.get(agent_type)
        if klass is None:
            raise ValueError(f"No agent registered for type: {agent_type.value}")
        return klass()

    @classmethod
    def list_types(cls) -> list[AgentType]:
        return list(cls._agents.keys())

    @classmethod
    def list_agents(cls) -> list[dict]:
        return [klass().describe() for klass in cls._agents.values()]

    @classmethod
    def is_registered(cls, agent_type: AgentType) -> bool:
        return agent_type in cls._agents

    @classmethod
    def clear(cls) -> None:
        """Reset registry (used in tests)."""
        cls._agents.clear()
