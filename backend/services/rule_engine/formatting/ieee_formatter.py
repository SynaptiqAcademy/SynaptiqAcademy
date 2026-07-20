"""IEEE reference formatter (IEEE Transactions style)."""
from __future__ import annotations

import re
from typing import Any

from .text_normalizer import normalize_journal_title


def format_ieee_journal(
    authors: list[str],
    title: str,
    journal: str,
    volume: str | int | None = None,
    number: str | int | None = None,
    pages: str | None = None,
    year: int | str = "",
    doi: str | None = None,
    ref_number: int | None = None,
) -> str:
    """Format a journal article in IEEE style.

    Example:
    [1] J. D. Smith and M. A. Brown, "The title of the article,"
    J. Res., vol. 45, no. 3, pp. 123–145, 2023, doi: 10.1234/abc.
    """
    prefix = f"[{ref_number}] " if ref_number is not None else ""
    author_str = _format_ieee_authors(authors)
    journal_str = normalize_journal_title(journal.strip())

    parts = [f'{prefix}{author_str}, "{title.strip()}," {journal_str}']
    if volume is not None:
        parts.append(f"vol. {volume}")
    if number is not None:
        parts.append(f"no. {number}")
    if pages:
        parts.append(f"pp. {_normalize_pages(pages)}")
    if year:
        parts.append(str(year))

    ref = ", ".join(parts) + "."
    if doi:
        doi_clean = _strip_doi_prefix(doi)
        ref += f" doi: {doi_clean}."
    return ref


def format_ieee_book(
    authors: list[str],
    title: str,
    publisher: str,
    year: int | str,
    edition: str | None = None,
    pages: str | None = None,
    ref_number: int | None = None,
) -> str:
    prefix = f"[{ref_number}] " if ref_number is not None else ""
    author_str = _format_ieee_authors(authors)
    ed_str = f", {edition} ed." if edition else ""
    pg_str = f", pp. {_normalize_pages(pages)}" if pages else ""
    return f'{prefix}{author_str}, *{title.strip()}*{ed_str}. {publisher}, {year}{pg_str}.'


def format_ieee_conference(
    authors: list[str],
    title: str,
    conference: str,
    year: int | str,
    pages: str | None = None,
    doi: str | None = None,
    ref_number: int | None = None,
) -> str:
    prefix = f"[{ref_number}] " if ref_number is not None else ""
    author_str = _format_ieee_authors(authors)
    pg_str = f", pp. {_normalize_pages(pages)}" if pages else ""
    ref = f'{prefix}{author_str}, "{title.strip()}," in *{conference.strip()}*, {year}{pg_str}.'
    if doi:
        ref += f" doi: {_strip_doi_prefix(doi)}."
    return ref


def format_ieee_report(
    authors: list[str],
    title: str,
    institution: str,
    year: int | str,
    report_number: str | None = None,
    ref_number: int | None = None,
) -> str:
    prefix = f"[{ref_number}] " if ref_number is not None else ""
    author_str = _format_ieee_authors(authors)
    num_str = f", Rep. {report_number}" if report_number else ""
    return f'{prefix}{author_str}, "{title.strip()}," {institution}{num_str}, {year}.'


def build_ieee_reference(reference: dict[str, Any], ref_number: int | None = None) -> str:
    ref_type = reference.get("type", "journal").lower()
    authors = reference.get("authors", [])
    title = reference.get("title", "Untitled")
    year = reference.get("year", "")

    if ref_type in ("journal", "article"):
        return format_ieee_journal(
            authors=authors, title=title, year=year,
            journal=reference.get("journal", ""),
            volume=reference.get("volume"),
            number=reference.get("issue") or reference.get("number"),
            pages=reference.get("pages"),
            doi=reference.get("doi"),
            ref_number=ref_number,
        )
    elif ref_type == "book":
        return format_ieee_book(
            authors=authors, title=title, year=year,
            publisher=reference.get("publisher", ""),
            edition=reference.get("edition"),
            ref_number=ref_number,
        )
    elif ref_type in ("conference", "conference_paper"):
        return format_ieee_conference(
            authors=authors, title=title, year=year,
            conference=reference.get("conference", ""),
            pages=reference.get("pages"),
            doi=reference.get("doi"),
            ref_number=ref_number,
        )
    # Minimal fallback
    prefix = f"[{ref_number}] " if ref_number is not None else ""
    author_str = _format_ieee_authors(authors)
    return f'{prefix}{author_str}, "{title.strip()}," {year}.'


def build_ieee_reference_list(references: list[dict[str, Any]]) -> list[str]:
    return [build_ieee_reference(ref, i + 1) for i, ref in enumerate(references)]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _format_ieee_authors(authors: list[str]) -> str:
    """Format authors as 'F. M. Last and F. M. Last'."""
    normalized = [_ieee_author(a) for a in authors if a.strip()]
    n = len(normalized)
    if n == 0:
        return "Anonymous"
    if n == 1:
        return normalized[0]
    if n <= 3:
        return " and ".join(normalized) if n == 2 else ", ".join(normalized[:-1]) + f", and {normalized[-1]}"
    return normalized[0] + " et al."


def _ieee_author(name: str) -> str:
    """Convert 'Smith, John M.' or 'John M. Smith' to 'J. M. Smith'."""
    name = name.strip()
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        last = parts[0].strip().capitalize()
        first_parts = parts[1].strip().split()
    else:
        parts = name.split()
        if not parts:
            return name
        last = parts[-1].capitalize()
        first_parts = parts[:-1]
    initials = " ".join(f"{p[0].upper()}." for p in first_parts if p)
    if initials:
        return f"{initials} {last}"
    return last


def _normalize_pages(pages: str) -> str:
    return re.sub(r"\s*[-–—]\s*", "–", pages.strip())


def _strip_doi_prefix(doi: str) -> str:
    doi = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/",
                   "https://dx.doi.org/", "doi:"):
        if doi.lower().startswith(prefix.lower()):
            return doi[len(prefix):]
    return doi
