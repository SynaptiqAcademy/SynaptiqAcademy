"""Timeline Agent (Phase XIII) — Gantt-style scheduling from research plan."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType


@AgentRegistry.register
class TimelineAgent(AcademicAgent):
    agent_id = "timeline_agent_v1"
    agent_type = AgentType.TIMELINE
    name = "Timeline Agent"
    domain = "Project Timeline & Scheduling"
    capabilities = [
        "gantt_scheduling", "deadline_management", "critical_path_analysis",
        "milestone_tracking", "delay_risk_assessment",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        md = task.metadata

        # Inherit milestones from Research Planning Agent
        planning_result = context.get_result(AgentType.RESEARCH_PLANNING)
        milestones: list[dict] = []
        total_weeks: int = 0

        if planning_result and planning_result.output.get("milestones"):
            milestones = planning_result.output["milestones"]
            total_weeks = planning_result.output.get("total_duration_weeks", 0)
        else:
            # Fallback: generic timeline
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            phases = [
                ("Literature Review", 4), ("Data Collection", 8), ("Analysis", 4),
                ("Writing", 6), ("Submission", 4),
            ]
            cursor = now
            for name, wks in phases:
                end = cursor + timedelta(weeks=wks)
                milestones.append({"phase": name, "duration_weeks": wks,
                                   "start_date": cursor.strftime("%Y-%m-%d"),
                                   "end_date": end.strftime("%Y-%m-%d")})
                cursor = end
                total_weeks += wks

        # Build Gantt-compatible structure
        gantt_bars = [
            {
                "id": i + 1,
                "task": m["phase"],
                "start": m["start_date"],
                "end": m["end_date"],
                "weeks": m["duration_weeks"],
                "dependencies": [i] if i > 0 else [],
                "is_critical_path": True,  # all sequential in default plan
            }
            for i, m in enumerate(milestones)
        ]

        # Critical path = longest sequential chain = total
        critical_path_weeks = total_weeks
        buffer_weeks = max(4, round(total_weeks * 0.15))

        warnings: list[str] = []
        if critical_path_weeks > 52:
            warnings.append(f"Project exceeds 1 year ({critical_path_weeks} weeks) — ensure sustained funding")
        if critical_path_weeks < 12:
            warnings.append("Very short timeline — verify feasibility, especially ethics and data collection phases")

        confidence = 0.80 if planning_result else 0.60

        output = {
            "gantt_chart": gantt_bars,
            "total_tasks": len(gantt_bars),
            "total_duration_weeks": total_weeks,
            "critical_path_weeks": critical_path_weeks,
            "recommended_buffer_weeks": buffer_weeks,
            "total_with_buffer_weeks": critical_path_weeks + buffer_weeks,
            "timeline_warnings": warnings,
            "key_deadlines": [
                {"milestone": m["phase"], "deadline": m["end_date"]}
                for m in milestones
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Built Gantt timeline with {len(gantt_bars)} tasks over "
                f"{total_weeks} weeks + {buffer_weeks}w buffer."
            ),
            evidence=[m["phase"] for m in milestones],
            t0=t0,
        )
