"""Academic Copilot — Workflow Planner (Phase XI).

Decomposes a list of detected intents into an ordered sequence of
WorkflowSteps. Steps with no dependencies can run in parallel.
"""
from __future__ import annotations

from .models import CopilotWorkflow, DetectedIntent, IntentType, WorkflowStep

# Credit cost per engine invocation (quick-scan mode, no full AI pass)
_ENGINE_CREDITS: dict[str, int] = {
    "manuscript":  2,
    "literature":  2,
    "gap":         2,
    "statistical": 2,
}

# Human-readable engine descriptions
_ENGINE_DESCS: dict[str, tuple[str, str]] = {
    "manuscript":  ("Manuscript Intelligence", "Analyse writing quality, structure, scientific rigour, and literature coverage."),
    "literature":  ("Literature Review Intelligence", "Scan and synthesise existing literature on your research topic."),
    "gap":         ("Research Gap Intelligence", "Identify underexplored areas and research opportunities."),
    "statistical": ("Statistical Intelligence", "Evaluate research design, sampling, data quality, and statistical methods."),
}

# Intents that share an engine step with another intent are grouped
_ENGINE_STEP: dict[str, str] = {
    "manuscript":  "engine:manuscript",
    "literature":  "engine:literature",
    "gap":         "engine:gap",
    "statistical": "engine:statistical",
}

# Default steps always present (before engines, in order)
_CONTEXT_STEP_ID   = "step:context"
_AI_STEP_ID        = "step:ai_advisor"
_COMPOSE_STEP_ID   = "step:compose"


def plan_workflow(
    message: str,
    intents: list[DetectedIntent],
    user_context: dict,
) -> CopilotWorkflow:
    """Build a CopilotWorkflow from detected intents."""
    workflow = CopilotWorkflow(trigger_message=message)
    workflow.intents = intents
    steps: list[WorkflowStep] = []

    # Step 1: Always build context first
    steps.append(WorkflowStep(
        step_id=_CONTEXT_STEP_ID,
        engine="context",
        title="Build Academic Context",
        description="Retrieve your research profile, manuscripts, projects, grants, and memory.",
        is_parallel=False,
        depends_on=[],
    ))

    # Collect all unique engines required across all intents
    required_engines: list[str] = []
    seen_engines: set[str] = set()
    for intent in intents:
        for eng in intent.requires_engines:
            if eng not in seen_engines:
                seen_engines.add(eng)
                required_engines.append(eng)

    # Step 2+: Engine steps — can all run in parallel after context
    engine_step_ids: list[str] = []
    for engine in required_engines:
        step_id = _ENGINE_STEP.get(engine, f"engine:{engine}")
        name, desc = _ENGINE_DESCS.get(engine, (engine.capitalize(), ""))
        steps.append(WorkflowStep(
            step_id=step_id,
            engine=engine,
            title=name,
            description=desc,
            is_parallel=True,
            depends_on=[_CONTEXT_STEP_ID],
        ))
        engine_step_ids.append(step_id)

    # If composite request has many intents and no engines, add an intent-reasoning step
    if len(intents) > 2 and not required_engines:
        steps.append(WorkflowStep(
            step_id="step:intent_reasoning",
            engine="rule",
            title="Decompose Research Goals",
            description="Analyse your request and map it to a multi-step action plan.",
            is_parallel=False,
            depends_on=[_CONTEXT_STEP_ID],
        ))
        engine_step_ids.append("step:intent_reasoning")

    # Step N-1: AI Advisor synthesises everything
    steps.append(WorkflowStep(
        step_id=_AI_STEP_ID,
        engine="ai",
        title="Academic Copilot Synthesis",
        description="Expert AI ensemble synthesises all findings into actionable guidance.",
        is_parallel=False,
        depends_on=engine_step_ids or [_CONTEXT_STEP_ID],
    ))

    # Step N: Compose final response
    steps.append(WorkflowStep(
        step_id=_COMPOSE_STEP_ID,
        engine="compose",
        title="Compose Integrated Response",
        description="Merge all engine outputs and AI guidance into a structured response.",
        is_parallel=False,
        depends_on=[_AI_STEP_ID],
    ))

    workflow.steps = steps
    workflow.total_credits = sum(
        _ENGINE_CREDITS.get(eng, 0) for eng in required_engines
    )
    return workflow


def describe_plan(workflow: CopilotWorkflow) -> str:
    """Return a readable one-line description of what the copilot will do."""
    engine_names = [
        _ENGINE_DESCS.get(s.engine, (s.engine.capitalize(), ""))[0]
        for s in workflow.steps
        if s.engine not in ("context", "ai", "compose", "rule")
    ]
    if not engine_names:
        return "Analysing your request and preparing a personalised academic response."
    if len(engine_names) == 1:
        return f"Running {engine_names[0]} and synthesising results."
    listed = ", ".join(engine_names[:-1]) + f" and {engine_names[-1]}"
    return f"Coordinating {listed} — then synthesising all findings."
