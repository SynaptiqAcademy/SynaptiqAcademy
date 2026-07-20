"""Base ingester interface and shared result types."""
from __future__ import annotations

from dataclasses import dataclass, field

from services.literature.models import Paper, PaperSource


@dataclass
class IngestionResult:
    success: bool
    paper: Paper | None = None
    error: str = ""
    source: PaperSource = PaperSource.MANUAL
    source_id: str = ""


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(str(text).split())
