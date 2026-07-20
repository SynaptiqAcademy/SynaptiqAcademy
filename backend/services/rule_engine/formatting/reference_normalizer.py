"""Reference field normalizers: DOI, author names, journal titles, dates."""
from __future__ import annotations

import re
from typing import Any

from .text_normalizer import (
    normalize_author_name, normalize_journal_title, normalize_whitespace
)
from ..validation.format_validator import validate_doi


def normalize_reference(ref: dict[str, Any]) -> dict[str, Any]:
    """Normalize all fields of a reference dict in-place (returns copy)."""
    r = dict(ref)

    if r.get("doi"):
        r["doi"] = normalize_doi_field(r["doi"])
    if r.get("authors") and isinstance(r["authors"], list):
        r["authors"] = [normalize_author_name(a) for a in r["authors"]]
    if r.get("journal"):
        r["journal"] = normalize_journal_title(r["journal"])
    if r.get("title"):
        r["title"] = normalize_title(r["title"])
    if r.get("pages"):
        r["pages"] = normalize_page_range(r["pages"])
    if r.get("year"):
        r["year"] = normalize_year(r["year"])
    if r.get("volume"):
        r["volume"] = str(r["volume"]).strip()
    if r.get("issue") or r.get("number"):
        r["issue"] = str(r.get("issue") or r.get("number", "")).strip()

    return r


def normalize_doi_field(doi: str) -> str:
    """Return the canonical https://doi.org/... form or the raw value if invalid."""
    result = validate_doi(doi.strip())
    return result.normalized if result.valid else doi.strip()


def normalize_title(title: str) -> str:
    """Clean whitespace and normalize Unicode; preserve capitalization."""
    return normalize_whitespace(title).strip()


def normalize_page_range(pages: str) -> str:
    """Normalize page separators to en dash: '123-145' → '123–145'."""
    pages = pages.strip()
    pages = re.sub(r"\s*[-–—]\s*", "–", pages)
    # Expand abbreviated end page: '123–45' → '123–145' for 3+ digit starts
    m = re.match(r"^(\d+)–(\d+)$", pages)
    if m:
        start, end = m.group(1), m.group(2)
        if len(end) < len(start):
            end = start[: len(start) - len(end)] + end
            pages = f"{start}–{end}"
    return pages


def normalize_year(year: Any) -> str | int:
    """Return year as int if parseable, else stripped string."""
    y = str(year).strip()
    m = re.search(r"\b(1[89]\d{2}|20\d{2})\b", y)
    if m:
        return int(m.group(1))
    return y


def normalize_author_list(raw: str | list) -> list[str]:
    """Accept a string 'Last, F. M. and Last, F. M.' or a list; return list of normalized names."""
    if isinstance(raw, list):
        return [normalize_author_name(a) for a in raw if a.strip()]
    # Split on ' and ' or '; ' or ','
    if " and " in raw:
        parts = raw.split(" and ")
    elif "; " in raw:
        parts = raw.split("; ")
    else:
        parts = [raw]
    return [normalize_author_name(p.strip()) for p in parts if p.strip()]


def extract_doi_from_text(text: str) -> str | None:
    """Extract the first DOI string found in free text."""
    m = re.search(r"(?:https?://(?:dx\.)?doi\.org/|doi:)?(10\.\d{4,9}/[^\s\"<>{}|\\^`\[\]]+)",
                  text, re.IGNORECASE)
    if m:
        doi = m.group(1) if not m.group(0).startswith("10.") else m.group(0)
        return normalize_doi_field(doi)
    return None


def clean_reference_list(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize every reference in a list."""
    return [normalize_reference(r) for r in refs]


def merge_duplicate_authors(author_list: list[str]) -> list[str]:
    """Deduplicate author names that refer to the same person (heuristic)."""
    normalized = [normalize_author_name(a) for a in author_list]
    seen: dict[str, str] = {}
    result: list[str] = []
    for original, norm in zip(author_list, normalized):
        key = norm.lower()
        if key not in seen:
            seen[key] = norm
            result.append(norm)
    return result
