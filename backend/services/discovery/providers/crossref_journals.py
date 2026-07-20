"""Crossref journals provider — back-fill ISSN-L from the public REST API.

Crossref Journal REST: GET https://api.crossref.org/journals?rows=1000&offset=N
"""
from __future__ import annotations

import logging
from typing import Optional

from services.discovery.base import (
    JournalProvider, journal_entity_key, normalize_issn, now_iso,
)
from services.discovery.http import fetch_json

logger = logging.getLogger("synaptiq.discovery.crossref")

API = "https://api.crossref.org/journals"


class CrossrefJournalsProvider(JournalProvider):
    name = "crossref"
    enabled_by_default = False

    async def fetch_batch(self, cursor: Optional[str], page_size: int):
        rows = max(1, min(1000, page_size))
        offset = int(cursor or "0")
        params = {"rows": rows, "offset": offset}
        data = await fetch_json(API, params=params)
        if not data or (data.get("status") != "ok"):
            return [], None
        items = (data.get("message") or {}).get("items") or []
        if not items:
            return [], None
        records = []
        for it in items:
            try:
                records.append(self._normalize(it))
            except Exception as e:
                logger.warning("crossref normalize failed: %s", e)
        next_offset = offset + len(items)
        # Crossref total-results is large; stop at 30k offsets to respect rate limits.
        next_cursor = str(next_offset) if next_offset < 30_000 else None
        return records, next_cursor

    def _normalize(self, it: dict) -> dict:
        title = it.get("title") or "Untitled"
        publisher = it.get("publisher") or ""
        issns = [normalize_issn(i) for i in it.get("ISSN") or [] if i]
        issns = [i for i in issns if i]
        issn_l = issns[0] if issns else None
        subjects = it.get("subjects") or []
        return {
            "entity_key": journal_entity_key(issn_l=issn_l, issns=issns, title=title, publisher=publisher),
            "source": self.name,
            "external_ids": {"crossref": it.get("id"), "issn_l": issn_l, "issns": issns},
            "title": title,
            "publisher": publisher,
            "country": None,
            "subjects": subjects[:6],
            "research_areas": subjects[:3],
            "last_seen_source_at": now_iso(),
        }
