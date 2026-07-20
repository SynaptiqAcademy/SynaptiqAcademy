"""Competitive landscape analysis for Research Gap Intelligence.

Determines active researchers, leading institutions, journals, conferences,
emerging/declining topics, publication density, and research maturity.
Combines corpus signals with AI synthesis.
"""
from __future__ import annotations

import logging
from collections import Counter

from .models import (
    CompetitiveLandscape, GapAnalysisResult, DetectedGap,
    PublicationDensity, ResearchMaturity,
)

log = logging.getLogger("synaptiq.research_gap.competitive")


def build_landscape_from_corpus(
    papers: list,
    analyses: list,
    topic: str = "",
    ai_landscape: dict | None = None,
) -> CompetitiveLandscape:
    """Build competitive landscape from corpus data, optionally overlaying AI output."""
    cl = CompetitiveLandscape()

    if papers:
        cl = _corpus_landscape(papers, analyses, cl)
    if ai_landscape:
        cl = _overlay_ai_landscape(ai_landscape, cl)

    cl = _infer_density_and_maturity(papers, cl)
    return cl


def build_landscape_from_ai(ai_landscape: dict) -> CompetitiveLandscape:
    """Build landscape entirely from AI-generated dict when no corpus is available."""
    cl = CompetitiveLandscape()
    return _overlay_ai_landscape(ai_landscape, cl)


def _corpus_landscape(papers: list, analyses: list, cl: CompetitiveLandscape) -> CompetitiveLandscape:
    # Extract authors from papers
    all_authors: list[str] = []
    for p in papers:
        all_authors.extend(getattr(p, "authors", []) or [])
    author_counter = Counter(all_authors)
    cl.active_researchers = [
        a for a, _ in author_counter.most_common(10) if a
    ]

    # Extract journals
    journals: list[str] = []
    for p in papers:
        j = getattr(p, "journal", "") or ""
        if j:
            journals.append(j)
    journal_counter = Counter(journals)
    cl.leading_journals = [j for j, _ in journal_counter.most_common(5)]

    # Keyword trends → emerging/declining topics
    years = sorted(set(p.year for p in papers if getattr(p, "year", None)))
    if years and len(years) >= 2:
        mid = years[len(years) // 2]
        early_kws = _collect_keywords(p for p in papers if getattr(p, "year", 0) <= mid)
        late_kws = _collect_keywords(p for p in papers if getattr(p, "year", 0) > mid)

        for kw, late_count in late_kws.most_common(15):
            if late_count > early_kws.get(kw, 0) * 1.5 and late_count >= 2:
                if kw not in cl.emerging_topics:
                    cl.emerging_topics.append(kw)
        cl.emerging_topics = cl.emerging_topics[:8]

        for kw, early_count in early_kws.most_common(15):
            if early_count > late_kws.get(kw, 0) * 2:
                if kw not in cl.declining_topics:
                    cl.declining_topics.append(kw)
        cl.declining_topics = cl.declining_topics[:5]

    return cl


def _overlay_ai_landscape(ai: dict, cl: CompetitiveLandscape) -> CompetitiveLandscape:
    def _merge(existing: list, new_items) -> list:
        seen = set(existing)
        combined = list(existing)
        for item in (new_items or []):
            s = str(item)
            if s and s not in seen:
                combined.append(s)
                seen.add(s)
        return combined

    cl.active_researchers = _merge(cl.active_researchers, ai.get("active_researchers", []))
    cl.leading_institutions = _merge(cl.leading_institutions, ai.get("leading_institutions", []))
    cl.leading_journals = _merge(cl.leading_journals, ai.get("leading_journals", []))
    cl.leading_conferences = _merge(cl.leading_conferences, ai.get("leading_conferences", []))
    cl.emerging_topics = _merge(cl.emerging_topics, ai.get("emerging_topics", []))
    cl.declining_topics = _merge(cl.declining_topics, ai.get("declining_topics", []))
    cl.competition_hotspots = _merge(cl.competition_hotspots, ai.get("competition_hotspots", []))
    cl.opportunity_whitespace = _merge(cl.opportunity_whitespace, ai.get("opportunity_whitespace", []))
    cl.field_growth_rate = ai.get("field_growth_rate", "") or cl.field_growth_rate
    cl.interdisciplinary_links = _merge(cl.interdisciplinary_links, ai.get("interdisciplinary_links", []))

    # Density and maturity from AI if not already set
    density_str = ai.get("publication_density", "")
    try:
        cl.publication_density = PublicationDensity(density_str)
    except ValueError:
        pass

    maturity_str = ai.get("research_maturity", "")
    try:
        cl.research_maturity = ResearchMaturity(maturity_str)
    except ValueError:
        pass

    return cl


def _infer_density_and_maturity(papers: list, cl: CompetitiveLandscape) -> CompetitiveLandscape:
    n = len(papers)
    if cl.publication_density == PublicationDensity.MODERATE:  # default; override if corpus available
        if n > 200:
            cl.publication_density = PublicationDensity.SATURATED
        elif n > 80:
            cl.publication_density = PublicationDensity.DENSE
        elif n < 15:
            cl.publication_density = PublicationDensity.SPARSE
    return cl


def _collect_keywords(paper_iter) -> Counter:
    kws: list[str] = []
    for p in paper_iter:
        kws.extend(k.lower() for k in (getattr(p, "keywords", []) or []))
    return Counter(kws)


def identify_opportunity_whitespace(
    gaps: list[DetectedGap],
    landscape: CompetitiveLandscape,
) -> list[str]:
    """Derive whitespace from low-competition high-opportunity gaps."""
    whitespace: list[str] = list(landscape.opportunity_whitespace)
    for gap in gaps:
        from .models import CompetitionLevel
        if (gap.competition_level in (CompetitionLevel.LOW, CompetitionLevel.MEDIUM)
                and gap.opportunity_score.overall_score >= 0.65):
            label = f"{gap.gap_type.value}: {gap.title[:60]}"
            if label not in whitespace:
                whitespace.append(label)
    return whitespace[:8]
