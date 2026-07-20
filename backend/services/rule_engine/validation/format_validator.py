"""Format validators for academic identifiers: DOI, ORCID, ISBN, ISSN, email, URL."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    valid: bool
    value: str = ""
    normalized: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


# ── DOI ──────────────────────────────────────────────────────────────────────

_DOI_RE = re.compile(
    r"^(?:https?://(?:dx\.)?doi\.org/|doi:)?(10\.\d{4,9}/[^\s\"<>{}|\\^`\[\]]+)$",
    re.IGNORECASE,
)


def validate_doi(doi: str) -> ValidationResult:
    doi = doi.strip()
    m = _DOI_RE.match(doi)
    if not m:
        return ValidationResult(
            valid=False,
            value=doi,
            errors=["DOI must match the pattern 10.XXXX/suffix (e.g., 10.1038/nature12345)"],
        )
    raw = m.group(1)
    normalized = f"https://doi.org/{raw}"
    return ValidationResult(valid=True, value=doi, normalized=normalized)


def normalize_doi(doi: str) -> str:
    r = validate_doi(doi)
    return r.normalized if r.valid else doi.strip()


# ── ORCID ─────────────────────────────────────────────────────────────────────

_ORCID_DIGITS_RE = re.compile(r"^(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$")
_ORCID_URL_RE = re.compile(
    r"https?://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", re.IGNORECASE
)


def _orcid_checksum(digits: str) -> bool:
    """Validate ORCID ISO 7064 MOD 11-2 check digit."""
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    check = (12 - (total % 11)) % 11
    expected = "X" if check == 10 else str(check)
    return expected == digits[-1].upper()


def validate_orcid(orcid: str) -> ValidationResult:
    orcid = orcid.strip()
    m = _ORCID_URL_RE.match(orcid) or _ORCID_DIGITS_RE.match(orcid)
    if not m:
        return ValidationResult(
            valid=False,
            value=orcid,
            errors=["ORCID must be in format 0000-0000-0000-0000 or https://orcid.org/0000-…"],
        )
    raw = m.group(1) if hasattr(m, "groups") and m.lastindex else m.group(0)
    raw = raw.replace("-", "").upper()
    digits = raw
    if not _orcid_checksum(digits):
        return ValidationResult(
            valid=False,
            value=orcid,
            errors=["ORCID check digit is invalid"],
        )
    formatted = f"{digits[0:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"
    return ValidationResult(
        valid=True,
        value=orcid,
        normalized=f"https://orcid.org/{formatted}",
    )


# ── ISBN ──────────────────────────────────────────────────────────────────────

def validate_isbn(isbn: str) -> ValidationResult:
    clean = re.sub(r"[\s\-]", "", isbn.strip())
    if len(clean) == 10:
        return _validate_isbn10(isbn, clean)
    if len(clean) == 13:
        return _validate_isbn13(isbn, clean)
    return ValidationResult(
        valid=False, value=isbn,
        errors=[f"ISBN must be 10 or 13 digits (got {len(clean)} after stripping hyphens)"],
    )


def _validate_isbn10(original: str, clean: str) -> ValidationResult:
    if not re.match(r"^\d{9}[\dX]$", clean, re.IGNORECASE):
        return ValidationResult(valid=False, value=original,
                                errors=["ISBN-10 must be 9 digits followed by a digit or X"])
    total = sum((10 - i) * (10 if c.upper() == "X" else int(c))
                for i, c in enumerate(clean))
    if total % 11 != 0:
        return ValidationResult(valid=False, value=original,
                                errors=["ISBN-10 check digit is invalid"])
    return ValidationResult(valid=True, value=original, normalized=clean.upper())


def _validate_isbn13(original: str, clean: str) -> ValidationResult:
    if not re.match(r"^\d{13}$", clean):
        return ValidationResult(valid=False, value=original,
                                errors=["ISBN-13 must be 13 digits"])
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(clean))
    if total % 10 != 0:
        return ValidationResult(valid=False, value=original,
                                errors=["ISBN-13 check digit is invalid"])
    return ValidationResult(valid=True, value=original, normalized=clean)


# ── ISSN ──────────────────────────────────────────────────────────────────────

_ISSN_RE = re.compile(r"^(\d{4})-(\d{3}[\dX])$", re.IGNORECASE)


def validate_issn(issn: str) -> ValidationResult:
    issn = issn.strip()
    m = _ISSN_RE.match(issn)
    if not m:
        return ValidationResult(valid=False, value=issn,
                                errors=["ISSN must be in format XXXX-XXXX (e.g., 1234-567X)"])
    digits = m.group(1) + m.group(2)
    total = sum(int(d) * (8 - i) for i, d in enumerate(digits[:-1]))
    check = (11 - total % 11) % 11
    expected = "X" if check == 10 else str(check)
    if expected.upper() != digits[-1].upper():
        return ValidationResult(valid=False, value=issn,
                                errors=["ISSN check digit is invalid"])
    return ValidationResult(valid=True, value=issn,
                            normalized=f"{m.group(1)}-{m.group(2).upper()}")


# ── Email ─────────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)
_DISPOSABLE_DOMAINS = frozenset({
    "mailinator.com", "guerrillamail.com", "10minutemail.com",
    "throwam.com", "yopmail.com", "tempmail.com", "fakeinbox.com",
})


def validate_email(email: str) -> ValidationResult:
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        return ValidationResult(valid=False, value=email,
                                errors=["Email address format is invalid"])
    domain = email.split("@", 1)[1]
    warnings: list[str] = []
    if domain in _DISPOSABLE_DOMAINS:
        warnings.append("This appears to be a disposable email address")
    return ValidationResult(valid=True, value=email, normalized=email, warnings=warnings)


# ── URL ───────────────────────────────────────────────────────────────────────

_URL_RE = re.compile(
    r"^(https?://)([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}(:\d+)?(/[^\s]*)?$"
)


def validate_url(url: str, require_https: bool = False) -> ValidationResult:
    url = url.strip()
    if not _URL_RE.match(url):
        return ValidationResult(valid=False, value=url,
                                errors=["URL format is invalid (must start with http:// or https://)"])
    warnings: list[str] = []
    if require_https and not url.startswith("https://"):
        warnings.append("URL should use HTTPS")
    return ValidationResult(valid=True, value=url, normalized=url, warnings=warnings)
