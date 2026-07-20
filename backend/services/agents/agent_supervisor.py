"""Supervisor Agent (Phase XIII) — meta-agent that validates all other agents."""
from __future__ import annotations

import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentStatus, AgentTask, AgentType

_ALL_AGENT_TYPES = [
    AgentType.LITERATURE_REVIEW, AgentType.RESEARCH_GAP, AgentType.METHODOLOGY,
    AgentType.STATISTICS, AgentType.ACADEMIC_WRITING, AgentType.RESEARCH_ETHICS,
    AgentType.DATA_ANALYSIS, AgentType.CITATION_INTELLIGENCE,
]


@AgentRegistry.register
class SupervisorAgent(AcademicAgent):
    agent_id = "supervisor_agent_v1"
    agent_type = AgentType.SUPERVISOR
    name = "Supervisor Agent"
    domain = "Multi-Agent Coordination & Validation"
    capabilities = [
        "cross_agent_validation", "inconsistency_detection", "quality_synthesis",
        "confidence_aggregation", "recommendation_integration",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()

        # Gather all prior results
        results = {
            at.value: context.get_result(at)
            for at in _ALL_AGENT_TYPES
            if context.get_result(at) is not None
        }

        if not results:
            return self._timed_result(
                task,
                {"message": "No agent results to supervise yet."},
                0.5,
                "No prior agent results available.",
                [],
                t0,
            )

        # Aggregate confidence
        confidences = [r.confidence for r in results.values() if r]
        avg_confidence = sum(confidences) / max(len(confidences), 1)

        # Detect cross-agent inconsistencies
        inconsistencies: list[str] = []

        lit = results.get(AgentType.LITERATURE_REVIEW.value)
        gap = results.get(AgentType.RESEARCH_GAP.value)
        meth = results.get(AgentType.METHODOLOGY.value)
        stat = results.get(AgentType.STATISTICS.value)
        ethics = results.get(AgentType.RESEARCH_ETHICS.value)

        if lit and gap:
            if lit.confidence < 0.5 and not gap.output.get("explicit_gaps_found"):
                inconsistencies.append("Literature review is weak but no gaps were identified — contradiction")

        if meth and stat:
            meth_designs = meth.output.get("detected_designs", [])
            stat_tests = stat.output.get("detected_tests", [])
            if "experimental" in meth_designs and "t-test" not in stat_tests and "ANOVA" not in stat_tests:
                inconsistencies.append("Experimental design detected but no group comparison test (t-test/ANOVA) found")
            if "qualitative" in meth_designs and stat_tests:
                inconsistencies.append("Qualitative design but quantitative tests detected — verify mixed-methods rationale")

        if ethics and ethics.output.get("involves_human_participants") and not ethics.output.get("has_ethics_approval"):
            inconsistencies.append("CRITICAL: Human participants involved but no ethics approval declared")

        # Failed agents
        failed = [at_val for at_val, r in results.items() if r.status == AgentStatus.FAILED]

        # Synthesis
        all_issues: list[str] = []
        for r in results.values():
            if r:
                for key in ("gaps_to_address", "methodological_issues", "statistical_issues",
                            "writing_issues", "compliance_issues", "critical_issues",
                            "citation_issues", "analysis_issues"):
                    all_issues.extend(r.output.get(key, [])[:2])

        quality_level = (
            "excellent" if avg_confidence >= 0.80 and not inconsistencies
            else "good" if avg_confidence >= 0.65 and len(inconsistencies) <= 1
            else "acceptable" if avg_confidence >= 0.50
            else "poor"
        )

        confidence = min(0.95, avg_confidence * (0.85 if inconsistencies else 1.0))

        output = {
            "agents_supervised": list(results.keys()),
            "avg_agent_confidence": round(avg_confidence, 3),
            "quality_level": quality_level,
            "cross_agent_inconsistencies": inconsistencies,
            "failed_agents": failed,
            "critical_issues_across_agents": [i for i in all_issues if "CRITICAL" in i.upper()],
            "top_issues_synthesised": list(dict.fromkeys(all_issues))[:8],
            "overall_recommendation": (
                "The research is strong — address minor issues before submission."
                if quality_level in ("excellent", "good")
                else "Significant revisions required across multiple dimensions."
            ),
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Supervised {len(results)} agents. "
                f"Avg confidence: {avg_confidence:.0%}. "
                f"Inconsistencies: {len(inconsistencies)}. "
                f"Quality: {quality_level}."
            ),
            evidence=inconsistencies + failed,
            t0=t0,
        )
