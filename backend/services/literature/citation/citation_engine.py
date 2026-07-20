"""Citation intelligence — network analysis, influence scoring, foundational works."""
from __future__ import annotations

import math
from collections import defaultdict

from services.literature.models import Paper


def build_citation_network(papers: list[Paper]) -> dict:
    """Build a citation graph from the paper corpus.

    Returns a dict suitable for frontend D3/Recharts rendering.
    """
    if not papers:
        return {"nodes": [], "edges": [], "stats": {}}

    paper_map = {p.paper_id: p for p in papers}
    doi_to_id = {p.doi.lower(): p.paper_id for p in papers if p.doi}
    pmid_to_id = {p.pmid: p.paper_id for p in papers if p.pmid}
    arxiv_to_id = {p.arxiv_id: p.paper_id for p in papers if p.arxiv_id}

    # Build nodes
    nodes = []
    for p in papers:
        influence = _influence_score(p, len(papers))
        nodes.append({
            "id": p.paper_id,
            "label": p.short_ref,
            "title": p.title[:80],
            "year": p.year,
            "citation_count": p.citation_count,
            "influence_score": influence,
            "journal": p.journal,
            "doi": p.doi,
        })

    # Build edges (within-corpus citations only)
    edges = []
    seen_edges: set[tuple[str, str]] = set()
    for p in papers:
        for ref in p.references:
            target_id = _resolve_id(ref, doi_to_id, pmid_to_id, arxiv_to_id)
            if target_id and target_id != p.paper_id:
                edge_key = (p.paper_id, target_id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "source": p.paper_id,
                        "target": target_id,
                        "type": "cites",
                    })
        for cited_by in p.cited_by:
            source_id = _resolve_id(cited_by, doi_to_id, pmid_to_id, arxiv_to_id)
            if source_id and source_id != p.paper_id:
                edge_key = (source_id, p.paper_id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "source": source_id,
                        "target": p.paper_id,
                        "type": "cites",
                    })

    # Compute in-degree (citation count within corpus)
    in_degree: dict[str, int] = defaultdict(int)
    for e in edges:
        in_degree[e["target"]] += 1

    # Update nodes with in-corpus citation count
    for node in nodes:
        node["corpus_citations"] = in_degree.get(node["id"], 0)

    # Foundational papers (highly cited within corpus)
    foundational = sorted(nodes, key=lambda n: -n["corpus_citations"])[:5]
    highly_cited = sorted(nodes, key=lambda n: -n["citation_count"])[:5]
    recent_influential = sorted(
        [n for n in nodes if n["year"] and n["year"] >= max((n["year"] for n in nodes), default=0) - 3],
        key=lambda n: -n["citation_count"]
    )[:5]

    stats = {
        "total_papers": len(papers),
        "total_edges": len(edges),
        "avg_citations": round(sum(p.citation_count for p in papers) / len(papers), 1),
        "foundational_papers": [{"id": n["id"], "label": n["label"]} for n in foundational],
        "highly_cited": [{"id": n["id"], "label": n["label"], "count": n["citation_count"]}
                         for n in highly_cited],
        "recent_influential": [{"id": n["id"], "label": n["label"]} for n in recent_influential],
    }

    return {"nodes": nodes, "edges": edges, "stats": stats}


def score_paper_influence(paper: Paper, corpus_size: int = 100) -> float:
    """Normalised influence score [0,1] based on citation count."""
    return _influence_score(paper, corpus_size)


def identify_foundational_works(papers: list[Paper], n: int = 10) -> list[Paper]:
    """Return the n most foundational papers by citation count."""
    return sorted(papers, key=lambda p: p.citation_count, reverse=True)[:n]


def identify_self_citations(papers: list[Paper]) -> list[dict]:
    """Detect papers that cite each other (potential self-citation patterns)."""
    doi_to_paper = {p.doi.lower(): p for p in papers if p.doi}
    pairs = []
    for p in papers:
        for ref in p.references:
            ref_norm = ref.lower()
            if ref_norm in doi_to_paper and doi_to_paper[ref_norm].paper_id != p.paper_id:
                cited = doi_to_paper[ref_norm]
                pairs.append({
                    "citing_id": p.paper_id,
                    "citing_title": p.title,
                    "cited_id": cited.paper_id,
                    "cited_title": cited.title,
                })
    return pairs[:20]


def compute_author_collaboration_graph(papers: list[Paper]) -> dict:
    """Build an author collaboration network for visualisation."""
    coauthor_edges: dict[tuple[str, str], int] = defaultdict(int)

    for p in papers:
        authors = p.authors[:10]   # cap per paper
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                a, b = sorted([authors[i][:40], authors[j][:40]])
                coauthor_edges[(a, b)] += 1

    # Collect author frequency
    author_freq: dict[str, int] = defaultdict(int)
    for p in papers:
        for a in p.authors[:10]:
            author_freq[a[:40]] += 1

    nodes = [{"id": a, "paper_count": c}
             for a, c in sorted(author_freq.items(), key=lambda x: -x[1])[:50]]
    node_ids = {n["id"] for n in nodes}

    edges = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in coauthor_edges.items()
        if a in node_ids and b in node_ids
    ]

    return {"nodes": nodes, "edges": edges}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _influence_score(paper: Paper, corpus_size: int) -> float:
    if paper.citation_count <= 0:
        return 0.0
    return round(min(1.0, math.log(paper.citation_count + 1) / math.log(max(corpus_size, 10) * 5)), 3)


def _resolve_id(
    ref: str,
    doi_to_id: dict[str, str],
    pmid_to_id: dict[str, str],
    arxiv_to_id: dict[str, str],
) -> str | None:
    ref_lower = ref.lower().strip()
    if ref_lower in doi_to_id:
        return doi_to_id[ref_lower]
    if ref in pmid_to_id:
        return pmid_to_id[ref]
    if ref in arxiv_to_id:
        return arxiv_to_id[ref]
    return None
