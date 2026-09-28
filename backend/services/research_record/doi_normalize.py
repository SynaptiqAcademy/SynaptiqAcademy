"""Canonical DOI normalization — a thin wrapper around the existing
services/rule_engine/validation/format_validator.py, not a second DOI parser.

format_validator.normalize_doi() returns a full `https://doi.org/...` URL,
which would silently break deduplication against every existing publication
record: services/orcid/sync.py (the canonical ORCID import pipeline) stores
DOIs bare and lowercased (e.g. "10.1038/s41586-021-04337-x", no scheme, no
prefix). This module reuses format_validator's validation regex for format
correctness, then extracts the same bare form already used across the
`publications` collection, so DOI-based dedup actually matches.
"""
from __future__ import annotations

from services.rule_engine.validation.format_validator import validate_doi, _DOI_RE


def normalize_doi(doi: str) -> str | None:
    """Return the canonical bare-form DOI (lowercased, no scheme/prefix),
    or None if `doi` doesn't match a valid DOI format."""
    doi = (doi or "").strip()
    if not doi:
        return None
    result = validate_doi(doi)
    if not result.valid:
        return None
    m = _DOI_RE.match(doi)
    return m.group(1).lower() if m else None


def is_valid_doi(doi: str) -> bool:
    return normalize_doi(doi) is not None
