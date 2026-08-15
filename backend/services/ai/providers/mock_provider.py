"""MockProvider — deterministic responses for dev, demo, and test environments.

Returned when no cloud API key is configured or when all real providers fail.
Responses are structured and academic in tone so the UI renders correctly.
"""
from __future__ import annotations

import json
import time
from typing import AsyncIterator

from services.ai.engine.config import ProviderConfig
from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer, ProviderHealth
from services.ai.providers.base import AIProvider

# Keys MUST match the exact `feature=` string each router passes to call_llm()
# (grep each router for `feature="..."` / `prompt_id="..."` to verify) — not a
# human-readable label. Every key below previously used the short/label form
# ("abstract_generator", "literature_review", ...) instead of the real
# namespaced feature id ("manuscript.abstract_generator",
# "literature_review.synthesis", ...), so none of them were ever selected:
# every mock response silently fell through to _DEFAULT_TEMPLATE regardless
# of which feature was called.
#
# research_gap.finder, literature_review.synthesis, manuscript.review, and
# manuscript.rewriting/abstract_generator all `json.loads()` the raw response
# (see their routers) — a markdown-prose demo string fails that parse and
# surfaces as a confusing generic error, so these templates return the exact
# JSON shape each router's prompt (gateway/prompt_registry.py or the router's
# own prompt constant) instructs the real model to produce, just with
# placeholder values instead of real analysis. admin_copilot renders its
# response as plain text (no JSON parsing), so it keeps a prose template.
_FEATURE_TEMPLATES: dict[str, str] = {
    "research_gap.finder": json.dumps({
        "topic_overview": {
            "summary": "(Demo Mode) Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env for a real gap analysis of this topic.",
            "maturity_level": "developing",
            "research_volume": "moderate",
            "key_disciplines_involved": ["General"],
            "knowledge_basis_note": "This is placeholder demo content, not a real analysis.",
        },
        "current_state_of_research": {
            "dominant_paradigms": ["Demo placeholder — configure an API key for real content"],
            "established_consensus": [],
            "active_frontiers": [],
            "synthesis": "Demo Mode — no real literature analysis was performed.",
        },
        "highly_studied_areas": [],
        "underexplored_areas": [{
            "area": "Demo Mode",
            "explanation": "Configure your API key to generate a real research gap analysis from your inputs.",
            "why_neglected": "N/A",
            "opportunity_level": "medium",
        }],
        "contradictory_findings": [],
    }),
    "literature_review.synthesis": json.dumps({
        "executive_summary": {
            "overview": "(Demo Mode) Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env for a real literature synthesis.",
            "scope_assessment": "Demo placeholder — not a real assessment.",
            "review_confidence": "N/A — demo mode",
        },
        "major_themes": [],
        "key_authors": [],
        "theoretical_foundations": [],
    }),
    "manuscript.review": json.dumps({
        "executive_summary": {
            "overview": "(Demo Mode) Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env for a real AI manuscript review.",
            "recommendation": "minor_revision",
            "overall_score": 70,
        },
        "sections": {},
    }),
    "manuscript.abstract_generator": json.dumps({
        "abstract": "(Demo Mode) This is placeholder text. Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env to generate a real abstract from your manuscript content.",
        "keywords": ["demo", "placeholder"],
        "word_count": 28,
        "key_contribution": "Demo Mode — configure an API key for a real abstract.",
    }),
    # Journal/conference/grant/reviewer matching (services/ai/matching.py)
    # all share this one feature id and all read result["recommendations"].
    # Real candidate ids can't be guessed here, so an empty list is the only
    # response that's both valid and honest — the caller already handles zero
    # matches gracefully (it hydrates by id and just returns what matched).
    "collaboration.matching": json.dumps({"recommendations": []}),
    # routers/collaboration_intelligence.py's /generate strictly json.loads()s
    # this and reads ["recommendations"]. routers/ai.py's recommend_collaborators
    # also uses this exact feature id but expects "ID|reason" lines instead —
    # it already falls back to its own heuristic when that parse finds no
    # matches, so this JSON response (which contains no "|") is safe for it too.
    "collaboration.researcher_matching": json.dumps({"recommendations": []}),
    "manuscript.rewriting": json.dumps({
        "rewritten": "(Demo Mode) Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env to receive real AI-powered rewriting.",
        "changes_summary": "Demo Mode — no real rewriting was performed.",
        "style_applied": "demo",
        "word_count_original": 0,
        "word_count_rewritten": 0,
    }),
    "teaching.lesson_plan": json.dumps({
        "title": "(Demo Mode) Configure an API key for a real lesson plan",
        "learning_objectives": ["Demo Mode — configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env"],
        "materials": ["Demo placeholder"],
        "outline": [{
            "phase": "Introduction", "duration_minutes": 0,
            "activity": "Demo Mode — no real lesson plan was generated.",
            "notes": "Configure an API key to generate real content.",
        }],
        "assessment_strategy": "Demo Mode — not a real assessment strategy.",
        "differentiation_strategies": ["Demo placeholder"],
        "teacher_notes": "Demo Mode — configure an API key for real teacher notes.",
    }),
    "statistical.advisor": json.dumps({
        "summary": "(Demo Mode) Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env for a real statistical review.",
        "publication_readiness": {"score": 0, "assessment": "Demo Mode — not a real assessment."},
        "issues": [],
        "recommendations": ["Demo Mode — configure an API key for real recommendations."],
    }),
    "research_design.advisor": json.dumps({
        "summary": "(Demo Mode) Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env for a real research design review.",
        "publication_readiness": {"score": 0, "assessment": "Demo Mode — not a real assessment."},
        "issues": [],
        "recommendations": ["Demo Mode — configure an API key for real recommendations."],
    }),
    "teaching.assessment": json.dumps({
        "instructions": "(Demo Mode) Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env for a real assessment.",
        "questions": [],
        "rubric_criteria": [],
        "teacher_notes": "Demo Mode — no real assessment was generated.",
    }),
    "admin_copilot": (
        "**Admin Briefing** (Demo Mode)\n\n"
        "Platform is operating within normal parameters. "
        "Key metrics are trending positively. "
        "No critical alerts detected.\n\n"
        "_Configure your ANTHROPIC_API_KEY to enable real AI copilot briefings._"
    ),
}

