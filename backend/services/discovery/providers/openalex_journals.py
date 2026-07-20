"""OpenAlex journals provider.

OpenAlex (https://docs.openalex.org) is a CC0 successor to Microsoft Academic
Graph. It exposes ~250k journals (called "sources" of type=journal) with rich
metadata: ISSN-L, subjects (concepts), open-access flags, APC, h-index, etc.

API entry:
    GET https://api.openalex.org/sources?filter=type:journal&per-page=200&cursor=*

Cursor pagination is recommended for deep listings (we use cursor=*).

We sort by works_count:desc so the first ~50k records cover the most-used
journals (long-tail can be filled later via secondary cursor).
"""
from __future__ import annotations

import logging
from typing import Optional

from services.discovery.base import (
    JournalProvider, journal_entity_key, normalize_issn, now_iso, slug,
)
from services.discovery.http import fetch_json

logger = logging.getLogger("synaptiq.discovery.openalex")

API = "https://api.openalex.org/sources"


def _oa_status_from_apc(is_oa: bool, apc_usd: Optional[int]) -> Optional[str]:
    if not is_oa: return None
    if apc_usd in (None, 0): return "diamond"
    return "gold"


def _quartile_from_2yr(mean: float | None) -> Optional[str]:
    """Approximate quartile from 2-year mean citedness when SJR/JCR are unavailable.
    This is a coarse heuristic and is clearly marked as "openalex_estimate" in the UI.
    """
    if mean is None: return None
    if mean >= 4.0: return "Q1"
    if mean >= 2.0: return "Q2"
    if mean >= 1.0: return "Q3"
    if mean > 0.0: return "Q4"
    return None


class OpenAlexJournalsProvider(JournalProvider):
    name = "openalex"

    async def fetch_batch(self, cursor: Optional[str], page_size: int):
        params = {
            "filter": "type:journal,works_count:>5",
            "per-page": str(max(1, min(200, page_size))),
            "cursor": cursor or "*",
            "sort": "works_count:desc",
            "select": (
                "id,display_name,issn_l,issn,country_code,"
                "is_oa,apc_usd,homepage_url,host_organization_name,"
                "works_count,cited_by_count,summary_stats,"
                "topics,abbreviated_title"
            ),
        }
        data = await fetch_json(API, params=params)
        if not data or "results" not in data:
            return [], None
        records: list[dict] = []
        for r in data["results"]:
            try:
                records.append(self._normalize(r))
            except Exception as e:
                logger.warning("normalize failed id=%s err=%s", r.get("id"), e)
        next_cursor = (data.get("meta") or {}).get("next_cursor")
        return records, next_cursor

    def _normalize(self, r: dict) -> dict:
        title = r.get("display_name") or r.get("abbreviated_title") or "Untitled"
        issn_l = normalize_issn(r.get("issn_l") or "")
        issns = [normalize_issn(i) for i in (r.get("issn") or []) if i]
        issns = [i for i in issns if i]
        publisher = r.get("host_organization_name") or ""
        is_oa = bool(r.get("is_oa"))
        apc_usd = r.get("apc_usd")
        topics = r.get("topics") or []
        # Build hierarchical subject lists from OpenAlex topics
        fields = list({(t.get("field") or {}).get("display_name") for t in topics if (t.get("field") or {}).get("display_name")})
        subfields = list({(t.get("subfield") or {}).get("display_name") for t in topics if (t.get("subfield") or {}).get("display_name")})
        topic_names = [t.get("display_name") for t in topics[:5] if t.get("display_name")]
        subjects = (fields + subfields)[:8]
        mean_2yr = (r.get("summary_stats") or {}).get("2yr_mean_citedness")
        h = int((r.get("summary_stats") or {}).get("h_index") or 0)
        works = int(r.get("works_count") or 0)
        cites = int(r.get("cited_by_count") or 0)
        # popularity_score: comparable across journals
        import math
        pop = round(math.log10(works + 1) * 2 + math.log10(cites + 1) + h / 20.0, 3)
        return {
            "entity_key": journal_entity_key(issn_l=issn_l, issns=issns, title=title, publisher=publisher),
            "source": self.name,
            "external_ids": {"openalex": r.get("id"), "issn_l": issn_l, "issns": issns},
            "title": title,
            "publisher": publisher,
            "country": r.get("country_code"),
            "language": None,
            "subjects": subjects,
            "research_areas": fields[:3],
            "scope_keywords": topic_names,
            "open_access": is_oa,
            "oa_status": _oa_status_from_apc(is_oa, apc_usd),
            "apc_usd": apc_usd,
            "has_apc": bool(apc_usd),
            "quartile": _quartile_from_2yr(mean_2yr),
            "quartile_source": "openalex_estimate" if mean_2yr else None,
            "h_index": h,
            "works_count": works,
            "cited_by_count": cites,
            "mean_citedness_2yr": mean_2yr,
            "homepage_url": r.get("homepage_url"),
            "submission_url": None,
            "review_time_weeks": None,
            "acceptance_rate": None,
            "popularity_score": pop,
            "last_seen_source_at": now_iso(),
        }
