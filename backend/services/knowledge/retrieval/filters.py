"""Permission-aware query filters for knowledge retrieval."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalFilter:
    """Specifies who is asking and what context they have access to."""
    user_id: str
    workspace_id: str | None = None
    institution_id: str | None = None
    # Include documents from these visibility levels
    allowed_visibility: list[str] = field(
        default_factory=lambda: ["private", "workspace", "public"]
    )
    # Narrow by document fields
    filter_language: str | None = None
    filter_year_min: int | None = None
    filter_year_max: int | None = None
    filter_source_kinds: list[str] = field(default_factory=list)
    filter_document_ids: list[str] = field(default_factory=list)


def build_mongo_filter(f: RetrievalFilter) -> dict:
    """Build a MongoDB query filter for permission-aware chunk retrieval."""
    or_clauses = []

    # Private documents owned by the user
    or_clauses.append({"user_id": f.user_id, "visibility": "private"})

    # Workspace-shared documents
    if f.workspace_id:
        or_clauses.append({
            "workspace_id": f.workspace_id,
            "visibility": "workspace",
        })

    # Public documents
    if "public" in f.allowed_visibility:
        or_clauses.append({"visibility": "public"})

    base_filter: dict = {"$or": or_clauses}

    # Optional narrows
    if f.filter_language:
        base_filter["language"] = f.filter_language
    if f.filter_year_min or f.filter_year_max:
        year_cond: dict = {}
        if f.filter_year_min:
            year_cond["$gte"] = f.filter_year_min
        if f.filter_year_max:
            year_cond["$lte"] = f.filter_year_max
        base_filter["publication_year"] = year_cond
    if f.filter_source_kinds:
        base_filter["source_kind"] = {"$in": f.filter_source_kinds}
    if f.filter_document_ids:
        base_filter["document_id"] = {"$in": f.filter_document_ids}

    return base_filter
