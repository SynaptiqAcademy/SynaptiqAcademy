"""PDF extractor — uses pypdf if available, falls back to heuristic text extraction."""
from __future__ import annotations

import io
import re

from services.knowledge.ingestion.extractors.base import DocumentExtractor, ExtractedDocument
from services.knowledge.models import DocumentMetadata

_SECTION_HEADINGS = re.compile(
    r"^(Abstract|Introduction|Background|Methods?|Methodology|Materials?\s+and\s+Methods?|"
    r"Results?|Discussion|Conclusion|References?|Acknowledgements?|Appendix|"
    r"Related\s+Work|Literature\s+Review|Evaluation|Experiments?|Data|Analysis|"
    r"Future\s+Work|Limitations?|Ethics|Funding)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_DOI_RE = re.compile(r"\b10\.\d{4,9}/\S+")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _detect_language(text: str) -> str:
    common_english = {"the", "and", "of", "to", "a", "in", "is", "that", "for"}
    words = set(text.lower().split()[:200])
    hits = len(words & common_english)
    return "en" if hits >= 3 else "unknown"


def _extract_sections(full_text: str) -> list[dict]:
    """Split text into sections based on heading detection."""
    lines = full_text.splitlines()
    sections: list[dict] = []
    current_heading = ""
    current_lines: list[str] = []
    page_num = 1

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^\f|^-+\s*\d+\s*-+$", stripped):
            page_num += 1
            continue
        if _SECTION_HEADINGS.match(stripped):
            if current_lines:
                sections.append({
                    "heading": current_heading,
                    "text": "\n".join(current_lines).strip(),
                    "page": page_num,
                })
            current_heading = stripped
            current_lines = []
        else:
            current_lines.append(stripped)

    if current_lines:
        sections.append({
            "heading": current_heading,
            "text": "\n".join(current_lines).strip(),
            "page": page_num,
        })

    return sections or [{"heading": "", "text": full_text.strip(), "page": 1}]


class PDFExtractor(DocumentExtractor):
    @property
    def supported_types(self) -> list[str]:
        return ["pdf"]

    def extract(self, content: bytes, filename: str = "") -> ExtractedDocument:
        text, pages, method = self._try_pypdf(content)
        if not text.strip():
            text = self._heuristic_extract(content)
            method = "heuristic"
            pages = 1

        sections = _extract_sections(text)
        doi = _DOI_RE.search(text)
        year_m = _YEAR_RE.search(text[:2000])
        meta = DocumentMetadata(
            title=filename.replace(".pdf", ""),
            doi=doi.group(0) if doi else "",
            publication_year=int(year_m.group(0)) if year_m else None,
            language=_detect_language(text),
        )
        return ExtractedDocument(
            text=text,
            sections=sections,
            metadata=meta,
            page_count=pages,
            language=meta.language,
            extraction_method=method,
        )

    def _try_pypdf(self, content: bytes) -> tuple[str, int, str]:
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            pages = len(reader.pages)
            texts: list[str] = []
            for page in reader.pages:
                t = page.extract_text() or ""
                texts.append(t)
            return "\n".join(texts), pages, "pypdf"
        except ImportError:
            pass
        except Exception:
            pass
        return "", 0, ""

    def _heuristic_extract(self, content: bytes) -> str:
        """Extract printable ASCII from raw PDF bytes — rough but dependency-free."""
        try:
            raw = content.decode("latin-1", errors="replace")
            # Extract text between BT/ET operators
            texts = re.findall(r"\(([^\)]{1,500})\)\s*Tj", raw)
            if texts:
                return " ".join(texts)
            # Fallback: extract printable runs
            printable = re.sub(r"[^\x20-\x7e\n]", " ", raw)
            printable = re.sub(r" {3,}", " ", printable)
            return printable[:50000]
        except Exception:
            return ""
