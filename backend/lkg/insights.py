"""Graph-based AI insights — synthesized from verified LKG data only."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .analytics import topic_trends, collaboration_density
from .reasoning import degree_centrality

logger = logging.getLogger("lkg.insights")


async def generate_user_insights(db, uid: str, limit: int = 6) -> dict:
    """
    Generate insights about a specific researcher from graph data.
    All insights trace to verified LKG edges — no invented statistics.
    """
    node_id = f"researcher:platform:{uid}"
    node    = await db.lkg_nodes.find_one({"node_id": node_id}, {"_id": 0})

    evidence = []
    context_parts = []

    # How many collaborations?
    collab_count = await db.lkg_edges.count_documents(
        {"$or": [{"from_id": node_id}, {"to_id": node_id}], "type": {"$in": ["CO_AUTHORED", "COLLABORATES_WITH"]}}
    )
    if collab_count > 0:
        evidence.append(f"{collab_count} collaboration edge(s) in graph")
        context_parts.append(f"Collaboration count (LKG): {collab_count}")

    # Topics this researcher is connected to
    topic_edges = await db.lkg_edges.find(
        {"from_id": node_id, "type": "BELONGS_TO_TOPIC"},
        {"to_id": 1}
    ).to_list(10)
    topic_ids = [e["to_id"] for e in topic_edges]
    if topic_ids:
        topic_nodes = await db.lkg_nodes.find(
            {"node_id": {"$in": topic_ids}}, {"label": 1, "_id": 0}
        ).to_list(10)
        topic_labels = [n["label"] for n in topic_nodes]
        evidence.append(f"Research topics in graph: {', '.join(topic_labels[:4])}")
        context_parts.append(f"Graph topics: {', '.join(topic_labels[:4])}")

    # Publications/manuscripts
    pub_count = await db.lkg_edges.count_documents(
        {"from_id": node_id, "type": "AUTHORED"}
    )
    if pub_count > 0:
        evidence.append(f"{pub_count} authored work(s) in graph")
        context_parts.append(f"Authored (LKG): {pub_count}")

    # Topic trends (platform-wide)
    try:
        trends = await topic_trends(db, months=6)
        trending_topics = [t["label"] for t in trends[:3] if t.get("label")]
    except Exception:
        trending_topics = []
    if trending_topics:
        context_parts.append(f"Trending topics platform-wide: {', '.join(trending_topics)}")

    if not context_parts:
        return {
            "insights": [{
                "id": "no_graph_data",
                "icon": "info",
                "title": "Not yet in the knowledge graph",
                "text": "Complete your profile and run an ORCID/OpenAlex sync to appear in the Living Knowledge Graph.",
                "source": "Synaptiq LKG",
            }],
            "evidence":  [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    from services.ai.llm import call_llm
    insight_text = await call_llm(
        system=(
            "You generate concise academic insights from knowledge graph data. "
            "ONLY reference data explicitly provided. Never add statistics, predictions, or outcomes not in the data. "
            "Generate up to 5 distinct one-sentence insights."
        ),
        user_msg=(
            f"Researcher in graph:\n" + "\n".join(f"• {c}" for c in context_parts) +
            "\n\nGenerate 5 distinct insights about this researcher's knowledge graph position. "
            "Each insight should be one sentence. Focus on what the graph data reveals about their research network."
        ),
        feature="lkg.insights",
        max_tokens=400,
    )

    # Parse numbered insights
    raw_lines = [l.strip() for l in insight_text.split("\n") if l.strip()]
    insight_list = []
    for i, line in enumerate(raw_lines[:limit]):
        clean = line.lstrip("0123456789.-) ").strip()
        if clean:
            insight_list.append({
                "id":     f"lkg_insight_{i}",
                "icon":   "brain",
                "title":  f"Graph insight {i+1}",
                "text":   clean,
                "source": "Synaptiq LKG database",
            })

    return {
        "insights":     insight_list,
        "evidence":     evidence,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy_note":  "All insights derived from verified LKG data. No invented statistics.",
    }


async def generate_platform_insights(db) -> dict:
    """Platform-wide insights from the Living Knowledge Graph."""
    try:
        stats = {
            "nodes": await db.lkg_nodes.count_documents({}),
            "edges": await db.lkg_edges.count_documents({}),
        }
        trends = await topic_trends(db, months=3)
        density = await collaboration_density(db)
        top_researchers = await degree_centrality(db, node_type="researcher", limit=5)
    except Exception as exc:
        logger.error("Platform insights error: %s", exc)
        return {"insights": [], "error": str(exc)}

    return {
        "graph_size":        stats,
        "emerging_topics":   trends[:5],
        "top_researchers":   top_researchers,
        "collaboration":     density,
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "source":            "Synaptiq LKG database — all figures from graph queries",
    }
