"""Multi-paper comparative analysis — agreement, disagreement, contradictions, trends."""
from __future__ import annotations

import json
import logging
import re
from collections import Counter

from services.literature.models import (
    ComparativeAnalysis, ComparisonPoint, Paper, PaperAnalysis,
)

log = logging.getLogger("synaptiq.literature.comparative")

_MAX_PAPERS_FOR_AI = 20    # summarise beyond this threshold
_MAX_CHARS_PER_PAPER = 800  # context budget per paper in AI prompt

_SYSTEM = """\
You are a research synthesis expert. Given structured analyses of multiple academic papers,
identify patterns of agreement, disagreement, contradiction, methodological diversity,
and knowledge evolution across the corpus.

RULES:
1. Be specific — cite evidence from the papers, not generic statements.
2. Contradictions must involve opposing conclusions on the same research question.
3. Knowledge evolution describes how understanding of the topic changed over time.
4. Return ONLY valid JSON — no markdown fences, no commentary.
"""

_PROMPT = """\
Analyse these {n} paper summaries and identify cross-paper patterns.

PAPERS:
{papers_block}

Return JSON with this exact schema:
{{
  "methodology_agreements": ["<shared methodological approach across papers>"],
  "methodology_disagreements": ["<conflicting methodological choices>"],
  "findings_agreements": ["<consistent findings across papers>"],
  "findings_disagreements": ["<divergent or contradictory findings>"],
  "contradictory_pairs": [
    {{"paper_a": "<title or ref>", "paper_b": "<title or ref>", "contradiction": "<what they disagree on>"}}
  ],
  "sample_notes": ["<key observations about sample diversity or homogeneity>"],
  "statistics_notes": ["<observations about statistical consistency or inconsistency>"],
  "dominant_methodologies": ["<top 3-5 methods across the corpus>"],
  "knowledge_evolution": ["<how the field evolved chronologically — 2-4 key shifts>"],
  "topic_evolution": ["<how the research topic/framing shifted over time>"],
  "research_trends": ["<current dominant trends based on recent papers>"],
  "synthesis_summary": "<paragraph synthesising the comparative findings>"
}}
"""


async def run_comparative_analysis(
    session_id: str,
    papers: list[Paper],
    analyses: list[PaperAnalysis],
) -> ComparativeAnalysis:
    """Build a ComparativeAnalysis across all papers."""
    # Rule-based pass (always runs)
    ca = _rule_based_comparison(session_id, papers, analyses)

    # AI enhancement (only if we have real analyses with content)
    if analyses and any(a.results for a in analyses):
        ai_result = await _ai_comparison(papers, analyses)
        _merge_ai_result(ca, ai_result)

    return ca


# ── Rule-based comparison ──────────────────────────────────────────────────────

def _rule_based_comparison(
    session_id: str,
    papers: list[Paper],
    analyses: list[PaperAnalysis],
) -> ComparativeAnalysis:
    ca = ComparativeAnalysis(session_id=session_id, paper_count=len(papers))

    if not analyses:
        return ca

    # Dominant methodologies
    methodologies = [a.methodology for a in analyses if a.methodology]
    meth_counts = Counter(m.strip().lower() for m in methodologies)
    ca.dominant_methodologies = [m for m, _ in meth_counts.most_common(5)]

    # Research trends (from recent 5 papers by year)
    recent = sorted(papers, key=lambda p: p.year, reverse=True)[:5]
    recent_ids = {p.paper_id for p in recent}
    recent_analyses = [a for a in analyses if a.paper_id in recent_ids]
    ca.research_trends = _extract_trends(recent_analyses)

    # Knowledge evolution (chronological)
    ca.knowledge_evolution = _build_evolution_notes(papers, analyses)

    # Contradictory pairs (rule: same domain, opposite results keywords)
    ca.contradictory_pairs = _detect_contradictions(analyses)

    # Methodology comparison
    ca.methodology_comparison = ComparisonPoint(
        dimension="methodology",
        agreements=list(set(ca.dominant_methodologies[:3])),
        disagreements=_methodology_disagreements(analyses),
    )

    return ca


def _extract_trends(recent: list[PaperAnalysis]) -> list[str]:
    kw_counts: Counter[str] = Counter()
    for a in recent:
        kw_counts.update(k.lower() for k in a.extracted_keywords)
    return [f"Growing focus on {kw}" for kw, _ in kw_counts.most_common(5) if kw]


