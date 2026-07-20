"""Collaboration Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_COLLAB_SIGNALS = {
    "interdisciplinary": ["interdisciplinary", "cross-disciplinary", "multidisciplinary", "transdisciplinary"],
    "international": ["international", "cross-national", "multicountry", "global collaboration"],
    "industry": ["industry partner", "private sector", "company", "enterprise", "startup"],
    "institutional": ["university", "institution", "hospital", "research centre", "laboratory"],
    "community": ["community", "patient", "stakeholder", "public engagement", "knowledge transfer"],
}


@AgentRegistry.register
class CollaborationAgent(AcademicAgent):
    agent_id = "collaboration_agent_v1"
    agent_type = AgentType.COLLABORATION
    name = "Collaboration Agent"
    domain = "Research Collaboration & Networking"
    capabilities = [
        "collaboration_gap_detection", "partner_recommendation",
        "co_authorship_analysis", "network_mapping", "knowledge_transfer",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()

        collab_types = {k: any(s in text_lower for s in signals)
                        for k, signals in _COLLAB_SIGNALS.items()}
        detected_types = [k for k, v in collab_types.items() if v]

        # Co-authorship signals
        author_count_match = re.search(r"\b(\d+)\s+author[s]?\b", text_lower)
        author_count = int(author_count_match.group(1)) if author_count_match else 0

        gaps: list[str] = []
        if not collab_types["interdisciplinary"]:
            gaps.append("No interdisciplinary collaboration detected — consider cross-disciplinary partners")
        if not collab_types["international"]:
            gaps.append("No international collaboration — global partnerships boost citation impact")
        if not collab_types["industry"]:
            gaps.append("Industry partnership not mentioned — consider knowledge transfer opportunities")

        recommendations: list[str] = [
            "Register on ResearchGate and Academia.edu to discover potential co-authors",
            "Use ResearcherID/ORCID to track and advertise your collaboration network",
            "Apply for collaborative grants (EU Collaborative Projects require 3+ countries)",
            "Attend conferences in adjacent disciplines to build interdisciplinary networks",
            "Use Synaptiq Collaboration Requests to find matching researchers",
        ]

        coverage = len(detected_types) / len(collab_types)
        confidence = min(0.88, 0.4 + 0.5 * coverage)

        output = {
            "collaboration_types_detected": detected_types,
            "collaboration_coverage_score": round(coverage, 3),
            "collaboration_gaps": gaps,
            "author_count_detected": author_count,
            "collaboration_recommendations": recommendations,
            "high_impact_collaboration_paths": [
                "EU Horizon Europe (3+ country consortium)",
                "NIH collaborative R01 grants",
                "Industry co-funding via Innovate UK / KTPs",
                "Joint PhD supervision across institutions",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Detected {len(detected_types)} collaboration type(s). "
                f"Coverage: {coverage:.0%}. "
                f"{len(gaps)} collaboration gaps identified."
            ),
            evidence=detected_types + gaps[:3],
            t0=t0,
        )
