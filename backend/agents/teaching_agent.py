"""Teaching Agent — lesson planning, assessments, and educational resource support."""
from __future__ import annotations

import logging
from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.teaching")


class TeachingAgent(BaseAgent):
    name         = "teaching"
    description  = "Supports educators with lesson planning, assessments, and learning outcomes."
    mission      = "Help academic educators design effective teaching materials and assessments."
    capabilities = [
        "Lesson plan creation",
        "Learning outcome design",
        "Assessment design",
        "Teaching quality improvement",
        "Educational resource planning",
        "Course structure design",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        domain   = memory.get("domain") or ""
        role     = memory.get("role") or ""
        interests = memory.get("interests") or []

        evidence = []
        context_parts = []

        # Check user role — teaching is for educators
        if domain in ("teaching", "both") or "teach" in role.lower():
            context_parts.append(f"Role: {role or 'Educator'}, Domain: {domain}")
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Teaching role confirmed: primary_domain={domain}"
            ))

        if interests:
            context_parts.append(f"Subject areas: {', '.join(interests[:4])}")
            evidence.append(self._ev(
                "profile_field", "Synaptiq platform database — user profile",
                f"Research/teaching interests: {', '.join(interests[:4])}"
            ))

        # Check for existing teaching materials in DB
        try:
            lesson_count = await db.lessons.count_documents({"creator_id": memory.get("uid")}) if memory.get("uid") else 0
            if lesson_count:
                evidence.append(self._ev(
                    "database_query", "Synaptiq platform database — lessons collection",
                    f"{lesson_count} existing lesson(s) found in your teaching hub"
                ))
        except Exception:
            lesson_count = 0

        evidence.append(self._ev(
            "user_input", "User-provided teaching request",
            f"Teaching task: '{task.user_input[:80]}'"
        ))

        from services.ai.llm import call_llm
        teaching_output = await call_llm(
            system=(
                "You are an Educational Design Specialist with expertise in higher education. "
                "Help educators create effective, research-informed teaching materials. "
                "Apply constructive alignment (Biggs) and active learning principles. "
                "Never fabricate research outcomes or learning effectiveness statistics. "
                "Be specific and practical — provide usable materials, not generic advice."
            ),
            user_msg=(
                f"Teaching task: {task.user_input}\n"
                f"Context: {', '.join(context_parts) if context_parts else 'No profile context.'}\n"
                + (f"Existing lessons: {lesson_count} on platform\n" if lesson_count else "")
                + "\nProvide: (1) Structured lesson/assessment plan, "
                "(2) Specific learning outcomes (using Bloom's taxonomy), "
                "(3) Active learning activities, "
                "(4) Assessment design with rubric outline, "
                "(5) Resources to recommend to students."
            ),
            feature="copilot_teaching",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=teaching_output,
            structured_data={"lessons_on_platform": lesson_count if "lesson_count" in dir() else 0},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="partial",
            limitations=[
                "Teaching advice is based on described context — actual student data is not available.",
                "Pedagogical research cited follows general evidence base, not specific institutional studies.",
            ],
        )


REGISTRY.register(TeachingAgent())
