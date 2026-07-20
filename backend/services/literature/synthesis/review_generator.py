"""AI-powered academic review generator — all 6 review types."""
from __future__ import annotations

import logging

from services.literature.models import (
    ComparativeAnalysis, GeneratedReview, Paper, PaperAnalysis,
    ResearchEvolution, ResearchGap, ReviewSession, ReviewType,
    ThematicCluster,
)
from services.literature.synthesis.templates import get_template

log = logging.getLogger("synaptiq.literature.generator")

_MAX_PAPERS_IN_CONTEXT = 30
_MAX_CHARS_PER_SUMMARY = 600


async def generate_review(
    session: ReviewSession,
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    topic: str = "",
    additional_instructions: str = "",
) -> GeneratedReview:
    """Generate a full academic review for a session."""
    template = get_template(session.review_type)

    # Build the context block that summarises all analysis
    context = _build_context(
        papers=papers,
        analyses=analyses,
        comparative=session.comparative_analysis,
        clusters=session.clusters,
        evolution=session.evolution,
        gaps=session.gaps,
        topic=topic,
    )

    prompt = _build_prompt(
        template=template,
        context=context,
        topic=topic,
        sections=template.sections,
        word_target=template.word_target,
        additional_instructions=additional_instructions,
    )

    system = template.system_prompt

    try:
        from services.ai.llm import call_llm
        raw = await call_llm(
            system=system,
            user_msg=prompt,
            feature="literature_review.synthesis",
            max_tokens=min(template.word_target * 2, 8000),
        )
        content = raw.strip()
    except Exception as exc:
        log.error("Review generation failed: %s", exc)
        content = _fallback_review(session, papers, analyses, topic, template)

    title = template.title_template.format(topic=topic or "the Research Topic")
    word_count = len(content.split())
    section_count = content.count("\n## ") + content.count("\n# ") + 1
    citations_included = content.count("(") and sum(
        1 for line in content.split("\n")
        if "(20" in line or "(19" in line
    )

    return GeneratedReview(
        review_type=session.review_type,
        title=title,
        content=content,
        word_count=word_count,
        section_count=section_count,
        citations_included=min(citations_included, len(papers)),
    )


# ── Context builder ────────────────────────────────────────────────────────────

