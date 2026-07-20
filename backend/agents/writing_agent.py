"""Writing Agent — academic writing quality, structure, clarity, and flow."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.writing")


class WritingAgent(BaseAgent):
    name         = "writing"
    description  = "Improves academic writing quality, structure, clarity, and scientific language."
    mission      = "Help researchers produce publication-ready academic prose from their own content."
    capabilities = [
        "Academic writing improvement",
        "Structural analysis",
        "Clarity and flow enhancement",
        "Grammar and style",
        "Scientific language consistency",
        "Abstract and section drafting",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        user_input  = task.user_input
        manuscripts = memory.get("manuscripts") or []

        evidence = []
        manuscript_text = ""

        # Use actual manuscript content if available
        if manuscripts:
            ms = manuscripts[0]
            ms_title   = ms.get("title", "Untitled")[:60]
            ms_abstract = ms.get("abstract") or ms.get("content") or ""
            if ms_abstract:
                manuscript_text = f"\nManuscript '{ms_title}':\n{ms_abstract[:1500]}"
                evidence.append(self._ev(
                    "database_query", "Synaptiq platform database — manuscripts",
                    f"Manuscript content retrieved: '{ms_title}'"
                ))

        # Reviewer agent output can inform writing priorities
        reviewer_out = memory.get_agent_output("reviewer")
        reviewer_context = ""
        if reviewer_out and reviewer_out.status in ("success", "partial"):
            reviewer_context = f"\nPeer review concerns identified:\n{reviewer_out.content[:400]}"
            evidence.append(self._ev(
                "agent_output", "Reviewer Agent",
                "Peer review simulation used to prioritize writing improvements"
            ))

        has_content = bool(manuscript_text or "write" in user_input.lower() or len(user_input) > 100)

        if not has_content:
            evidence.append(self._ev(
                "user_input", "User request",
                f"Writing request received: '{user_input[:80]}'"
            ))

        from services.ai.llm import call_llm
        writing_output = await call_llm(
            system=(
                "You are an Academic Writing Specialist with expertise in scientific publication. "
                "When provided with the user's actual text, improve it. "
                "When asked for structure guidance, provide it based on the described manuscript type. "
                "Do not invent content the user hasn't provided. "
                "Maintain the author's voice while improving clarity and academic rigor."
            ),
            user_msg=(
                f"Writing task: {user_input}{manuscript_text}{reviewer_context}\n\n"
                "Provide: (1) Writing quality assessment of the provided content, "
                "(2) Specific improvements with examples, "
                "(3) Structural recommendations, "
                "(4) Academic language improvements, "
                "(5) Next writing steps."
            ),
            feature="copilot_writing",
        )

        evidence.append(self._ev(
            "user_input", "User-provided content",
            "Analysis based on user-supplied text and platform manuscript data"
        ))

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=writing_output,
            structured_data={"manuscript_used": bool(manuscript_text)},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient" if manuscript_text else "partial",
            limitations=[
                "Writing improvements are based only on text provided — full manuscript review requires complete content.",
                "Domain-specific terminology accuracy depends on user's own input.",
            ],
        )


REGISTRY.register(WritingAgent())
