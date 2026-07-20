"""Manuscript section detector — Phase IX.

Detects 35 section types from manuscript text using:
  1. Heading keyword patterns (case-insensitive, numbered or plain)
  2. Content keyword signals (fallback when no heading found)
  3. Structural position heuristics (abstract near top, references near end)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import SectionType, DetectedSection, ParsedDocument

# ── Heading patterns per section type ────────────────────────────────────────
# Each entry: (SectionType, list of heading regex patterns)
# Patterns are matched case-insensitively at the start of a line.

_HEADING_PATTERNS: list[tuple[SectionType, list[str]]] = [
    (SectionType.ABSTRACT, [r"abstract", r"summary", r"synopsis"]),
    (SectionType.KEYWORDS, [r"key\s*words?", r"index\s+terms?"]),
    (SectionType.INTRODUCTION, [r"introduction", r"background\s+and\s+motivation"]),
    (SectionType.BACKGROUND, [r"background", r"context"]),
    (SectionType.LITERATURE_REVIEW, [
        r"literature\s+review", r"review\s+of\s+(?:related\s+)?literature",
        r"related\s+work", r"state\s+of\s+the\s+art", r"prior\s+work",
    ]),
    (SectionType.RESEARCH_GAP, [
        r"research\s+gap", r"gap\s+in\s+(?:the\s+)?literature",
        r"motivation", r"problem\s+statement",
    ]),
    (SectionType.OBJECTIVES, [
        r"objectives?", r"aims?\s+(?:and|&)\s+objectives?",
        r"purpose\s+of\s+(?:the\s+)?study",
    ]),
    (SectionType.RESEARCH_QUESTIONS, [
        r"research\s+questions?", r"study\s+questions?",
    ]),
    (SectionType.HYPOTHESES, [
        r"hypothes[ei]s", r"hypotheses", r"propositions?",
    ]),
    (SectionType.THEORETICAL_FRAMEWORK, [
        r"theoretical\s+framework", r"theory", r"theoretical\s+background",
    ]),
    (SectionType.CONCEPTUAL_FRAMEWORK, [
        r"conceptual\s+framework", r"conceptual\s+model",
    ]),
    (SectionType.METHODOLOGY, [
        r"method(?:ology|s?)", r"research\s+method(?:ology|s)?",
        r"materials?\s+and\s+method", r"methods?\s+and\s+materials?",
    ]),
    (SectionType.RESEARCH_DESIGN, [
        r"research\s+design", r"study\s+design", r"experimental\s+design",
    ]),
    (SectionType.PARTICIPANTS, [
        r"participants?", r"sample", r"subjects?", r"population",
        r"respondents?", r"patients?",
    ]),
    (SectionType.INSTRUMENTS, [
        r"instruments?", r"measures?", r"survey\s+design", r"questionnaire",
        r"interview\s+guide",
    ]),
    (SectionType.DATA_COLLECTION, [
        r"data\s+collection", r"data\s+gathering", r"procedure",
    ]),
    (SectionType.DATA_ANALYSIS, [
        r"data\s+anal(?:ysis|yses)", r"analytic(?:al)?\s+approach",
        r"statistical\s+anal(?:ysis|yses)",
    ]),
    (SectionType.RESULTS, [
        r"results?", r"findings?", r"outcomes?",
    ]),
    (SectionType.FINDINGS, [
        r"key\s+findings?", r"empirical\s+results?",
    ]),
    (SectionType.DISCUSSION, [
        r"discussion", r"interpretation",
    ]),
    (SectionType.IMPLICATIONS, [
        r"implications?", r"theoretical\s+implications?",
        r"practical\s+implications?", r"managerial\s+implications?",
    ]),
    (SectionType.LIMITATIONS, [
        r"limitations?", r"constraints?", r"weaknesses?",
    ]),
    (SectionType.FUTURE_WORK, [
        r"future\s+(?:work|research|directions?|studies?)",
        r"directions?\s+for\s+future",
    ]),
    (SectionType.CONCLUSIONS, [
        r"conclusions?", r"concluding\s+remarks?", r"summary\s+and\s+conclusions?",
    ]),
    (SectionType.ACKNOWLEDGEMENTS, [
        r"acknowledgements?", r"acknowledgments?",
    ]),
    (SectionType.FUNDING, [
        r"funding", r"financial\s+support", r"grant",
    ]),
    (SectionType.ETHICS, [
        r"ethics(?:\s+statement)?", r"ethical\s+(?:approval|statement|considerations?)",
        r"institutional\s+review",
    ]),
    (SectionType.CONFLICT_OF_INTEREST, [
        r"conflict(?:s?)\s+of\s+interest", r"competing\s+interests?",
        r"declarations?\s+of\s+interest",
    ]),
    (SectionType.DATA_AVAILABILITY, [
        r"data\s+availability", r"data\s+access", r"availability\s+of\s+data",
    ]),
    (SectionType.REFERENCES, [
        r"references?", r"bibliography", r"works?\s+cited",
    ]),
    (SectionType.APPENDIX, [
        r"appendix(?:es|ices)?", r"supplemental\s+material",
    ]),
]

_COMPILED: list[tuple[SectionType, re.Pattern]] = []
for _st, _patterns in _HEADING_PATTERNS:
    combined = "|".join(f"(?:{p})" for p in _patterns)
    pat = re.compile(
        rf"^(?:\d+[\.\s]+)?(?:[A-Z][\.\s]+)?(?:{combined})[\s:.\-–]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    _COMPILED.append((_st, pat))

# ── Content-signal fallback ───────────────────────────────────────────────────
# Used when no heading was found — checks first 200 chars of a block.

_CONTENT_SIGNALS: dict[SectionType, list[str]] = {
    SectionType.ABSTRACT: [
        "this study", "this paper", "this article", "this research",
        "we investigate", "we present", "we propose", "we examine",
        "we report", "aim of this",
    ],
    SectionType.HYPOTHESES: [
        "h1:", "h2:", "h3:", "hypothesis 1", "hypothesis 2",
        "we hypothesize", "it is hypothesized",
    ],
    SectionType.ETHICS: [
        "institutional review board", "irb approval", "ethical clearance",
        "ethics committee", "helsinki declaration",
    ],
    SectionType.FUNDING: [
        "funded by", "supported by", "grant number", "this work was supported",
    ],
    SectionType.CONFLICT_OF_INTEREST: [
        "no conflict", "no competing interest", "the authors declare",
    ],
    SectionType.DATA_AVAILABILITY: [
        "data available", "dataset available", "data will be made available",
        "data can be accessed", "available upon request",
    ],
}


# ── Line-based section splitter ───────────────────────────────────────────────

_HEADING_LINE = re.compile(
    r"^(?:\d{1,2}[\.\s]+)?([A-Z][A-Za-z\s&\-/]{2,60})$",
    re.MULTILINE,
)


def detect_sections(doc: ParsedDocument) -> list[DetectedSection]:
    """Detect manuscript sections from a ParsedDocument."""
    text = doc.full_text
    if not text:
        return []

    # ── 1. Find all candidate heading positions ────────────────────────────────
    positions: list[tuple[int, SectionType, str]] = []  # (char_pos, type, heading)

    for st, pat in _COMPILED:
        for m in pat.finditer(text):
            heading = m.group(0).strip()
            positions.append((m.start(), st, heading))

    # Sort by position; deduplicate same-position entries (keep first match)
    positions.sort(key=lambda x: x[0])
    seen_pos: set[int] = set()
    unique: list[tuple[int, SectionType, str]] = []
    for pos, st, heading in positions:
        if pos not in seen_pos:
            unique.append((pos, st, heading))
            seen_pos.add(pos)

    # ── 2. Slice text between heading positions ────────────────────────────────
    detected: list[DetectedSection] = []
    for i, (start, st, heading) in enumerate(unique):
        end = unique[i + 1][0] if i + 1 < len(unique) else len(text)
        content = text[start:end].strip()
        ds = DetectedSection(
            section_type=st,
            heading=heading,
            content=content,
            word_count=len(content.split()),
            start_char=start,
            end_char=end,
            confidence=0.90,
        )
        detected.append(ds)

    # ── 3. Content-signal fallback for key missing sections ────────────────────
    detected_types = {d.section_type for d in detected}
    text_lower = text.lower()
    for st, signals in _CONTENT_SIGNALS.items():
        if st in detected_types:
            continue
        for sig in signals:
            if sig in text_lower:
                # Find the occurrence position
                pos = text_lower.index(sig)
                # Grab surrounding context (up to 500 chars)
                snippet = text[max(0, pos - 50): pos + 500].strip()
                detected.append(DetectedSection(
                    section_type=st,
                    heading="",
                    content=snippet,
                    word_count=len(snippet.split()),
                    start_char=pos,
                    end_char=pos + 500,
                    confidence=0.65,
                ))
                detected_types.add(st)
                break

    detected.sort(key=lambda d: d.start_char)
    return detected


def section_type_labels() -> dict[str, str]:
    """Human-readable labels for all section types."""
    return {st.value: st.value.replace("_", " ").title() for st in SectionType}
