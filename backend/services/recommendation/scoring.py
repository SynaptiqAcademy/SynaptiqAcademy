from __future__ import annotations

import math
from typing import Iterable


def normalize_set(items: Iterable) -> set[str]:
    """Lowercase and strip each item, return deduped set."""
    result: set[str] = set()
    for item in (items or []):
        if item and isinstance(item, str):
            stripped = item.strip().lower()
            if stripped:
                result.add(stripped)
    return result


def jaccard(a: set, b: set) -> float:
    """|A ∩ B| / |A ∪ B|, returns 0.0-1.0. Returns 0 if both empty."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def overlap_score(a: set, b: set, weight: float) -> float:
    """Returns jaccard(a,b) * weight * 100, capped at weight*100."""
    return min(jaccard(a, b) * weight * 100, weight * 100)


def keyword_idf_weight(shared: set, universe_size: int) -> float:
    """TF-IDF-like weight: rare shared keywords count more. Returns 0-1.

    Each shared keyword contributes log(universe_size / 1) normalized weight.
    The final score is normalized to 0-1 relative to what a perfect match would yield.
    """
    if not shared or universe_size <= 0:
        return 0.0

    total_weight = 0.0
    for _ in shared:
        # Treat each keyword as occurring once in the universe pool
        # Using log(universe_size) as the IDF baseline so rare == high weight
        total_weight += math.log(max(universe_size, 2))

    # Normalize: maximum possible weight would be universe_size keywords all shared
    max_possible = len(shared) * math.log(max(universe_size, 2))
    if max_possible == 0:
        return 0.0

    raw = total_weight / max_possible
    # Scale by number of shared items relative to universe for sparsity penalty
    sparsity = min(len(shared) / max(universe_size, 1), 1.0)
    return min(raw * (0.5 + 0.5 * sparsity), 1.0)


def career_complement(role_a: str, role_b: str) -> float:
    """Returns 0.0-1.0 based on how complementary the roles are.

    Complementary pairs (return 1.0):
    - phd_student + professor/associate_professor
    - postdoc + professor
    - researcher + senior_researcher

    Same-level (return 0.5):
    - researcher + researcher, etc.

    Very different (return 0.3):
    - phd_student + phd_student (more competition than complement)
    """
    COMPLEMENTARY_PAIRS: list[frozenset] = [
        frozenset({"phd_student", "professor"}),
        frozenset({"phd_student", "associate_professor"}),
        frozenset({"phd_student", "principal_investigator"}),
        frozenset({"postdoc", "professor"}),
        frozenset({"postdoc", "associate_professor"}),
        frozenset({"postdoc", "principal_investigator"}),
        frozenset({"researcher", "senior_researcher"}),
        frozenset({"researcher", "professor"}),
        frozenset({"junior_researcher", "senior_researcher"}),
        frozenset({"junior_researcher", "professor"}),
        frozenset({"phd_student", "senior_researcher"}),
        frozenset({"postdoc", "senior_researcher"}),
        frozenset({"phd_student", "emeritus"}),
        frozenset({"postdoc", "emeritus"}),
    ]

    SAME_LEVEL_GROUPS: list[set] = [
        {"researcher", "researcher"},
        {"senior_researcher", "senior_researcher"},
        {"professor", "professor"},
        {"associate_professor", "associate_professor"},
        {"principal_investigator", "principal_investigator"},
    ]

    LOW_COMPLEMENT: set[str] = {"phd_student", "postdoc", "student", "undergraduate"}

    ra = (role_a or "").strip().lower().replace(" ", "_").replace("-", "_")
    rb = (role_b or "").strip().lower().replace(" ", "_").replace("-", "_")

    if not ra or not rb:
        return 0.5

    pair = frozenset({ra, rb})

    for cp in COMPLEMENTARY_PAIRS:
        if pair == cp:
            return 1.0

    if ra == rb:
        if ra in LOW_COMPLEMENT:
            return 0.3
        return 0.5

    # Both in low complement group
    if ra in LOW_COMPLEMENT and rb in LOW_COMPLEMENT:
        return 0.3

    # Moderate complement: different roles but neither is clearly junior/senior
    return 0.5


def clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))
