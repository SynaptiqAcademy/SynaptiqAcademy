"""Discovery engine — uncovers non-obvious connections from LKG graph structure."""
from __future__ import annotations

import logging
from typing import Optional

from .reasoning import infer_collaborations

logger = logging.getLogger("lkg.discovery")


async def discover_hidden_collaborations(db, user_id: str, limit: int = 10) -> dict:
    """
    Find researchers this user is NOT connected to but shares a common collaborator with.
    Uses friend-of-friend reasoning from the LKG.
    All results labeled 'inferred' — never presented as verified connections.
    """
    node_id   = f"researcher:platform:{user_id}"
    inferred  = await infer_collaborations(db, limit=500)

    user_results = [
        r for r in inferred
        if r["from_id"] == node_id or r["to_id"] == node_id
    ][:limit]

    enriched = []
    for r in user_results:
        other_id = r["to_id"] if r["from_id"] == node_id else r["from_id"]
        other_node = await db.lkg_nodes.find_one({"node_id": other_id}, {"_id": 0})
        via_node   = await db.lkg_nodes.find_one({"node_id": r.get("via")}, {"_id": 0}) if r.get("via") else None
        enriched.append({
            "other_researcher": other_node,
            "via_collaborator":  via_node,
            "confidence":        "low",
            "status":            "inferred",
            "reasoning":         f"Both are connected to {via_node.get('label', r.get('via', '?')) if via_node else '?'} in the knowledge graph",
            "evidence":          [{"type": "graph_inference", "source": "Synaptiq LKG", "detail": "Friend-of-friend graph pattern"}],
        })

    return {
        "user_node_id": node_id,
        "discoveries":  enriched,
        "count":        len(enriched),
        "method":       "Friend-of-friend inference from CO_AUTHORED and COLLABORATES_WITH edges",
        "status_note":  "All results are INFERRED — not verified collaborations. Users should evaluate relevance independently.",
        "source":       "Synaptiq LKG reasoning engine",
    }


async def discover_emerging_topics(db, user_id: Optional[str] = None) -> dict:
    """
    Identify research topics growing fastest in the graph.
    If user_id is given, also check overlap with their research interests.
    """
    from .analytics import topic_trends

    trends = await topic_trends(db, months=6)
    top_growing = [t for t in trends if t.get("growth_rate", 0) > 0.5][:10]

    user_overlap = []
    if user_id:
        node_id = f"researcher:platform:{user_id}"
        user_topics = await db.lkg_edges.find(
            {"from_id": node_id, "type": "BELONGS_TO_TOPIC"}, {"to_id": 1}
        ).to_list(20)
        user_topic_ids = {e["to_id"] for e in user_topics}

        for t in top_growing:
            if t["topic_id"] in user_topic_ids:
                user_overlap.append(t)

    return {
        "emerging_topics":      top_growing,
        "overlapping_with_user": user_overlap,
        "count":                len(top_growing),
        "method":               "Topics with highest recent_90d / older growth ratio in LKG",
        "source":               "Synaptiq LKG database — verified graph edges only",
        "status_note":          "Growth rates are computed from platform graph data, not external citations.",
    }


async def discover_funding_opportunities(db, user_id: str) -> dict:
    """
    Find funding programs connected to topics this researcher works on.
    Looks for FUNDED_BY and RELATED_TO edges in the graph.
    All opportunities from verified LKG records.
    """
    node_id = f"researcher:platform:{user_id}"
    topic_edges = await db.lkg_edges.find(
        {"from_id": node_id, "type": "BELONGS_TO_TOPIC"}, {"to_id": 1}
    ).to_list(10)
    topic_ids = [e["to_id"] for e in topic_edges]

    if not topic_ids:
        return {
            "opportunities": [],
            "message": "No research topics found in graph. Connect your ORCID or add research interests to your profile.",
            "source": "Synaptiq LKG",
        }

    # Find funding programs related to these topics
    funding_edges = await db.lkg_edges.find(
        {"to_id": {"$in": topic_ids}, "type": {"$in": ["FUNDED_BY", "RELATED_TO"]}},
        {"from_id": 1, "type": 1}
    ).limit(20).to_list(20)

    funding_ids = [e["from_id"] for e in funding_edges
                   if e["from_id"].startswith("funding_program:")]

    if not funding_ids:
        return {
            "opportunities": [],
            "message": "No funding programs found in graph for your research topics. Run the grants ingestion pipeline to populate this.",
            "source": "Synaptiq LKG",
        }

    funding_nodes = await db.lkg_nodes.find(
        {"node_id": {"$in": funding_ids}}, {"_id": 0}
    ).to_list(10)

    return {
        "opportunities": funding_nodes,
        "count":         len(funding_nodes),
        "topic_ids":     topic_ids,
        "method":        "Graph traversal: researcher → topics → funding_programs via FUNDED_BY/RELATED_TO edges",
        "source":        "Synaptiq LKG database — verified graph records",
    }


async def discover_potential_reviewers(db, manuscript_id: str) -> dict:
    """
    Find researchers whose graph topics overlap with a manuscript's topics.
    Labeled as 'candidate' — not assigned or confirmed.
    """
    ms_id = f"manuscript:platform:{manuscript_id}"
    ms_topics = await db.lkg_edges.find(
        {"from_id": ms_id, "type": "BELONGS_TO_TOPIC"}, {"to_id": 1}
    ).to_list(5)
    topic_ids = [e["to_id"] for e in ms_topics]

    if not topic_ids:
        return {
            "reviewers": [],
            "message": "Manuscript not yet in knowledge graph or has no topics assigned.",
            "source": "Synaptiq LKG",
        }

    # Researchers connected to same topics (who didn't author this manuscript)
    authors = {
        e["from_id"] for e in
        await db.lkg_edges.find({"to_id": ms_id, "type": "AUTHORED"}, {"from_id": 1}).to_list(10)
    }

    reviewer_edges = await db.lkg_edges.find(
        {"to_id": {"$in": topic_ids}, "type": "BELONGS_TO_TOPIC",
         "from_id": {"$nin": list(authors), "$regex": "^researcher:"}},
        {"from_id": 1}
    ).limit(20).to_list(20)

    reviewer_ids = list({e["from_id"] for e in reviewer_edges})
    reviewer_nodes = await db.lkg_nodes.find(
        {"node_id": {"$in": reviewer_ids}}, {"_id": 0}
    ).to_list(10)

    return {
        "reviewers":    reviewer_nodes,
        "count":        len(reviewer_nodes),
        "topics_used":  topic_ids,
        "status_note":  "CANDIDATE reviewers only — topic overlap detected, no conflicts checked, no invitation sent.",
        "method":       "Graph traversal: manuscript → topics → researchers with topic overlap",
        "source":       "Synaptiq LKG database",
    }
