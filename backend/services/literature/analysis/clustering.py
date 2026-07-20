"""Thematic clustering via TF-IDF + cosine-similarity greedy grouping.

Pure-Python — no sklearn, no numpy dependency.
Works well for corpora up to ~500 papers.
"""
from __future__ import annotations

import math
import re
import uuid
from collections import Counter, defaultdict

from services.literature.models import Paper, PaperAnalysis, ThematicCluster

# Common English stop-words for TF-IDF
_STOP = frozenset({
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "by","from","is","are","was","were","be","been","being","have","has",
    "had","do","does","did","will","would","could","should","may","might",
    "this","that","these","those","it","its","we","our","they","their",
    "also","study","paper","research","results","method","methods","data",
    "using","based","used","analysis","approach","show","shows","showed",
    "proposed","present","presented","found","findings","authors","conclusion",
    "however","thus","therefore","furthermore","moreover","among","across",
    "between","within","such","more","one","two","three","can","which","when",
    "after","before","than","then","while","both","each","all","any","some",
    "not","no","only","into","over","under","around","through","during",
})

_MIN_CLUSTER_SIZE = 2
_SIMILARITY_THRESHOLD = 0.12


def cluster_papers(
    papers: list[Paper],
    analyses: list[PaperAnalysis] | None = None,
    n_clusters: int | None = None,
) -> list[ThematicCluster]:
    """Group papers into thematic clusters using TF-IDF similarity."""
    if len(papers) < 2:
        if papers:
            return [_single_cluster(papers[0])]
        return []

    # Build document texts: title + abstract + extracted keywords
    docs = _build_docs(papers, analyses)
    if not any(docs):
        return [_single_cluster(p) for p in papers[:5]]

    # TF-IDF
    tf_idf_matrix = _compute_tfidf(docs)

    # Greedy clustering by cosine similarity
    target_k = n_clusters or max(2, min(10, len(papers) // 4))
    assignments = _greedy_cluster(tf_idf_matrix, target_k)

    # Build ThematicCluster objects
    return _build_clusters(papers, assignments, tf_idf_matrix)


def label_clusters_with_ai_hint(
    clusters: list[ThematicCluster],
    papers: list[Paper],
) -> list[ThematicCluster]:
    """Post-process: generate descriptive labels from top keywords."""
    paper_map = {p.paper_id: p for p in papers}
    for cluster in clusters:
        if cluster.top_keywords:
            cluster.label = _generate_label(cluster.top_keywords, cluster.dominant_methodology)
    return clusters


# ── TF-IDF ────────────────────────────────────────────────────────────────────

def _build_docs(papers: list[Paper], analyses: list[PaperAnalysis] | None) -> list[list[str]]:
    analysis_map: dict[str, PaperAnalysis] = {}
    if analyses:
        analysis_map = {a.paper_id: a for a in analyses}

    docs: list[list[str]] = []
    for p in papers:
        tokens: list[str] = []
        tokens += _tokenize(p.title)
        tokens += _tokenize(p.abstract)
        tokens += [k.lower() for k in p.keywords]
        an = analysis_map.get(p.paper_id)
        if an:
            tokens += _tokenize(an.domain)
            tokens += _tokenize(an.methodology)
            tokens += [k.lower() for k in an.extracted_keywords]
        docs.append(tokens)
    return docs


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return [w for w in words if w not in _STOP]


def _compute_tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    n = len(docs)
    # Document frequency
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))

    result: list[dict[str, float]] = []
    for doc in docs:
        tf = Counter(doc)
        total = len(doc) or 1
        tfidf: dict[str, float] = {}
        for term, count in tf.items():
            tf_score = count / total
            idf_score = math.log((n + 1) / (df[term] + 1)) + 1.0
            tfidf[term] = tf_score * idf_score
        # L2 normalise
        norm = math.sqrt(sum(v * v for v in tfidf.values())) or 1.0
        result.append({k: v / norm for k, v in tfidf.items()})
    return result


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    shared = set(a) & set(b)
    return sum(a[k] * b[k] for k in shared)


# ── Clustering ────────────────────────────────────────────────────────────────

