"""Text normalization utilities for academic content."""
from __future__ import annotations

import re
import unicodedata


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def normalize_unicode(text: str, form: str = "NFC") -> str:
    return unicodedata.normalize(form, text)


def strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&[a-zA-Z]+;|&#\d+;", " ", clean)
    return normalize_whitespace(clean)


def normalize_quotes(text: str) -> str:
    """Replace curly quotes and other variants with straight ASCII equivalents."""
    replacements = {
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "′": "'", "″": '"',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def normalize_dashes(text: str) -> str:
    """Normalize em-dashes and en-dashes to a consistent form."""
    text = re.sub(r"—|–", "—", text)   # em/en dash → em dash
    text = re.sub(r"\s*—\s*", " — ", text)         # space around em dash
    return text


def remove_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_author_name(name: str) -> str:
    """Normalize author name to 'Last, F. M.' format when possible."""
    name = normalize_whitespace(normalize_unicode(name))
    # Already "Last, First" form
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        last = parts[0].strip().title()
        first = parts[1].strip()
        initials = _to_initials(first)
        return f"{last}, {initials}"
    # "First Last" form
    parts = name.split()
    if len(parts) >= 2:
        last = parts[-1].title()
        initials = _to_initials(" ".join(parts[:-1]))
        return f"{last}, {initials}"
    return name.title()


def _to_initials(first_names: str) -> str:
    """'John Michael' → 'J. M.'"""
    parts = first_names.split()
    return " ".join(f"{p[0].upper()}." for p in parts if p)


def normalize_institution_name(name: str) -> str:
    """Light normalization: expand common abbreviations, title case."""
    abbrevs = {
        r"\bUniv\b\.?": "University",
        r"\bInst\b\.?": "Institute",
        r"\bDept\b\.?": "Department",
        r"\bLab\b\.?": "Laboratory",
        r"\bCtr\b\.?": "Center",
        r"\bTech\b\.?": "Technology",
        r"\bSci\b\.?": "Science",
    }
    result = name.strip()
    for pattern, replacement in abbrevs.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return " ".join(w.capitalize() if w.lower() not in {"of", "and", "the", "for", "in"}
                    else w.lower()
                    for w in result.split())


def normalize_country_name(name: str) -> str:
    """Normalize common country name variants."""
    mapping = {
        "usa": "United States", "u.s.a.": "United States", "us": "United States",
        "u.s.": "United States", "united states of america": "United States",
        "uk": "United Kingdom", "u.k.": "United Kingdom", "great britain": "United Kingdom",
        "prc": "China", "p.r.c.": "China", "people's republic of china": "China",
        "uae": "United Arab Emirates",
    }
    return mapping.get(name.strip().lower(), name.strip().title())


def normalize_journal_title(title: str) -> str:
    """Light normalization: expand abbreviations, consistent capitalization."""
    common = {
        "J.": "Journal",
        "Proc.": "Proceedings",
        "Int.": "International",
        "Sci.": "Science",
        "Rev.": "Review",
        "Lett.": "Letters",
        "Trans.": "Transactions",
        "Res.": "Research",
        "Eng.": "Engineering",
        "Technol.": "Technology",
        "Commun.": "Communications",
        "Comput.": "Computing",
        "Appl.": "Applied",
    }
    _minor = {"of", "and", "the", "for", "in", "on", "at", "by", "a", "an", "to"}
    result = title.strip()
    for abbrev, full in common.items():
        result = re.sub(re.escape(abbrev), full, result)
    words = result.split()
    return " ".join(
        w.capitalize() if (i == 0 or w.lower() not in _minor) else w.lower()
        for i, w in enumerate(words)
    )


def clean_academic_text(text: str) -> str:
    """Full pipeline: HTML → unicode → whitespace → quotes → dashes."""
    text = strip_html(text)
    text = normalize_unicode(text)
    text = normalize_whitespace(text)
    text = normalize_quotes(text)
    text = normalize_dashes(text)
    return text