# Features whose template above is a JSON payload (the caller does
# json.loads() on the raw response) rather than prose — the "> quoted
# excerpt of your prompt" prefix generate() adds below is a nice touch for
# chat/prose demo responses, but prepending it to one of these breaks JSON
# parsing entirely.
_JSON_TEMPLATE_FEATURES = {
    "research_gap.finder", "literature_review.synthesis", "manuscript.review",
    "manuscript.abstract_generator", "manuscript.rewriting", "collaboration.matching",
    "collaboration.researcher_matching", "teaching.lesson_plan", "teaching.assessment",
    "statistical.advisor", "research_design.advisor",
}

_DEFAULT_TEMPLATE = (
    "**Synaptiq AI** (Demo Mode)\n\n"
    "I received your request. To enable full AI capabilities, add your API key to "
    "`backend/.env`:\n\n"
    "```\nANTHROPIC_API_KEY=sk-ant-...\n```\n\n"
    "**Available AI features:**\n"
    "- Research Gap Finder\n"
    "- Literature Review\n"
    "- Manuscript & Statistical Review\n"
    "- Abstract Generator & Rewriting\n"
    "- Journal, Conference, Grant & Reviewer Matching\n"
    "- Collaboration Intelligence\n"
    "- Teaching Materials & Assessments\n"
    "- Synaptiq AI OS Chat\n\n"
    "_Set your API key and restart the server to activate all features._"
)


class MockProvider(AIProvider):
    """Zero-dependency provider that returns structured demo responses."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self._config = config or ProviderConfig(name="mock", default_model="mock-v1")

    @property
    def name(self) -> str:
        return "mock"

    async def generate(self, request: AIRequest) -> AIResponse:
        start = time.monotonic()
        text = _FEATURE_TEMPLATES.get(request.feature, _DEFAULT_TEMPLATE)

        if request.feature not in _JSON_TEMPLATE_FEATURES:
            last_user = next(
                (m["content"] for m in reversed(request.messages) if m.get("role") == "user"),
                "",
            )
            if last_user.strip():
                snippet = last_user.strip()[:80]
                text = f'> "{snippet}"\n\n{text}'

        latency_ms = int((time.monotonic() - start) * 1000)
        return AIResponse(
            text=text,
            layer=ExecutionLayer.CLOUD,
            provider="mock",
            model="mock-v1",
            input_tokens=self.estimate_tokens(request.messages),
            output_tokens=len(text) // 4,
            latency_ms=latency_ms,
            cost_usd=0.0,
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        response = await self.generate(request)
        for word in response.text.split(" "):
            yield word + " "

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            name="mock",
            available=True,
            latency_ms=0,
            models=["mock-v1"],
        )

    def estimate_tokens(self, messages: list[dict]) -> int:
        return sum(len(str(m.get("content", ""))) for m in messages) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def validate(self) -> bool:
        return True