def _build_evolution_notes(papers: list[Paper], analyses: list[PaperAnalysis]) -> list[str]:
    sorted_by_year = sorted(
        [(p, a) for p in papers for a in analyses if a.paper_id == p.paper_id],
        key=lambda x: x[0].year,
    )
    if len(sorted_by_year) < 2:
        return []
    earliest = sorted_by_year[0]
    latest = sorted_by_year[-1]
    notes = []
    if earliest[0].year and latest[0].year and earliest[0].year != latest[0].year:
        notes.append(
            f"Corpus spans {earliest[0].year}–{latest[0].year} "
            f"({latest[0].year - earliest[0].year} years of research)"
        )
    # Design shift
    early_designs = [a.research_design for _, a in sorted_by_year[:3] if a.research_design]
    late_designs = [a.research_design for _, a in sorted_by_year[-3:] if a.research_design]
    if early_designs and late_designs and set(early_designs) != set(late_designs):
        notes.append(f"Research design shifted from {early_designs[0]} to {late_designs[-1]}")
    return notes


def _detect_contradictions(analyses: list[PaperAnalysis]) -> list[dict]:
    contradictions = []
    positive_kw = re.compile(r"\beffective\b|\bimproves\b|\bpositive\b|\bbeneficial\b|\bsignificant\b", re.I)
    negative_kw = re.compile(r"\bineffective\b|\bno effect\b|\bnegative\b|\bno significant\b|\bnot significant\b", re.I)

    pos_papers = [a for a in analyses if a.results and positive_kw.search(a.results)]
    neg_papers = [a for a in analyses if a.results and negative_kw.search(a.results)]

    for pos in pos_papers[:3]:
        for neg in neg_papers[:3]:
            if pos.paper_id != neg.paper_id and pos.domain == neg.domain:
                contradictions.append({
                    "paper_a": pos.paper_id,
                    "paper_b": neg.paper_id,
                    "contradiction": f"Conflicting conclusions in {pos.domain or 'same domain'}",
                })
    return contradictions[:5]


def _methodology_disagreements(analyses: list[PaperAnalysis]) -> list[str]:
    designs = set(a.research_design.lower() for a in analyses if a.research_design)
    if len(designs) >= 3:
        return [f"Heterogeneous study designs: {', '.join(list(designs)[:4])}"]
    return []


# ── AI enhancement ─────────────────────────────────────────────────────────────

async def _ai_comparison(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
) -> dict:
    # Build compact summaries for context
    paper_map = {p.paper_id: p for p in papers}
    summaries_to_use = analyses[:_MAX_PAPERS_FOR_AI]
    blocks = []
    for i, a in enumerate(summaries_to_use, 1):
        p = paper_map.get(a.paper_id)
        title = (p.title if p else "") or "Unknown"
        year = (p.year if p else 0) or ""
        block = (
            f"[{i}] {title} ({year})\n"
            f"  Design: {a.research_design or 'unknown'}\n"
            f"  Method: {a.methodology or 'unknown'}\n"
            f"  Results: {a.results[:300] if a.results else 'N/A'}\n"
            f"  Keywords: {', '.join(a.extracted_keywords[:5])}"
        )
        blocks.append(block)

    try:
        from services.ai.llm import call_llm
        raw = await call_llm(
            system=_SYSTEM,
            user_msg=_PROMPT.format(n=len(summaries_to_use),
                                    papers_block="\n\n".join(blocks)),
            feature="literature_review.synthesis",
            max_tokens=2500,
        )
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.split("```")[0].strip()
        return json.loads(text)
    except Exception as exc:
        log.warning("Comparative AI analysis failed: %s", exc)
        return {}


def _merge_ai_result(ca: ComparativeAnalysis, ai: dict) -> None:
    if not ai:
        return

    def _lst(key: str) -> list[str]:
        return [str(v) for v in ai.get(key, []) if v]

    ca.methodology_comparison.agreements = _lst("methodology_agreements")
    ca.methodology_comparison.disagreements = _lst("methodology_disagreements")
    ca.findings_comparison.agreements = _lst("findings_agreements")
    ca.findings_comparison.disagreements = _lst("findings_disagreements")
    ca.sample_comparison.notes = "; ".join(_lst("sample_notes"))
    ca.statistics_comparison.notes = "; ".join(_lst("statistics_notes"))

    if ai.get("dominant_methodologies"):
        ca.dominant_methodologies = _lst("dominant_methodologies")
    if ai.get("knowledge_evolution"):
        ca.knowledge_evolution = _lst("knowledge_evolution")
    if ai.get("topic_evolution"):
        ca.topic_evolution = _lst("topic_evolution")
    if ai.get("research_trends"):
        ca.research_trends = _lst("research_trends")
    if ai.get("contradictory_pairs"):
        ca.contradictory_pairs = [d for d in ai["contradictory_pairs"]
                                   if isinstance(d, dict)][:10]
    if ai.get("synthesis_summary"):
        ca.synthesis_summary = str(ai["synthesis_summary"])
