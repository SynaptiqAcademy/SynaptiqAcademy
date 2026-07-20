"""Research Planning Agent (Phase XIII)."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_PHASE_TEMPLATES = {
    "empirical": [
        ("Literature Review & Protocol", 4),
        ("Ethics Approval", 3),
        ("Data Collection", 8),
        ("Data Analysis", 4),
        ("Writing Draft", 6),
        ("Peer Review & Revision", 8),
        ("Submission & Publication", 4),
    ],
    "theoretical": [
        ("Literature Review", 6),
        ("Framework Development", 6),
        ("Draft Writing", 8),
        ("Expert Feedback", 4),
        ("Revision & Submission", 4),
    ],
    "review": [
        ("Protocol Development & Registration", 2),
        ("Database Search & Screening", 4),
        ("Data Extraction", 3),
        ("Quality Assessment", 2),
        ("Meta-Analysis / Synthesis", 4),
        ("Writing & Peer Review", 6),
    ],
    "default": [
        ("Planning & Literature Review", 4),
        ("Data Collection", 6),
        ("Analysis", 4),
        ("Writing", 6),
        ("Submission", 4),
    ],
}


def _detect_project_type(text: str) -> str:
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["systematic review", "meta-analysis", "prisma"]):
        return "review"
    if any(kw in text_lower for kw in ["theory", "theoretical", "framework", "conceptual"]):
        return "theoretical"
    if any(kw in text_lower for kw in ["data collection", "survey", "experiment", "participant"]):
        return "empirical"
    return "default"


@AgentRegistry.register
class ResearchPlanningAgent(AcademicAgent):
    agent_id = "research_planning_agent_v1"
    agent_type = AgentType.RESEARCH_PLANNING
    name = "Research Planning Agent"
    domain = "Research Project Planning"
    capabilities = [
        "project_phase_planning", "milestone_generation", "resource_planning",
        "risk_identification", "deliverable_mapping",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        md = task.metadata

        project_type = _detect_project_type(text)
        phases = _PHASE_TEMPLATES.get(project_type, _PHASE_TEMPLATES["default"])

        now = datetime.now(timezone.utc)
        milestones: list[dict] = []
        cursor = now
        for phase_name, weeks in phases:
            end_date = cursor + timedelta(weeks=weeks)
            milestones.append({
                "phase": phase_name,
                "duration_weeks": weeks,
                "start_date": cursor.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            })
            cursor = end_date

        total_weeks = sum(w for _, w in phases)
        total_months = round(total_weeks / 4.3, 1)

        # Risk identification
        risks: list[str] = []
        if "ethics" in text.lower() and "approval" not in text.lower():
            risks.append("Ethics approval may delay data collection (add 4–12 weeks buffer)")
        if "participant" in text.lower() and "recruit" not in text.lower():
            risks.append("Participant recruitment timeline risk — plan recruitment strategy early")
        if "funding" not in text.lower():
            risks.append("No funding source mentioned — verify resource availability")
        risks.append("Journal review process may add 3–6 months beyond initial estimate")

        confidence = 0.80

        output = {
            "project_type": project_type,
            "total_phases": len(milestones),
            "total_duration_weeks": total_weeks,
            "total_duration_months": total_months,
            "milestones": milestones,
            "identified_risks": risks,
            "key_deliverables": [m["phase"] for m in milestones],
            "resource_requirements": [
                "Statistical software (R/SPSS/Python)",
                "Reference manager (Zotero/Mendeley)",
                "Institutional repository access",
                "Research ethics approval",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Generated {len(milestones)}-phase {project_type} research plan "
                f"spanning {total_months} months."
            ),
            evidence=[m["phase"] for m in milestones],
            t0=t0,
        )
