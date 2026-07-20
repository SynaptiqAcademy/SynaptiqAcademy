"""Multi-Agent Orchestrator — intent analysis, planning, parallel execution, merge.

Flow per request:
  1. detect_intent()   — keyword-based workflow selection
  2. build_plan()      — stage list (parallel agents per stage)
  3. stream_execute()  — async generator yielding SSE-ready events
     ├─ memory.load_context() — load user data from DB once
     ├─ Per stage: asyncio.gather() of all agents in parallel
     ├─ After each agent: write to SharedMemory, yield "agent_output" event
     ├─ After all stages: QUALITY_AGENT.validate()
     └─ merge_outputs() — single AI call to produce coherent final response
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, AsyncGenerator

from .base_agent import AgentTask, AgentOutput
from .memory import SharedMemory, get_or_create
from .quality_agent import QUALITY_AGENT
from .registry import REGISTRY

logger = logging.getLogger("copilot.orchestrator")

# ── Workflow definitions ─────────────────────────────────────────────────────
#
# Each workflow has:
#   phrases — keywords that trigger it (longest/most-specific phrases first)
#   stages  — list of lists; inner list = agents run in parallel per stage
#   label   — human-readable description shown to user

WORKFLOWS: dict[str, dict] = {
    "publish_paper": {
        "phrases":  ["publish my paper", "submit paper", "journal submission", "submit manuscript", "ready to publish"],
        "stages":   [["ethics", "literature"], ["writing", "citation"], ["reviewer", "journal"]],
        "label":    "Publishing workflow: ethics + literature → writing + citation quality → peer review + journal matching",
    },
    "grant_preparation": {
        "phrases":  ["grant proposal", "funding proposal", "apply for grant", "write a proposal", "grant application", "research funding"],
        "stages":   [["funding", "literature"], ["collaboration", "statistics"], ["writing"]],
        "label":    "Grant workflow: opportunity mapping → methodology + collaboration → proposal writing",
    },
    "literature_review": {
        "phrases":  ["literature review", "systematic review", "related work", "state of the art", "find papers", "research papers on"],
        "stages":   [["literature"], ["gap", "citation"]],
        "label":    "Literature workflow: search → gap analysis + citation quality",
    },
    "methodology_design": {
        "phrases":  ["study design", "research design", "experimental design", "methodology", "sampling strategy", "research method"],
        "stages":   [["study_design", "statistics"]],
        "label":    "Methodology workflow: study design + statistical guidance",
    },
    "peer_review_sim": {
        "phrases":  ["peer review", "simulate review", "review my paper", "review my manuscript", "get feedback", "critique my paper"],
        "stages":   [["ethics", "statistics"], ["reviewer", "citation"]],
        "label":    "Peer review simulation: ethics + stats check → review simulation + citation quality",
    },
    "career_development": {
        "phrases":  ["academic career", "career advice", "promotion", "career development", "tenure", "career plan"],
        "stages":   [["career"]],
        "label":    "Career development: profile-based career guidance",
    },
    "collaboration_search": {
        "phrases":  ["find collaborator", "co-author", "research partner", "collaboration opportunity", "find expert", "team up"],
        "stages":   [["collaboration", "literature"]],
        "label":    "Collaboration workflow: opportunity discovery + research context",
    },
    "teaching_support": {
        "phrases":  ["lesson plan", "teaching", "course design", "assessment design", "learning outcomes", "teach my students"],
        "stages":   [["teaching"]],
        "label":    "Teaching support: lesson and assessment design",
    },
    "institution_analytics": {
        "phrases":  ["institution analytics", "faculty analytics", "research office", "department performance", "university benchmarking"],
        "stages":   [["institution"]],
        "label":    "Institution analytics: verified platform data insights",
    },
    "ethics_check": {
        "phrases":  ["ethics check", "check for bias", "plagiarism", "research integrity", "data protection", "ethical concerns"],
        "stages":   [["ethics"]],
        "label":    "Ethics compliance check",
    },
    "statistics_help": {
        "phrases":  ["statistical", "statistics", "sample size", "power analysis", "regression", "hypothesis test", "data analysis"],
        "stages":   [["statistics"]],
        "label":    "Statistical guidance and analysis support",
    },
    "writing_assistance": {
        "phrases":  ["improve my writing", "writing quality", "grammar check", "clarity", "rewrite", "academic writing help"],
        "stages":   [["writing", "citation"]],
        "label":    "Writing improvement: quality + citation check",
    },
    "citation_check": {
        "phrases":  ["check citations", "validate references", "missing citations", "bibliography", "reference list"],
        "stages":   [["citation", "literature"]],
        "label":    "Citation quality: validation + related paper discovery",
    },
    "funding_discovery": {
        "phrases":  ["find grants", "find funding", "funding opportunities", "grant opportunities"],
        "stages":   [["funding", "collaboration"]],
        "label":    "Funding discovery: grant matching + collaboration opportunities",
    },
    "general_research": {
        "phrases":  [],
        "stages":   [["literature", "gap"], ["writing"]],
        "label":    "General research assistance: literature + gap analysis + writing guidance",
    },
}


def detect_intent(user_input: str) -> str:
    """Return the best-matching workflow key from WORKFLOWS."""
    text = user_input.lower().strip()
    # Try longest phrases first to avoid substring false-matches
    best_match = ("general_research", 0)
    for wid, cfg in WORKFLOWS.items():
        if wid == "general_research":
            continue
        for phrase in cfg["phrases"]:
            if phrase in text:
                # Prefer longer phrase matches
                if len(phrase) > best_match[1]:
                    best_match = (wid, len(phrase))
    return best_match[0]


async def _run_stage(stage_agents: list[str], task_input: str, memory: SharedMemory, db) -> list[AgentOutput]:
    """Run all agents in a stage in parallel; return their outputs."""
    tasks = []
    names = []
    for agent_name in stage_agents:
        agent = REGISTRY.get(agent_name)
        if not agent:
            logger.warning("Agent not registered: %s", agent_name)
            continue
        t = AgentTask(user_input=task_input, subtask=f"Stage task for {agent_name}")
        tasks.append(agent.execute(t, memory, db))
        names.append(agent_name)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    outputs = []
    for agent_name, result in zip(names, results):
        if isinstance(result, Exception):
            logger.error("Agent %s raised: %s", agent_name, result, exc_info=True)
            agent = REGISTRY.get(agent_name)
            output = agent._error(agent_name, str(result)[:100]) if agent else AgentOutput(
                agent_name=agent_name, task_id="err", status="error",
                content=str(result), structured_data={}, evidence=[],
                confidence="not_applicable", confidence_basis="",
                data_quality="insufficient", limitations=[]
            )
        else:
            output = result
        memory.set_agent_output(agent_name, output)
        outputs.append(output)

    return outputs


async def _merge_outputs(outputs: list[AgentOutput], user_input: str, workflow_label: str) -> str:
    """Merge all agent outputs into one coherent, evidence-respecting response."""
    from services.ai.llm import call_llm

    agent_sections = []
    for o in outputs:
        if o.status in ("success", "partial") and o.content:
            agent_sections.append(
                f"=== {o.agent_name.upper()} AGENT (confidence: {o.confidence}) ===\n{o.content[:800]}"
            )

    if not agent_sections:
        return (
            "No substantive agent outputs were produced. "
            "This may be because your profile lacks sufficient data for evidence-based recommendations. "
            "Please complete your profile, add manuscripts, and connect your ORCID."
        )

    combined = "\n\n".join(agent_sections)

    return await call_llm(
        system=(
            "You are a Research Orchestrator. You have received outputs from multiple specialized AI research agents. "
            "Your task: synthesize these into ONE coherent, well-structured, actionable response. "
            "Rules: (1) Only include information that appears in the agent outputs — do not add new information. "
            "(2) Resolve any contradictions by noting the discrepancy. "
            "(3) Label section headings clearly by research area. "
            "(4) Preserve confidence ratings — do not upgrade any 'low' or 'partial' evidence claims. "
            "(5) Maintain the evidence-based tone — never add statistics or claims not in the agent outputs. "
            "(6) Be concise — researchers need clear, actionable guidance."
        ),
        user_msg=(
            f"User's original request: {user_input}\n"
            f"Workflow: {workflow_label}\n\n"
            f"Agent outputs:\n{combined}\n\n"
            "Synthesize into one unified, actionable response with clearly labeled sections."
        ),
        feature="copilot_orchestrator",
        max_tokens=3000,
    )


async def stream_execute(
    user_input: str,
    user: dict,
    db: Any,
    session_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Async generator yielding SSE-ready event dicts.

    Events:
      plan          — workflow intent detected, stages listed
      context_ready — user context loaded from DB
      stage_start   — stage N beginning, agent names listed
      agent_output  — one agent completed
      quality_check — quality validation result
      final         — merged response + meta
      error         — fatal error
    """
    if not session_id:
        session_id = uuid.uuid4().hex

    try:
        # 1. Detect intent
        workflow_id = detect_intent(user_input)
        workflow    = WORKFLOWS[workflow_id]
        stages      = workflow["stages"]

        yield {
            "event": "plan",
            "data": {
                "session_id":    session_id,
                "workflow_id":   workflow_id,
                "workflow_label": workflow["label"],
                "stages":        stages,
                "agent_count":   sum(len(s) for s in stages),
            },
        }

        # 2. Load shared memory / context
        uid    = str(user["_id"])
        memory = await get_or_create(session_id, user, user_input)
        await memory.load_context(db, uid)

        yield {"event": "context_ready", "data": {"uid": uid, "session_id": session_id}}

        # 3. Execute stages
        all_outputs: list[AgentOutput] = []

        for stage_idx, stage_agents in enumerate(stages):
            # Filter out agents not registered
            available = [a for a in stage_agents if REGISTRY.get(a)]

            yield {
                "event": "stage_start",
                "data": {"stage": stage_idx, "agents": available},
            }

            stage_outputs = await _run_stage(available, user_input, memory, db)
            all_outputs.extend(stage_outputs)

            for output in stage_outputs:
                yield {"event": "agent_output", "data": output.to_dict()}

        # 4. Quality check
        quality = QUALITY_AGENT.validate(all_outputs, user_input)
        yield {"event": "quality_check", "data": quality.to_dict()}

        # 5. Merge into final response
        merged = await _merge_outputs(all_outputs, user_input, workflow["label"])

        agents_used = [o.agent_name for o in all_outputs]
        confidence_map = {o.agent_name: o.confidence for o in all_outputs}
        evidence_sources = list({e.source for o in all_outputs for e in o.evidence})

        yield {
            "event": "final",
            "data": {
                "session_id":      session_id,
                "response":        merged,
                "workflow_id":     workflow_id,
                "agents_used":     agents_used,
                "confidence_map":  confidence_map,
                "evidence_sources": evidence_sources,
                "quality_score":   quality.score,
                "quality_passed":  quality.passed,
                "agent_outputs":   [o.to_dict() for o in all_outputs],
            },
        }

    except Exception as exc:
        logger.exception("Orchestrator fatal error: %s", exc)
        yield {"event": "error", "data": {"message": str(exc)[:200]}}
