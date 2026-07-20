"""Journal Agent — journal matching and submission guidance using platform DB."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.journal")


class JournalAgent(BaseAgent):
    name         = "journal"
    description  = "Matches manuscripts to journals using platform database and submission guidelines."
    mission      = "Help researchers find and evaluate appropriate journals for their work."
    capabilities = [
        "Journal matching",
        "Scope compatibility analysis",
        "Submission requirements",
        "Predatory journal avoidance guidance",
        "Alternative journal suggestions",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        interests   = memory.get("interests") or []
        manuscripts = memory.get("manuscripts") or []

        evidence = []
        journals = []

        # Query platform journal database
        try:
            q_filter: dict = {}
            if interests:
                q_filter["$or"] = [
                    {"research_areas": {"$in": interests}},
                    {"fields": {"$in": interests}},
                    {"keywords": {"$in": interests}},
                ]
            found = await db.journals.find(q_filter).limit(10).to_list(10)
            journals = found
            if journals:
                evidence.append(self._ev(
                    "database_query", "Synaptiq platform database — journals collection",
                    f"{len(journals)} journal(s) found matching research interests"
                ))
        except Exception as exc:
            logger.debug("Journal DB query failed: %s", exc)

        ms_context = ""
        if manuscripts:
            ms = manuscripts[0]
            ms_title    = ms.get("title", "Untitled")[:60]
            ms_abstract = (ms.get("abstract") or "")[:400]
            ms_context  = f"\nManuscript: '{ms_title}'\n{ms_abstract}"
            evidence.append(self._ev(
                "database_query", "Synaptiq platform database — manuscripts",
                f"Using manuscript '{ms_title}' for scope matching"
            ))

        if interests:
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Research interests: {', '.join(interests[:4])}"
            ))

        if not interests and not manuscripts:
            return self._insufficient(task.id, [
                "Research interests (set in profile)",
                "Manuscript abstract (add a manuscript to your profile)",
            ])

        journals_text = ""
        if journals:
            for j in journals[:8]:
                name  = j.get("name") or j.get("title") or "Unknown journal"
                scope = j.get("scope") or j.get("description") or ""
                journals_text += f"• {name}" + (f": {scope[:80]}" if scope else "") + "\n"

        from services.ai.llm import call_llm
        journal_advice = await call_llm(
            system=(
                "You are a Journal Selection Specialist. "
                "Your job is to help researchers select appropriate journals for submission. "
                "ONLY reference journals that are explicitly listed below (from the platform database) or well-known journals you are certain exist. "
                "Never invent impact factors or acceptance rates. "
                "Include guidance on scope fit, predatory journal risks, and open access options."
            ),
            user_msg=(
                f"Submission task: {task.user_input}"
                f"{ms_context}\n"
                f"Research interests: {', '.join(interests[:5]) if interests else 'Not specified'}\n\n"
                + (f"Journals in platform database matching interests:\n{journals_text}\n" if journals_text else
                   "No journals found in the platform database for this research area.\n")
                + "\nProvide: (1) Journal recommendations with rationale, "
                "(2) Scope compatibility analysis for each recommended journal, "
                "(3) Submission format requirements to check, "
                "(4) Red flags to watch for (predatory indicators), "
                "(5) Submission strategy (tier targeting)."
            ),
            feature="copilot_journal",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success" if journals or interests else "partial",
            content=journal_advice,
            structured_data={"journals_found": len(journals), "using_profile": bool(interests)},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient" if journals else "partial",
            limitations=[
                "Journal scope compatibility is based on keyword/area matching — not deep content analysis.",
                "Impact factors change yearly — verify current values on journal websites.",
                "No acceptance probability estimates are provided (none can be reliably computed).",
            ],
        )


REGISTRY.register(JournalAgent())
