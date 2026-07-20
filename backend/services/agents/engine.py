"""Autonomous Research Agents — Main engine + async singleton (Phase XIII)."""
from __future__ import annotations

import asyncio
import time
from typing import Any

# Import all agent modules so they self-register with AgentRegistry
from . import (  # noqa: F401
    agent_literature, agent_gap, agent_methodology, agent_statistics,
    agent_writing, agent_journal, agent_conference, agent_grant,
    agent_citation, agent_ethics, agent_data_analysis, agent_peer_review,
    agent_supervisor, agent_publication_strategy, agent_research_planning,
    agent_timeline, agent_teaching, agent_career, agent_collaboration,
    agent_knowledge_graph,
)

from .base_agent import AgentRegistry
from .execution_engine import (
    execute_agents_parallel, execute_agents_sequential, execute_workflow,
)
from .memory_bus import MemoryBusRegistry
from .models import (
    AgentContext, AgentPlatformResponse, AgentType,
    WorkflowExecution, WorkflowType,
)
from .orchestrator import detect_workflow, select_agents, synthesise_response
from .quality_controller import validate_execution
from .telemetry import get_telemetry
from .workflow_engine import list_templates


class AgentPlatformEngine:
    """
    Main façade for the Autonomous Research Agents Platform.

    Provides:
      - run_workflow(workflow_type, content, user_id)  → AgentPlatformResponse
      - run_task(message, content, user_id)            → AgentPlatformResponse
      - list_agents()                                  → list[dict]
      - list_workflows()                               → list[dict]
    """

    # ── Workflow execution ────────────────────────────────────────────────────

    async def run_workflow(
        self,
        workflow_type: WorkflowType,
        content: str,
        user_id: str,
        metadata: dict | None = None,
    ) -> AgentPlatformResponse:
        t0 = time.monotonic()
        tel = get_telemetry()
        tel.record_workflow_run(workflow_type.value)

        try:
            execution: WorkflowExecution = await execute_workflow(
                workflow_type, content, user_id, metadata
            )

            # Record per-agent telemetry
            for result in execution.results.values():
                if hasattr(result, "agent_type"):
                    tel.record_agent_invocation(result.agent_type.value)
                    if result.status.value == "failed":
                        tel.record_agent_failure(result.agent_type.value)

            quality_report = validate_execution(execution.results, execution.execution_id)
            response = synthesise_response(execution, quality_report, user_id)
            tel.record_latency(time.monotonic() - t0)
            return response

        except Exception:
            tel.record_error()
            raise

    # ── Ad-hoc task (auto-detects workflow) ───────────────────────────────────

    async def run_task(
        self,
        message: str,
        content: str,
        user_id: str,
        metadata: dict | None = None,
        max_agents: int = 6,
    ) -> AgentPlatformResponse:
        t0 = time.monotonic()
        tel = get_telemetry()
        tel.record_ad_hoc_run()

        try:
            # Auto-detect workflow or select specific agents
            workflow_type = detect_workflow(message)
            return await self.run_workflow(workflow_type, content, user_id, metadata)

        except Exception:
            tel.record_error()
            raise

    # ── Single-agent execution ────────────────────────────────────────────────

    async def run_agent(
        self,
        agent_type: AgentType,
        content: str,
        user_id: str,
        metadata: dict | None = None,
    ) -> dict:
        from .models import AgentTask
        from .execution_engine import _run_single
        from .workflow_engine import WorkflowStep

        tel = get_telemetry()
        tel.record_agent_invocation(agent_type.value)

        context = AgentContext(user_id=user_id, memory=metadata or {})
        step = WorkflowStep(agent_type=agent_type, name=agent_type.value)
        task = AgentTask(agent_type=agent_type, content=content, metadata=metadata or {})

        result = await _run_single(step, task, context)

        if result.status.value == "failed":
            tel.record_agent_failure(agent_type.value)

        return result.to_dict()

    # ── Agent parallel dispatch ───────────────────────────────────────────────

    async def run_agents_parallel(
        self,
        agent_types: list[str],
        content: str,
        user_id: str,
        metadata: dict | None = None,
    ) -> dict:
        types = [AgentType(a) for a in agent_types]
        context = AgentContext(user_id=user_id, memory=metadata or {})
        results = await execute_agents_parallel(types, content, context, metadata)
        return {k: v.to_dict() for k, v in results.items()}

    # ── Registry info ─────────────────────────────────────────────────────────

    def list_agents(self) -> list[dict]:
        return AgentRegistry.list_agents()

    def list_workflows(self) -> list[dict]:
        return list_templates()

    def agent_info(self, agent_type: AgentType) -> dict:
        agent = AgentRegistry.create(agent_type)
        return agent.describe()


# ── Async singleton ───────────────────────────────────────────────────────────

_engine_lock = asyncio.Lock()
_engine_instance: AgentPlatformEngine | None = None


async def get_agent_engine() -> AgentPlatformEngine:
    global _engine_instance
    if _engine_instance is None:
        async with _engine_lock:
            if _engine_instance is None:
                _engine_instance = AgentPlatformEngine()
    return _engine_instance


def reset_agent_engine() -> None:
    global _engine_instance
    _engine_instance = None
