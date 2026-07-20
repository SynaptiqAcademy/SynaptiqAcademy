"""Literature Review Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_THEME_SIGNALS = {
    "methodology": ["method", "approach", "design", "framework", "model"],
    "empirical findings": ["result", "finding", "outcome", "effect", "significant"],
    "theory": ["theory", "theoretical", "concept", "framework", "paradigm"],
    "review": ["review", "meta-analysis", "systematic", "synthesis", "scoping"],
    "application": ["application", "practice", "implementation", "adoption", "use"],
}

_CITATION_RE = re.compile(r"\([\w\s]+,?\s*\d{4}\)|\[\d+\]")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


@AgentRegistry.register
class LiteratureReviewAgent(AcademicAgent):
    agent_id = "literature_review_agent_v1"
    agent_type = AgentType.LITERATURE_REVIEW
    name = "Literature Review Agent"
    domain = "Academic Literature"
    capabilities = [
        "literature_search", "evidence_synthesis", "theme_extraction",
        "research_evolution", "comparison", "retrieval",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()

        # Extract themes
        themes_found = [
            theme for theme, signals in _THEME_SIGNALS.items()
            if any(s in text_lower for s in signals)
        ]

        # Count citations and year range
        citations = _CITATION_RE.findall(text)
        years = [int(y) for y in _YEAR_RE.findall(text) if 1950 <= int(y) <= 2030]
        year_range = (min(years), max(years)) if years else (None, None)

        # Detect review maturity
        word_count = len(text.split())
        ref_density = len(citations) / max(word_count / 100, 1)

        # Quality signals
        has_systematic = any(kw in text_lower for kw in ["systematic", "prisma", "inclusion criteria", "exclusion criteria"])
        has_synthesis = any(kw in text_lower for kw in ["synthesis", "meta-analysis", "pooled", "aggregate"])

        # Gaps to explore
        gaps: list[str] = []
        if not has_systematic:
            gaps.append("Consider a systematic search protocol with explicit inclusion/exclusion criteria")
        if ref_density < 2:
            gaps.append("Reference density is low — expand literature coverage")
        if not themes_found:
            gaps.append("No clear thematic clusters detected — structure themes explicitly")
        if year_range[0] and year_range[0] < 2010:
            gaps.append("Literature spans old studies — verify if recent developments are covered")

        evidence_count = len(citations)
        confidence = min(0.95, 0.4 + 0.1 * len(themes_found) + 0.05 * min(evidence_count, 5))

        output = {
            "themes_identified": themes_found,
            "citation_count": evidence_count,
            "year_range": list(year_range),
            "reference_density_per_100_words": round(ref_density, 2),
            "has_systematic_approach": has_systematic,
            "has_synthesis": has_synthesis,
            "word_count": word_count,
            "gaps_to_address": gaps,
            "search_recommendations": [
                "Search Scopus, Web of Science, and PubMed using MeSH/controlled vocabulary",
                "Apply PRISMA/PRISMA-ScR reporting standards",
                "Include grey literature where relevant",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Identified {len(themes_found)} thematic clusters and {evidence_count} citations "
                f"(year range {year_range[0]}–{year_range[1]}). "
                + ("Systematic approach detected. " if has_systematic else "No systematic protocol detected. ")
            ),
            evidence=[f"Citation detected: {c}" for c in citations[:5]],
            t0=t0,
        )
