"""MockProvider — deterministic responses for dev, demo, and test environments.

Returned when no cloud API key is configured or when all real providers fail.
Responses are structured and academic in tone so the UI renders correctly.
"""
from __future__ import annotations

import time
from typing import AsyncIterator

from services.ai.engine.config import ProviderConfig
from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer, ProviderHealth
from services.ai.providers.base import AIProvider

_FEATURE_TEMPLATES: dict[str, str] = {
    "research_gap_finder": (
        "**Research Gap Analysis** (Demo Mode)\n\n"
        "Based on the provided context, the following research gaps have been identified:\n\n"
        "1. **Methodological gap** — Current studies lack longitudinal designs that track outcomes "
        "across multiple institutional contexts.\n"
        "2. **Population gap** — Underrepresented groups remain understudied in this domain.\n"
        "3. **Synthesis gap** — No systematic review has integrated findings from the last five years.\n\n"
        "_To receive real AI analysis, configure your API key in `backend/.env`._"
    ),
    "literature_review": (
        "**Literature Review** (Demo Mode)\n\n"
        "## Key Themes\n- Theme 1: Foundational theoretical frameworks\n"
        "- Theme 2: Empirical evidence base\n- Theme 3: Methodological approaches\n\n"
        "## Research Trajectory\nThe field has evolved from descriptive studies toward "
        "experimental and mixed-methods designs.\n\n"
        "_Configure your API key to receive a full AI-generated literature review._"
    ),
    "manuscript_review": (
        "**Manuscript Review** (Demo Mode)\n\n"
        "## Strengths\n- Clear research question\n- Appropriate methodology\n\n"
        "## Areas for Improvement\n- Abstract could be more concise\n"
        "- Discussion section should address limitations more explicitly\n- References need updating\n\n"
        "_Configure your API key to receive a detailed peer-review report._"
    ),
    "abstract_generator": (
        "**Generated Abstract** (Demo Mode)\n\n"
        "This study examines [topic] using a [methodology] approach. "
        "Data were collected from [sample] and analysed using [methods]. "
        "Results indicate [key findings]. These findings contribute to "
        "[field] by [contribution]. Implications for [audience] are discussed.\n\n"
        "_Configure your API key to generate a real abstract from your manuscript._"
    ),
    "ai_rewriting": (
        "**Rewritten Text** (Demo Mode)\n\n"
        "The revised version improves clarity, concision, and academic register. "
        "Passive constructions have been converted to active voice where appropriate, "
        "and technical terminology has been standardised throughout.\n\n"
        "_Configure your API key to receive AI-powered rewriting._"
    ),
    "admin_copilot": (
        "**Admin Briefing** (Demo Mode)\n\n"
        "Platform is operating within normal parameters. "
        "Key metrics are trending positively. "
        "No critical alerts detected.\n\n"
        "_Configure your ANTHROPIC_API_KEY to enable real AI copilot briefings._"
    ),
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
