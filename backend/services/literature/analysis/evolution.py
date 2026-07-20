"""Research evolution builder — chronological milestones and topic trends."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from services.literature.models import Milestone, Paper, PaperAnalysis, ResearchEvolution


def build_evolution(
    session_id: str,
    papers: list[Paper],
    analyses: list[PaperAnalysis] | None = None,
) -> ResearchEvolution:
    """Build a chronological research evolution from a paper corpus."""
    if not papers:
        return ResearchEvolution(session_id=session_id)

    analysis_map = {a.paper_id: a for a in (analyses or [])}
    sorted_papers = sorted(papers, key=lambda p: p.year or 9999)

    years_with_papers = [(p.year, p) for p in sorted_papers if p.year]
    if not years_with_papers:
        return ResearchEvolution(session_id=session_id)

    earliest = years_with_papers[0][0]
    latest = years_with_papers[-1][0]

    # Group papers by year
    by_year: dict[int, list[Paper]] = defaultdict(list)
    for year, p in years_with_papers:
        by_year[year].append(p)

    # Build milestones — one per distinct year bucket (or every 5 years for large spans)
    milestones = _build_milestones(by_year, analysis_map, span=latest - earliest)

    # Topic evolution: keyword frequency per time-window
    emerging, declining = _analyse_topic_trends(sorted_papers)

    # Future directions from analyses
    future_dirs = _extract_future_directions(analyses or [])

    # Summary
    span_years = latest - earliest
    paper_count = len(papers)
    summary = (
        f"The corpus of {paper_count} papers spans {span_years} years "
        f"({earliest}–{latest}). "
    )
    if milestones:
        n_major = sum(1 for m in milestones if m.significance == "major")
        if n_major:
            summary += f"{n_major} major milestone{'s' if n_major > 1 else ''} identified. "
    if emerging:
        summary += f"Emerging topics: {', '.join(emerging[:3])}."

    return ResearchEvolution(
        session_id=session_id,
        milestones=milestones,
        emerging_topics=emerging,
        declining_topics=declining,
        future_directions=future_dirs,
        earliest_year=earliest,
        latest_year=latest,
        evolution_summary=summary.strip(),
    )


def _build_milestones(
    by_year: dict[int, list[Paper]],
    analysis_map: dict[str, PaperAnalysis],
    span: int,
) -> list[Milestone]:
    """Create one milestone per year (or per 5-year bucket for large spans)."""
    milestones: list[Milestone] = []
    bucket_size = 1 if span <= 10 else (3 if span <= 25 else 5)

    # Group years into buckets
    all_years = sorted(by_year)
    buckets: dict[int, list[Paper]] = defaultdict(list)
    for year in all_years:
        bucket = (year // bucket_size) * bucket_size
        buckets[bucket].extend(by_year[year])

    for bucket_year, papers_in_bucket in sorted(buckets.items()):
        if not papers_in_bucket:
            continue

        # Find most-cited paper in the bucket as the milestone representative
        anchor = max(papers_in_bucket, key=lambda p: p.citation_count)
        analysis = analysis_map.get(anchor.paper_id)

        # Build description
        desc = _describe_milestone(bucket_year, bucket_size, papers_in_bucket, anchor, analysis)
        significance = _classify_significance(anchor, papers_in_bucket)

        milestones.append(Milestone(
            year=bucket_year,
            description=desc,
            paper_ids=[p.paper_id for p in papers_in_bucket],
            significance=significance,
        ))

    return milestones[:30]   # cap for very large corpora


def _describe_milestone(
    year: int,
    bucket_size: int,
    papers: list[Paper],
    anchor: Paper,
    analysis: PaperAnalysis | None,
) -> str:
    period = str(year) if bucket_size == 1 else f"{year}–{year + bucket_size - 1}"
    count = len(papers)

    if analysis and analysis.contribution:
        return f"{period}: {analysis.contribution[:200]} ({anchor.short_ref})"

    if anchor.abstract:
        # First sentence of abstract as description
        first_sentence = re.split(r"(?<=[.!?])\s+", anchor.abstract.strip())[0]
        return f"{period}: {first_sentence[:200]}"

    return f"{period}: {count} paper{'s' if count > 1 else ''} published — {anchor.title[:100]}"


def _classify_significance(anchor: Paper, papers: list[Paper]) -> str:
    if anchor.citation_count > 100 or len(papers) >= 5:
        return "major"
    if anchor.citation_count > 20 or len(papers) >= 2:
        return "normal"
    return "minor"


def _analyse_topic_trends(papers: list[Paper]) -> tuple[list[str], list[str]]:
    """Identify keywords that grew or declined over time."""
    if len(papers) < 4:
        all_kw = []
        for p in papers:
            all_kw.extend(k.lower() for k in p.keywords)
        return list(dict.fromkeys(all_kw))[:5], []

    midpoint = len(papers) // 2
    early = papers[:midpoint]
    late = papers[midpoint:]

    early_kw = Counter(k.lower() for p in early for k in p.keywords)
    late_kw = Counter(k.lower() for p in late for k in p.keywords)

    # Normalise by corpus size
    early_total = sum(early_kw.values()) or 1
    late_total = sum(late_kw.values()) or 1

    all_kw = set(early_kw) | set(late_kw)
    emerging: list[tuple[str, float]] = []
    declining: list[tuple[str, float]] = []

    for kw in all_kw:
        early_freq = early_kw[kw] / early_total
        late_freq = late_kw[kw] / late_total
        delta = late_freq - early_freq
        if delta > 0.002 and late_kw[kw] >= 2:
            emerging.append((kw, delta))
        elif delta < -0.002 and early_kw[kw] >= 2:
            declining.append((kw, -delta))

    return (
        [kw for kw, _ in sorted(emerging, key=lambda x: -x[1])[:8]],
        [kw for kw, _ in sorted(declining, key=lambda x: -x[1])[:5]],
    )


def _extract_future_directions(analyses: list[PaperAnalysis]) -> list[str]:
    directions: list[str] = []
    seen: set[str] = set()
    for a in analyses:
        if a.future_work and len(a.future_work) > 20:
            key = a.future_work[:40].lower()
            if key not in seen:
                seen.add(key)
                directions.append(a.future_work[:200])
    return directions[:8]
