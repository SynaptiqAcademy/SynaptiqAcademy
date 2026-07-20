"""Ethics Agent — compliance checks, bias detection, and publication ethics."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.ethics")

# Known ethics red flags for rule-based checks
ETHICS_RED_FLAGS = [
    ("p-hack", "p-hacking"),
    ("HARKing", "hypothesizing after results known"),
    ("salami", "salami slicing"),
    ("ghost author", "ghost authorship"),
    ("duplicate submit", "duplicate submission"),
    ("fabricat", "data fabrication"),
    ("falsif", "data falsification"),
    ("plagiar", "plagiarism"),
    ("gift author", "gift authorship"),
    ("predatory", "predatory journal submission"),
]


class EthicsAgent(BaseAgent):
    name         = "ethics"
    description  = "Checks research ethics compliance, bias risks, and publication ethics."
    mission      = "Identify potential ethics concerns before submission or publication."
    capabilities = [
        "Ethics compliance check",
        "Research bias identification",
        "Academic integrity verification",
        "Consent and data protection guidance",
        "Publication ethics (authorship, duplicate submission)",
        "Plagiarism risk indicators",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        manuscripts = memory.get("manuscripts") or []
        user_input  = task.user_input.lower()

        evidence    = []
        flags_found = []

        # Rule-based red flag detection in user input
        for keyword, label in ETHICS_RED_FLAGS:
            if keyword.lower() in user_input:
                flags_found.append(label)

        ms_context = ""
        if manuscripts:
            ms = manuscripts[0]
            ms_title    = ms.get("title", "Untitled")[:60]
            ms_abstract = (ms.get("abstract") or "")[:800]
            ms_text     = ms_abstract.lower()
            ms_context  = f"\nManuscript: '{ms_title}'\n{ms_abstract}"
            evidence.append(self._ev(
                "database_query", "Synaptiq platform database — manuscripts",
                f"Manuscript retrieved for ethics check: '{ms_title}'"
            ))
            # Check manuscript text for flags
            for keyword, label in ETHICS_RED_FLAGS:
                if keyword.lower() in ms_text and label not in flags_found:
                    flags_found.append(label)

        if flags_found:
            evidence.append(self._ev(
                "rule_check", "Ethics rule engine (keyword analysis)",
                f"Terms flagged for ethics review: {', '.join(flags_found)}"
            ))

        evidence.append(self._ev(
            "user_input", "User-provided research description",
            "Ethics analysis performed on described research context"
        ))

        from services.ai.llm import call_llm
        ethics_review = await call_llm(
            system=(
                "You are a Research Ethics Specialist and Publication Ethics Advisor. "
                "Your role is to identify potential ethics concerns in research and publication practices. "
                "Base your analysis ONLY on what is described. Never fabricate violations. "
                "Be constructive — explain what to do, not just what is wrong. "
                "Reference established ethics guidelines: COPE, Declaration of Helsinki, ICMJE where relevant."
            ),
            user_msg=(
                f"Ethics review request: {task.user_input}{ms_context}\n\n"
                + (f"Potential flags detected: {', '.join(flags_found)}\n" if flags_found else "")
                + "\nProvide: (1) Ethics compliance checklist for this type of research, "
                "(2) Specific concerns identified (if any), "
                "(3) Data protection and consent considerations, "
                "(4) Authorship and contribution transparency, "
                "(5) Publication ethics (duplicate submission, self-plagiarism risks), "
                "(6) Concrete next steps to address any concerns."
            ),
            feature="copilot_ethics",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=ethics_review,
            structured_data={"flags_detected": flags_found, "flags_count": len(flags_found)},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="partial",
            limitations=[
                "Ethics analysis is based on described context only — not a formal ethics review.",
                "Institutional IRB/ethics board approval is required for human subjects research.",
                "This does not replace formal ethics committee review.",
            ],
        )


REGISTRY.register(EthicsAgent())
