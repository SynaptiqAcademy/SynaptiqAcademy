"""Section-aware manuscript context for AI requests.

A request like "Improve the Discussion" needs the Discussion (plus a little
supporting context such as the abstract), not the whole manuscript. This
module picks the sections a request refers to from the manuscript's stored
`sections` dict, within a character budget. It never invents content and
never drops the section the user asked about in favour of others.
"""
from __future__ import annotations

import re

# Canonical section -> stored keys / words users use for it.
SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "abstract":          ("abstract", "summary"),
    "introduction":      ("introduction", "intro", "background"),
    "literature_review": ("literature review", "literature_review", "related work", "state of the art"),
    "methodology":       ("methodology", "methods", "method", "materials and methods", "study design"),
    "results":           ("results", "findings"),
    "discussion":        ("discussion",),
    "conclusion":        ("conclusion", "conclusions", "concluding remarks"),
    "references":        ("references", "bibliography", "citations"),
}

DEFAULT_BUDGET_CHARS = 24_000      # ~6k tokens of manuscript text
SUPPORTING_CHARS = 1_500           # abstract excerpt kept as orientation


def _stored_key(sections: dict, canonical: str) -> str | None:
    for key in sections:
        k = key.lower().replace("-", "_")
        if k == canonical or k in {a.replace(" ", "_") for a in SECTION_ALIASES[canonical]}:
            return key
    return None


def requested_sections(text: str, sections: dict) -> list[str]:
    """Canonical sections the request text mentions and the manuscript has."""
    t = (text or "").lower()
    found = []
    for canonical, aliases in SECTION_ALIASES.items():
        if any(re.search(rf"\b{re.escape(a)}\b", t) for a in aliases):
            key = _stored_key(sections, canonical)
            if key and (sections.get(key) or "").strip():
                found.append(canonical)
    return found


def build_section_context(text: str, sections: dict, budget_chars: int = DEFAULT_BUDGET_CHARS) -> str:
    """Relevant sections (verbatim, truncated to budget) + abstract excerpt.
    Returns "" when the request names no section — callers then keep their
    existing behaviour."""
    wanted = requested_sections(text, sections or {})
    if not wanted:
        return ""
    parts: list[str] = []
    per_section = max(2_000, budget_chars // len(wanted))
    for canonical in wanted:
        body = sections[_stored_key(sections, canonical)].strip()
        clipped = body[:per_section]
        note = "" if len(body) <= per_section else f"\n[section truncated: {len(body) - per_section:,} more characters]"
        parts.append(f"### {canonical.replace('_', ' ').title()}\n{clipped}{note}")
    if "abstract" not in wanted:
        abs_key = _stored_key(sections, "abstract")
        if abs_key and (sections.get(abs_key) or "").strip():
            parts.insert(0, f"### Abstract (supporting context)\n{sections[abs_key].strip()[:SUPPORTING_CHARS]}")
    return "\n\n".join(parts)
