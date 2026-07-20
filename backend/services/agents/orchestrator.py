"""Autonomous Research Agents — Task orchestrator (Phase XIII).

Decomposes user requests into agent workflows, selects the right agents,
and synthesises their outputs into a single integrated response.
"""
from __future__ import annotations

import re
from .models import (
    AgentContext, AgentPlatformResponse, AgentType, ExecutionGraph,
    GraphNode, QualityReport, WorkflowExecution, WorkflowType,
)
from .quality_controller import validate_execution

# ── Workflow detection ────────────────────────────────────────────────────────

_WORKFLOW_SIGNALS: list[tuple[WorkflowType, list[str]]] = [
    (WorkflowType.SYSTEMATIC_REVIEW, [
        "systematic review", "meta-analysis", "prisma", "scoping review",
    ]),
    (WorkflowType.PUBLICATION, [
        "publish", "submit manuscript", "write a paper", "journal submission",
        "manuscript ready", "peer review",
    ]),
    (WorkflowType.GRANT, [
        "grant proposal", "funding application", "apply for grant",
        "research grant", "write a proposal",
    ]),
    (WorkflowType.DOCTORAL, [
        "phd", "doctoral", "thesis", "dissertation", "complete my phd",
    ]),
    (WorkflowType.JOURNAL_SUBMISSION, [
        "which journal", "target journal", "journal match", "submit to",
        "best journal", "where to publish",
    ]),
    (WorkflowType.CONFERENCE, [
        "conference", "submit abstract", "present my research",
        "conference match", "cfp", "call for papers",
    ]),
    (WorkflowType.RESEARCH_PROPOSAL, [
        "research proposal", "study design", "propose a study",
        "write a proposal", "research plan",
    ]),
    (WorkflowType.TEACHING, [
        "teaching", "lesson plan", "course design", "curriculum",
        "pedagogical", "student learning",
    ]),
    (WorkflowType.INSTITUTION, [
        "institution", "university strategy", "research office",
        "department research", "institutional",
    ]),
    (WorkflowType.LITERATURE_REVIEW, [
        "literature review", "review the literature", "existing research",
        "what research exists", "prior studies",
    ]),
]


def detect_workflow(message: str) -> WorkflowType:
    """Pick the best-matching workflow for a free-text request."""
    lower = message.lower()
    for wf_type, signals in _WORKFLOW_SIGNALS:
        if any(s in lower for s in signals):
            return wf_type
    return WorkflowType.LITERATURE_REVIEW  # safe default


# ── Ad-hoc agent selection ────────────────────────────────────────────────────

_AGENT_SIGNALS: dict[AgentType, list[str]] = {
    AgentType.LITERATURE_REVIEW:    ["literature", "review", "existing research", "prior work", "background"],
    AgentType.RESEARCH_GAP:         ["gap", "novelty", "missing", "unexplored", "future research"],
    AgentType.METHODOLOGY:          ["methodology", "research design", "study design", "approach"],
    AgentType.STATISTICS:           ["statistic", "analysis", "regression", "anova", "power", "effect size"],
    AgentType.ACADEMIC_WRITING:     ["writing", "clarity", "grammar", "structure", "readability"],
    AgentType.JOURNAL_INTELLIGENCE: ["journal", "where to publish", "impact factor", "q1", "open access"],
    AgentType.CONFERENCE_INTELLIGENCE: ["conference", "abstract", "present"],
    AgentType.GRANT_INTELLIGENCE:   ["grant", "funding", "fellowship", "proposal"],
    AgentType.CITATION_INTELLIGENCE:["citation", "reference", "doi", "bibliography"],
    AgentType.RESEARCH_ETHICS:      ["ethics", "irb", "consent", "participant"],
    AgentType.DATA_ANALYSIS:        ["data", "dataset", "python", "r statistical", "spss", "reproducib"],
    AgentType.TEACHING:             ["teaching", "course", "curriculum", "lesson", "student"],
    AgentType.CAREER_DEVELOPMENT:   ["career", "promotion", "tenure", "postdoc", "phd"],
    AgentType.COLLABORATION:        ["collaborat", "partner", "network", "international"],
    AgentType.PEER_REVIEW:          ["peer review", "reviewer", "revision", "decision"],
    AgentType.PUBLICATION_STRATEGY: ["publication strategy", "roadmap", "strategy", "backup journal"],
    AgentType.RESEARCH_PLANNING:    ["research plan", "milestone", "work package", "timeline"],
    AgentType.TIMELINE:             ["timeline", "schedule", "gantt", "deadline", "when"],
    AgentType.KNOWLEDGE_GRAPH:      ["knowledge graph", "concept", "entity", "relationship"],
    AgentType.SUPERVISOR:           ["validate", "check everything", "full review", "comprehensive"],
}


