"""WikiCFP conferences provider — paginated RSS feeds by topic.

WikiCFP (http://www.wikicfp.com) publishes RSS feeds per category and per
search. There is no documented JSON API; the RSS feeds are stable and the
public-facing entry points are intended to be machine-readable.

Strategy:
  1. Walk a curated list of categories (Computer Science, Engineering, Medicine,
     Social Sciences, Humanities, ...) — WikiCFP exposes feeds by category id.
  2. For each category, walk pages until the feed returns empty / repeats.
  3. Parse with `feedparser` (already installed).

The records carry submission deadline, conference dates, and topics extracted
from the entry summary.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import feedparser

from services.discovery.base import (
    ConferenceProvider, conference_entity_key, now_iso, parse_iso_date, parse_year, slug,
)
from services.discovery.http import fetch_text

logger = logging.getLogger("synaptiq.discovery.wikicfp")

# Curated category IDs from WikiCFP. Each category page exposes an "Active CFPs"
# RSS feed at /cfp/rss?cat=NAME&page=N
CATEGORIES = [
    "computer science", "engineering", "data mining", "machine learning",
    "artificial intelligence", "computer vision", "natural language processing",
    "robotics", "networking", "software engineering", "human-computer interaction",
    "security", "cryptography", "databases", "distributed systems",
    "cloud computing", "big data", "image processing", "signal processing",
    "communications", "bioinformatics", "biotechnology", "biomedical",
    "medicine", "health informatics", "public health",
    "physics", "chemistry", "mathematics", "statistics", "operations research",
    "psychology", "education", "social sciences", "economics", "finance",
    "management", "marketing", "law", "linguistics", "philosophy",
    "renewable energy", "environment", "climate", "ecology", "agriculture",
    "civil engineering", "mechanical engineering", "materials science",
    "nanotechnology", "remote sensing",
]


def _extract_dates(summary: str) -> dict:
    """Pull location + start/end dates out of WikiCFP RSS summary.

    The RSS summary uses the compact form:
        "<canonical name> [<location>] [<start_date> - <end_date>]"
    Submission deadlines / camera-ready dates are NOT exposed in the RSS;
    they require an HTML follow-up which is scrape-only and respected for
    now (we leave those fields null).
    """
    out: dict = {}
    # bracketed segments
    brackets = re.findall(r"\[([^\]]+)\]", summary or "")
    # Location is the first non-date bracket
    for b in brackets:
        looks_like_date = re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d", b)
        if not looks_like_date and "location" not in out:
            out["location"] = b.strip()
            break
    # Find the date-range bracket
    for b in brackets:
        m = re.search(r"([A-Z][a-z]+\s+\d{1,2},\s*\d{4})\s*-\s*([A-Z][a-z]+\s+\d{1,2},\s*\d{4})", b)
        if m:
            s = parse_iso_date(m.group(1)); e = parse_iso_date(m.group(2))
            if s: out["start_date"] = s
            if e: out["end_date"] = e
            break
        m2 = re.search(r"([A-Z][a-z]+\s+\d{1,2},\s*\d{4})", b)
        if m2:
            s = parse_iso_date(m2.group(1))
            if s: out["start_date"] = s
            break
    return out


def _parse_acronym_year(title: str) -> tuple[Optional[str], Optional[int]]:
    # "ICML 2025 : 41st Intl Conf on Machine Learning"
    m = re.match(r"^([A-Z][A-Z0-9\-]+)\s+(\d{4})", title)
    if m: return m.group(1), int(m.group(2))
    # "FOSE 2025 The ..."
    m = re.match(r"^([A-Z][A-Za-z0-9\-]{1,12})\s+(\d{4})", title)
    if m: return m.group(1), int(m.group(2))
    return None, parse_year(title)


class WikiCFPConferencesProvider(ConferenceProvider):
    name = "wikicfp"

    async def fetch_batch(self, cursor: Optional[str], page_size: int):
        """Cursor = 'cat_idx' — one category per call (WikiCFP RSS doesn't paginate)."""
        cat_idx = int(cursor or "0")
        if cat_idx >= len(CATEGORIES):
            return [], None
        category = CATEGORIES[cat_idx]
        url = "http://www.wikicfp.com/cfp/rss"
        params = {"cat": category}
        xml = await fetch_text(url, params=params)
        next_cursor = str(cat_idx + 1) if cat_idx + 1 < len(CATEGORIES) else None
        if not xml:
            return [], next_cursor
        parsed = feedparser.parse(xml)
        entries = parsed.get("entries") or []
        records: list[dict] = []
        for e in entries:
            try:
                rec = self._normalize(e, category=category)
                if rec: records.append(rec)
            except Exception as exc:
                logger.warning("wikicfp normalize failed: %s", exc)
        return records, next_cursor

    def _normalize(self, e: dict, *, category: str) -> Optional[dict]:
        title = (e.get("title") or "").strip()
        if not title: return None
        acro, year = _parse_acronym_year(title)
        summary = e.get("summary") or ""
        dates = _extract_dates(summary)
        link = e.get("link") or ""
        # canonicalize name: drop "ACRO YYYY :" prefix
        name = re.sub(r"^[A-Z][A-Z0-9\-]+\s+\d{4}\s*:?\s*", "", title).strip() or title
        if not year and "submission_deadline" in dates:
            year = parse_year(dates["submission_deadline"])
        return {
            "entity_key": conference_entity_key(acronym=acro, year=year, name=name),
            "source": self.name,
            "external_ids": {"wikicfp": link, "wikicfp_guid": e.get("id")},
            "name": name,
            "acronym": acro,
            "year": year,
            "organizer": None,
            "research_areas": [category.title()],
            "topics": dates.get("topics") or [],
            "rank": None, "rank_source": None,
            "location": dates.get("location"),
            "country": None,
            "format": None,
            "submission_deadline": dates.get("submission_deadline"),
            "notification_date": dates.get("notification_date"),
            "camera_ready_date": dates.get("camera_ready_date"),
            "start_date": dates.get("start_date"),
            "end_date": dates.get("end_date"),
            "website": link,
            "cfp_url": link,
            "last_seen_source_at": now_iso(),
        }
