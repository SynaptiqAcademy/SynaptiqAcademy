"""Research Gap Agent — identifies gaps using literature results and user context."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.gap")


class GapAgent(BaseAgent):
    name         = "gap"
    description  = "Identifies research gaps and novelty opportunities."
    mission      = "Determine what has NOT been studied based on available literature and user research area."
    capabilities = [
        "Research gap identification",
        "Novelty detection",
        "Future research directions",
        "Contribution analysis",
        "Duplicate research avoidance",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        # Read literature agent output from shared memory if available
        lit_output = memory.get_agent_output("literature")
        lit_content = (lit_output.content if lit_output and lit_output.status in ("success", "partial") else "")

        interests = memory.get("interests") or []
        manuscripts = memory.get("manuscripts") or []

        user_topics = ", ".join(interests[:5]) if interests else "Not specified"

        if not lit_content and not interests:
            return self._insufficient(task.id, [
                "Literature context (run Literature Agent first)",
                "Research interests (set in profile)",
            ])

        evidence = []
        if lit_content:
            evidence.append(self._ev(
                "agent_output", "Literature Agent (OpenAlex search results)",
                f"Retrieved {len(lit_output.structured_data.get('papers', []))} real papers for gap analysis"
                if lit_output else "Literature agent output used"
            ))
        if interests:
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Research interests on file: {', '.join(interests[:4])}"
            ))
        if manuscripts:
            evidence.append(self._ev(
                "database_query", "Synaptiq platform database — manuscripts collection",
                f"{len(manuscripts)} manuscript(s) found in your profile"
            ))

        ms_context = ""
        if manuscripts:
            ms_titles = ", ".join(m.get("title", "Untitled")[:40] for m in manuscripts[:3])
            ms_context = f"\nUser's current manuscripts: {ms_titles}"

        from services.ai.llm import call_llm
        gap_analysis = await call_llm(
            system=(
                "You are a Research Gap Specialist. Your role is to identify genuine research gaps "
                "and opportunities for novel contributions. Base your analysis ONLY on the information provided. "
                "Never invent papers, statistics, or outcomes. Be specific about what is missing and why it matters."
            ),
            user_msg=(
                f"User's research question: {task.user_input}\n"
                f"Research interests: {user_topics}{ms_context}\n\n"
                f"Literature context:\n{lit_content or 'No literature retrieved yet.'}\n\n"
                "Identify: (1) Clear research gaps visible from the literature context, "
                "(2) Underexplored angles or populations, (3) Methodological gaps, "
                "(4) 2-3 specific research questions that appear to be unanswered, "
                "(5) How the user's research area could fill one of these gaps. "
                "Note: base your answer only on what is evident from the provided context."
            ),
            feature="copilot_gap",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=gap_analysis,
            structured_data={"sources_used": [e.source for e in evidence]},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="partial" if lit_content else "insufficient",
            limitations=[
                "Gap analysis is only as comprehensive as the literature retrieved.",
                "Without full-text access, some gaps may not be detectable.",
            ],
        )


REGISTRY.register(GapAgent())
