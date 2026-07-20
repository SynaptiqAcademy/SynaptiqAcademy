"""Autonomous Research Agents — Execution engine (Phase XIII).

Supports parallel, sequential, conditional, and dynamic execution.
Handles retries and agent failover with graceful degradation.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from .base_agent import AgentRegistry
from .models import (
    AgentContext, AgentResult, AgentStatus, AgentTask, AgentType,
    ExecutionMode, WorkflowExecution, WorkflowStep, WorkflowType,
)
from .workflow_engine import get_template, resolve_execution_order

_DEFAULT_TIMEOUT = 30.0   # seconds per agent
_DEFAULT_RETRIES = 2


async def _run_single(
    step: WorkflowStep,
    task: AgentTask,
    context: AgentContext,
) -> AgentResult:
    """Execute one agent with retry logic and timeout."""
    agent = AgentRegistry.create(step.agent_type)
    last_exc: Exception | None = None

    for attempt in range(max(1, step.retry_count)):
        try:
            result = await asyncio.wait_for(
                agent.execute(task, context),
                timeout=float(step.timeout_seconds),
            )
            context.add_result(result)
            return result
        except asyncio.TimeoutError as e:
            last_exc = e
        except Exception as e:
            last_exc = e

    # All retries exhausted → return failed result
    return AgentResult(
        task_id=task.task_id,
        agent_id=getattr(agent, "agent_id", step.agent_type.value),
        agent_type=step.agent_type,
        status=AgentStatus.FAILED,
        output={"error": str(last_exc)},
        confidence=0.0,
        reasoning=f"Agent failed after {step.retry_count} attempt(s): {last_exc}",
    )


def _evaluate_condition(condition: str, context: AgentContext) -> bool:
    """Evaluate a simple condition expression against the last result's confidence."""
    if not condition:
        return True
    try:
        # Safe: only allow simple 'confidence > X' or 'confidence >= X' checks
        parts = condition.strip().split()
        if len(parts) == 3 and parts[0] == "confidence":
            op, val = parts[1], float(parts[2])
            # Find the most recent result
            if context.previous_results:
                last = list(context.previous_results.values())[-1]
                conf = last.confidence
                if op == ">":  return conf > val
                if op == ">=": return conf >= val
                if op == "<":  return conf < val
                if op == "<=": return conf <= val
                if op == "==": return conf == val
    except Exception:
        pass
    return True


async def execute_workflow(
    workflow_type: WorkflowType,
    content: str,
    user_id: str,
    metadata: dict | None = None,
) -> WorkflowExecution:
    """Run a named workflow template end-to-end."""
    template = get_template(workflow_type)
    batches = resolve_execution_order(template.steps)

    execution = WorkflowExecution(
        workflow_type=workflow_type,
        user_id=user_id,
        steps=template.steps,
    )

    context = AgentContext(
        user_id=user_id,
        memory=metadata or {},
        user_profile=metadata.get("user_profile", {}) if metadata else {},
    )

    for batch in batches:
        # Build tasks for this batch
        tasks_to_run: list[tuple[WorkflowStep, AgentTask]] = []
        for step in batch:
            # Evaluate conditional steps
            if step.execution_mode == ExecutionMode.CONDITIONAL:
                if not _evaluate_condition(step.condition, context):
                    execution.results[step.step_id] = AgentResult(
                        agent_type=step.agent_type,
                        status=AgentStatus.SKIPPED,
                        reasoning="Condition not met — step skipped.",
                    )
                    continue

            task = AgentTask(
                agent_type=step.agent_type,
                content=content,
                metadata=metadata or {},
            )
            tasks_to_run.append((step, task))

        if not tasks_to_run:
            continue

        # All steps in a batch run in parallel
        coros = [_run_single(step, task, context) for step, task in tasks_to_run]
        results = await asyncio.gather(*coros, return_exceptions=True)

        for (step, _), result in zip(tasks_to_run, results):
            if isinstance(result, Exception):
                execution.results[step.step_id] = AgentResult(
                    agent_type=step.agent_type,
                    status=AgentStatus.FAILED,
                    output={"error": str(result)},
                )
            else:
                execution.results[step.step_id] = result

    from datetime import datetime, timezone
    execution.completed_at = datetime.now(timezone.utc)
    execution.status = (
        AgentStatus.COMPLETED
        if all(
            r.status in (AgentStatus.COMPLETED, AgentStatus.SKIPPED)
            for r in execution.results.values()
            if isinstance(r, AgentResult)
        )
        else AgentStatus.FAILED
    )

    return execution


async def execute_agents_parallel(
    agent_types: list[AgentType],
    content: str,
    context: AgentContext,
    metadata: dict | None = None,
) -> dict[str, AgentResult]:
    """Fire a set of agents in parallel and return their results."""
    async def _run(agent_type: AgentType) -> tuple[str, AgentResult]:
        agent = AgentRegistry.create(agent_type)
        task = AgentTask(agent_type=agent_type, content=content, metadata=metadata or {})
        try:
            result = await asyncio.wait_for(agent.execute(task, context), timeout=_DEFAULT_TIMEOUT)
        except Exception as e:
            result = AgentResult(
                agent_type=agent_type, status=AgentStatus.FAILED,
                output={"error": str(e)}, confidence=0.0,
            )
        context.add_result(result)
        return agent_type.value, result

    pairs = await asyncio.gather(*[_run(at) for at in agent_types], return_exceptions=False)
    return {k: v for k, v in pairs}


async def execute_agents_sequential(
    agent_types: list[AgentType],
    content: str,
    context: AgentContext,
    metadata: dict | None = None,
) -> dict[str, AgentResult]:
    """Run agents one after another, feeding context between them."""
    results: dict[str, AgentResult] = {}
    for agent_type in agent_types:
        agent = AgentRegistry.create(agent_type)
        task = AgentTask(agent_type=agent_type, content=content, metadata=metadata or {})
        try:
            result = await asyncio.wait_for(agent.execute(task, context), timeout=_DEFAULT_TIMEOUT)
        except Exception as e:
            result = AgentResult(
                agent_type=agent_type, status=AgentStatus.FAILED,
                output={"error": str(e)}, confidence=0.0,
            )
        context.add_result(result)
        results[agent_type.value] = result
    return results
