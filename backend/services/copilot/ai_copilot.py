"""Academic Copilot — Multi-Expert LLM Persona (Phase XI).

Wraps the existing call_llm() with a rich multi-expert system prompt that
combines 10 academic personas. Engine scan results are injected as structured
context so the AI response is grounded in real analysis, not hallucination.
"""
from __future__ import annotations

import logging
import re

from .models import DetectedIntent, IntentType

logger = logging.getLogger("synaptiq.copilot.ai")

# ── System prompt ─────────────────────────────────────────────────────────────

_COPILOT_SYSTEM = """\
You are SYNAPTIQ Academic Copilot — the central intelligence of Synaptiq Academy.

You embody a panel of 10 world-class academic experts who collaborate to answer:
  • Researcher        — research design, novelty, methodology, feasibility
  • University Professor — academic rigour, theoretical frameworks, pedagogy
  • Journal Editor    — publication standards, desk rejection risks, fit
  • Peer Reviewer     — critical appraisal, methodological flaws, reporting gaps
  • Statistician      — data quality, assumption checks, effect sizes, power
  • Research Supervisor — doctoral guidance, milestones, career trajectory
  • Grant Consultant  — funding strategy, proposal strength, funder alignment
  • Academic Writing Coach — clarity, structure, flow, APA/Vancouver style
  • Methodology Expert — design appropriateness, validity, reliability
  • Career Mentor     — academic career progression, reputation, visibility

CORE PRINCIPLES:
1. Never fabricate citations, publications, data, or statistics.
2. Always reference the user's actual profile data when relevant.
3. Give concrete, actionable advice — not generic platitudes.
4. When engine scan results are provided, ground your response in them.
5. Structure responses with clear headers when the response is multi-part.
6. Always include: (a) your assessment, (b) specific improvements, (c) next steps.
7. Express calibrated confidence — acknowledge uncertainty honestly.
8. Prioritise scientific rigour over user comfort.

VOICE: Expert-level, direct, evidence-grounded, encouraging without being sycophantic.
NEVER say "Great question!" or similar filler phrases.
"""

# ── Engine result summarisers ─────────────────────────────────────────────────

def _summarise_engine_results(engine_results: dict) -> str:
    if not engine_results:
        return ""

    parts = ["\n\n## INTELLIGENCE ENGINE SCAN RESULTS (use these to ground your response):\n"]

    ms = engine_results.get("manuscript")
    if ms and "error" not in ms:
        issues = ms.get("top_issues") or []
        issue_text = "; ".join(f'{i["severity"].upper()}: {i["title"]}' for i in issues[:4])
        parts.append(
            f"MANUSCRIPT SCAN: {ms.get('word_count', 0):,} words | "
            f"{ms.get('section_count', 0)} sections | "
            f"Scientific score={ms.get('scientific_score', 0):.0f}/100 | "
            f"Writing score={ms.get('writing_score', 0):.0f}/100 | "
            f"Statistical score={ms.get('statistical_score', 0):.0f}/100 | "
            f"Critical issues={ms.get('critical_issue_count', 0)} | "
            f"Major issues={ms.get('major_issue_count', 0)}"
            + (f"\nTop issues: {issue_text}" if issue_text else "")
        )

    stat = engine_results.get("statistical")
    if stat and "error" not in stat:
        parts.append(
            f"STATISTICAL SCAN: Design={stat.get('study_type', 'N/A')} | "
            f"Method={stat.get('primary_method', 'N/A')} | "
            f"N={stat.get('sample_size', 'N/A')} | "
            f"Sampling adequate={stat.get('sampling_adequate', 'N/A')} | "
            f"Has p-values={stat.get('has_p_values')} | "
            f"Has effect sizes={stat.get('has_effect_sizes')} | "
            f"Has CIs={stat.get('has_confidence_intervals')}"
        )

    lit = engine_results.get("literature")
    if lit and "error" not in lit:
        parts.append(
            f"LITERATURE SCAN: {lit.get('reference_count', 0)} references | "
            f"Recent={lit.get('recent_citation_count', 0)} | "
            f"Year range={lit.get('year_range', 'N/A')} | "
            f"Recency ratio={lit.get('recency_ratio', 0):.0%} | "
            f"Needs more refs={lit.get('needs_more_refs')}"
        )

    gap = engine_results.get("gap")
    if gap and "error" not in gap:
        parts.append(
            f"RESEARCH GAP SCAN: Gap signals={gap.get('gap_signal_count', 0)} | "
            f"Novelty claims={gap.get('novelty_claim_count', 0)} | "
            f"Has explicit gap={gap.get('has_explicit_gap')}"
        )

    return "\n".join(parts)


