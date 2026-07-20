"""Visualization data builders — returns JSON-serialisable dicts for frontend rendering."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from services.literature.models import (
    Paper, PaperAnalysis, ResearchEvolution, ThematicCluster,
)


def build_all_visualizations(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    clusters: list[ThematicCluster],
    evolution: ResearchEvolution | None,
) -> dict:
    """Return all visualization data structures in one call."""
    return {
        "timeline": build_timeline(papers),
        "cluster_map": build_cluster_map(clusters, papers),
        "keyword_network": build_keyword_network(papers, analyses),
        "methodology_distribution": build_methodology_distribution(analyses),
        "publication_trends": build_publication_trends(papers),
        "topic_evolution": build_topic_evolution(papers, evolution),
        "concept_map": build_concept_map(analyses),
    }


def build_timeline(papers: list[Paper]) -> dict:
    """Year-by-year publication count with representative papers."""
    by_year: dict[int, list[dict]] = defaultdict(list)
    for p in papers:
        if p.year:
            by_year[p.year].append({
                "id": p.paper_id,
                "title": p.title[:60],
                "citations": p.citation_count,
            })

    data_points = []
    for year in sorted(by_year):
        plist = sorted(by_year[year], key=lambda x: -x["citations"])
        data_points.append({
            "year": year,
            "count": len(by_year[year]),
            "top_paper": plist[0]["title"] if plist else "",
            "papers": plist[:5],
        })

    return {
        "type": "timeline",
        "data": data_points,
        "total_years": len(by_year),
        "year_range": [min(by_year) if by_year else 0, max(by_year) if by_year else 0],
    }


def build_cluster_map(
    clusters: list[ThematicCluster],
    papers: list[Paper],
) -> dict:
    """Cluster graph — nodes are clusters, connected if they share keywords."""
    paper_map = {p.paper_id: p for p in papers}
    nodes = []
    for c in clusters:
        years = [paper_map[pid].year for pid in c.paper_ids if pid in paper_map and paper_map[pid].year]
        nodes.append({
            "id": c.cluster_id,
            "label": c.label,
            "size": len(c.paper_ids),
            "keywords": c.top_keywords[:5],
            "coherence": c.coherence_score,
            "year_range": list(c.year_range),
            "dominant_methodology": c.dominant_methodology,
        })

    # Edges: clusters with overlapping keywords
    edges = []
    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            kw_a = set(clusters[i].top_keywords)
            kw_b = set(clusters[j].top_keywords)
            overlap = len(kw_a & kw_b)
            if overlap >= 2:
                edges.append({
                    "source": clusters[i].cluster_id,
                    "target": clusters[j].cluster_id,
                    "weight": overlap,
                })

    return {"type": "cluster_map", "nodes": nodes, "edges": edges}


def build_keyword_network(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
) -> dict:
    """Keyword co-occurrence network — which keywords appear together frequently."""
    analysis_map = {a.paper_id: a for a in analyses}

    # Collect all keywords per paper (paper.keywords + analysis.extracted_keywords)
    all_paper_kw: list[list[str]] = []
    for p in papers:
        kws = list(p.keywords)
        an = analysis_map.get(p.paper_id)
        if an:
            kws.extend(an.extracted_keywords)
        # Normalise
        kws = [k.lower().strip() for k in kws if len(k) > 2][:15]
        all_paper_kw.append(kws)

    # Node frequency
    kw_freq: Counter[str] = Counter()
    for kws in all_paper_kw:
        kw_freq.update(kws)

    # Top keywords only
    top_kw = {kw for kw, _ in kw_freq.most_common(50)}

    # Co-occurrence edges
    cooccurrence: dict[tuple[str, str], int] = defaultdict(int)
    for kws in all_paper_kw:
        filtered = [k for k in kws if k in top_kw]
        for i in range(len(filtered)):
            for j in range(i + 1, len(filtered)):
                pair = tuple(sorted([filtered[i], filtered[j]]))
                cooccurrence[pair] += 1

    nodes = [{"id": kw, "weight": kw_freq[kw]} for kw in top_kw]
    edges = [
        {"source": a, "target": b, "count": c}
        for (a, b), c in cooccurrence.items() if c >= 2
    ]

    return {"type": "keyword_network", "nodes": nodes, "edges": edges}


def build_methodology_distribution(analyses: list[PaperAnalysis]) -> dict:
    """Pie/bar chart data for methodology and research design distribution."""
    meth_counter: Counter[str] = Counter()
    design_counter: Counter[str] = Counter()

    for a in analyses:
        if a.methodology:
            meth_counter[a.methodology.strip().lower()] += 1
        if a.research_design:
            design_counter[a.research_design.strip().lower()] += 1

    total = len(analyses) or 1

    methodologies = [
        {"method": m, "count": c, "percentage": round(c / total * 100, 1)}
        for m, c in meth_counter.most_common(10)
    ]
    designs = [
        {"design": d, "count": c, "percentage": round(c / total * 100, 1)}
        for d, c in design_counter.most_common(10)
    ]

    return {
        "type": "methodology_distribution",
        "methodologies": methodologies,
        "designs": designs,
        "total_papers": len(analyses),
    }


def build_publication_trends(papers: list[Paper]) -> dict:
    """Publication count per year + domain breakdown."""
    by_year: dict[int, Counter[str]] = defaultdict(Counter)

    for p in papers:
        if p.year:
            # Use journal or keywords as domain proxy
            domain = _guess_domain(p.keywords)
            by_year[p.year][domain] += 1

    data = []
    for year in sorted(by_year):
        year_data: dict = {"year": year, "total": sum(by_year[year].values())}
        for domain, count in by_year[year].most_common(3):
            year_data[domain] = count
        data.append(year_data)

    return {"type": "publication_trends", "data": data}


def build_topic_evolution(
    papers: list[Paper],
    evolution: ResearchEvolution | None,
) -> dict:
    """Show how topics evolved over time based on keyword trends."""
    if evolution:
        return {
            "type": "topic_evolution",
            "emerging_topics": evolution.emerging_topics,
            "declining_topics": evolution.declining_topics,
            "future_directions": evolution.future_directions[:5],
            "milestones": [
                {"year": m.year, "description": m.description[:100], "significance": m.significance}
                for m in (evolution.milestones or [])[:15]
            ],
        }

    # Fallback: keyword frequency over time
    decade_kw: dict[str, Counter[str]] = defaultdict(Counter)
    for p in papers:
        if p.year and p.keywords:
            decade = f"{(p.year // 10) * 10}s"
            decade_kw[decade].update(k.lower() for k in p.keywords[:8])

    timeline = []
    for decade in sorted(decade_kw):
        top = [kw for kw, _ in decade_kw[decade].most_common(5)]
        timeline.append({"period": decade, "top_topics": top})

    return {"type": "topic_evolution", "timeline": timeline}


def build_concept_map(analyses: list[PaperAnalysis]) -> dict:
    """Concept relationship map from cross-paper keyword co-occurrence."""
    concepts: dict[str, set[str]] = defaultdict(set)

    for a in analyses:
        kws = [k.lower().strip() for k in a.extracted_keywords if len(k) > 3][:10]
        for i, k1 in enumerate(kws):
            for k2 in kws[i + 1:]:
                concepts[k1].add(k2)
                concepts[k2].add(k1)

    # Keep top 30 most connected concepts
    by_degree = sorted(concepts.items(), key=lambda x: -len(x[1]))[:30]
    top_concepts = {c for c, _ in by_degree}

    nodes = [{"id": c, "connections": len(concepts[c])} for c in top_concepts]
    edges = []
    seen: set[tuple[str, str]] = set()
    for c, neighbors in by_degree:
        for n in neighbors:
            if n in top_concepts:
                pair = tuple(sorted([c, n]))
                if pair not in seen:
                    seen.add(pair)
                    edges.append({"source": c, "target": n})

    return {"type": "concept_map", "nodes": nodes, "edges": edges}


# ── Internal ──────────────────────────────────────────────────────────────────

_DOMAIN_HINTS = {
    "medicine": ["clinical", "patient", "treatment", "disease", "medical", "cancer", "drug"],
    "computer science": ["algorithm", "neural", "machine learning", "software", "deep learning"],
    "education": ["learning", "student", "teaching", "curriculum", "classroom"],
    "psychology": ["cognitive", "behavior", "mental", "emotion", "anxiety"],
    "engineering": ["design", "system", "structural", "mechanical", "electrical"],
    "social sciences": ["social", "community", "society", "political", "cultural"],
    "environment": ["climate", "environment", "ecology", "sustainability", "energy"],
}


def _guess_domain(keywords: list[str]) -> str:
    kws = " ".join(keywords).lower()
    best, best_count = "other", 0
    for domain, hints in _DOMAIN_HINTS.items():
        count = sum(1 for h in hints if h in kws)
        if count > best_count:
            best, best_count = domain, count
    return best
