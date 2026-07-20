"""Unified Workflow Engine — orchestrate complete academic workflows."""
from __future__ import annotations

import threading
import time

from .models import (
    StepStatus, WorkflowDefinition, WorkflowStatus, WorkflowStep, WorkflowType,
)

_MAX_WORKFLOWS = 5_000

# ── Step templates per workflow type ──────────────────────────────────────────

_STEP_TEMPLATES: dict[str, list[dict]] = {
    WorkflowType.RESEARCH_PIPELINE.value: [
        {"name": "Literature Review",        "engine_type": "literature_review",      "description": "Survey existing research"},
        {"name": "Research Gap Analysis",    "engine_type": "research_gap",           "description": "Identify open questions"},
        {"name": "Methodology Planning",     "engine_type": "manuscript",             "description": "Design research approach"},
        {"name": "Project Setup",            "engine_type": "project_center",         "description": "Create project & workspace"},
        {"name": "Team Formation",           "engine_type": "collaboration",          "description": "Recruit collaborators"},
        {"name": "Writing",                  "engine_type": "copilot",                "description": "Draft manuscript"},
        {"name": "Statistical Review",       "engine_type": "statistical",            "description": "Validate statistical methods"},
        {"name": "Manuscript Review",        "engine_type": "manuscript",             "description": "Peer review simulation"},
        {"name": "Journal Selection",        "engine_type": "journal_predictor",      "description": "Rank target journals"},
        {"name": "Conference Selection",     "engine_type": "conference_predictor",   "description": "Rank target conferences"},
        {"name": "Grant Application",        "engine_type": "grant_predictor",        "description": "Assess funding opportunities"},
        {"name": "Submission",               "engine_type": "publishing",             "description": "Prepare submission package"},
        {"name": "Revision",                 "engine_type": "manuscript",             "description": "Address reviewer comments"},
        {"name": "Publication",              "engine_type": "publication",            "description": "Finalize and publish"},
        {"name": "Citation Monitoring",      "engine_type": "citation_monitoring",    "description": "Track citations"},
        {"name": "Career Update",            "engine_type": "career_forecaster",      "description": "Update career metrics"},
        {"name": "Institution Analytics",    "engine_type": "institution_forecaster", "description": "Update institution profile"},
    ],
    WorkflowType.MANUSCRIPT_PIPELINE.value: [
        {"name": "Quality Assessment",         "engine_type": "manuscript",           "description": "Initial quality score"},
        {"name": "Statistical Review",         "engine_type": "statistical",          "description": "Validate statistics"},
        {"name": "Peer Review Simulation",     "engine_type": "manuscript",           "description": "Simulate reviewer feedback"},
        {"name": "Journal Recommendation",     "engine_type": "journal_predictor",    "description": "Rank journals"},
        {"name": "Conference Recommendation",  "engine_type": "conference_predictor", "description": "Rank conferences"},
        {"name": "Submission Package",         "engine_type": "publishing",           "description": "Build submission package"},
    ],
    WorkflowType.GRANT_PIPELINE.value: [
        {"name": "Research Gap Analysis",  "engine_type": "research_gap",      "description": "Validate novelty"},
        {"name": "Grant Assessment",       "engine_type": "grant_predictor",   "description": "Predict funding probability"},
        {"name": "Team Formation",         "engine_type": "collaboration",     "description": "Build grant team"},
        {"name": "Application Writing",    "engine_type": "copilot",           "description": "Draft grant application"},
        {"name": "Budget Planning",        "engine_type": "grant_predictor",   "description": "Validate budget adequacy"},
        {"name": "Submission",             "engine_type": "grant",             "description": "Submit application"},
    ],
    WorkflowType.CAREER_PIPELINE.value: [
        {"name": "Career Assessment",     "engine_type": "career_forecaster", "description": "Baseline career metrics"},
        {"name": "Goal Setting",          "engine_type": "career_forecaster", "description": "Define career goals"},
        {"name": "Skill Gap Analysis",    "engine_type": "career_forecaster", "description": "Identify skill gaps"},
        {"name": "Reputation Building",   "engine_type": "reputation",        "description": "Improve visibility"},
        {"name": "Milestone Tracking",    "engine_type": "career_forecaster", "description": "Track progress"},
    ],
    WorkflowType.COLLABORATION_PIPELINE.value: [
        {"name": "Partner Discovery",       "engine_type": "recommendation_engine",   "description": "Find collaborators"},
        {"name": "Compatibility Analysis",  "engine_type": "collaboration",           "description": "Assess team fit"},
        {"name": "Collaboration Request",   "engine_type": "collaboration",           "description": "Send invitation"},
        {"name": "Project Setup",           "engine_type": "project_center",          "description": "Create shared project"},
        {"name": "Success Forecasting",     "engine_type": "collaboration_forecaster","description": "Predict outcomes"},
    ],
}


