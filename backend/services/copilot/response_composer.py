"""Academic Copilot — Response Composer (Phase XI).

Merges AI narrative, engine scan results, and proactive suggestions into
a final CopilotResponse. Also extracts suggested actions and sources from
the AI text and the engine results.
"""
from __future__ import annotations

import re

from .models import (
    CopilotResponse, CopilotWorkflow, DetectedIntent,
    IntentType, ProactiveSuggestion,
)


def _extract_suggested_actions(
    ai_text: str,
    engine_results: dict,
    context: dict,
) -> list[dict]:
    actions: list[dict] = []
    lower = ai_text.lower()

    if any(p in lower for p in ["create a project", "start a project", "new project"]):
        actions.append({"action_type": "create_project", "label": "Create Project", "params": {}})

    if any(p in lower for p in ["create a manuscript", "start writing", "write a paper", "draft a manuscript"]):
        actions.append({"action_type": "create_manuscript", "label": "Create Manuscript", "params": {}})

    if any(p in lower for p in ["submit to", "submit your manuscript", "submit your paper"]):
        actions.append({"action_type": "find_journal", "label": "Find Target Journal", "params": {}})

    if any(p in lower for p in ["full manuscript review", "run a manuscript review", "manuscript intelligence"]):
        actions.append({"action_type": "full_manuscript_review", "label": "Run Manuscript Review", "params": {}})

    if any(p in lower for p in ["statistical review", "statistical intelligence"]):
        actions.append({"action_type": "full_statistical_review", "label": "Run Statistical Review", "params": {}})

    if any(p in lower for p in ["literature review", "search literature"]):
        actions.append({"action_type": "full_literature_review", "label": "Run Literature Review", "params": {}})

    if any(p in lower for p in ["apply for a grant", "grant proposal"]):
        actions.append({"action_type": "find_grant", "label": "Find Grant Opportunities", "params": {}})

    if any(p in lower for p in ["remember this", "save this", "keep this in mind"]):
        actions.append({"action_type": "save_memory", "label": "Save to Memory", "params": {"memory_type": "general"}})

    if any(p in lower for p in ["roadmap", "research plan", "publication plan"]):
        actions.append({"action_type": "generate_roadmap", "label": "Generate Roadmap", "params": {}})

    # Add actions based on engine findings
    ms = engine_results.get("manuscript")
    if ms and ms.get("critical_issue_count", 0) > 0:
        actions.append({
            "action_type": "full_manuscript_review",
            "label": f"Fix {ms['critical_issue_count']} Critical Issue(s)",
            "params": {},
        })

    stat = engine_results.get("statistical")
    if stat and stat.get("issue_count", 0) > 3:
        actions.append({
            "action_type": "full_statistical_review",
            "label": "Deep Statistical Analysis",
            "params": {},
        })

    # Deduplicate by action_type
    seen: set[str] = set()
    unique: list[dict] = []
    for a in actions:
        if a["action_type"] not in seen:
            seen.add(a["action_type"])
            unique.append(a)

    return unique[:5]


def _extract_sources(ai_text: str, context: dict) -> list[dict]:
    sources: list[dict] = []
    lower = ai_text.lower()

    for ms in (context.get("manuscripts") or []):
        title = ms.get("title", "")
        if title and len(title) > 4 and title.lower() in lower:
            sources.append({"type": "manuscript", "title": title, "id": ms.get("id", "")})

    for p in (context.get("projects") or []):
        title = p.get("title", "")
        if title and len(title) > 4 and title.lower() in lower:
            sources.append({"type": "project", "title": title, "id": p.get("id", "")})

    for g in (context.get("grants_applied") or []):
        title = g.get("grant_title") or g.get("title") or ""
        if title and len(title) > 4 and title.lower() in lower:
            sources.append({"type": "grant", "title": title, "id": g.get("grant_id", "")})

    return sources[:5]


def _infer_confidence(
    intents: list[DetectedIntent],
    engine_results: dict,
    ai_text: str,
) -> float:
    """Heuristic confidence for the overall response."""
    if not intents:
        return 0.5

    primary_conf = intents[0].confidence

    # Boost if engine results are available
    engine_boost = 0.1 * len([v for v in engine_results.values() if "error" not in v])

    # Penalise if AI text is very short (likely a fallback/error)
    length_penalty = -0.2 if len(ai_text) < 200 else 0.0

    return max(0.1, min(1.0, primary_conf + engine_boost + length_penalty))


def _infer_agent_type(intents: list[DetectedIntent]) -> str:
    if not intents:
        return "general"
    type_map = {
        IntentType.MANUSCRIPT_REVIEW:   "publication",
        IntentType.LITERATURE_REVIEW:   "research",
        IntentType.GAP_ANALYSIS:        "research",
        IntentType.STATISTICAL_REVIEW:  "research",
        IntentType.JOURNAL_REC:         "journal",
        IntentType.GRANT_GUIDANCE:      "grant",
        IntentType.CONFERENCE_GUIDANCE: "general",
        IntentType.METHODOLOGY_ADVICE:  "research",
        IntentType.CAREER_PLANNING:     "profile",
        IntentType.WRITING_COACHING:    "publication",
        IntentType.ROADMAP_REQUEST:     "analytics",
        IntentType.PROJECT_PLANNING:    "analytics",
        IntentType.GENERAL_CHAT:        "general",
    }
    return type_map.get(intents[0].intent_type, "general")


def compose(
    user_id: str,
    ai_text: str,
    intents: list[DetectedIntent],
    engine_results: dict,
    context: dict,
    workflow: CopilotWorkflow | None = None,
    suggestions: list[ProactiveSuggestion] | None = None,
    tokens_used: int = 0,
    latency_ms: float = 0.0,
) -> CopilotResponse:
    return CopilotResponse(
        user_id=user_id,
        message=ai_text,
        intents=intents,
        workflow=workflow,
        engine_results={k: {ek: ev for ek, ev in v.items() if ek != "raw_output"}
                        for k, v in engine_results.items()},
        suggested_actions=_extract_suggested_actions(ai_text, engine_results, context),
        proactive_suggestions=suggestions or [],
        sources=_extract_sources(ai_text, context),
        reasoning=f"Primary intent: {intents[0].intent_type.value} (confidence={intents[0].confidence:.2f}). "
                  f"Engines invoked: {list(engine_results.keys()) or ['none']}."
                  if intents else "General academic guidance.",
        confidence=_infer_confidence(intents, engine_results, ai_text),
        agent_type=_infer_agent_type(intents),
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )
