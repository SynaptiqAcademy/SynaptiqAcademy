"""Autonomous Research Agents — Workflow engine (Phase XIII).

10 pre-built workflow templates. Each template is a DAG of WorkflowSteps.
The engine resolves steps, runs them in dependency order, and returns a
WorkflowExecution with per-step AgentResults.
"""
from __future__ import annotations

from .models import (
    AgentType, ExecutionMode, WorkflowStep, WorkflowTemplate, WorkflowType,
)

# ── Template factory helpers ──────────────────────────────────────────────────

def _seq(agent_type: AgentType, name: str, depends_on: list[str] | None = None) -> WorkflowStep:
    return WorkflowStep(
        agent_type=agent_type,
        name=name,
        execution_mode=ExecutionMode.SEQUENTIAL,
        depends_on=depends_on or [],
        required=True,
    )


def _par(agent_type: AgentType, name: str, depends_on: list[str] | None = None) -> WorkflowStep:
    return WorkflowStep(
        agent_type=agent_type,
        name=name,
        execution_mode=ExecutionMode.PARALLEL,
        depends_on=depends_on or [],
        required=True,
    )


def _opt(agent_type: AgentType, name: str, depends_on: list[str] | None = None) -> WorkflowStep:
    return WorkflowStep(
        agent_type=agent_type,
        name=name,
        execution_mode=ExecutionMode.SEQUENTIAL,
        depends_on=depends_on or [],
        required=False,
    )


# ── 10 Workflow Templates ─────────────────────────────────────────────────────

