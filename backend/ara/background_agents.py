"""
Background Monitor Agents — persistent watches that run outside user-initiated missions.

Monitors:
  - publication_monitor:  new papers matching researcher topics (OpenAlex)
  - citation_monitor:     citations to researcher's own work
  - grant_monitor:        new funding opportunities
  - conference_monitor:   upcoming deadlines in researcher domains
  - trend_monitor:        emerging topic shifts in LKG

Each monitor produces an alert dict stored in ara_logs (event="monitor_alert").
These are surfaced on the AgentWorkforce dashboard under "Background Monitors".

NOTE: Monitors only read data. They NEVER send emails, submit anything, or modify records.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from repo.shim import make_db_proxy

logger = logging.getLogger("ara.monitors")


# ── Alert builder ──────────────────────────────────────────────────────────────

def _alert(monitor: str, title: str, body: str, data: dict,
           evidence: list[dict]) -> dict:
    return {
        "monitor":    monitor,
        "title":      title,
        "body":       body,
        "data":       data,
        "evidence":   evidence,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Publication monitor ────────────────────────────────────────────────────────

async def run_publication_monitor(db, user_id: str, topics: list[str]) -> list[dict]:
    """
    Check OpenAlex for recent publications in researcher's topics.
    Returns alerts (does NOT store them — caller stores via append_log).
    """
    if not topics:
        return []

    import httpx
    alerts = []
    for topic in topics[:3]:  # limit to avoid rate-limiting
        url = "https://api.openalex.org/works"
        params = {
            "search":       topic,
            "filter":       "from_publication_date:2024-01-01",
            "sort":         "cited_by_count:desc",
            "per-page":     5,
            "mailto":       "admin@synaptiq.academy",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    alerts.append(_alert(
                        "publication_monitor",
                        f"New publications: {topic}",
                        f"Found {len(results)} recent papers on '{topic}'",
                        {"topic": topic, "count": len(results),
                         "top_title": results[0].get("title", "")},
                        [{"source": "OpenAlex API", "type": "api_response",
                          "note": f"{len(results)} results for '{topic}'"}],
                    ))
        except Exception as exc:
            logger.warning("publication_monitor error for topic '%s': %s", topic, exc)

    return alerts


# ── Grant monitor ─────────────────────────────────────────────────────────────

async def run_grant_monitor(db, user_id: str) -> list[dict]:
    """Check platform grants DB for deadlines in the next 30 days."""
    db = make_db_proxy(db, system=True)
    from datetime import timedelta
    alerts = []
    try:
        now     = datetime.now(timezone.utc)
        cutoff  = now + timedelta(days=30)
        grants  = await db["grants"].find({
            "deadline": {"$gte": now, "$lte": cutoff},
        }, {"title": 1, "deadline": 1, "amount": 1}).to_list(10)

        if grants:
            alerts.append(_alert(
                "grant_monitor",
                f"{len(grants)} grant deadline(s) in 30 days",
                "Funding opportunities with upcoming deadlines",
                {"grants": [{"title": g.get("title"), "deadline": str(g.get("deadline"))}
                             for g in grants]},
                [{"source": "Synaptiq grants DB", "type": "database_query",
                  "note": f"{len(grants)} grants with deadline ≤ 30 days"}],
            ))
    except Exception as exc:
        logger.warning("grant_monitor error: %s", exc)

    return alerts


# ── Trend monitor ─────────────────────────────────────────────────────────────

async def run_trend_monitor(db, user_id: str) -> list[dict]:
    """
    Detect emerging topics in LKG that the researcher is not yet connected to.
    Returns up to 3 alerts.
    """
    db = make_db_proxy(db, system=True)
    alerts = []
    try:
        from bson import ObjectId
        # Most connected topic nodes added in last 90 days
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        hot_topics = await db["lkg_nodes"].find(
            {"type": "topic", "created_at": {"$gte": cutoff}},
            {"id": 1, "label": 1},
        ).sort("degree", -1).limit(5).to_list(5)

        # Check which ones the user is NOT connected to
        user_node_id = f"researcher:internal:{user_id}"
        connected_topics = set()
        async for edge in db["lkg_edges"].find(
            {"from_id": user_node_id, "to_type": "topic"}, {"to_id": 1}
        ):
            connected_topics.add(edge["to_id"])

        new_topics = [t for t in hot_topics if t.get("id") not in connected_topics]
        if new_topics:
            alerts.append(_alert(
                "trend_monitor",
                f"{len(new_topics)} emerging topic(s) in your field",
                "New knowledge graph topics not yet in your profile",
                {"topics": [t.get("label") for t in new_topics]},
                [{"source": "Synaptiq LKG", "type": "graph_analysis",
                  "note": f"{len(new_topics)} unconnected emerging topics"}],
            ))
    except Exception as exc:
        logger.warning("trend_monitor error: %s", exc)

    return alerts


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def run_all_monitors(db, user_id: str, user: dict) -> list[dict]:
    """
    Run all background monitors for a user.
    Returns flat list of alerts; caller decides what to store.
    """
    topics = user.get("research_interests") or []
    if isinstance(topics, str):
        topics = [t.strip() for t in topics.split(",") if t.strip()]

    results = []
    for coro in [
        run_publication_monitor(db, user_id, topics),
        run_grant_monitor(db, user_id),
        run_trend_monitor(db, user_id),
    ]:
        try:
            results.extend(await coro)
        except Exception as exc:
            logger.error("Monitor run error: %s", exc)

    return results
