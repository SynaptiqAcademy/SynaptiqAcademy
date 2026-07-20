"""Academic Knowledge Graph — Academic Copilot Integration (Phase XVII).

The Academic Copilot queries the Knowledge Graph before generating responses.
This module enriches any Copilot prompt with graph-derived context:

  - relevant researcher nodes
  - related publications
  - topic cluster context
  - hidden collaboration opportunities
  - methodological context
"""
from __future__ import annotations

from .graph_query import query_by_topic, query_type_filter
from .graph_store import AcademicKnowledgeGraph
from .models import NodeType, QueryScope
from .semantic_reasoner import find_emerging_topics, find_influential_methods


def enrich_copilot_context(
    graph: AcademicKnowledgeGraph,
    query: str,
    researcher_node_id: str | None = None,
    max_context_nodes: int = 10,
) -> dict:
    """
    Given a Copilot query string, extract relevant graph context.
    Returns a structured dict the Copilot can inject into its prompt.
    """
    context: dict = {
        "query":           query,
        "graph_available": graph.node_count() > 0,
        "relevant_nodes":  [],
        "related_topics":  [],
        "related_methods": [],
        "collaboration_hints": [],
        "copilot_context_text": "",
    }

    if graph.node_count() == 0:
        context["copilot_context_text"] = (
            "The Knowledge Graph is currently empty. "
            "Import platform data to enable graph-enhanced recommendations."
        )
        return context

    # 1. Topic-based search
    topic_result = query_by_topic(graph, query, scope=QueryScope.ALL, max_hops=1,
                                   max_results=max_context_nodes)
    context["relevant_nodes"] = topic_result.nodes[:5]
    context["related_topics"] = [
        n for n in topic_result.nodes
        if n.get("node_type") in ("topic", "keyword", "concept", "domain")
    ][:5]

    # 2. Method extraction
    methods = find_influential_methods(graph, top_k=5)
    context["related_methods"] = [m for m in methods
                                   if query.lower() in m.get("label", "").lower() or
                                   any(query.lower() in str(v).lower()
                                       for v in m.get("label", ""))][:3]

    # 3. Collaboration hints for the researcher
    if researcher_node_id and graph.get_node(researcher_node_id):
        from .semantic_reasoner import find_hidden_collaborators
        hidden = find_hidden_collaborators(graph, researcher_node_id, max_results=3)
        context["collaboration_hints"] = [h.to_dict() for h in hidden]

    # 4. Build natural language context for injection
    lines = []
    if context["relevant_nodes"]:
        labels = [n["label"] for n in context["relevant_nodes"][:3]]
        lines.append(f"Knowledge Graph context: related entities include {', '.join(labels)}.")
    if context["related_topics"]:
        topic_labels = [t["label"] for t in context["related_topics"][:3]]
        lines.append(f"Related research topics: {', '.join(topic_labels)}.")
    if context["related_methods"]:
        method_labels = [m["label"] for m in context["related_methods"][:3]]
        lines.append(f"Relevant methods identified: {', '.join(method_labels)}.")
    if context["collaboration_hints"]:
        collab_labels = [c["label"] for c in context["collaboration_hints"][:2]]
        lines.append(f"Potential collaborators: {', '.join(collab_labels)}.")

    context["copilot_context_text"] = " ".join(lines) or (
        f"Knowledge Graph queried for '{query}'; {graph.node_count()} nodes available."
    )
    return context


def graph_enhanced_recommendation(
    graph: AcademicKnowledgeGraph,
    researcher_node_id: str,
    recommendation_type: str = "collaboration",
) -> list[dict]:
    """
    Generate graph-enhanced recommendations for a researcher.
    Recommendation types: collaboration, topic, method, publication, grant
    """
    if not graph.get_node(researcher_node_id):
        return []

    if recommendation_type == "collaboration":
        from .semantic_reasoner import find_hidden_collaborators
        return [h.to_dict() for h in find_hidden_collaborators(graph, researcher_node_id)]

    if recommendation_type == "topic":
        from .semantic_reasoner import find_interdisciplinary_opportunities
        return find_interdisciplinary_opportunities(graph, researcher_node_id)

    if recommendation_type == "method":
        return find_influential_methods(graph, top_k=5)

    if recommendation_type == "publication":
        from .semantic_reasoner import find_foundational_publications
        return find_foundational_publications(graph, top_k=5)

    if recommendation_type == "grant":
        from .semantic_reasoner import identify_future_collaborations
        return identify_future_collaborations(graph, researcher_node_id)

    return []
