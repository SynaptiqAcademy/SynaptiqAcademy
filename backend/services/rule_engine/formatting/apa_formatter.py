"""APA 7th edition reference formatter."""
from __future__ import annotations

import re
from typing import Any

from .text_normalizer import normalize_author_name, normalize_journal_title


def format_apa_journal(
    authors: list[str],
    year: int | str,
    title: str,
    journal: str,
    volume: str | int | None = None,
    issue: str | int | None = None,
    pages: str | None = None,
    doi: str | None = None,
    advance_online: bool = False,
) -> str:
    """Format a journal article in APA 7th edition style.

    Example output:
    Smith, J. D., & Brown, M. A. (2023). The title of the article.
    Journal of Research, 45(3), 123–145. https://doi.org/10.1234/abc
    """
    author_str = _format_apa_authors(authors)
    title_str = _sentence_case(title.strip())
    journal_str = normalize_journal_title(journal.strip())

    location = journal_str
    if volume is not None:
        location += f", {volume}"
        if issue is not None:
            location += f"({issue})"
    if pages:
        location += f", {_normalize_pages(pages)}"
    if advance_online:
        location += ". Advance online publication"

    ref = f"{author_str} ({year}). {title_str}. {location}."
    if doi:
        doi_url = _normalize_doi(doi)
        ref += f" {doi_url}"
    return ref


def format_apa_book(
    authors: list[str],
    year: int | str,
    title: str,
    publisher: str,
    edition: str | None = None,
    doi: str | None = None,
) -> str:
    """Format a book in APA 7th edition style."""
    author_str = _format_apa_authors(authors)
    title_str = f"*{_sentence_case(title.strip())}*"
    ed_str = f" ({edition} ed.)" if edition else ""
    ref = f"{author_str} ({year}). {title_str}{ed_str}. {publisher}."
    if doi:
        ref += f" {_normalize_doi(doi)}"
    return ref


def format_apa_chapter(
    chapter_authors: list[str],
    year: int | str,
    chapter_title: str,
    editors: list[str],
    book_title: str,
    pages: str,
    publisher: str,
    doi: str | None = None,
) -> str:
    author_str = _format_apa_authors(chapter_authors)
    ed_str = _format_apa_editors(editors)
    ch_title = _sentence_case(chapter_title.strip())
    bk_title = f"*{_sentence_case(book_title.strip())}*"
    ref = f"{author_str} ({year}). {ch_title}. In {ed_str}, {bk_title} (pp. {_normalize_pages(pages)}). {publisher}."
    if doi:
        ref += f" {_normalize_doi(doi)}"
    return ref


def format_apa_conference(
    authors: list[str],
    year: int | str,
    title: str,
    conference_name: str,
    location: str | None = None,
    doi: str | None = None,
) -> str:
    author_str = _format_apa_authors(authors)
    title_str = _sentence_case(title.strip())
    loc_str = f", {location}" if location else ""
    ref = f"{author_str} ({year}). {title_str}. *{conference_name}*{loc_str}."
    if doi:
        ref += f" {_normalize_doi(doi)}"
    return ref


# ── Internal helpers ──────────────────────────────────────────────────────────

def _format_apa_authors(authors: list[str]) -> str:
    normalized = [normalize_author_name(a) for a in authors if a.strip()]
    n = len(normalized)
    if n == 0:
        return "Anonymous"
    if n == 1:
        return normalized[0]
    if n == 2:
        return f"{normalized[0]}, & {normalized[1]}"
    if n <= 20:
        return ", ".join(normalized[:-1]) + f", & {normalized[-1]}"
    # APA 7 rule: list first 19, then ellipsis, then last author
    return ", ".join(normalized[:19]) + ", … " + normalized[-1]


def _format_apa_editors(editors: list[str]) -> str:
    normalized = [normalize_author_name(e) for e in editors]
    n = len(normalized)
    label = "Ed." if n == 1 else "Eds."
    if n == 1:
        return f"{normalized[0]} ({label})"
    if n == 2:
        return f"{normalized[0]} & {normalized[1]} ({label})"
    return ", ".join(normalized[:-1]) + f", & {normalized[-1]} ({label})"


def _sentence_case(text: str) -> str:
    """Convert to sentence case: only first word and proper nouns capitalized."""
    if not text:
        return text
    result = text[0].upper() + text[1:].lower()
    # Preserve proper nouns heuristically (capitalized words after space)
    for m in re.finditer(r"(?<=[.!?:]\s)[a-z]", result):
        result = result[: m.start()] + result[m.start()].upper() + result[m.start() + 1:]
    return result


def _normalize_pages(pages: str) -> str:
    """Normalize page range to use en dash: '123-145' → '123–145'."""
    return re.sub(r"\s*[-–—]\s*", "–", pages.strip())


def _normalize_doi(doi: str) -> str:
    doi = doi.strip()
    if doi.startswith("10."):
        return f"https://doi.org/{doi}"
    if doi.startswith("doi:"):
        return f"https://doi.org/{doi[4:].strip()}"
    if "doi.org/" in doi and not doi.startswith("https"):
        return "https://" + doi.lstrip("http://")
    return doi


def build_apa_reference(reference: dict[str, Any]) -> str:
    """Build an APA reference from a generic reference dict."""
    ref_type = reference.get("type", "journal").lower()
    authors = reference.get("authors", [])
    year = reference.get("year", "n.d.")
    title = reference.get("title", "Untitled")

    if ref_type in ("journal", "article"):
        return format_apa_journal(
            authors=authors, year=year, title=title,
            journal=reference.get("journal", ""),
            volume=reference.get("volume"),
            issue=reference.get("issue"),
            pages=reference.get("pages"),
            doi=reference.get("doi"),
        )
    elif ref_type == "book":
        return format_apa_book(
            authors=authors, year=year, title=title,
            publisher=reference.get("publisher", ""),
            edition=reference.get("edition"),
            doi=reference.get("doi"),
        )
    elif ref_type in ("chapter", "book_chapter"):
        return format_apa_chapter(
            chapter_authors=authors, year=year,
            chapter_title=title,
            editors=reference.get("editors", []),
            book_title=reference.get("book_title", ""),
            pages=reference.get("pages", ""),
            publisher=reference.get("publisher", ""),
            doi=reference.get("doi"),
        )
    elif ref_type in ("conference", "conference_paper"):
        return format_apa_conference(
            authors=authors, year=year, title=title,
            conference_name=reference.get("conference", ""),
            location=reference.get("location"),
            doi=reference.get("doi"),
        )
    # Fallback: minimal format
    author_str = _format_apa_authors(authors)
    return f"{author_str} ({year}). {_sentence_case(title)}."
