"""
OpenAlex ingestion connector.

Fetches works matching research topics that are already in the LKG
and adds them as publication nodes with CITED / BELONGS_TO_TOPIC edges.

OpenAlex API is free, no authentication required.
Rate limit: polite pool ~10 req/s (User-Agent with email included).
Docs: https://docs.openalex.org/
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from ..graph_store import upsert_node, upsert_edge
from ..models import LKGNode, LKGEdge, make_node_id
from .base_connector import BaseConnector, IngestionResult

logger = logging.getLogger("lkg.ingestion.openalex")

OPENALEX_WORKS = "https://api.openalex.org/works"
USER_AGENT     = "Synaptiq/1.0 (mailto:admin@synaptiq.ai)"
_SOURCE        = "OpenAlex"


class OpenAlexConnector(BaseConnector):
    name        = "openalex"
    source      = _SOURCE
    description = "Ingests academic publications from OpenAlex matching platform research topics"

    async def ingest(self, db: Any, topics: list[str] | None = None, max_works: int = 200, **kwargs) -> IngestionResult:
        result = IngestionResult(connector=self.name)

        if not topics:
            # Auto-discover topics from LKG
            topic_nodes = await db.lkg_nodes.find(
                {"type": "topic"}, {"label": 1}
            ).limit(10).to_list(10)
            topics = [n["label"] for n in topic_nodes if n.get("label")]

        if not topics:
            result.errors.append("No topics to search — populate LKG topics first via internal connector")
            return result.finish()

        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=30) as client:
            for topic in topics[:5]:  # Limit external calls
                try:
                    await self._ingest_topic(client, db, topic, max_works // len(topics[:5]), result)
                except Exception as exc:
                    result.errors.append(f"topic '{topic}': {exc}")
                    logger.error("[openalex] topic error: %s", exc)

        return result.finish()

    async def _ingest_topic(
        self, client: httpx.AsyncClient, db, topic: str, limit: int, result: IngestionResult
    ) -> None:
        params = {
            "filter":  f"default.search:{topic}",
            "select":  "id,doi,title,publication_year,authorships,primary_location,concepts,cited_by_count",
            "per-page": min(limit, 25),
            "mailto":   "admin@synaptiq.ai",
        }
        try:
            resp = await client.get(OPENALEX_WORKS, params=params)
            resp.raise_for_status()
        except Exception as exc:
            result.errors.append(f"OpenAlex API error for topic '{topic}': {exc}")
            return

        works = resp.json().get("results", [])
        topic_id = make_node_id("topic", "keyword", topic.lower().replace(" ", "_"))

        for work in works:
            doi   = (work.get("doi") or "").replace("https://doi.org/", "").strip()
            title = (work.get("title") or "").strip()
            if not title:
                result.skipped += 1
                continue

            node_id_key = doi if doi else f"openalex_{work.get('id', title[:40])}"
            node_id = make_node_id("publication", "doi" if doi else "openalex", node_id_key)

            pub_node = LKGNode(
                node_id  = node_id,
                type     = "publication",
                label    = title[:200],
                source   = _SOURCE,
                metadata = {
                    "doi":             doi or None,
                    "year":            work.get("publication_year"),
                    "cited_by_count":  work.get("cited_by_count", 0),
                    "openalex_id":     work.get("id"),
                    "venue":           (work.get("primary_location") or {}).get("source", {}).get("display_name") if work.get("primary_location") else None,
                },
                confidence = "high",
            )
            op = await upsert_node(db, pub_node)
            if op and op.upserted_id:
                result.nodes_added += 1
            else:
                result.nodes_updated += 1

            # BELONGS_TO_TOPIC edge
            te = LKGEdge(
                from_id  = node_id,
                to_id    = topic_id,
                type     = "BELONGS_TO_TOPIC",
                source   = _SOURCE,
                status   = "verified",
                metadata = {},
            )
            op = await upsert_edge(db, te)
            if op and op.upserted_id:
                result.edges_added += 1

            # Author nodes + CO_AUTHORED / AUTHORED edges
            authorships = work.get("authorships") or []
            author_node_ids = []
            for authorship in authorships[:5]:
                author = authorship.get("author") or {}
                orcid  = (author.get("orcid") or "").replace("https://orcid.org/", "").strip()
                aname  = (author.get("display_name") or "").strip()
                if not aname:
                    continue
                a_node_id = make_node_id("researcher", "orcid" if orcid else "openalex", orcid or aname.lower().replace(" ", "_"))
                a_node = LKGNode(
                    node_id    = a_node_id,
                    type       = "researcher",
                    label      = aname,
                    source     = _SOURCE,
                    metadata   = {"orcid": orcid or None, "openalex_author_id": author.get("id")},
                    confidence = "high" if orcid else "medium",
                )
                await upsert_node(db, a_node)
                ae = LKGEdge(
                    from_id  = a_node_id,
                    to_id    = node_id,
                    type     = "AUTHORED",
                    source   = _SOURCE,
                    status   = "verified",
                    metadata = {},
                )
                op = await upsert_edge(db, ae)
                if op and op.upserted_id:
                    result.edges_added += 1
                author_node_ids.append(a_node_id)

            # CO_AUTHORED edges between authors of same work
            for i, a1 in enumerate(author_node_ids):
                for a2 in author_node_ids[i + 1:]:
                    ce = LKGEdge(
                        from_id  = a1,
                        to_id    = a2,
                        type     = "CO_AUTHORED",
                        source   = _SOURCE,
                        status   = "verified",
                        metadata = {"publication_node_id": node_id},
                    )
                    op = await upsert_edge(db, ce)
                    if op and op.upserted_id:
                        result.edges_added += 1
