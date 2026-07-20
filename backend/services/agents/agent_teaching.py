"""Teaching Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_PEDAGOGY_SIGNALS = {
    "active learning": ["active learning", "problem-based", "inquiry-based", "flipped classroom"],
    "assessment": ["assessment", "rubric", "formative", "summative", "feedback"],
    "technology": ["e-learning", "lms", "moodle", "canvas", "blended", "online", "digital"],
    "differentiation": ["differentiation", "inclusive", "accessibility", "adaptive", "personalised"],
    "outcomes": ["learning outcome", "objective", "competency", "skill", "bloom's"],
}

_LEVEL_SIGNALS = {
    "undergraduate": ["undergraduate", "bachelor", "bsc", "ba", "first year", "second year"],
    "postgraduate": ["postgraduate", "master", "msc", "mba", "taught"],
    "doctoral": ["phd", "doctoral", "research student", "thesis supervision"],
    "professional": ["cpd", "professional development", "continuing education"],
}


@AgentRegistry.register
class TeachingAgent(AcademicAgent):
    agent_id = "teaching_agent_v1"
    agent_type = AgentType.TEACHING
    name = "Teaching Agent"
    domain = "Academic Teaching & Learning Design"
    capabilities = [
        "pedagogy_assessment", "curriculum_alignment", "assessment_design",
        "learning_outcome_mapping", "teaching_technology_recommendations",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()

        pedagogy = {k: any(s in text_lower for s in signals)
                    for k, signals in _PEDAGOGY_SIGNALS.items()}
        levels = {k: any(s in text_lower for s in signals)
                  for k, signals in _LEVEL_SIGNALS.items()}

        detected_pedagogy = [k for k, v in pedagogy.items() if v]
        detected_levels = [k for k, v in levels.items() if v]

        issues: list[str] = []
        if not pedagogy["outcomes"]:
            issues.append("No learning outcomes defined — use Bloom's Taxonomy to align objectives")
        if not pedagogy["assessment"]:
            issues.append("No assessment strategy described — define formative and summative assessments")
        if not detected_levels:
            issues.append("Teaching level not specified — tailor content to student level")

        coverage = sum(pedagogy.values()) / len(pedagogy)
        confidence = min(0.90, 0.40 + 0.50 * coverage)

        output = {
            "detected_pedagogy": detected_pedagogy,
            "detected_teaching_levels": detected_levels,
            "pedagogy_coverage_score": round(coverage, 3),
            "teaching_issues": issues,
            "recommendations": [
                "Align all activities with measurable learning outcomes (Bloom's Taxonomy)",
                "Include both formative (low-stakes) and summative (high-stakes) assessments",
                "Incorporate active learning strategies to boost engagement",
                "Use UDL (Universal Design for Learning) principles for inclusivity",
                "Embed digital literacy skills into course activities",
            ],
            "suggested_tools": [
                "Moodle/Canvas for LMS", "Kahoot for formative assessment",
                "Padlet for collaborative activities", "Peergrade for peer review",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Pedagogy coverage: {coverage:.0%}. "
                f"Detected: {', '.join(detected_pedagogy) or 'none'}. "
                f"Level: {', '.join(detected_levels) or 'unspecified'}."
            ),
            evidence=detected_pedagogy + detected_levels,
            t0=t0,
        )
