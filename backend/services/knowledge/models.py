"""Core data models for the Knowledge Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DocumentMetadata:
    """Metadata extracted from or associated with a source document."""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    doi: str = ""
    orcid_ids: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    abstract: str = ""
    publication_year: int | None = None
    journal: str = ""
    language: str = "en"
    citation_count: int = 0
    source_url: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "doi": self.doi,
            "orcid_ids": self.orcid_ids,
            "keywords": self.keywords,
            "abstract": self.abstract,
            "publication_year": self.publication_year,
            "journal": self.journal,
            "language": self.language,
            "citation_count": self.citation_count,
            "source_url": self.source_url,
        }


@dataclass
class KnowledgeDocument:
    """A document stored in the knowledge base."""
    document_id: str          # MongoDB _id as string
    user_id: str
    filename: str
    file_type: str            # pdf | docx | txt | md | html | csv
    source_kind: str          # manuscript | project | workspace | repository | orcid | crossref
    source_id: str            # FK to the source entity
    workspace_id: str | None
    visibility: str           # private | workspace | public
    metadata: DocumentMetadata
    chunk_count: int = 0
    indexed_at: datetime | None = None
    status: str = "pending"   # pending | indexing | indexed | failed
    error: str = ""
    file_size_bytes: int = 0
    storage_key: str = ""

    def to_dict(self) -> dict:
        return {
            "_id": self.document_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "workspace_id": self.workspace_id,
            "visibility": self.visibility,
            "metadata": self.metadata.to_dict(),
            "chunk_count": self.chunk_count,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "status": self.status,
            "error": self.error,
            "file_size_bytes": self.file_size_bytes,
        }


@dataclass
class Chunk:
    """A text chunk ready for embedding and indexing."""
    document_id: str
    chunk_index: int
    text: str
    heading: str = ""         # nearest section heading
    section: str = ""         # section label (Abstract, Methods, etc.)
    page_number: int | None = None
    paragraph_index: int | None = None
    token_count: int = 0
    # Populated after embedding
    embedding: list[float] = field(default_factory=list)
    # Permissions (inherited from document)
    user_id: str = ""
    workspace_id: str | None = None
    visibility: str = "private"
    # Citation fields
    doi: str = ""
    authors: list[str] = field(default_factory=list)
    title: str = ""
    publication_year: int | None = None

    def to_mongo_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "heading": self.heading,
            "section": self.section,
            "page_number": self.page_number,
            "paragraph_index": self.paragraph_index,
            "token_count": self.token_count,
            "embedding": self.embedding,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "visibility": self.visibility,
            "doi": self.doi,
            "authors": self.authors,
            "title": self.title,
            "publication_year": self.publication_year,
        }


@dataclass
class SearchResult:
    """A single retrieval result."""
    chunk_id: str             # MongoDB _id of the chunk
    document_id: str
    text: str
    score: float              # 0.0–1.0 (combined semantic + keyword)
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    heading: str = ""
    section: str = ""
    page_number: int | None = None
    doi: str = ""
    authors: list[str] = field(default_factory=list)
    title: str = ""
    publication_year: int | None = None
    filename: str = ""

    def to_citation(self) -> "Citation":
        return Citation(
            document_id=self.document_id,
            chunk_id=self.chunk_id,
            text_excerpt=self.text[:300] + ("…" if len(self.text) > 300 else ""),
            heading=self.heading,
            section=self.section,
            page_number=self.page_number,
            doi=self.doi,
            authors=self.authors,
            title=self.title,
            publication_year=self.publication_year,
            filename=self.filename,
        )

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "score": round(self.score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "keyword_score": round(self.keyword_score, 4),
            "heading": self.heading,
            "section": self.section,
            "page_number": self.page_number,
            "doi": self.doi,
            "authors": self.authors,
            "title": self.title,
            "publication_year": self.publication_year,
            "filename": self.filename,
        }


@dataclass
class Citation:
    """A citable source chunk, included in AI context."""
    document_id: str
    chunk_id: str
    text_excerpt: str
    heading: str = ""
    section: str = ""
    page_number: int | None = None
    doi: str = ""
    authors: list[str] = field(default_factory=list)
    title: str = ""
    publication_year: int | None = None
    filename: str = ""

    def format_short(self) -> str:
        """Short inline citation: 'Smith et al. (2023) — Methods'"""
        if self.authors:
            first = self.authors[0].split(",")[0].strip()
            author_str = f"{first} et al." if len(self.authors) > 1 else first
        else:
            author_str = self.title[:40] or self.filename
        year = f" ({self.publication_year})" if self.publication_year else ""
        section = f" — {self.section or self.heading}" if (self.section or self.heading) else ""
        return f"{author_str}{year}{section}"

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "text_excerpt": self.text_excerpt,
            "heading": self.heading,
            "section": self.section,
            "page_number": self.page_number,
            "doi": self.doi,
            "authors": self.authors,
            "title": self.title,
            "publication_year": self.publication_year,
            "filename": self.filename,
        }


@dataclass
class IndexingJob:
    """A document queued for background indexing."""
    job_id: str
    document_id: str
    user_id: str
    filename: str
    file_type: str
    content_bytes: bytes = field(default_factory=bytes)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    workspace_id: str | None = None
    source_kind: str = "upload"
    source_id: str = ""
    visibility: str = "private"
    priority: int = 5         # 1=highest, 10=lowest
    enqueued_at: float = field(default_factory=lambda: __import__("time").time())
