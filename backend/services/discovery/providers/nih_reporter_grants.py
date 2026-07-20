"""NIH RePORTER grants provider — public REST.

API: https://api.reporter.nih.gov/v2/projects/search
This is the modern v2 endpoint that accepts JSON POST with criteria.
"""
from __future__ import annotations

import logging
from typing import Optional

from services.discovery.base import GrantProvider, grant_entity_key, now_iso, parse_iso_date
from services.discovery.http import get_http

logger = logging.getLogger("synaptiq.discovery.nih")

API = "https://api.reporter.nih.gov/v2/projects/search"


class NIHReporterGrantsProvider(GrantProvider):
    name = "nih"

    async def fetch_batch(self, cursor: Optional[str], page_size: int):
        offset = int(cursor or "0")
        size = max(1, min(500, page_size))
        body = {
            "criteria": {
                "advanced_text_search": {
                    "operator": "Or",
                    "search_field": "all",
                    "search_text": "research"
                },
                "exclude_subprojects": True,
            },
            "include_fields": [
                "ProjectNum","ProjectTitle","FiscalYear","Organization","AwardAmount",
                "AwardType","Terms","ProjectStartDate","ProjectEndDate","AgencyIcAdmin",
                "AgencyCode","FundingMechanism","StudySection","Abstract","ProjectDetailUrl",
            ],
            "offset": offset,
            "limit": size,
            "sort_field": "fiscal_year", "sort_order": "desc",
        }
        client = await get_http()
        try:
            r = await client.post(API, json=body)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning("nih fetch failed offset=%s err=%s", offset, e)
            return [], None
        results = data.get("results") or []
        if not results:
            return [], None
        records = []
        for it in results:
            try: records.append(self._normalize(it))
            except Exception as e: logger.warning("nih normalize: %s", e)
        next_offset = offset + len(results)
        return records, str(next_offset) if next_offset < 15_000 else None

    def _normalize(self, p: dict) -> dict:
        title = p.get("project_title") or "NIH research project"
        code = p.get("project_num")
        org = (p.get("organization") or {}).get("org_name")
        ic = (p.get("agency_ic_admin") or {}).get("name") or p.get("agency_code") or "NIH"
        amount = p.get("award_amount")
        try: amount = float(amount) if amount else None
        except Exception: amount = None
        terms = (p.get("terms") or "").split(";") if isinstance(p.get("terms"), str) else (p.get("terms") or [])
        keywords = [t.strip() for t in terms if t and str(t).strip()][:10]
        return {
            "entity_key": grant_entity_key(sponsor="NIH", external_id=str(code or ""), title=title),
            "source": self.name,
            "external_ids": {"nih": code, "nih_appl_id": p.get("appl_id")},
            "title": title,
            "program": p.get("funding_mechanism"),
            "sponsor": "NIH — " + ic if ic else "NIH",
            "sponsor_country": "US",
            "research_areas": keywords[:5],
            "keywords": keywords,
            "funding_amount": {"currency": "USD", "amount": amount, "range_text": None},
            "eligibility": "Eligible US/international institutions per NIH program announcement.",
            "funding_type": "grant",
            "career_stage": "any",
            "country": "US",
            "region": "Americas",
            "open_date": parse_iso_date(p.get("project_start_date")),
            "deadline": parse_iso_date(p.get("project_end_date")),
            "url": p.get("project_detail_url"),
            "status": "open" if (parse_iso_date(p.get("project_end_date")) or "") > now_iso()[:10] else "closed",
            "abstract_text": (p.get("abstract_text") or "")[:1200],
            "last_seen_source_at": now_iso(),
        }
