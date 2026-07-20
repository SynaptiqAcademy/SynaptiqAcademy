"""Institution Agent — analytics, benchmarking, and faculty insights from verified data."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.institution")


class InstitutionAgent(BaseAgent):
    name         = "institution"
    description  = "Provides institution-level analytics and research productivity insights."
    mission      = "Support research offices and institution leaders with verified data-driven insights."
    capabilities = [
        "Institution research analytics",
        "Faculty productivity data",
        "Research benchmarking",
        "Executive reporting",
        "Output forecasting guidance",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        uid         = memory.get("uid")
        institution = memory.get("institution") or ""

        evidence = []

        if institution:
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Institution on file: {institution}"
            ))

        # Platform-level institution analytics
        inst_data: dict = {}
        try:
            inst_data["total_users"] = await db.users.count_documents(
                {"institution": institution} if institution else {}
            )
            inst_data["total_manuscripts"] = await db.manuscripts.count_documents({})
            inst_data["total_projects"]    = await db.projects.count_documents({"status": "active"})
            inst_data["total_collabs"]     = await db.collaborations.count_documents({"status": "open"})

            if any(v > 0 for v in inst_data.values()):
                evidence.append(self._ev(
                    "database_query", "Synaptiq platform database — aggregated counts",
                    f"Platform totals: {inst_data['total_users']} users, {inst_data['total_manuscripts']} manuscripts, "
                    f"{inst_data['total_projects']} active projects"
                ))
        except Exception as exc:
            logger.debug("Institution analytics error: %s", exc)

        if not institution and not inst_data:
            return self._insufficient(task.id, [
                "Institution information (set institution in profile)",
                "Institution-level database records",
            ])

        inst_summary = (
            f"Platform data for {institution or 'your institution'}:\n"
            f"• Users on platform: {inst_data.get('total_users', 'N/A')}\n"
            f"• Manuscripts recorded: {inst_data.get('total_manuscripts', 'N/A')}\n"
            f"• Active projects: {inst_data.get('total_projects', 'N/A')}\n"
            f"• Open collaborations: {inst_data.get('total_collabs', 'N/A')}\n"
        )

        from services.ai.llm import call_llm
        inst_advice = await call_llm(
            system=(
                "You are an Institution Research Intelligence Analyst. "
                "Provide evidence-based insights for research office leaders. "
                "Only reference data explicitly provided below. "
                "Never fabricate benchmark comparisons, rankings, or outcome statistics. "
                "Focus on actionable recommendations based on the verified platform data."
            ),
            user_msg=(
                f"Institution analytics request: {task.user_input}\n"
                f"Institution: {institution or 'Not specified'}\n\n"
                f"Verified platform data:\n{inst_summary}\n"
                "Provide: (1) Research activity summary from platform data, "
                "(2) Productivity insights and trends based on the counts, "
                "(3) Strategic recommendations for research office, "
                "(4) KPIs to track going forward, "
                "(5) Data gaps that need attention."
            ),
            feature="copilot_institution",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=inst_advice,
            structured_data=inst_data,
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="partial",
            limitations=[
                "Analytics are limited to Synaptiq platform activity — not all institutional research output.",
                "No external ranking or benchmark data is used.",
                "Counts reflect platform records only, not verified institutional submissions.",
            ],
        )


REGISTRY.register(InstitutionAgent())
