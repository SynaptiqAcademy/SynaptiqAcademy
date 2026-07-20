"""Research Gap Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_GAP_SIGNALS = [
    "gap in the literature", "research gap", "little is known", "limited research",
    "no study", "few studies", "understudied", "underexplored", "future research",
    "calls for research", "needs further investigation", "remains unclear",
    "not yet studied", "overlooked", "neglected area",
]

_NOVELTY_SIGNALS = [
    "first study", "novel", "unique", "original contribution", "to our knowledge",
    "previously unexplored", "new approach", "innovative", "pioneering",
]


@AgentRegistry.register
class ResearchGapAgent(AcademicAgent):
    agent_id = "research_gap_agent_v1"
    agent_type = AgentType.RESEARCH_GAP
    name = "Research Gap Agent"
    domain = "Knowledge Gap Analysis"
    capabilities = [
        "gap_identification", "novelty_assessment", "future_work_extraction",
        "research_opportunity_mapping", "contribution_analysis",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()

        # Find explicit gap signals
        gaps_found = [sig for sig in _GAP_SIGNALS if sig in text_lower]
        novelty_signals = [sig for sig in _NOVELTY_SIGNALS if sig in text_lower]

        # Look at literature result for additional gaps
        prev_lit = context.get_result(AgentType.LITERATURE_REVIEW)
        inherited_gaps: list[str] = []
        if prev_lit and prev_lit.output:
            inherited_gaps = prev_lit.output.get("gaps_to_address", [])

        # Identify research opportunities
        opportunities: list[str] = []
        if "quantitative" not in text_lower and "qualitative" in text_lower:
            opportunities.append("Quantitative replication of qualitative findings is an open gap")
        if "longitudinal" not in text_lower:
            opportunities.append("Longitudinal studies are lacking in this area")
        if "cross-cultural" not in text_lower and "culture" in text_lower:
            opportunities.append("Cross-cultural validation is an underexplored opportunity")
        if "intervention" not in text_lower:
            opportunities.append("Intervention studies or randomised designs are needed")
        if not gaps_found:
            opportunities.append("No explicit gap statements found — a gap statement should be added to the Introduction")

        # Assess novelty
        has_novelty = len(novelty_signals) >= 1
        novelty_score = min(1.0, len(novelty_signals) * 0.2 + (0.3 if gaps_found else 0))

        confidence = min(0.92, 0.5 + 0.1 * len(gaps_found) + 0.1 * has_novelty)

        output = {
            "explicit_gaps_found": gaps_found[:10],
            "novelty_signals": novelty_signals[:5],
            "has_novelty_claim": has_novelty,
            "novelty_score": round(novelty_score, 3),
            "research_opportunities": opportunities[:6],
            "inherited_gaps_from_literature": inherited_gaps[:3],
            "recommended_gap_statement": (
                f"While prior research has addressed related themes, "
                f"{'no study has' if not gaps_found else 'gaps remain in'} "
                f"systematically examining this phenomenon. "
                f"This study addresses {len(opportunities)} identified opportunities."
            ),
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Detected {len(gaps_found)} explicit gap signals and "
                f"{len(novelty_signals)} novelty claims. "
                f"Identified {len(opportunities)} research opportunities."
            ),
            evidence=gaps_found[:5] + novelty_signals[:3],
            t0=t0,
        )
