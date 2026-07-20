"""Publication Strategy Agent (Phase XIII)."""
from __future__ import annotations

import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType


@AgentRegistry.register
class PublicationStrategyAgent(AcademicAgent):
    agent_id = "publication_strategy_agent_v1"
    agent_type = AgentType.PUBLICATION_STRATEGY
    name = "Publication Strategy Agent"
    domain = "Publication Strategy & Roadmap"
    capabilities = [
        "journal_selection", "submission_roadmap", "backup_planning",
        "open_access_strategy", "citation_maximisation",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        md = task.metadata
        discipline = md.get("discipline", "general")
        quality = float(md.get("manuscript_quality", 70))
        title = md.get("title", "Research Manuscript")

        # Inherit journal results
        journal_result = context.get_result(AgentType.JOURNAL_INTELLIGENCE)
        top_journal = "your target journal"
        if journal_result and journal_result.output.get("top_journal_matches"):
            top_journal = journal_result.output["top_journal_matches"][0]["journal"]["name"]

        # Build strategy
        strategy_dict: dict = {}
        try:
            from services.publishing.strategy_builder import build_publication_strategy
            strategy = build_publication_strategy(title, text, discipline, quality)
            strategy_dict = strategy.to_dict()
        except Exception:
            pass

        confidence = 0.78 if strategy_dict else 0.50

        output = {
            "top_target_journal": top_journal,
            "strategy": strategy_dict,
            "key_recommendations": [
                f"Submit to {top_journal} first (highest overall fit)",
                "Prepare a preprint on arXiv/SSRN/bioRxiv for immediate visibility",
                "Build a list of 3 backup journals before submitting",
                "Track submission via a personal spreadsheet",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=f"Built publication strategy targeting '{top_journal}'.",
            evidence=[top_journal],
            t0=t0,
        )