def _greedy_cluster(
    tfidf: list[dict[str, float]],
    target_k: int,
) -> list[int]:
    """Assign each document to the nearest centroid; iterate to convergence."""
    n = len(tfidf)
    if n == 0:
        return []

    # Initialise: pick evenly-spaced seeds
    step = max(1, n // target_k)
    centroids = [dict(tfidf[i * step]) for i in range(min(target_k, n))]
    assignments = [0] * n

    for _iteration in range(20):
        # Assignment step
        new_assignments = []
        for doc in tfidf:
            best = 0
            best_sim = -1.0
            for j, centroid in enumerate(centroids):
                sim = _cosine(doc, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best = j
            new_assignments.append(best)

        if new_assignments == assignments:
            break
        assignments = new_assignments

        # Update centroids
        clusters_terms: list[dict[str, list[float]]] = [defaultdict(list) for _ in centroids]
        for i, cid in enumerate(assignments):
            for term, score in tfidf[i].items():
                clusters_terms[cid][term].append(score)

        for j, ct in enumerate(clusters_terms):
            if ct:
                centroids[j] = {t: sum(v) / len(v) for t, v in ct.items()}

    return assignments


def _build_clusters(
    papers: list[Paper],
    assignments: list[int],
    tfidf: list[dict[str, float]],
) -> list[ThematicCluster]:
    groups: dict[int, list[int]] = defaultdict(list)
    for i, cid in enumerate(assignments):
        groups[cid].append(i)

    clusters: list[ThematicCluster] = []
    for cid, indices in sorted(groups.items(), key=lambda x: -len(x[1])):
        if len(indices) < _MIN_CLUSTER_SIZE:
            continue
        paper_ids = [papers[i].paper_id for i in indices]
        years = [papers[i].year for i in indices if papers[i].year]
        year_range = (min(years), max(years)) if years else (0, 0)

        # Top keywords from cluster centroid
        merged: dict[str, float] = defaultdict(float)
        for i in indices:
            for t, v in tfidf[i].items():
                merged[t] += v
        top_kw = [t for t, _ in sorted(merged.items(), key=lambda x: -x[1])[:8]]

        # Dominant methodology from papers
        all_kw = []
        for i in indices:
            all_kw.extend(papers[i].keywords)
        meth = _dominant_methodology(all_kw)

        # Coherence: average intra-cluster similarity
        coherence = _intra_similarity(tfidf, indices)

        cluster = ThematicCluster(
            cluster_id=str(uuid.uuid4()),
            paper_ids=paper_ids,
            top_keywords=top_kw,
            dominant_methodology=meth,
            year_range=year_range,
            coherence_score=round(coherence, 3),
        )
        cluster.label = _generate_label(top_kw, meth)
        cluster.description = f"Cluster of {len(paper_ids)} papers spanning {year_range[0]}–{year_range[1]}"
        clusters.append(cluster)

    return clusters


def _intra_similarity(tfidf: list[dict], indices: list[int]) -> float:
    if len(indices) < 2:
        return 1.0
    total = 0.0
    count = 0
    for i in range(len(indices)):
        for j in range(i + 1, len(indices)):
            total += _cosine(tfidf[indices[i]], tfidf[indices[j]])
            count += 1
    return total / count if count else 0.0


def _dominant_methodology(keywords: list[str]) -> str:
    kwl = [k.lower() for k in keywords]
    counts = {
        "quantitative": sum(1 for k in kwl if any(t in k for t in ["quantitative", "statistical", "regression", "survey"])),
        "qualitative": sum(1 for k in kwl if any(t in k for t in ["qualitative", "interview", "thematic", "ethnograph"])),
        "computational": sum(1 for k in kwl if any(t in k for t in ["neural", "learning", "algorithm", "model", "deep", "machine"])),
        "experimental": sum(1 for k in kwl if any(t in k for t in ["experiment", "trial", "rct", "randomised", "randomized"])),
    }
    best = max(counts, key=lambda k: counts[k])
    return best if counts[best] > 0 else "mixed"


def _generate_label(keywords: list[str], methodology: str) -> str:
    if not keywords:
        return "Miscellaneous"
    primary = " ".join(w.title() for w in keywords[:2])
    return f"{primary} Research"


def _single_cluster(paper: Paper) -> ThematicCluster:
    c = ThematicCluster(
        cluster_id=str(uuid.uuid4()),
        paper_ids=[paper.paper_id],
        top_keywords=paper.keywords[:5],
        year_range=(paper.year, paper.year),
        coherence_score=1.0,
    )
    c.label = paper.title[:50] if paper.title else "Single Paper"
    return c
