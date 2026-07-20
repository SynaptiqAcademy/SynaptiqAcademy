"""Peer Review Agent (Phase XIII)."""
from __future__ import annotations

import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType


@AgentRegistry.register
class PeerReviewAgent(AcademicAgent):
    agent_id = "peer_review_agent_v1"
    agent_type = AgentType.PEER_REVIEW
    name = "Peer Review Agent"
    domain = "Manuscript Peer Review Simulation"
    capabilities = [
        "manuscript_review", "quality_scoring", "review_comment_generation",
        "decision_recommendation", "revision_planning",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()
        md = task.metadata

        # Aggregate signals from prior agents
        lit_result = context.get_result(AgentType.LITERATURE_REVIEW)
        meth_result = context.get_result(AgentType.METHODOLOGY)
        stat_result = context.get_result(AgentType.STATISTICS)
        write_result = context.get_result(AgentType.ACADEMIC_WRITING)
        ethics_result = context.get_result(AgentType.RESEARCH_ETHICS)

        scores: dict[str, float] = {}
        scores["literature"] = (lit_result.confidence if lit_result else 0.5)
        scores["methodology"] = (meth_result.confidence if meth_result else 0.5)
        scores["statistics"] = (stat_result.confidence if stat_result else 0.5)
        scores["writing"] = (write_result.confidence if write_result else 0.5)
        scores["ethics"] = (ethics_result.confidence if ethics_result else 0.5)

        overall = sum(scores.values()) / len(scores)

        # Reviewer comments (synthesised from agent outputs)
        comments: list[str] = []
        if lit_result and lit_result.output.get("gaps_to_address"):
            comments.extend(lit_result.output["gaps_to_address"][:2])
        if meth_result and meth_result.output.get("methodological_issues"):
            comments.extend(meth_result.output["methodological_issues"][:2])
        if stat_result and stat_result.output.get("statistical_issues"):
            comments.extend(stat_result.output["statistical_issues"][:2])
        if write_result and write_result.output.get("writing_issues"):
            comments.extend(write_result.output["writing_issues"][:2])
        if ethics_result and ethics_result.output.get("critical_issues"):
            comments.extend(ethics_result.output["critical_issues"][:2])

        # Decision
        if ethics_result and not ethics_result.output.get("is_compliant", True):
            decision = "Reject — critical ethics compliance issues"
        elif overall >= 0.75:
            decision = "Minor Revision" if len(comments) <= 3 else "Major Revision"
        elif overall >= 0.55:
            decision = "Major Revision"
        elif overall >= 0.35:
            decision = "Major Revision with Concerns"
        else:
            decision = "Reject — significant issues require fundamental revision"

        confidence = min(0.90, 0.3 + 0.7 * overall)

        output = {
            "reviewer_scores": scores,
            "overall_score": round(overall, 3),
            "editorial_decision": decision,
            "reviewer_comments": comments[:10],
            "strengths": [
                "Well-structured academic manuscript",
                "Clear research question",
            ] if overall >= 0.6 else [],
            "revision_priority": (
                "Address ethics compliance issues first"
                if not (ethics_result and ethics_result.output.get("is_compliant", True))
                else "Focus on methodology and statistical reporting"
            ),
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Peer review based on {len([v for v in scores.values() if v > 0])} agent reports. "
                f"Overall quality: {overall:.0%}. Decision: {decision}."
            ),
            evidence=[f"{k}: {v:.0%}" for k, v in scores.items()],
            t0=t0,
        )
