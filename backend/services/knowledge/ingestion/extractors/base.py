"""Base document extractor interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from services.knowledge.models import DocumentMetadata


@dataclass
class ExtractedDocument:
    """Result of document text extraction."""
    text: str                          # full plain text
    sections: list[dict]               # [{heading, text, page}]
    metadata: DocumentMetadata
    page_count: int = 0
    word_count: int = 0
    language: str = "en"
    extraction_method: str = ""        # "pypdf" | "python-docx" | "plain" | "xml-fallback"

    def __post_init__(self) -> None:
        if not self.word_count:
            self.word_count = len(self.text.split())


class DocumentExtractor(ABC):
    """Abstract base for all document extractors."""

    @property
    @abstractmethod
    def supported_types(self) -> list[str]:
        """File extensions this extractor handles, e.g. ['pdf']."""
        ...

    @abstractmethod
    def extract(self, content: bytes, filename: str = "") -> ExtractedDocument:
        """Extract text and metadata from raw file bytes."""
        ...

    def supports(self, file_type: str) -> bool:
        return file_type.lower().lstrip(".") in self.supported_types