def _intent_instruction(intents: list[DetectedIntent]) -> str:
    if not intents:
        return ""

    primary = intents[0].intent_type
    instructions: dict[IntentType, str] = {
        IntentType.MANUSCRIPT_REVIEW: (
            "Focus on manuscript quality: structure, scientific rigour, literature coverage, "
            "statistical reporting, and writing clarity. Use engine scan results if available."
        ),
        IntentType.LITERATURE_REVIEW: (
            "Focus on literature coverage: recency, breadth, key papers, gaps. "
            "Recommend specific search strategies and databases."
        ),
        IntentType.GAP_ANALYSIS: (
            "Focus on research gaps: what is missing, understudied, contradicted, or contested. "
            "Suggest 3+ specific gap directions with rationale."
        ),
        IntentType.STATISTICAL_REVIEW: (
            "Focus on statistical quality: research design, sampling adequacy, assumption checking, "
            "effect sizes, confidence intervals, and APA reporting standards."
        ),
        IntentType.JOURNAL_REC: (
            "Recommend 3–5 specific journals with rationale: scope fit, quartile, "
            "acceptance rate, typical turnaround, and open access options."
        ),
        IntentType.GRANT_GUIDANCE: (
            "Advise on grant strategy: identify suitable calls, assess proposal strength, "
            "highlight critical sections (impact statement, work plan, budget)."
        ),
        IntentType.CONFERENCE_GUIDANCE: (
            "Recommend 3+ specific conferences with submission deadlines, "
            "prestige level, and fit assessment."
        ),
        IntentType.METHODOLOGY_ADVICE: (
            "Recommend the most appropriate methodology with full justification: "
            "design, sampling, instruments, analysis plan."
        ),
        IntentType.CAREER_PLANNING: (
            "Provide a prioritised career strategy with specific, measurable actions "
            "tailored to the user's current stage and goals."
        ),
        IntentType.WRITING_COACHING: (
            "Analyse writing quality and provide specific, actionable improvements "
            "at the sentence, paragraph, and section level."
        ),
        IntentType.ROADMAP_REQUEST: (
            "Outline a step-by-step roadmap with phases, estimated durations, "
            "key milestones, and risks."
        ),
        IntentType.PROJECT_PLANNING: (
            "Help plan and prioritise research tasks, milestones, and deadlines "
            "based on the user's active projects."
        ),
        IntentType.GENERAL_CHAT: (
            "Provide expert academic guidance relevant to the user's profile and goals."
        ),
    }
    return f"\nFOCUS FOR THIS RESPONSE: {instructions.get(primary, '')}"


# ── Public API ────────────────────────────────────────────────────────────────

async def generate_copilot_response(
    user_message: str,
    conversation_history: list[dict],
    context: dict,
    intents: list[DetectedIntent],
    engine_results: dict,
    max_tokens: int = 2500,
) -> tuple[str, int]:
    """Generate the copilot LLM response. Returns (text, tokens_used)."""
    try:
        from services.ai.llm import call_llm
    except ImportError:
        logger.warning("call_llm not available — returning mock response")
        return _mock_response(user_message, intents, engine_results), 0

    engine_summary = _summarise_engine_results(engine_results)
    intent_instruction = _intent_instruction(intents)

    # Build context section from user profile + memory
    summary = context.get("summary", "")
    memory_items = context.get("memory") or []
    memory_lines = "\n".join(
        f"  [{m.get('memory_type', 'general')}] {m.get('content', '')}"
        for m in memory_items[:8]
    )
    memory_section = f"\n\nUSER MEMORY:\n{memory_lines}" if memory_lines else ""

    manuscripts = context.get("manuscripts") or []
    projects = context.get("projects") or []
    impact = context.get("impact") or {}

    data_parts = []
    if manuscripts:
        data_parts.append(
            "Manuscripts: " + " | ".join(
                f"\"{m.get('title', 'Untitled')}\" ({m.get('status', '')})"
                for m in manuscripts[:4]
            )
        )
    if projects:
        data_parts.append(
            "Projects: " + " | ".join(
                f"\"{p.get('title', 'Untitled')}\" ({p.get('status', '')})"
                for p in projects[:4]
            )
        )
    if impact.get("publication_count"):
        data_parts.append(
            f"Impact: {impact.get('publication_count')} publications, "
            f"H-index={impact.get('h_index', 0)}, SIS={impact.get('sis_total', 0)}/10000"
        )
    data_section = "\n".join(data_parts)

    system = (
        f"{_COPILOT_SYSTEM}"
        f"\n\nUSER CONTEXT:\n{summary}"
        + (f"\n{data_section}" if data_section else "")
        + memory_section
        + engine_summary
        + intent_instruction
    )

    messages: list[dict] = []
    for msg in (conversation_history or [])[-12:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": str(content)})
    messages.append({"role": "user", "content": user_message})

    try:
        response_text = await call_llm(
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            feature="copilot.advisor",
        )
    except Exception as exc:
        logger.error("copilot LLM call failed: %s", exc)
        response_text = (
            "I encountered a temporary issue. Your request is understood — "
            "please try again in a moment."
        )

    tokens_used = len(response_text) // 4
    return response_text, tokens_used


def _mock_response(message: str, intents: list[DetectedIntent], engine_results: dict) -> str:
    primary = intents[0].intent_type.value if intents else "general_chat"
    return (
        f"[Copilot — {primary}] I've analysed your request. "
        f"Engine results available: {list(engine_results.keys())}. "
        "Configure ANTHROPIC_API_KEY or OPENAI_API_KEY for full responses."
    )
