"""Study Design Agent — methodology and experimental design guidance."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.study_design")


class StudyDesignAgent(BaseAgent):
    name         = "study_design"
    description  = "Recommends research methodology and experimental design frameworks."
    mission      = "Help researchers choose and justify the right study design for their research question."
    capabilities = [
        "Research methodology selection",
        "Experimental design",
        "Sampling strategy",
        "Variable identification",
        "Validity and reliability planning",
        "Research framework recommendation",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        interests   = memory.get("interests") or []
        domain      = memory.get("domain") or ""
        manuscripts = memory.get("manuscripts") or []

        context_parts = []
        evidence = []

        if interests:
            context_parts.append(f"Research domain: {', '.join(interests[:4])}")
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Research interests: {', '.join(interests[:4])}"
            ))

        if domain:
            context_parts.append(f"Primary domain: {domain}")
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Primary domain: {domain}"
            ))

        if manuscripts:
            ms = manuscripts[0]
            ms_title = ms.get("title", "Untitled manuscript")[:60]
            context_parts.append(f"Current manuscript: {ms_title}")
            evidence.append(self._ev(
                "database_query", "Synaptiq platform database — manuscripts",
                f"Active manuscript found: '{ms_title}'"
            ))

        # Gap agent output may provide research question context
        gap_out = memory.get_agent_output("gap")
        gap_context = ""
        if gap_out and gap_out.status in ("success", "partial"):
            gap_context = f"\nResearch gaps identified:\n{gap_out.content[:500]}"
            evidence.append(self._ev(
                "agent_output", "Research Gap Agent",
                "Gap analysis used to inform methodology recommendation"
            ))

        user_context = "\n".join(context_parts) if context_parts else "No profile context available."

        from services.ai.llm import call_llm
        design_advice = await call_llm(
            system=(
                "You are a Research Methodology Expert specializing in academic study design. "
                "Provide evidence-informed methodology guidance based ONLY on what the user has described. "
                "Never fabricate statistics about success rates or outcomes. "
                "Reference established methodology frameworks and name them accurately."
            ),
            user_msg=(
                f"User's research need: {task.user_input}\n"
                f"Context:\n{user_context}{gap_context}\n\n"
                "Provide: (1) Recommended study design(s) with rationale, "
                "(2) Sampling strategy recommendations, "
                "(3) Key variables to consider (independent, dependent, confounders), "
                "(4) Validity threats to plan for, "
                "(5) Alternative designs if the primary isn't feasible."
            ),
            feature="copilot_study_design",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=design_advice,
            structured_data={"context_loaded": bool(context_parts)},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient" if context_parts else "partial",
            limitations=[
                "Methodology advice is based on the user's description only — not on reviewing actual study data.",
                "Domain-specific institutional constraints are not accounted for.",
            ],
        )


REGISTRY.register(StudyDesignAgent())
