"""UKRI Gateway to Research grants provider.

API: https://gtr.ukri.org/gtr/api/projects?p=N&s=PAGE_SIZE
"""
from __future__ import annotations

import logging
from typing import Optional

from services.discovery.base import GrantProvider, grant_entity_key, now_iso, parse_iso_date
from services.discovery.http import get_http

logger = logging.getLogger("synaptiq.discovery.ukri")

API = "https://gtr.ukri.org/gtr/api/projects"


class UKRIGrantsProvider(GrantProvider):
    name = "ukri"

    async def fetch_batch(self, cursor: Optional[str], page_size: int):
        page = int(cursor or "1")
        size = max(10, min(100, page_size))  # UKRI rejects size < 10
        client = await get_http()
        headers = {"Accept": "application/vnd.rcuk.gtr.json-v7"}
        try:
            r = await client.get(API, params={"p": page, "s": size}, headers=headers)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning("ukri fetch failed page=%s err=%s", page, e)
            return [], None
        projects = data.get("project") or []
        if not projects:
            return [], None
        records = []
        for it in projects:
            try: records.append(self._normalize(it))
            except Exception as e: logger.warning("ukri normalize: %s", e)
        total_pages = int(data.get("totalPages") or 1)
        next_cursor = str(page + 1) if page < min(total_pages, 200) else None
        return records, next_cursor

    def _normalize(self, p: dict) -> dict:
        title = p.get("title") or "UKRI project"
        code = p.get("grantReference")
        funder = p.get("leadFunder") or "UKRI"
        # `funder` may be a string ("EPSRC") or a dict ({"name":..,"id":..}).
        # Same for several other UKRI fields — guard every access.
        funder_block = p.get("funder")
        if isinstance(funder_block, dict):
            funder_full = funder_block.get("name") or funder
        else:
            funder_full = funder if isinstance(funder, str) else "UKRI"
        fund_block = p.get("fund")
        amount = None
        if isinstance(fund_block, dict):
            amount = fund_block.get("valuePounds")
            if isinstance(amount, dict): amount = amount.get("amount")
        try: amount = float(amount) if amount else None
        except Exception: amount = None
        topics_raw = p.get("researchTopics") or []
        if isinstance(topics_raw, dict): topics_raw = topics_raw.get("researchTopic") or []
        if not isinstance(topics_raw, list): topics_raw = []
        research_areas = []
        for t in topics_raw[:5]:
            if isinstance(t, dict) and t.get("text"): research_areas.append(t["text"])
            elif isinstance(t, str): research_areas.append(t)
        href = p.get("href")
        if isinstance(href, list): href = href[0] if href else None
        return {
            "entity_key": grant_entity_key(sponsor=str(funder_full), external_id=str(code or ""), title=title),
            "source": self.name,
            "external_ids": {"ukri": p.get("id"), "ukri_ref": code},
            "title": title if isinstance(title, str) else "UKRI project",
            "program": p.get("grantCategory") if isinstance(p.get("grantCategory"), str) else None,
            "sponsor": str(funder_full),
            "sponsor_country": "GB",
            "research_areas": research_areas,
            "keywords": research_areas,
            "funding_amount": {"currency": "GBP", "amount": amount, "range_text": None},
            "eligibility": "Eligible UK research institutions; check call specifics.",
            "funding_type": "grant",
            "career_stage": "any",
            "country": "GB",
            "region": "Europe",
            "open_date": parse_iso_date(p.get("startDate")),
            "deadline": parse_iso_date(p.get("endDate")),
            "url": href if isinstance(href, str) else None,
            "status": "open" if (parse_iso_date(p.get("endDate")) or "") > now_iso()[:10] else "closed",
            "abstract_text": (p.get("abstractText") or "")[:1200] if isinstance(p.get("abstractText"), str) else "",
            "last_seen_source_at": now_iso(),
        }
