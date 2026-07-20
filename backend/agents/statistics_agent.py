"""Statistics Agent — statistical methods, sample size, and analysis guidance."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.statistics")


class StatisticsAgent(BaseAgent):
    name         = "statistics"
    description  = "Provides statistical guidance based on study design and data description."
    mission      = "Recommend appropriate statistical methods and help interpret quantitative results."
    capabilities = [
        "Statistical method selection",
        "Sample size guidance",
        "Power analysis concepts",
        "Regression and hypothesis testing",
        "Model selection",
        "Result interpretation support",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        evidence = []

        # Read study design agent output if available
        design_out = memory.get_agent_output("study_design")
        design_context = ""
        if design_out and design_out.status in ("success", "partial"):
            design_context = f"\nStudy design context:\n{design_out.content[:500]}"
            evidence.append(self._ev(
                "agent_output", "Study Design Agent",
                "Study design used to inform statistical method recommendation"
            ))

        manuscripts = memory.get("manuscripts") or []
        if manuscripts:
            evidence.append(self._ev(
                "database_query", "Synaptiq platform database — manuscripts",
                f"{len(manuscripts)} manuscript record(s) found"
            ))

        if not task.user_input.strip() and not design_context:
            return self._insufficient(task.id, [
                "Research question or methodology description",
                "Data type description (quantitative/qualitative/mixed)",
            ])

        from services.ai.llm import call_llm
        stats_advice = await call_llm(
            system=(
                "You are a Biostatistics and Research Methods expert. "
                "Provide specific, accurate statistical guidance based only on what the user has described. "
                "Name methods accurately. Reference standard assumptions (normality, independence, etc.). "
                "Never fabricate p-values, effect sizes, or outcome statistics. "
                "When the data type is unclear, say so and ask for clarification."
            ),
            user_msg=(
                f"Research context: {task.user_input}{design_context}\n\n"
                "Provide: (1) Recommended statistical test(s) with justification, "
                "(2) Key assumptions that must be checked, "
                "(3) Sample size considerations (qualitative guidance only — not a calculated number without knowing parameters), "
                "(4) Common pitfalls to avoid for this type of analysis, "
                "(5) How to report results in academic format."
            ),
            feature="copilot_statistics",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=stats_advice,
            structured_data={"used_design_context": bool(design_context)},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="partial",
            limitations=[
                "Statistical guidance is qualitative — exact sample sizes require parameters (effect size, power, alpha).",
                "Cannot analyze actual data without access to the dataset.",
            ],
        )


REGISTRY.register(StatisticsAgent())
