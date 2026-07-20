"""Collaboration Agent — finds research partners from verified platform data."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.collaboration")


class CollaborationAgent(BaseAgent):
    name         = "collaboration"
    description  = "Identifies collaboration opportunities from real platform listings."
    mission      = "Help researchers find verified collaboration opportunities and research partners."
    capabilities = [
        "Research partner discovery",
        "Open collaboration listing",
        "Expert matching by research area",
        "Network analysis",
        "Co-authorship opportunities",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        interests      = memory.get("interests") or []
        collaborations = memory.get("collaborations") or []

        evidence = []

        if not collaborations:
            try:
                collaborations = await db.collaborations.find({"status": "open"}).limit(15).to_list(15)
                memory.set("collaborations", collaborations)
            except Exception as exc:
                logger.debug("Collaborations DB error: %s", exc)

        if collaborations:
            evidence.append(self._ev(
                "database_query", "Synaptiq platform database — collaborations collection",
                f"{len(collaborations)} open collaboration post(s) found"
            ))

        if interests:
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Research interests: {', '.join(interests[:4])}"
            ))

        # Find platform researchers with matching interests
        researchers = []
        try:
            if interests:
                researchers = await db.users.find(
                    {
                        "$or": [
                            {"research_interests": {"$in": interests}},
                            {"research_areas": {"$in": interests}},
                        ],
                        "profile_visibility": {"$ne": "private"},
                    },
                    {"full_name": 1, "institution": 1, "research_interests": 1, "user_type": 1}
                ).limit(8).to_list(8)
                if researchers:
                    evidence.append(self._ev(
                        "database_query", "Synaptiq platform database — users collection",
                        f"{len(researchers)} researchers found with overlapping research interests (public profiles only)"
                    ))
        except Exception as exc:
            logger.debug("Researcher search error: %s", exc)

        if not collaborations and not researchers:
            return self._insufficient(task.id, [
                "Open collaborations in the platform database",
                "Other researchers with matching interests on the platform",
            ])

        collab_lines = []
        for c in collaborations[:8]:
            title   = c.get("title") or c.get("name") or "Untitled collaboration"
            areas   = ", ".join((c.get("research_areas") or [])[:3])
            creator = c.get("creator_name") or ""
            overlap = [kw for kw in interests if kw.lower() in str(c).lower()]
            collab_lines.append(
                f"• {title[:60]}"
                + (f" | Areas: {areas}" if areas else "")
                + (f" | By: {creator[:30]}" if creator else "")
                + (" ★ MATCH" if overlap else "")
            )

        researcher_lines = [
            f"• {r.get('full_name', 'Anonymous')} | {r.get('institution', 'Unknown institution')} "
            f"| Interests: {', '.join((r.get('research_interests') or [])[:3])}"
            for r in researchers[:6]
        ]

        from services.ai.llm import call_llm
        collab_advice = await call_llm(
            system=(
                "You are a Research Collaboration Specialist. "
                "Advise researchers on collaboration opportunities based ONLY on the data provided. "
                "Never invent researcher names, institutions, or project titles. "
                "Focus on genuine overlap identification and practical collaboration steps."
            ),
            user_msg=(
                f"Collaboration request: {task.user_input}\n"
                f"Research interests: {', '.join(interests[:5]) if interests else 'Not specified'}\n\n"
                + (f"Open collaborations:\n" + "\n".join(collab_lines) + "\n\n" if collab_lines else "No open collaborations found.\n")
                + (f"Researchers with overlapping interests (public profiles):\n" + "\n".join(researcher_lines) + "\n" if researcher_lines else "")
                + "\nProvide: (1) Best-matched collaborations with rationale, "
                "(2) Recommended outreach approach for each, "
                "(3) What to include in a collaboration request message, "
                "(4) How to structure the collaboration arrangement."
            ),
            feature="copilot_collaboration",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=collab_advice,
            structured_data={"collaborations_found": len(collaborations), "researchers_found": len(researchers)},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient" if collaborations or researchers else "partial",
            limitations=[
                "Only public platform profiles and open collaborations are shown.",
                "No compatibility score is computed — matching is keyword-based.",
            ],
        )


REGISTRY.register(CollaborationAgent())
