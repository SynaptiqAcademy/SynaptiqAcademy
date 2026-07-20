"""Funding Agent — grant matching using verified platform database entries only."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.funding")


class FundingAgent(BaseAgent):
    name         = "funding"
    description  = "Matches researchers to verified grant opportunities from the platform database."
    mission      = "Surface real, open grant opportunities aligned with the researcher's profile."
    capabilities = [
        "Grant opportunity matching",
        "Eligibility guidance",
        "Proposal quality checklist",
        "Deadline tracking",
        "Application planning",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        interests = memory.get("interests") or []
        grants    = memory.get("grants")  or []
        now       = datetime.now(timezone.utc)

        evidence  = []

        if not grants:
            try:
                grants = await db.grants.find({"deadline": {"$gte": now}}).sort("deadline", 1).limit(20).to_list(20)
                memory.set("grants", grants)
            except Exception as exc:
                logger.debug("Grants DB error: %s", exc)

        if not grants:
            return self._insufficient(task.id, [
                "Open grant opportunities in the platform database (none currently available)",
            ])

        evidence.append(self._ev(
            "database_query", "Synaptiq platform database — grants collection",
            f"{len(grants)} open grant(s) retrieved with future deadlines"
        ))

        if interests:
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Research interests used for matching: {', '.join(interests[:4])}"
            ))

        # Build grant summaries from real data only
        grant_lines = []
        for g in grants[:10]:
            title  = g.get("title", "Untitled")[:60]
            funder = g.get("funder") or g.get("organization") or ""
            dl     = g.get("deadline")
            dl_str = dl.strftime("%Y-%m-%d") if isinstance(dl, datetime) else str(dl)[:10] if dl else "?"
            amount = g.get("amount") or g.get("max_award") or ""
            amount_str = f" — {amount}" if amount else ""
            areas  = ", ".join((g.get("research_areas") or g.get("fields") or [])[:3])
            overlap = [kw for kw in interests if any(kw.lower() in (a.lower()) for a in (g.get("research_areas") or g.get("fields") or []))]
            match_indicator = " ★ INTEREST MATCH" if overlap else ""
            grant_lines.append(f"• {title}{amount_str} | {funder} | Deadline: {dl_str} | Areas: {areas or 'Not specified'}{match_indicator}")

        grants_text = "\n".join(grant_lines)

        from services.ai.llm import call_llm
        funding_advice = await call_llm(
            system=(
                "You are a Research Funding Specialist. "
                "Advise researchers on grant opportunities based ONLY on the data provided below. "
                "Never invent grant names, amounts, funders, or deadlines. "
                "Never estimate funding probability or success rates. "
                "Focus on eligibility criteria, application strategy, and realistic next steps."
            ),
            user_msg=(
                f"Funding request: {task.user_input}\n"
                f"Researcher interests: {', '.join(interests[:5]) if interests else 'Not specified'}\n\n"
                f"Open grants in platform database:\n{grants_text}\n\n"
                "Provide: (1) Most relevant grants (★ marked) with brief eligibility rationale, "
                "(2) Application prioritization advice, "
                "(3) Proposal quality checklist for academic grants, "
                "(4) Deadline urgency notes, "
                "(5) Collaboration opportunities that could strengthen applications."
            ),
            feature="copilot_funding",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=funding_advice,
            structured_data={"grants_found": len(grants), "matched_by_interest": sum(
                1 for g in grants if any(kw.lower() in str(g).lower() for kw in interests)
            )},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient",
            limitations=[
                "Only grants listed in the Synaptiq platform database are shown.",
                "Eligibility must be verified directly with the funding body.",
                "No funding probability estimates are provided.",
            ],
        )


REGISTRY.register(FundingAgent())
