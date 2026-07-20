"""Journal Intelligence Agent (Phase XIII)."""
from __future__ import annotations

import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType


@AgentRegistry.register
class JournalIntelligenceAgent(AcademicAgent):
    agent_id = "journal_intelligence_agent_v1"
    agent_type = AgentType.JOURNAL_INTELLIGENCE
    name = "Journal Intelligence Agent"
    domain = "Journal Selection & Analysis"
    capabilities = [
        "journal_matching", "scope_analysis", "acceptance_probability",
        "predatory_risk_assessment", "submission_strategy",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        md = task.metadata
        discipline = md.get("discipline", "general")
        quality = float(md.get("manuscript_quality", 70))

        top_fits: list[dict] = []
        try:
            from services.publishing.journal_analyzer import analyze_journal_fit
            fits = analyze_journal_fit(text, discipline, quality)[:5]
            top_fits = [f.to_dict() for f in fits]
        except Exception as exc:
            top_fits = []

        confidence = 0.75 if top_fits else 0.40

        output = {
            "top_journal_matches": top_fits[:5],
            "discipline": discipline,
            "manuscript_quality_used": quality,
            "recommendation": (
                top_fits[0]["journal"]["name"]
                if top_fits
                else "Run journal analysis with manuscript text"
            ),
            "strategy_notes": [
                "Target Q1/Q2 journals for career advancement",
                "Consider open-access journals if funders require it",
                "Prepare a backup journal list before submitting",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=f"Matched {len(top_fits)} journals for discipline '{discipline}'.",
            evidence=[f["journal"]["name"] for f in top_fits[:5]],
            t0=t0,
        )
