"""Conference Intelligence Agent (Phase XIII)."""
from __future__ import annotations

import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType


@AgentRegistry.register
class ConferenceIntelligenceAgent(AcademicAgent):
    agent_id = "conference_intelligence_agent_v1"
    agent_type = AgentType.CONFERENCE_INTELLIGENCE
    name = "Conference Intelligence Agent"
    domain = "Conference Selection & Strategy"
    capabilities = [
        "conference_matching", "deadline_tracking", "networking_value",
        "acceptance_probability", "abstract_strategy",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        md = task.metadata
        discipline = md.get("discipline", "general")
        quality = float(md.get("manuscript_quality", 70))

        top_fits: list[dict] = []
        try:
            from services.publishing.conference_analyzer import analyze_conference_fit
            fits = analyze_conference_fit(text, discipline, quality)[:5]
            top_fits = [f.to_dict() for f in fits]
        except Exception:
            pass

        confidence = 0.72 if top_fits else 0.38

        output = {
            "top_conference_matches": top_fits,
            "discipline": discipline,
            "strategy_notes": [
                "Conference presentation builds visibility before journal submission",
                "A*/A-ranked conferences carry significant prestige weight",
                "Journal-track conferences allow simultaneous publication",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=f"Matched {len(top_fits)} conferences for '{discipline}'.",
            evidence=[f["name"] for f in top_fits[:5]],
            t0=t0,
        )
