"""Grant Intelligence Agent (Phase XIII)."""
from __future__ import annotations

import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType


@AgentRegistry.register
class GrantIntelligenceAgent(AcademicAgent):
    agent_id = "grant_intelligence_agent_v1"
    agent_type = AgentType.GRANT_INTELLIGENCE
    name = "Grant Intelligence Agent"
    domain = "Grant Matching & Strategy"
    capabilities = [
        "grant_matching", "eligibility_assessment", "competitiveness_analysis",
        "proposal_readiness", "funding_strategy",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        md = task.metadata
        discipline = md.get("discipline", "general")
        quality = float(md.get("manuscript_quality", 70))
        user_profile = md.get("user_profile") or context.user_profile or {}

        top_fits: list[dict] = []
        try:
            from services.publishing.grant_analyzer import analyze_grant_fit
            fits = analyze_grant_fit(text, discipline, quality, user_profile)[:5]
            top_fits = [f.to_dict() for f in fits]
        except Exception:
            pass

        confidence = 0.73 if top_fits else 0.40

        output = {
            "top_grant_matches": top_fits,
            "discipline": discipline,
            "funding_strategy": [
                "Apply to multiple grants at different funding levels",
                "Start with smaller grants to build track record",
                "ERC/NIH require strong preliminary data — build this first",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=f"Matched {len(top_fits)} grants for '{discipline}'.",
            evidence=[f["title"] for f in top_fits[:5]],
            t0=t0,
        )