def _build_context(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    comparative: ComparativeAnalysis | None,
    clusters: list[ThematicCluster],
    evolution: ResearchEvolution | None,
    gaps: list[ResearchGap],
    topic: str,
) -> str:
    blocks: list[str] = []

    # ── Paper summaries ────────────────────────────────────────────────────────
    paper_map = {p.paper_id: p for p in papers}
    analysis_map = {a.paper_id: a for a in analyses}

    # Prioritise: most-cited + most recently analysed (up to limit)
    sorted_papers = sorted(papers, key=lambda p: p.citation_count, reverse=True)
    papers_for_context = sorted_papers[:_MAX_PAPERS_IN_CONTEXT]

    paper_blocks = []
    for p in papers_for_context:
        a = analysis_map.get(p.paper_id)
        lines = [f"**{p.short_ref}** — {p.title[:100]}"]
        if p.journal:
            lines.append(f"  Journal: {p.journal}")
        if p.citation_count:
            lines.append(f"  Citations: {p.citation_count}")
        if a:
            if a.research_question:
                lines.append(f"  RQ: {a.research_question[:200]}")
            if a.methodology:
                lines.append(f"  Method: {a.methodology}")
            if a.results:
                lines.append(f"  Results: {a.results[:300]}")
            if a.contribution:
                lines.append(f"  Contribution: {a.contribution[:200]}")
            if a.limitations:
                lines.append(f"  Limitations: {'; '.join(a.limitations[:2])}")
        elif p.abstract:
            lines.append(f"  Abstract: {p.abstract[:400]}")
        paper_blocks.append("\n".join(lines))

    blocks.append("## PAPER SUMMARIES\n" + "\n\n".join(paper_blocks))

    if len(papers) > _MAX_PAPERS_IN_CONTEXT:
        blocks.append(
            f"*Note: {len(papers) - _MAX_PAPERS_IN_CONTEXT} additional papers in corpus "
            f"not shown here. Synthesise findings at the thematic level.*"
        )

    # ── Thematic clusters ──────────────────────────────────────────────────────
    if clusters:
        cluster_lines = ["## THEMATIC CLUSTERS"]
        for i, c in enumerate(clusters[:8], 1):
            cluster_lines.append(
                f"Cluster {i}: {c.label} ({c.paper_count} papers, {c.year_range[0]}–{c.year_range[1]})\n"
                f"  Keywords: {', '.join(c.top_keywords[:5])}"
            )
        blocks.append("\n".join(cluster_lines))

    # ── Comparative findings ───────────────────────────────────────────────────
    if comparative and comparative.synthesis_summary:
        blocks.append(f"## COMPARATIVE SYNTHESIS\n{comparative.synthesis_summary}")

    if comparative and comparative.contradictory_pairs:
        contra = [f"- {p.get('contradiction', '')}" for p in comparative.contradictory_pairs[:3]]
        blocks.append("## CONTRADICTIONS\n" + "\n".join(contra))

    # ── Research evolution ─────────────────────────────────────────────────────
    if evolution and evolution.evolution_summary:
        blocks.append(f"## RESEARCH EVOLUTION\n{evolution.evolution_summary}")
        if evolution.emerging_topics:
            blocks.append(f"Emerging topics: {', '.join(evolution.emerging_topics[:5])}")

    # ── Research gaps ──────────────────────────────────────────────────────────
    if gaps:
        gap_lines = ["## IDENTIFIED RESEARCH GAPS"]
        for g in gaps[:6]:
            gap_lines.append(f"- [{g.severity.upper()}] {g.title}: {g.description[:150]}")
        blocks.append("\n".join(gap_lines))

    return "\n\n".join(blocks)


def _build_prompt(
    template,
    context: str,
    topic: str,
    sections: list[str],
    word_target: int,
    additional_instructions: str,
) -> str:
    sections_str = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(sections))
    add_inst = f"\nADDITIONAL INSTRUCTIONS:\n{additional_instructions}\n" if additional_instructions else ""

    return f"""\
Write a complete, publication-quality {template.review_type.value.replace('_', ' ')} review on:
**Topic: {topic or "the provided corpus"}**

TARGET LENGTH: ~{word_target} words
REQUIRED SECTIONS (follow in order):
{sections_str}
{add_inst}
Use the following corpus analysis as your primary evidence base:

{context}

FORMATTING:
- Use ## for section headers
- Write in academic English with formal register
- Include in-text citations (Author, Year) for every major claim
- Do not use bullet lists within sections — write flowing prose
- End with a References section listing all cited papers
"""


def _fallback_review(
    session: ReviewSession,
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    topic: str,
    template,
) -> str:
    """Generate a minimal structured review when AI fails."""
    title = template.title_template.format(topic=topic or "the Topic")
    lines = [f"# {title}", ""]

    lines.append("## Introduction")
    lines.append(
        f"This {session.review_type.value.replace('_', ' ')} review synthesises "
        f"{len(papers)} papers on {topic or 'the research topic'}."
    )

    if analyses:
        methodologies = list(set(a.methodology for a in analyses if a.methodology))[:3]
        if methodologies:
            lines.append(f"\n## Methodology\nStudies employed: {', '.join(methodologies)}.")

    lines.append("\n## Summary of Findings")
    for a in analyses[:5]:
        p = next((p for p in papers if p.paper_id == a.paper_id), None)
        if p and a.results:
            lines.append(f"- {p.short_ref}: {a.results[:200]}")

    lines.append("\n## Conclusion")
    lines.append("Further systematic analysis is recommended.")

    return "\n".join(lines)
