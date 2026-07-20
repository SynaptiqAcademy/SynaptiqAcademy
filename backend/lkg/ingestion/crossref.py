"""
CrossRef DOI connector.

Resolves DOIs from platform manuscripts that don't yet have a publication node,
and from OpenAlex records, adding verified metadata from CrossRef.

No auth required. Polite pool: include email in User-Agent.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from ..graph_store import upsert_node, upsert_edge
from ..models import LKGNode, LKGEdge, make_node_id
from .base_connector import BaseConnector, IngestionResult

logger = logging.getLogger("lkg.ingestion.crossref")

CROSSREF_WORKS = "https://api.crossref.org/works"
MAILTO         = "admin@synaptiq.ai"
_SOURCE        = "CrossRef"
_DOI_RE        = re.compile(r"10\.\d{4,}[^\s\"<>]+")


class CrossRefConnector(BaseConnector):
    name        = "crossref"
    source      = _SOURCE
    description = "Validates and enriches DOIs from manuscripts via CrossRef API"

    async def ingest(self, db: Any, **kwargs) -> IngestionResult:
        result = IngestionResult(connector=self.name)

        # Gather DOIs from manuscripts that have one
        cursor = db.manuscripts.find({"doi": {"$exists": True, "$ne": ""}}, {"_id": 1, "doi": 1, "user_id": 1})
        pairs: list[tuple[str, str, str]] = []
        async for ms in cursor:
            doi = str(ms.get("doi", "")).strip()
            doi = doi.replace("https://doi.org/", "").strip()
            if _DOI_RE.match(doi):
                pairs.append((str(ms["_id"]), doi, str(ms.get("user_id", ""))))

        if not pairs:
            result.skipped = 1
            result.errors.append("No manuscripts with valid DOIs found — nothing to resolve via CrossRef")
            return result.finish()

        async with httpx.AsyncClient(timeout=20) as client:
            for ms_id, doi, uid in pairs[:50]:  # Limit to avoid rate-limiting
                try:
                    await self._resolve_doi(client, db, ms_id, doi, uid, result)
                except Exception as exc:
                    result.errors.append(f"DOI {doi}: {exc}")

        return result.finish()

    async def _resolve_doi(
        self, client: httpx.AsyncClient, db, ms_id: str, doi: str, uid: str, result: IngestionResult
    ) -> None:
        url = f"{CROSSREF_WORKS}/{doi}"
        try:
            resp = await client.get(url, params={"mailto": MAILTO})
            if resp.status_code == 404:
                result.skipped += 1
                return
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            result.skipped += 1
            return

        data  = resp.json().get("message", {})
        title = " ".join(data.get("title") or [""])[:200]
        if not title:
            result.skipped += 1
            return

        node_id = make_node_id("publication", "doi", doi)
        pub_node = LKGNode(
            node_id  = node_id,
            type     = "publication",
            label    = title,
            source   = _SOURCE,
            metadata = {
                "doi":          doi,
                "year":         (data.get("published") or {}).get("date-parts", [[None]])[0][0],
                "journal":      " ".join(data.get("container-title") or [])[:200] or None,
                "publisher":    data.get("publisher"),
                "type":         data.get("type"),
                "crossref_verified": True,
            },
            confidence = "high",  # CrossRef is a trusted DOI registry
        )
        op = await upsert_node(db, pub_node)
        if op and op.upserted_id:
            result.nodes_added += 1
        else:
            result.nodes_updated += 1

        # Link the internal manuscript to this publication node
        ms_node_id = make_node_id("manuscript", "platform", ms_id)
        link_edge = LKGEdge(
            from_id  = ms_node_id,
            to_id    = node_id,
            type     = "PUBLISHED_AS",
            source   = _SOURCE,
            status   = "verified",
            metadata = {"doi": doi},
        )
        op = await upsert_edge(db, link_edge)
        if op and op.upserted_id:
            result.edges_added += 1

        # Author nodes from CrossRef
        for author in (data.get("author") or [])[:5]:
            given  = (author.get("given") or "").strip()
            family = (author.get("family") or "").strip()
            orcid  = (author.get("ORCID") or "").replace("http://orcid.org/", "").replace("https://orcid.org/", "").strip()
            aname  = f"{given} {family}".strip()
            if not aname:
                continue

            a_id_key = orcid if orcid else aname.lower().replace(" ", "_")
            a_node_id = make_node_id("researcher", "orcid" if orcid else "crossref", a_id_key)
            a_node = LKGNode(
                node_id    = a_node_id,
                type       = "researcher",
                label      = aname,
                source     = _SOURCE,
                metadata   = {"orcid": orcid or None},
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
