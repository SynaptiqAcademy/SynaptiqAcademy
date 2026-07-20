"""OpenAlex enrichment — fetch citation metrics by ORCID (preferred) or name+institution.

Polite usage: include `mailto` parameter in `User-Agent` per OpenAlex docs.
Doc: https://docs.openalex.org/
"""
from __future__ import annotations
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("synaptiq.reputation.openalex")

OPENALEX_BASE = "https://api.openalex.org"
MAILTO = os.environ.get("OPENALEX_MAILTO", "admin@synaptiq.academy")
HEADERS = {"User-Agent": f"SYNAPTIQ/1.0 (mailto:{MAILTO})"}

# Simple in-memory author-metrics cache (key → (result, expires_at))
# TTL: 6 hours — author stats change slowly; avoids hammering OpenAlex on
# repeated page loads or batch reputation recalculations.
_AUTHOR_CACHE: dict[str, tuple[dict | None, float]] = {}
_CACHE_TTL = 6 * 3600  # 6 hours in seconds


def _normalize_orcid(orcid) -> Optional[str]:
    if not orcid: return None
    # Accept both plain string "0000-..." and dict {"orcid_id": "..."} shapes
    if isinstance(orcid, dict):
        orcid = orcid.get("orcid_id") or ""
    if not orcid: return None
    s = str(orcid).strip().replace("https://orcid.org/", "").replace("http://orcid.org/", "")
    s = s.replace(" ", "").upper()
    # Basic ORCID format: ####-####-####-#### (X allowed as checksum)
    parts = s.split("-")
    if len(parts) == 4 and all(len(p) == 4 for p in parts):
        return s
    return None


async def fetch_author_metrics(*, orcid: Optional[str] = None,
                                full_name: Optional[str] = None,
                                institution: Optional[str] = None) -> Optional[dict]:
    """Return {works_count, citations, h_index, i10_index, openalex_id, last_synced}.

    Resolves the author via ORCID when available, otherwise by best-effort
    name+institution search. Results are cached in-process for 6 hours to
    avoid hammering OpenAlex on repeated calls.
    """
    # Build a stable cache key from the resolution inputs
    norm_orcid = _normalize_orcid(orcid or "")
    cache_key = norm_orcid or f"{(full_name or '').lower()}|{(institution or '').lower()}"

    # Return cached result if still fresh
    if cache_key and cache_key in _AUTHOR_CACHE:
        cached_result, expires_at = _AUTHOR_CACHE[cache_key]
        if time.monotonic() < expires_at:
            logger.debug("OpenAlex author cache hit for key=%s", cache_key[:40])
            return cached_result

    async with httpx.AsyncClient(timeout=10, headers=HEADERS) as cli:
        author = None
        if norm_orcid:
            try:
                r = await cli.get(f"{OPENALEX_BASE}/authors/orcid:{norm_orcid}")
                if r.status_code == 200:
                    author = r.json()
            except Exception as e:
                logger.warning("OpenAlex ORCID lookup failed: %s", e)
        if not author and full_name:
            try:
                params = {"search": full_name, "per_page": 1}
                if institution:
                    params["filter"] = f"affiliations.institution.display_name.search:{institution}"
                r = await cli.get(f"{OPENALEX_BASE}/authors", params=params)
                if r.status_code == 200:
                    results = r.json().get("results") or []
                    if results:
                        author = results[0]
            except Exception as e:
                logger.warning("OpenAlex name search failed: %s", e)

    if not author:
        # Cache negative result for 30 minutes to avoid thundering herd
        if cache_key:
            _AUTHOR_CACHE[cache_key] = (None, time.monotonic() + 1800)
        return None

    stats = author.get("summary_stats") or {}
    result = {
        "works_count":  int(author.get("works_count") or 0),
        "citations":    int(author.get("cited_by_count") or 0),
        "h_index":      int(stats.get("h_index") or 0),
        "i10_index":    int(stats.get("i10_index") or 0),
        "openalex_id":  author.get("id"),
        "display_name": author.get("display_name"),
        "last_synced":  datetime.now(timezone.utc).isoformat(),
    }

    if cache_key:
        _AUTHOR_CACHE[cache_key] = (result, time.monotonic() + _CACHE_TTL)

    return result
