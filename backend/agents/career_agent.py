"""Career Agent — academic career development based on verified profile and activity data."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.career")

CAREER_STAGES = {
    "phd_student":       "PhD Student",
    "postdoc":           "Postdoctoral Researcher",
    "early_career":      "Early Career Researcher",
    "assistant_prof":    "Assistant Professor",
    "associate_prof":    "Associate Professor",
    "full_prof":         "Full Professor",
    "researcher":        "Researcher",
    "practitioner":      "Practitioner-Researcher",
}


class CareerAgent(BaseAgent):
    name         = "career"
    description  = "Provides academic career development guidance based on your verified profile data."
    mission      = "Help researchers plan their academic career trajectory using evidence from their actual profile."
    capabilities = [
        "Career stage assessment",
        "Promotion readiness analysis",
        "Publication strategy",
        "Reviewer and editorial opportunities",
        "Academic reputation building",
        "Career risk identification",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        uid         = memory.get("uid") or ""
        role        = memory.get("role") or ""
        institution = memory.get("institution") or ""
        interests   = memory.get("interests") or []
        manuscripts = memory.get("manuscripts") or []
        orcid       = memory.get("orcid")

        evidence = []

        stage = CAREER_STAGES.get(role.lower().replace(" ", "_"), role or "Unknown")
        if role:
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Academic role: {stage}"
            ))
        if institution:
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Institution: {institution}"
            ))
        if manuscripts:
            evidence.append(self._ev(
                "database_query", "Synaptiq platform database — manuscripts",
                f"{len(manuscripts)} manuscript record(s) in profile"
            ))

        ms_count = len(manuscripts)
        pub_count = sum(1 for m in manuscripts if m.get("status") == "published")

        profile_context = (
            f"Role: {stage} | Institution: {institution or 'Not specified'} | "
            f"Manuscripts on platform: {ms_count} ({pub_count} published) | "
            f"ORCID: {'Connected' if orcid else 'Not connected'} | "
            f"Research areas: {', '.join(interests[:4]) if interests else 'Not specified'}"
        )

        if not role and not manuscripts and not interests:
            return self._insufficient(task.id, [
                "Academic role (set in profile)",
                "Research interests (set in profile)",
                "Publication records",
            ])

        from services.ai.llm import call_llm
        career_advice = await call_llm(
            system=(
                "You are an Academic Career Advisor with expertise in higher education career development. "
                "Provide honest, stage-appropriate career guidance based on the researcher's verified profile data. "
                "Never fabricate publication counts, citation numbers, or promotion timelines. "
                "Be specific about actionable steps and realistic about timelines. "
                "Acknowledge when profile data is sparse and advise accordingly."
            ),
            user_msg=(
                f"Career guidance request: {task.user_input}\n\n"
                f"Verified profile (from Synaptiq database):\n{profile_context}\n\n"
                "Provide: (1) Career stage assessment and what typically comes next, "
                "(2) Publication strategy for this stage (based on current manuscript count), "
                "(3) Reputation-building priorities (reviewer, editorial, conference roles), "
                "(4) Concrete 3-6 month action plan, "
                "(5) Career risks to be aware of at this stage."
            ),
            feature="copilot_career",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=career_advice,
            structured_data={"stage": stage, "manuscript_count": ms_count, "published_count": pub_count},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient" if role and interests else "partial",
            limitations=[
                "Career advice is based on platform profile data only — not verified external publications or citations.",
                "Academic career timelines vary significantly by field, institution, and country.",
            ],
        )


REGISTRY.register(CareerAgent())
