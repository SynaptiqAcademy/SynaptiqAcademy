"""Reviewer Agent — simulates peer review of manuscripts (clearly labeled as simulation)."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.reviewer")


class ReviewerAgent(BaseAgent):
    name         = "reviewer"
    description  = "Simulates peer review to identify major concerns before submission."
    mission      = "Provide structured peer review simulation to help prepare manuscripts for real review."
    capabilities = [
        "Peer review simulation",
        "Major concern identification",
        "Minor revision suggestions",
        "Novelty evaluation",
        "Methodological criticism",
        "Acceptance risk assessment",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        manuscripts = memory.get("manuscripts") or []

        evidence = []
        manuscript_text = ""

        if manuscripts:
            ms = manuscripts[0]
            ms_title    = ms.get("title", "Untitled")[:60]
            ms_abstract = ms.get("abstract") or ms.get("content") or ""
            if ms_abstract:
                manuscript_text = f"Title: {ms_title}\n\nAbstract/Content:\n{ms_abstract[:2000]}"
                evidence.append(self._ev(
                    "database_query", "Synaptiq platform database — manuscripts",
                    f"Manuscript retrieved for review simulation: '{ms_title}'"
                ))

        # Also accept text directly from user input
        user_text = task.user_input
        if len(user_text) > 200 and not manuscript_text:
            manuscript_text = user_text
            evidence.append(self._ev(
                "user_input", "User-provided manuscript text",
                f"User provided {len(user_text)} characters of manuscript text"
            ))

        # Ethics agent output may flag issues
        ethics_out = memory.get_agent_output("ethics")
        ethics_context = ""
        if ethics_out and ethics_out.status in ("success", "partial"):
            ethics_context = f"\nEthics analysis:\n{ethics_out.content[:300]}"
            evidence.append(self._ev(
                "agent_output", "Ethics Agent",
                "Ethics analysis incorporated into review simulation"
            ))

        # Stats agent may flag methodological issues
        stats_out = memory.get_agent_output("statistics")
        stats_context = ""
        if stats_out and stats_out.status in ("success", "partial"):
            stats_context = f"\nStatistical guidance:\n{stats_out.content[:300]}"
            evidence.append(self._ev(
                "agent_output", "Statistics Agent",
                "Statistical review incorporated"
            ))

        if not manuscript_text:
            return self._insufficient(task.id, [
                "Manuscript text or abstract (provide text in your message or add a manuscript to your profile)",
            ])

        from services.ai.llm import call_llm
        review = await call_llm(
            system=(
                "You are simulating a thorough academic peer reviewer for a top-tier journal. "
                "This is a SIMULATION to help the author prepare — clearly label it as such. "
                "Be critical but constructive. Base all concerns on what is actually present in the text. "
                "Never invent data, references, or outcome statistics. "
                "Follow the standard peer review format with major concerns, minor concerns, and recommendations."
            ),
            user_msg=(
                f"[SIMULATION] Peer review request: {task.user_input}\n\n"
                f"Manuscript to review:\n{manuscript_text}"
                f"{ethics_context}{stats_context}\n\n"
                "Provide a structured review: (1) Summary of the manuscript (2-3 sentences), "
                "(2) Major concerns (numbered — must be addressed for publication), "
                "(3) Minor concerns (grammar, clarity, formatting), "
                "(4) Novelty and significance assessment, "
                "(5) Recommendation: Accept / Minor revision / Major revision / Reject — with clear rationale."
                "\n\nIMPORTANT: Label everything as SIMULATION. This is not real peer review."
            ),
            feature="copilot_reviewer",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=f"⚠️ PEER REVIEW SIMULATION — Not a real peer review.\n\n{review}",
            structured_data={"manuscript_used": bool(manuscripts), "is_simulation": True},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient" if manuscript_text else "insufficient",
            limitations=[
                "THIS IS A SIMULATION — not a real peer review from a qualified expert.",
                "Based only on the provided text — full review requires methodology, data, and supplementary materials.",
                "No actual journal or reviewer is involved.",
            ],
        )


REGISTRY.register(ReviewerAgent())
