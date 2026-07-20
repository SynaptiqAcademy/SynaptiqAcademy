"""File-based paper ingestion — PDF, DOCX, TXT, Markdown."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from services.literature.ingestion.base import IngestionResult, _clean
from services.literature.models import Paper, PaperSource

log = logging.getLogger("synaptiq.literature.file_parser")

_MAX_CHARS = 120_000   # trim very large documents


def parse_file(
    content: bytes,
    filename: str,
    session_id: str = "",
) -> IngestionResult:
    """Parse an uploaded file and return an IngestionResult.

    Supports: .pdf, .docx, .txt, .md, .markdown
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(content, filename, session_id)
    if suffix in (".docx", ".doc"):
        return _parse_docx(content, filename, session_id)
    if suffix in (".md", ".markdown"):
        return _parse_text(content.decode("utf-8", errors="replace"), filename,
                           session_id, PaperSource.MARKDOWN)
    if suffix == ".txt":
        return _parse_text(content.decode("utf-8", errors="replace"), filename,
                           session_id, PaperSource.TXT)

    # Unknown extension — try as plain text
    try:
        text = content.decode("utf-8", errors="replace")
        return _parse_text(text, filename, session_id, PaperSource.TXT)
    except Exception as exc:
        return IngestionResult(success=False, error=f"Unsupported file type: {suffix}",
                               source=PaperSource.TXT, source_id=filename)


def _parse_pdf(content: bytes, filename: str, session_id: str) -> IngestionResult:
    try:
        import io
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages_text: list[str] = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                pass
        full_text = "\n".join(pages_text)
        return _build_paper_from_text(full_text, filename, session_id, PaperSource.PDF)
    except ImportError:
        return IngestionResult(success=False,
                               error="pypdf not installed — cannot parse PDF",
                               source=PaperSource.PDF, source_id=filename)
    except Exception as exc:
        return IngestionResult(success=False, error=f"PDF parse error: {exc}",
                               source=PaperSource.PDF, source_id=filename)


def _parse_docx(content: bytes, filename: str, session_id: str) -> IngestionResult:
    try:
        import io
        from docx import Document

        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs)
        return _build_paper_from_text(full_text, filename, session_id, PaperSource.DOCX)
    except ImportError:
        return IngestionResult(success=False,
                               error="python-docx not installed — cannot parse DOCX",
                               source=PaperSource.DOCX, source_id=filename)
    except Exception as exc:
        return IngestionResult(success=False, error=f"DOCX parse error: {exc}",
                               source=PaperSource.DOCX, source_id=filename)


def _parse_text(text: str, filename: str, session_id: str, source: PaperSource) -> IngestionResult:
    return _build_paper_from_text(text, filename, session_id, source)


def _build_paper_from_text(
    text: str, filename: str, session_id: str, source: PaperSource
) -> IngestionResult:
    if not text.strip():
        return IngestionResult(success=False, error="File is empty or could not be read",
                               source=source, source_id=filename)

    text = text[:_MAX_CHARS]

    # Heuristic extraction of title (first non-empty line that looks like a title)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    title = _extract_title(lines)
    abstract = _extract_abstract(text)
    doi = _extract_doi(text)
    year = _extract_year(text)
    authors = _extract_authors(lines, title)

    paper = Paper(
        source=source,
        source_id=filename,
        session_id=session_id,
        title=title or Path(filename).stem,
        authors=authors,
        year=year,
        abstract=abstract,
        full_text=text,
        doi=doi,
    )
    return IngestionResult(success=True, paper=paper, source=source, source_id=filename)


def _extract_title(lines: list[str]) -> str:
    for line in lines[:10]:
        if 10 < len(line) < 200 and not line.startswith("#"):
            # Skip lines that look like author lists or metadata
            if not re.search(r"@|doi:|http|volume|issue|journal", line, re.I):
                return _clean(line)
    return ""


def _extract_abstract(text: str) -> str:
    match = re.search(
        r"(?:Abstract|ABSTRACT)[:\s]+(.{100,2000}?)(?:\n\n|\n(?=[A-Z][a-z])|Introduction|INTRODUCTION)",
        text, re.DOTALL
    )
    if match:
        return _clean(match.group(1))
    return ""


def _extract_doi(text: str) -> str:
    match = re.search(r"(?:doi:|DOI:|https?://doi\.org/)(10\.\d{4,}/\S+)", text)
    return match.group(1).rstrip(".") if match else ""


def _extract_year(text: str) -> int:
    # Look for 4-digit years between 1900-2030
    matches = re.findall(r"\b(19[0-9]{2}|20[0-2][0-9])\b", text[:3000])
    if matches:
        years = [int(y) for y in matches if 1950 <= int(y) <= 2030]
        if years:
            return min(years)   # earliest is likely publication year
    return 0


def _extract_authors(lines: list[str], title: str) -> list[str]:
    """Very basic heuristic: lines after the title that look like author names."""
    author_lines = []
    in_author_zone = False
    for line in lines[:20]:
        if line == title:
            in_author_zone = True
            continue
        if in_author_zone:
            if re.search(r"Abstract|doi:|Introduction|Department", line, re.I):
                break
            # Line with 1-5 comma-separated proper-cased words is likely authors
            if re.match(r"^[A-Z][a-z]", line) and len(line) < 200:
                author_lines.append(line)
            if len(author_lines) >= 3:
                break

    if not author_lines:
        return []

    # Join and split on common delimiters
    raw = " ".join(author_lines)
    parts = re.split(r",\s*(?=[A-Z])|;\s*|\band\b", raw)
    return [p.strip() for p in parts if len(p.strip()) > 3][:10]