def select_agents(message: str, max_agents: int = 6) -> list[AgentType]:
    """Select the most relevant agents for a free-text message."""
    lower = message.lower()
    hits: list[tuple[int, AgentType]] = []
    for agent_type, signals in _AGENT_SIGNALS.items():
        score = sum(1 for s in signals if s in lower)
        if score > 0:
            hits.append((score, agent_type))

    hits.sort(key=lambda x: -x[0])
    selected = [at for _, at in hits[:max_agents]]

    if not selected:
        selected = [AgentType.LITERATURE_REVIEW, AgentType.RESEARCH_GAP, AgentType.SUPERVISOR]

    # Always include supervisor for quality control
    if AgentType.SUPERVISOR not in selected:
        selected.append(AgentType.SUPERVISOR)

    return selected


# ── Response synthesis ────────────────────────────────────────────────────────

def _build_execution_graph(execution: WorkflowExecution) -> ExecutionGraph:
    nodes: list[GraphNode] = []
    edges: list[dict] = []

    prev_step_id: str | None = None
    for step in execution.steps:
        result = execution.results.get(step.step_id)
        nodes.append(GraphNode(
            node_id=step.step_id,
            agent_type=step.agent_type.value,
            name=step.name,
            status=result.status.value if result else "idle",
            confidence=result.confidence if result else 0.0,
            latency_seconds=result.latency_seconds if result else 0.0,
        ))
        for dep in step.depends_on:
            edges.append({"from": dep, "to": step.step_id, "label": "depends"})

    return ExecutionGraph(execution_id=execution.execution_id, nodes=nodes, edges=edges)


def synthesise_response(
    execution: WorkflowExecution,
    quality_report: QualityReport,
    user_id: str,
) -> AgentPlatformResponse:
    """Merge all agent results into one integrated platform response."""
    results_dict = {k: v for k, v in execution.results.items() if hasattr(v, "output")}

    agent_contributions: list[dict] = []
    for step in execution.steps:
        result = execution.results.get(step.step_id)
        if result and hasattr(result, "output"):
            agent_contributions.append({
                "agent_type": result.agent_type.value,
                "agent_name": step.name,
                "confidence": round(result.confidence, 3),
                "status": result.status.value,
                "reasoning": result.reasoning[:200] if result.reasoning else "",
                "key_output": {
                    k: v for k, v in list(result.output.items())[:4]
                    if not isinstance(v, list) or len(v) <= 10
                },
            })

    # Build integrated output
    integrated: dict = {}
    for step in execution.steps:
        result = execution.results.get(step.step_id)
        if result and result.output and result.status.value == "completed":
            integrated[result.agent_type.value] = result.output

    total_latency = sum(
        getattr(r, "latency_seconds", 0.0)
        for r in execution.results.values()
        if hasattr(r, "latency_seconds")
    )

    # Build summary
    top_issues: list[str] = quality_report.inconsistencies[:2] + quality_report.recommendations[:2]
    supervisor_result = next(
        (r for r in execution.results.values()
         if hasattr(r, "agent_type") and r.agent_type == AgentType.SUPERVISOR),
        None,
    )
    summary = (
        supervisor_result.output.get("overall_recommendation", "")
        if supervisor_result
        else f"Completed {len(execution.results)} agent analyses. "
             f"Quality: {quality_report.overall_quality.value}."
    )

    return AgentPlatformResponse(
        user_id=user_id,
        workflow_type=execution.workflow_type,
        execution_id=execution.execution_id,
        summary=summary,
        agent_contributions=agent_contributions,
        integrated_output=integrated,
        quality_report=quality_report,
        execution_graph=_build_execution_graph(execution),
        overall_confidence=quality_report.overall_confidence,
        total_agents_used=len(agent_contributions),
        total_latency_seconds=round(total_latency, 3),
    )