def _literature_review_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.LITERATURE_REVIEW, "Search & retrieve literature")
    s2 = _seq(AgentType.CITATION_INTELLIGENCE, "Analyse citations", [s1.step_id])
    s3 = _seq(AgentType.RESEARCH_GAP, "Identify research gaps", [s1.step_id])
    s4 = _seq(AgentType.KNOWLEDGE_GRAPH, "Build concept map", [s1.step_id, s3.step_id])
    s5 = _seq(AgentType.ACADEMIC_WRITING, "Review writing quality", [s4.step_id])
    s6 = _seq(AgentType.SUPERVISOR, "Supervise & validate", [s5.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.LITERATURE_REVIEW,
        name="Literature Review Workflow",
        description="End-to-end literature review: search, synthesis, gap analysis, concept mapping.",
        steps=[s1, s2, s3, s4, s5, s6],
        estimated_minutes=4,
    )


def _publication_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.LITERATURE_REVIEW, "Review existing literature")
    s2 = _seq(AgentType.RESEARCH_GAP, "Identify knowledge gaps", [s1.step_id])
    s3 = _seq(AgentType.METHODOLOGY, "Assess methodology", [s2.step_id])
    s4 = _par(AgentType.STATISTICS, "Review statistical analysis", [s3.step_id])
    s5 = _par(AgentType.RESEARCH_ETHICS, "Check ethics compliance", [s3.step_id])
    s6 = _seq(AgentType.ACADEMIC_WRITING, "Review writing quality", [s4.step_id, s5.step_id])
    s7 = _seq(AgentType.CITATION_INTELLIGENCE, "Verify citations", [s6.step_id])
    s8 = _seq(AgentType.JOURNAL_INTELLIGENCE, "Match target journals", [s6.step_id])
    s9 = _seq(AgentType.PUBLICATION_STRATEGY, "Build publication strategy", [s8.step_id])
    s10 = _seq(AgentType.PEER_REVIEW, "Simulate peer review", [s7.step_id, s9.step_id])
    s11 = _seq(AgentType.SUPERVISOR, "Final supervision", [s10.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.PUBLICATION,
        name="Publication Workflow",
        description="Complete manuscript-to-publication workflow: literature → methodology → writing → journal → peer review.",
        steps=[s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11],
        estimated_minutes=8,
    )


def _grant_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.LITERATURE_REVIEW, "Establish evidence base")
    s2 = _seq(AgentType.RESEARCH_GAP, "Identify funding opportunity gap", [s1.step_id])
    s3 = _seq(AgentType.RESEARCH_PLANNING, "Build research plan", [s2.step_id])
    s4 = _seq(AgentType.TIMELINE, "Schedule milestones", [s3.step_id])
    s5 = _seq(AgentType.GRANT_INTELLIGENCE, "Match grants", [s2.step_id])
    s6 = _seq(AgentType.ACADEMIC_WRITING, "Review proposal writing", [s3.step_id])
    s7 = _seq(AgentType.RESEARCH_ETHICS, "Ethics compliance check", [s3.step_id])
    s8 = _seq(AgentType.SUPERVISOR, "Final validation", [s4.step_id, s5.step_id, s6.step_id, s7.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.GRANT,
        name="Grant Workflow",
        description="Full grant lifecycle: evidence → planning → timeline → matching → writing review.",
        steps=[s1, s2, s3, s4, s5, s6, s7, s8],
        estimated_minutes=6,
    )


def _doctoral_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.RESEARCH_PLANNING, "Define PhD research plan")
    s2 = _seq(AgentType.LITERATURE_REVIEW, "Comprehensive literature review", [s1.step_id])
    s3 = _seq(AgentType.METHODOLOGY, "Design research methodology", [s2.step_id])
    s4 = _seq(AgentType.STATISTICS, "Plan statistical analysis", [s3.step_id])
    s5 = _seq(AgentType.TIMELINE, "Build PhD timeline", [s1.step_id])
    s6 = _seq(AgentType.GRANT_INTELLIGENCE, "Identify doctoral grants", [s1.step_id])
    s7 = _seq(AgentType.CAREER_DEVELOPMENT, "Career development strategy", [s1.step_id])
    s8 = _seq(AgentType.SUPERVISOR, "Supervisor validation", [s4.step_id, s5.step_id, s7.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.DOCTORAL,
        name="Doctoral Workflow",
        description="PhD lifecycle support: planning → literature → methodology → timeline → career strategy.",
        steps=[s1, s2, s3, s4, s5, s6, s7, s8],
        estimated_minutes=7,
    )


def _journal_submission_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.ACADEMIC_WRITING, "Writing quality review")
    s2 = _seq(AgentType.CITATION_INTELLIGENCE, "Citation audit", [s1.step_id])
    s3 = _seq(AgentType.RESEARCH_ETHICS, "Ethics & compliance check", [s1.step_id])
    s4 = _seq(AgentType.JOURNAL_INTELLIGENCE, "Journal matching", [s1.step_id])
    s5 = _seq(AgentType.PUBLICATION_STRATEGY, "Submission strategy", [s4.step_id])
    s6 = _seq(AgentType.PEER_REVIEW, "Pre-submission peer review", [s2.step_id, s3.step_id])
    s7 = _seq(AgentType.SUPERVISOR, "Final readiness check", [s5.step_id, s6.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.JOURNAL_SUBMISSION,
        name="Journal Submission Workflow",
        description="Pre-submission checklist: writing → citations → ethics → journal match → peer review.",
        steps=[s1, s2, s3, s4, s5, s6, s7],
        estimated_minutes=5,
    )


def _conference_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.ACADEMIC_WRITING, "Abstract quality review")
    s2 = _seq(AgentType.RESEARCH_GAP, "Novelty assessment", [s1.step_id])
    s3 = _seq(AgentType.CONFERENCE_INTELLIGENCE, "Conference matching", [s1.step_id, s2.step_id])
    s4 = _seq(AgentType.CAREER_DEVELOPMENT, "Career impact assessment", [s3.step_id])
    s5 = _seq(AgentType.TIMELINE, "Submission deadline planning", [s3.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.CONFERENCE,
        name="Conference Workflow",
        description="Conference submission: abstract quality → novelty → conference matching → career impact.",
        steps=[s1, s2, s3, s4, s5],
        estimated_minutes=3,
    )


def _research_proposal_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.LITERATURE_REVIEW, "Background literature review")
    s2 = _seq(AgentType.RESEARCH_GAP, "Gap analysis & rationale", [s1.step_id])
    s3 = _seq(AgentType.METHODOLOGY, "Methodology design", [s2.step_id])
    s4 = _seq(AgentType.STATISTICS, "Statistical power planning", [s3.step_id])
    s5 = _seq(AgentType.RESEARCH_PLANNING, "Work package planning", [s2.step_id])
    s6 = _seq(AgentType.TIMELINE, "Project timeline", [s5.step_id])
    s7 = _seq(AgentType.RESEARCH_ETHICS, "Ethics framework", [s3.step_id])
    s8 = _seq(AgentType.ACADEMIC_WRITING, "Proposal writing quality", [s3.step_id])
    s9 = _seq(AgentType.SUPERVISOR, "Proposal validation", [s4.step_id, s6.step_id, s7.step_id, s8.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.RESEARCH_PROPOSAL,
        name="Research Proposal Workflow",
        description="Complete research proposal: background → gap → methodology → statistics → planning → ethics.",
        steps=[s1, s2, s3, s4, s5, s6, s7, s8, s9],
        estimated_minutes=7,
    )


def _systematic_review_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.LITERATURE_REVIEW, "Systematic database search")
    s2 = _seq(AgentType.CITATION_INTELLIGENCE, "Citation screening & audit", [s1.step_id])
    s3 = _seq(AgentType.DATA_ANALYSIS, "Data extraction & quality", [s2.step_id])
    s4 = _seq(AgentType.STATISTICS, "Meta-analytic synthesis", [s3.step_id])
    s5 = _seq(AgentType.RESEARCH_GAP, "Future research directions", [s4.step_id])
    s6 = _seq(AgentType.ACADEMIC_WRITING, "PRISMA-compliant writing", [s5.step_id])
    s7 = _seq(AgentType.JOURNAL_INTELLIGENCE, "High-impact journal matching", [s6.step_id])
    s8 = _seq(AgentType.SUPERVISOR, "Systematic review validation", [s7.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.SYSTEMATIC_REVIEW,
        name="Systematic Review Workflow",
        description="Full systematic review: PRISMA search → screening → extraction → meta-analysis → writing.",
        steps=[s1, s2, s3, s4, s5, s6, s7, s8],
        estimated_minutes=6,
    )


def _teaching_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.TEACHING, "Pedagogy & curriculum review")
    s2 = _seq(AgentType.DATA_ANALYSIS, "Learning analytics review", [s1.step_id])
    s3 = _opt(AgentType.CAREER_DEVELOPMENT, "Teaching career development", [s1.step_id])
    s4 = _seq(AgentType.SUPERVISOR, "Teaching quality validation", [s2.step_id, s3.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.TEACHING,
        name="Teaching Workflow",
        description="Teaching quality review: pedagogy → learning analytics → career development.",
        steps=[s1, s2, s3, s4],
        estimated_minutes=3,
    )


def _institution_workflow() -> WorkflowTemplate:
    s1 = _seq(AgentType.COLLABORATION, "Collaboration network analysis")
    s2 = _seq(AgentType.RESEARCH_PLANNING, "Institutional research strategy", [s1.step_id])
    s3 = _seq(AgentType.GRANT_INTELLIGENCE, "Institutional grant matching", [s2.step_id])
    s4 = _seq(AgentType.TIMELINE, "Strategic timeline", [s2.step_id])
    s5 = _seq(AgentType.CAREER_DEVELOPMENT, "Researcher development plan", [s2.step_id])
    s6 = _seq(AgentType.SUPERVISOR, "Institution strategy validation", [s3.step_id, s4.step_id, s5.step_id])
    return WorkflowTemplate(
        workflow_type=WorkflowType.INSTITUTION,
        name="Institution Workflow",
        description="Institutional intelligence: collaboration → strategy → grants → timeline → career.",
        steps=[s1, s2, s3, s4, s5, s6],
        estimated_minutes=5,
    )


# ── Registry ──────────────────────────────────────────────────────────────────

_TEMPLATES: dict[WorkflowType, WorkflowTemplate] = {
    WorkflowType.LITERATURE_REVIEW:  _literature_review_workflow(),
    WorkflowType.PUBLICATION:        _publication_workflow(),
    WorkflowType.GRANT:              _grant_workflow(),
    WorkflowType.DOCTORAL:           _doctoral_workflow(),
    WorkflowType.JOURNAL_SUBMISSION: _journal_submission_workflow(),
    WorkflowType.CONFERENCE:         _conference_workflow(),
    WorkflowType.RESEARCH_PROPOSAL:  _research_proposal_workflow(),
    WorkflowType.SYSTEMATIC_REVIEW:  _systematic_review_workflow(),
    WorkflowType.TEACHING:           _teaching_workflow(),
    WorkflowType.INSTITUTION:        _institution_workflow(),
}


def get_template(workflow_type: WorkflowType) -> WorkflowTemplate:
    tpl = _TEMPLATES.get(workflow_type)
    if tpl is None:
        raise ValueError(f"No workflow template for: {workflow_type.value}")
    return tpl


def list_templates() -> list[dict]:
    return [t.to_dict() for t in _TEMPLATES.values()]


def resolve_execution_order(steps: list[WorkflowStep]) -> list[list[WorkflowStep]]:
    """Topological sort → batches of steps that can run in parallel."""
    step_map = {s.step_id: s for s in steps}
    resolved: set[str] = set()
    batches: list[list[WorkflowStep]] = []

    remaining = list(steps)
    while remaining:
        ready = [s for s in remaining if all(d in resolved for d in s.depends_on)]
        if not ready:
            raise ValueError("Circular dependency detected in workflow steps")
        batches.append(ready)
        for s in ready:
            resolved.add(s.step_id)
            remaining.remove(s)

    return batches
