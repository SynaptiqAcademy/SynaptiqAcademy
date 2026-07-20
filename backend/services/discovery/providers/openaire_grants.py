"""OpenAIRE grants provider.

OpenAIRE Graph Search API: https://graph.openaire.eu/docs/apis/search-api/

Endpoint:
    GET https://api.openaire.eu/search/projects?format=json&size=100&page=N

Returns funded projects from EU FP7/H2020/Horizon Europe + many national
agencies federated under OpenAIRE.
"""
from __future__ import annotations

import logging
from typing import Optional

from services.discovery.base import GrantProvider, grant_entity_key, now_iso, parse_iso_date, parse_year

from services.discovery.http import fetch_json

logger = logging.getLogger("synaptiq.discovery.openaire")

API = "https://api.openaire.eu/search/projects"


def _g(rec: dict, *path):
    cur = rec
    for k in path:
        if isinstance(cur, list): cur = cur[0] if cur else None
        if cur is None: return None
        cur = (cur or {}).get(k)
    return cur


class OpenAIREGrantsProvider(GrantProvider):
    name = "openaire"

    async def fetch_batch(self, cursor: Optional[str], page_size: int):
        page = int(cursor or "1")
        size = max(1, min(50, page_size))
        params = {"format": "json", "size": size, "page": page,
                  "sortBy": "projectstartdate,descending"}
        data = await fetch_json(API, params=params)
        if not data:
            return [], None
        # OpenAIRE returns response.results.result[].metadata.oaf:entity.oaf:project
        results = (((data or {}).get("response") or {}).get("results") or {}).get("result") or []
        records = []
        for r in results:
            try:
                rec = self._normalize(r)
                if rec: records.append(rec)
            except Exception as e:
                logger.warning("openaire normalize: %s", e)
        next_cursor = str(page + 1) if results else None
        return records, next_cursor

    def _normalize(self, raw: dict) -> Optional[dict]:
        meta = ((raw or {}).get("metadata") or {}).get("oaf:entity") or {}
        proj = meta.get("oaf:project") or {}
        if not proj:
            return None
        title = _g(proj, "title") or "Untitled project"
        if isinstance(title, dict): title = title.get("$") or "Untitled"
        code = _g(proj, "code")
        funder_block = _g(proj, "fundingtree") or {}
        sponsor = _g(funder_block, "funder", "name") or _g(funder_block, "funder") or "Funder"
        if isinstance(sponsor, dict): sponsor = sponsor.get("name") or "Funder"
        country = _g(funder_block, "funder", "jurisdiction")
        if isinstance(country, dict): country = country.get("$")
        program = _g(funder_block, "funding_level_0", "name") or _g(funder_block, "name")
        if isinstance(program, dict): program = program.get("$")
        start_raw = _g(proj, "startdate"); end_raw = _g(proj, "enddate")
        if isinstance(start_raw, dict): start_raw = start_raw.get("$")
        if isinstance(end_raw, dict): end_raw = end_raw.get("$")
        amount = _g(proj, "totalcost")
        if isinstance(amount, dict): amount = amount.get("$")
        try: amount = float(amount) if amount else None
        except Exception: amount = None
        currency = _g(proj, "currency") or "EUR"
        if isinstance(currency, dict): currency = currency.get("$") or "EUR"
        keywords_raw = _g(proj, "keywords") or ""
        if isinstance(keywords_raw, dict): keywords_raw = keywords_raw.get("$") or ""
        keywords = [k.strip() for k in str(keywords_raw).split(",") if k.strip()][:10]
        summary = _g(proj, "summary")
        if isinstance(summary, dict): summary = summary.get("$") or ""
        title_str = title if isinstance(title, str) else (title.get("$") if isinstance(title, dict) else "")
        return {
            "entity_key": grant_entity_key(sponsor=str(sponsor), external_id=str(code or ""), title=title_str),
            "source": self.name,
            "external_ids": {"openaire": code, "oaf_id": raw.get("header", {}).get("dri:objIdentifier")},
            "title": title_str,
            "program": program if isinstance(program, str) else None,
            "sponsor": str(sponsor),
            "sponsor_country": country if isinstance(country, str) else None,
            "research_areas": keywords[:5],
            "keywords": keywords,
            "funding_amount": {"currency": str(currency).upper() if currency else "EUR",
                                "amount": amount, "range_text": None},
            "eligibility": None,
            "funding_type": "consortium",
            "career_stage": "any",
            "country": country if isinstance(country, str) else None,
            "region": "EU" if country in (None,) else None,
            "open_date": parse_iso_date(start_raw),
            "deadline": parse_iso_date(end_raw),
            "url": None,
            "status": "open" if end_raw and parse_iso_date(end_raw) and parse_iso_date(end_raw) > now_iso()[:10] else "closed",
            "summary": (summary or "")[:600],
            "last_seen_source_at": now_iso(),
        }
