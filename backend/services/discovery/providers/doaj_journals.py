"""DOAJ journals provider (Directory of Open Access Journals).

DOAJ Public Data API: https://doaj.org/api/v3/docs
Endpoint: GET https://doaj.org/api/v3/search/journals/*?page=N&pageSize=100

DOAJ adds vetted OA status + APC + subject classification for ~21k OA journals.
We use it primarily as a *back-fill* — OpenAlex remains the bulk source.
"""
from __future__ import annotations

import logging
from typing import Optional

from services.discovery.base import (
    JournalProvider, journal_entity_key, normalize_issn, now_iso,
)
from services.discovery.http import fetch_json

logger = logging.getLogger("synaptiq.discovery.doaj")

API = "https://doaj.org/api/v3/search/journals/*"


class DOAJJournalsProvider(JournalProvider):
    name = "doaj"
    enabled_by_default = False  # opt-in to keep ingest predictable

    async def fetch_batch(self, cursor: Optional[str], page_size: int):
        page = int(cursor or "1")
        params = {"page": page, "pageSize": max(1, min(100, page_size))}
        data = await fetch_json(API, params=params)
        if not data or "results" not in data:
            return [], None
        records = []
        for hit in data["results"]:
            try:
                records.append(self._normalize(hit))
            except Exception as e:
                logger.warning("doaj normalize failed id=%s err=%s", hit.get("id"), e)
        next_page = page + 1 if data.get("next") else None
        return records, str(next_page) if next_page else None

    def _normalize(self, hit: dict) -> dict:
        b = hit.get("bibjson") or {}
        title = b.get("title") or "Untitled"
        issns = []
        for ident in b.get("identifier") or []:
            if ident.get("type") in ("eissn", "pissn") and ident.get("id"):
                issns.append(normalize_issn(ident["id"]))
        issns = [i for i in issns if i]
        issn_l = issns[0] if issns else None
        publisher = (b.get("publisher") or {}).get("name") or ""
        country = (b.get("publisher") or {}).get("country")
        apc_block = b.get("apc") or {}
        apc_usd = None
        if apc_block.get("has_apc") and apc_block.get("max"):
            mx = apc_block["max"]
            if isinstance(mx, list) and mx and isinstance(mx[0], dict):
                apc_usd = mx[0].get("price")
        subjects = [s.get("term") for s in b.get("subject") or [] if s.get("term")]
        return {
            "entity_key": journal_entity_key(issn_l=issn_l, issns=issns, title=title, publisher=publisher),
            "source": self.name,
            "external_ids": {"doaj": hit.get("id"), "issn_l": issn_l, "issns": issns},
            "title": title,
            "publisher": publisher,
            "country": country,
            "language": (b.get("language") or [None])[0],
            "subjects": subjects[:6],
            "research_areas": subjects[:3],
            "scope_keywords": b.get("keywords") or [],
            "open_access": True,
            "oa_status": "diamond" if (apc_block.get("has_apc") is False) else "gold",
            "apc_usd": apc_usd,
            "has_apc": bool(apc_block.get("has_apc")),
            "homepage_url": (b.get("ref") or {}).get("journal"),
            "submission_url": (b.get("ref") or {}).get("author_instructions"),
            "last_seen_source_at": now_iso(),
        }
