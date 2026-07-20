"""Citation Intelligence Agent (Phase XIII)."""
from __future__ import annotations

import re
import time
from collections import Counter

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_APA_RE     = re.compile(r"\(([A-Z][a-zA-Z\s\-&]+),?\s*(\d{4})\)", re.IGNORECASE)
_YEAR_RE    = re.compile(r"\b(19|20)(\d{2})\b")
_DOI_RE     = re.compile(r"\b10\.\d{4,}/\S+", re.IGNORECASE)
_URL_RE     = re.compile(r"https?://\S+", re.IGNORECASE)
_IBID_RE    = re.compile(r"\bibid\b|\bop\.?\s*cit\b", re.IGNORECASE)


@AgentRegistry.register
class CitationIntelligenceAgent(AcademicAgent):
    agent_id = "citation_intelligence_agent_v1"
    agent_type = AgentType.CITATION_INTELLIGENCE
    name = "Citation Intelligence Agent"
    domain = "Citation Analysis & Verification"
    capabilities = [
        "citation_counting", "recency_analysis", "self_citation_detection",
        "doi_verification", "citation_style_detection", "coverage_assessment",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()

        # Parse citations
        apa_cites = _APA_RE.findall(text)
        years = [int(m[0] + m[1]) for m in _YEAR_RE.findall(text) if 1950 <= int(m[0] + m[1]) <= 2030]
        dois = _DOI_RE.findall(text)
        urls = _URL_RE.findall(text)
        ibid_count = len(_IBID_RE.findall(text))

        total_cites = max(len(apa_cites), len(dois))
        recent_count = sum(1 for y in years if y >= 2019)
        recency_ratio = recent_count / max(len(years), 1)

        # Author frequency (detect self-citation patterns)
        author_freq = Counter(auth.strip().lower() for auth, _ in apa_cites)
        most_cited = author_freq.most_common(3)
        high_self_cite = any(freq >= 5 for _, freq in most_cited)

        issues: list[str] = []
        if total_cites < 10:
            issues.append(f"Low citation count ({total_cites}) — expand literature coverage")
        if recency_ratio < 0.3 and years:
            issues.append(f"Only {recency_ratio:.0%} of citations are from 2019+ — consider adding recent work")
        if high_self_cite:
            issues.append("Potential over-self-citation detected — keep self-citations < 20%")
        if ibid_count > 0:
            issues.append(f"Avoid 'ibid' ({ibid_count} instances) — use full citations per journal style")
        if urls and not dois:
            issues.append("URLs detected without DOIs — prefer stable DOI references")

        confidence = min(0.92, 0.4 + 0.06 * min(total_cites, 8) + 0.2 * recency_ratio)

        output = {
            "total_citations_detected": total_cites,
            "apa_citations": len(apa_cites),
            "dois_detected": len(dois),
            "urls_detected": len(urls),
            "year_range": [min(years), max(years)] if years else [],
            "recency_ratio_post_2019": round(recency_ratio, 3),
            "recent_citations_count": recent_count,
            "most_cited_authors": [{"author": a, "count": c} for a, c in most_cited],
            "citation_style_detected": "APA" if apa_cites else ("numeric" if dois else "unknown"),
            "citation_issues": issues,
            "recommendations": [
                "Aim for at least 25 well-distributed references",
                "Include recent studies (post-2020) to demonstrate currency",
                "Use DOIs for all references where available",
                "Verify citation accuracy against original sources",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Detected {total_cites} citations, {recent_count} recent (2019+), "
                f"{len(dois)} DOIs. Recency ratio: {recency_ratio:.0%}."
            ),
            evidence=[f"({a}, {y})" for a, y in apa_cites[:5]],
            t0=t0,
        )
