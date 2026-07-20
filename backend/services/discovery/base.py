"""SYNAPTIQ Discovery Suite — provider abstraction.

Every external data source (OpenAlex, Crossref, DOAJ, WikiCFP, OpenAIRE, ...)
implements one of the three base classes below. The IngestRunner pulls batches
via `fetch_batch(...)` until exhausted or until `max_records` is hit.

Each batch returns *normalized* records — already in SYNAPTIQ canonical schema
shape. Normalization stays inside the provider so the runner has no source-
specific knowledge.

Provider contract:
    fetch_batch(cursor, page_size) -> (records: list[dict], next_cursor: str|None)

Every normalized record MUST include:
    - "entity_key": deterministic dedup key (see resolve_entity_key)
    - "source": provider.name
    - "external_ids": dict of stable IDs
"""
from __future__ import annotations

import logging
import re
import unicodedata
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("synaptiq.discovery.base")


# ---------------------------------- helpers ----------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(text: str) -> str:
    if not text: return ""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t.lower()).strip("-")
    return t[:120]


def normalize_issn(s: str) -> Optional[str]:
    if not s: return None
    s = re.sub(r"[^0-9Xx]", "", s).upper()
    if len(s) == 8: return f"{s[:4]}-{s[4:]}"
    return None


def parse_year(value) -> Optional[int]:
    try:
        if isinstance(value, int): return value if 1800 < value < 2100 else None
        if isinstance(value, str):
            m = re.search(r"(19|20)\d{2}", value)
            if m: return int(m.group(0))
    except Exception:
        return None
    return None


def parse_iso_date(value) -> Optional[str]:
    """Best-effort ISO date extractor."""
    if not value: return None
    if isinstance(value, str):
        # Already ISO or close to it
        m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", value)
        if m:
            y, mo, d = m.groups()
            try:
                return datetime(int(y), int(mo), int(d), tzinfo=timezone.utc).date().isoformat()
            except Exception:
                return None
        # WikiCFP style: "Aug 15, 2025"
        try:
            dt = datetime.strptime(value.strip(), "%b %d, %Y")
            return dt.date().isoformat()
        except Exception:
            pass
    return None


# ---------------------- Entity-key (dedup primary keys) ----------------------
def journal_entity_key(*, issn_l: Optional[str], issns: list[str] | None,
                       title: str, publisher: str) -> str:
    if issn_l: return f"issn-l:{issn_l}"
    if issns:
        for i in issns:
            if i: return f"issn:{normalize_issn(i) or i}"
    return f"name:{slug(title)}-{slug(publisher)[:40]}"


def conference_entity_key(*, acronym: Optional[str], year: Optional[int], name: str) -> str:
    """Conference dedup key.

    We deliberately include a name slug even when acronym+year are present,
    because WikiCFP regularly publishes multiple distinct editions/tracks of
    the same acronym in the same year (e.g. two "ISCSLP 2026" CFPs with
    different subtitles). Collapsing them loses signal.
    """
    name_slug = slug(name)[:60]
    if acronym and year: return f"acronym-year-name:{slug(acronym)}-{year}-{name_slug}"
    if acronym: return f"acronym-name:{slug(acronym)}-{name_slug}"
    return f"name-year:{name_slug}-{year or 'na'}"


def grant_entity_key(*, sponsor: str, external_id: Optional[str], title: str) -> str:
    if external_id: return f"sponsor-extid:{slug(sponsor)}-{slug(external_id)}"
    return f"sponsor-title:{slug(sponsor)}-{slug(title)[:80]}"


# --------------------------------- bases ------------------------------------
class BaseDiscoveryProvider(ABC):
    """All discovery providers share this contract."""
    name: str = "base"
    kind: str = "base"          # "journal" | "conference" | "grant"
    enabled_by_default: bool = True

    @abstractmethod
    async def fetch_batch(self, cursor: Optional[str], page_size: int) -> tuple[list[dict], Optional[str]]:
        """Return (records, next_cursor). Empty list signals exhaustion."""


class JournalProvider(BaseDiscoveryProvider):
    kind = "journal"


class ConferenceProvider(BaseDiscoveryProvider):
    kind = "conference"


class GrantProvider(BaseDiscoveryProvider):
    kind = "grant"