def _make_steps(workflow_type: str, custom_steps: list[dict] | None = None) -> list[WorkflowStep]:
    templates = _STEP_TEMPLATES.get(workflow_type, [])
    if custom_steps:
        templates = custom_steps
    return [
        WorkflowStep(
            name=t.get("name", f"Step {i+1}"),
            engine_type=t.get("engine_type", ""),
            description=t.get("description", ""),
            order=i,
            skippable=t.get("skippable", False),
        )
        for i, t in enumerate(templates)
    ]


class WorkflowEngine:
    def __init__(self):
        self._lock      = threading.Lock()
        self._workflows: dict[str, WorkflowDefinition] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create_workflow(
        self,
        workflow_type: str,
        name:          str,
        owner_cohort:  str  = "general",
        project_id:    str  = "",
        description:   str  = "",
        custom_steps:  list | None = None,
        context:       dict | None = None,
    ) -> WorkflowDefinition:
        wf = WorkflowDefinition(
            workflow_type=workflow_type,
            name=name,
            description=description,
            owner_cohort=owner_cohort,
            project_id=project_id,
            steps=_make_steps(workflow_type, custom_steps),
            status=WorkflowStatus.RUNNING.value,
            context=context or {},
        )
        if wf.steps:
            wf.steps[0].status = StepStatus.RUNNING.value
            wf.steps[0].started_at = time.time()
        with self._lock:
            self._workflows[wf.workflow_id] = wf
            if len(self._workflows) > _MAX_WORKFLOWS:
                oldest = next(iter(self._workflows))
                del self._workflows[oldest]
        return wf

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        with self._lock:
            return self._workflows.get(workflow_id)

    def get_workflows_by_project(self, project_id: str) -> list[WorkflowDefinition]:
        with self._lock:
            return [w for w in self._workflows.values() if w.project_id == project_id]

    def get_active_workflows(self) -> list[WorkflowDefinition]:
        with self._lock:
            return [w for w in self._workflows.values() if w.status == WorkflowStatus.RUNNING.value]

    def get_all_workflows(self, limit: int = 100) -> list[WorkflowDefinition]:
        with self._lock:
            return list(self._workflows.values())[-limit:]

    # ── Step advancement ──────────────────────────────────────────────────────

    def advance_step(
        self,
        workflow_id:  str,
        step_output:  dict | None = None,
        skip_current: bool        = False,
    ) -> WorkflowDefinition | None:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if not wf or wf.status not in (WorkflowStatus.RUNNING.value,):
                return wf

            idx = wf.current_step_index
            if idx >= len(wf.steps):
                return wf

            current = wf.steps[idx]
            now     = time.time()
            current.status       = StepStatus.SKIPPED.value if skip_current else StepStatus.COMPLETED.value
            current.completed_at = now
            if step_output:
                current.output_data = step_output

            next_idx = idx + 1
            if next_idx >= len(wf.steps):
                wf.status         = WorkflowStatus.COMPLETED.value
                wf.completed_at   = now
                wf.current_step_index = next_idx
            else:
                wf.current_step_index = next_idx
                next_step             = wf.steps[next_idx]
                next_step.status      = StepStatus.RUNNING.value
                next_step.started_at  = now

            wf.updated_at = now
        return wf

    def fail_step(self, workflow_id: str, error: str) -> WorkflowDefinition | None:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if not wf:
                return None
            idx = wf.current_step_index
            if idx < len(wf.steps):
                wf.steps[idx].status = StepStatus.FAILED.value
                wf.steps[idx].error  = error
            wf.status     = WorkflowStatus.FAILED.value
            wf.updated_at = time.time()
        return wf

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def pause_workflow(self, workflow_id: str) -> bool:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if not wf or wf.status != WorkflowStatus.RUNNING.value:
                return False
            wf.status     = WorkflowStatus.PAUSED.value
            wf.updated_at = time.time()
        return True

    def resume_workflow(self, workflow_id: str) -> bool:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if not wf or wf.status != WorkflowStatus.PAUSED.value:
                return False
            wf.status     = WorkflowStatus.RUNNING.value
            wf.updated_at = time.time()
        return True

    def cancel_workflow(self, workflow_id: str) -> bool:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if not wf or wf.status in (WorkflowStatus.COMPLETED.value, WorkflowStatus.CANCELLED.value):
                return False
            wf.status     = WorkflowStatus.CANCELLED.value
            wf.updated_at = time.time()
        return True

    def update_context(self, workflow_id: str, context_updates: dict) -> bool:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if not wf:
                return False
            wf.context.update(context_updates)
            wf.updated_at = time.time()
        return True

    def summary(self) -> dict:
        with self._lock:
            by_status: dict[str, int] = {}
            by_type:   dict[str, int] = {}
            for wf in self._workflows.values():
                by_status[wf.status]        = by_status.get(wf.status, 0) + 1
                by_type[wf.workflow_type]   = by_type.get(wf.workflow_type, 0) + 1
        return {"total": len(self._workflows), "by_status": by_status, "by_type": by_type}
