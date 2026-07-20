"""Academic Knowledge Graph — Embedding Engine (Phase XVII).

Pure Python structural embeddings for knowledge graph nodes.

Approach: hash-based random projection + structural features (degree, type, neighborhood)
→ deterministic 16-dimensional vectors that capture graph topology.

Supports:
  - Node embedding generation
  - Cosine similarity search
  - KNN (k-nearest neighbors) for recommendation
  - Community-aware similarity
"""
from __future__ import annotations

import hashlib
import math

from .graph_store import AcademicKnowledgeGraph
from .models import GraphEmbedding, NodeType


_EMB_DIM = 16

# One-hot offset for each NodeType in the embedding
_TYPE_ORDER = list(NodeType)
_TYPE_DIM   = 8   # bits allocated for type info within the dim budget


def _hash_proj(node_id: str, dim_idx: int) -> float:
    """Deterministic pseudo-random projection via MD5."""
    raw = hashlib.md5(f"{node_id}::dim{dim_idx}".encode()).digest()
    val = int.from_bytes(raw[:4], "big") / 0xFFFFFFFF
    return val * 2.0 - 1.0  # ∈ [-1, 1]


def _type_features(node_type: NodeType) -> list[float]:
    """8-bit encoding of node type (grouped categories)."""
    researcher_types = {NodeType.RESEARCHER, NodeType.STUDENT,
                        NodeType.SUPERVISOR, NodeType.REVIEWER, NodeType.EDITOR}
    institution_types = {NodeType.INSTITUTION, NodeType.DEPARTMENT,
                         NodeType.RESEARCH_CENTER, NodeType.LABORATORY,
                         NodeType.ORGANIZATION}
    content_types = {NodeType.PUBLICATION, NodeType.PATENT,
                     NodeType.DATASET, NodeType.TEACHING_MATERIAL,
                     NodeType.COURSE}
    knowledge_types = {NodeType.TOPIC, NodeType.KEYWORD, NodeType.CONCEPT,
                       NodeType.DOMAIN, NodeType.HYPOTHESIS,
                       NodeType.RESEARCH_QUESTION}
    method_types = {NodeType.METHOD, NodeType.STATISTICAL_METHOD,
                    NodeType.PROGRAMMING_LANGUAGE, NodeType.SOFTWARE,
                    NodeType.AI_MODEL}
    funding_types = {NodeType.GRANT, NodeType.FUNDING_AGENCY, NodeType.POLICY}
    venue_types   = {NodeType.JOURNAL, NodeType.CONFERENCE}
    return [
        1.0 if node_type in researcher_types    else 0.0,
        1.0 if node_type in institution_types   else 0.0,
        1.0 if node_type in content_types       else 0.0,
        1.0 if node_type in knowledge_types     else 0.0,
        1.0 if node_type in method_types        else 0.0,
        1.0 if node_type in funding_types       else 0.0,
        1.0 if node_type in venue_types         else 0.0,
        float(_TYPE_ORDER.index(node_type)) / len(_TYPE_ORDER),
    ]


def embed_node(
    graph: AcademicKnowledgeGraph,
    node_id: str,
    dim: int = _EMB_DIM,
) -> GraphEmbedding | None:
    """Generate a structural embedding for a single node."""
    node = graph.get_node(node_id)
    if not node:
        return None

    # Structural features
    degree    = graph.degree(node_id)
    in_deg    = graph.in_degree(node_id)
    out_deg   = graph.out_degree(node_id)

    # Neighbor type diversity
    nb_types: set[str] = set()
    for nb in graph.neighbors(node_id, direction="both"):
        nb_node = graph.get_node(nb)
        if nb_node:
            nb_types.add(nb_node.node_type.value)

    # Build vector
    vec: list[float] = []

    # 1. Hash-based random projection (8 dims)
    for i in range(8):
        vec.append(_hash_proj(node_id, i))

    # 2. Type features (8 dims)
    vec.extend(_type_features(node.node_type))

    # 3. Structural features woven into remaining dims
    if len(vec) < dim:
        # Normalize degree features
        vec.append(min(math.log1p(degree)    / 6.0, 1.0))
        vec.append(min(math.log1p(in_deg)    / 6.0, 1.0))
        vec.append(min(math.log1p(out_deg)   / 6.0, 1.0))
        vec.append(min(len(nb_types) / 10.0, 1.0))

    # Trim / pad to exactly dim
    vec = vec[:dim] + [0.0] * max(0, dim - len(vec))

    # L2 normalise for cosine-friendly comparisons
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    vec  = [v / norm for v in vec]

    return GraphEmbedding(node_id=node_id, vector=vec, embedding_dim=dim)


def embed_all(
    graph: AcademicKnowledgeGraph,
    dim: int = _EMB_DIM,
    node_type_filter: NodeType | None = None,
) -> dict[str, GraphEmbedding]:
    """Embed all (or all of a given type) nodes."""
    results: dict[str, GraphEmbedding] = {}
    nids = (graph.nodes_by_type(node_type_filter)
            if node_type_filter else graph.all_nodes())
    for item in nids:
        nid = item.node_id if hasattr(item, "node_id") else item
        emb = embed_node(graph, nid, dim)
        if emb:
            results[nid] = emb
    return results


# ── Similarity ────────────────────────────────────────────────────────────────

def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two pre-normalised vectors."""
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))


def similar_nodes(
    graph: AcademicKnowledgeGraph,
    query_node_id: str,
    top_k: int = 10,
    node_type_filter: NodeType | None = None,
    embeddings: dict[str, GraphEmbedding] | None = None,
) -> list[dict]:
    """
    Find top-k nodes most similar to the query node.
    Returns list of {node_id, label, node_type, similarity}.
    """
    if embeddings is None:
        embeddings = embed_all(graph, node_type_filter=node_type_filter)

    query_emb = embeddings.get(query_node_id)
    if not query_emb:
        return []

    scores: list[tuple[float, str]] = []
    for nid, emb in embeddings.items():
        if nid == query_node_id:
            continue
        sim = _cosine(query_emb.vector, emb.vector)
        scores.append((sim, nid))

    scores.sort(reverse=True)
    results = []
    for sim, nid in scores[:top_k]:
        node = graph.get_node(nid)
        if node:
            results.append({
                "node_id":   nid,
                "label":     node.label,
                "node_type": node.node_type.value,
                "similarity": round(sim, 4),
            })
    return results


def community_aware_similarity(
    graph: AcademicKnowledgeGraph,
    query_node_id: str,
    community_map: dict[str, int],
    top_k: int = 10,
    embeddings: dict[str, GraphEmbedding] | None = None,
) -> list[dict]:
    """
    Similar to similar_nodes but boosts nodes in different communities
    to encourage cross-community discovery.
    """
    if embeddings is None:
        embeddings = embed_all(graph)

    query_emb = embeddings.get(query_node_id)
    if not query_emb:
        return []

    my_community = community_map.get(query_node_id, -1)
    scores: list[tuple[float, str]] = []
    for nid, emb in embeddings.items():
        if nid == query_node_id:
            continue
        sim   = _cosine(query_emb.vector, emb.vector)
        boost = 0.1 if community_map.get(nid, -2) != my_community else 0.0
        scores.append((sim + boost, nid))

    scores.sort(reverse=True)
    results = []
    for score, nid in scores[:top_k]:
        node = graph.get_node(nid)
        if node:
            results.append({
                "node_id":   nid,
                "label":     node.label,
                "node_type": node.node_type.value,
                "similarity": round(score, 4),
                "community": community_map.get(nid),
            })
    return results
