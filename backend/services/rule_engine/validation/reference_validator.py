"""APA and IEEE reference format validators."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .format_validator import ValidationResult


# ── APA validator ─────────────────────────────────────────────────────────────

# APA 7th edition journal article pattern (relaxed for partial matching):
# Author(s). (Year). Title. Journal, Volume(Issue), Pages. DOI
_APA_JOURNAL_RE = re.compile(
    r"^[A-Z][^\(]+\(\d{4}\)\.\s+[^.]+\.\s+[^\d,]+,\s*\d+",
    re.DOTALL,
)
_APA_YEAR_RE = re.compile(r"\(\d{4}[a-z]?\)\.")
_APA_DOI_RE = re.compile(r"https://doi\.org/10\.\d{4,9}/\S+")
_APA_AUTHOR_RE = re.compile(
    r"^[A-Z][a-zA-Z\-']+,\s+[A-Z]\.\s*(?:,\s*[A-Z][a-zA-Z\-']+,\s+[A-Z]\.\s*)*"
    r"(?:&\s*[A-Z][a-zA-Z\-']+,\s+[A-Z]\.)?"
)


def validate_apa_reference(ref: str) -> ValidationResult:
    ref = ref.strip()
    errors: list[str] = []
    warnings: list[str] = []

    if not _APA_YEAR_RE.search(ref):
        errors.append("Missing publication year in parentheses: (YYYY).")
    if not re.search(r"\.", ref):
        errors.append("References must contain periods separating components.")
    if len(ref) < 30:
        errors.append("Reference appears too short to be complete.")
    if not re.search(r"[A-Z]", ref[:15]):
        errors.append("Reference should start with author's last name (capitalized).")
    if _APA_DOI_RE.search(ref):
        pass  # DOI found — good
    elif re.search(r"10\.\d{4,9}/", ref):
        warnings.append("DOI found but not in canonical https://doi.org/ format.")
    elif re.search(r"pp?\.\s*\d+", ref, re.IGNORECASE):
        pass  # page numbers present — acceptable
    else:
        warnings.append("No DOI or page numbers detected; add a DOI for verifiability.")
    if not re.search(r"\d{4}", ref):
        errors.append("No year found in reference.")

    return ValidationResult(
        valid=len(errors) == 0,
        value=ref,
        errors=errors,
        warnings=warnings,
    )


def validate_apa_reference_list(refs: list[str]) -> dict[str, Any]:
    results = [validate_apa_reference(r) for r in refs]
    valid_count = sum(1 for r in results if r.valid)
    return {
        "total": len(refs),
        "valid": valid_count,
        "invalid": len(refs) - valid_count,
        "score": round(valid_count / len(refs) * 100, 1) if refs else 100.0,
        "items": [
            {"reference": r.value[:120], "valid": r.valid,
             "errors": r.errors, "warnings": r.warnings}
            for r in results
        ],
    }


# ── IEEE validator ────────────────────────────────────────────────────────────

# IEEE format: [N] I. Lastname and I. Lastname, "Title," Journal, vol. X, no. Y, pp. Z–ZZ, Year.
_IEEE_NUM_RE = re.compile(r"^\[\d+\]")
_IEEE_TITLE_RE = re.compile(r'"[^"]{5,}"')
_IEEE_YEAR_RE = re.compile(
    r",\s*(?:Jan\.?|Feb\.?|Mar\.?|Apr\.?|May|Jun\.?|Jul\.?|Aug\.?|"
    r"Sep\.?|Oct\.?|Nov\.?|Dec\.?)?\s*\d{4}\."
)


def validate_ieee_reference(ref: str) -> ValidationResult:
    ref = ref.strip()
    errors: list[str] = []
    warnings: list[str] = []

    if not _IEEE_NUM_RE.match(ref):
        errors.append('IEEE references must start with a reference number, e.g., "[1]".')
    if not _IEEE_TITLE_RE.search(ref):
        errors.append('Article/chapter title must be enclosed in double quotes.')
    if not re.search(r"\d{4}", ref):
        errors.append("No year found in reference.")
    if not ref.rstrip().endswith("."):
        warnings.append("IEEE references should end with a period.")
    if re.search(r"\bvol\.\s*\d+", ref, re.IGNORECASE):
        pass
    elif "conference" in ref.lower() or "proc." in ref.lower():
        pass  # conference proceedings — volume not required
    else:
        warnings.append("Journal reference should include volume number (vol. X).")
    if len(ref) < 40:
        errors.append("Reference appears too short to be complete.")

    return ValidationResult(
        valid=len(errors) == 0,
        value=ref,
        errors=errors,
        warnings=warnings,
    )


def validate_ieee_reference_list(refs: list[str]) -> dict[str, Any]:
    results = [validate_ieee_reference(r) for r in refs]
    valid_count = sum(1 for r in results if r.valid)
    return {
        "total": len(refs),
        "valid": valid_count,
        "invalid": len(refs) - valid_count,
        "score": round(valid_count / len(refs) * 100, 1) if refs else 100.0,
        "items": [
            {"reference": r.value[:120], "valid": r.valid,
             "errors": r.errors, "warnings": r.warnings}
            for r in results
        ],
    }


# ── Duplicate detection ───────────────────────────────────────────────────────

def find_duplicate_references(refs: list[str]) -> list[dict[str, Any]]:
    """Detect near-duplicate references by normalized form."""
    normalized = [_normalize_ref(r) for r in refs]
    duplicates: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for i, n in enumerate(normalized):
        if n in seen:
            duplicates.append({
                "index_a": seen[n],
                "index_b": i,
                "reference_a": refs[seen[n]][:100],
                "reference_b": refs[i][:100],
            })
        else:
            seen[n] = i
    return duplicates


def _normalize_ref(ref: str) -> str:
    """Aggressive normalization for duplicate detection."""
    r = ref.lower()
    r = re.sub(r"https?://\S+", "", r)     # strip URLs
    r = re.sub(r"\[\d+\]", "", r)          # strip IEEE numbers
    r = re.sub(r"\d{4}", "", r)            # strip years
    r = re.sub(r"[^\w\s]", "", r)          # strip punctuation
    r = re.sub(r"\s+", " ", r).strip()
    return r
