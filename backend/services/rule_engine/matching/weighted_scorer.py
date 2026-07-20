"""Core weighted scoring primitives shared by all matchers."""
from __future__ import annotations

from typing import Any


def jaccard_similarity(set_a: list | set, set_b: list | set) -> float:
    """Jaccard index for two sets. Returns 0.0 if both empty."""
    a, b = set(s.lower().strip() for s in set_a), set(s.lower().strip() for s in set_b)
    if not a and not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def overlap_coefficient(set_a: list | set, set_b: list | set) -> float:
    """Overlap coefficient: intersection / min(|a|, |b|)."""
    a, b = set(s.lower() for s in set_a), set(s.lower() for s in set_b)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def cosine_text_similarity(terms_a: list[str], terms_b: list[str]) -> float:
    """Sparse cosine similarity on term frequency vectors."""
    from collections import Counter
    if not terms_a or not terms_b:
        return 0.0
    c_a = Counter(t.lower() for t in terms_a)
    c_b = Counter(t.lower() for t in terms_b)
    dot = sum(c_a[t] * c_b[t] for t in c_a if t in c_b)
    norm_a = sum(v * v for v in c_a.values()) ** 0.5
    norm_b = sum(v * v for v in c_b.values()) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def weighted_score(factors: dict[str, tuple[float, float]]) -> float:
    """Compute weighted sum.

    factors: {name: (value_0_to_1, weight)}
    Returns score in [0, 100].
    """
    total_weight = sum(w for _, w in factors.values())
    if total_weight == 0:
        return 0.0
    raw = sum(v * w for v, w in factors.values())
    return round(raw / total_weight * 100, 2)


def rank_candidates(
    candidates: list[dict],
    score_key: str = "score",
    top_n: int | None = None,
    min_score: float = 0.0,
) -> list[dict]:
    """Sort candidates by score_key descending; filter by min_score; optionally limit."""
    ranked = sorted(
        [c for c in candidates if c.get(score_key, 0) >= min_score],
        key=lambda x: x.get(score_key, 0),
        reverse=True,
    )
    return ranked[:top_n] if top_n else ranked


def build_match_explanation(factors: dict[str, tuple[float, float, str]]) -> str:
    """Build human-readable match explanation.

    factors: {name: (value_0_to_1, weight, label)}
    """
    strong = [(label, v) for _, (v, w, label) in factors.items() if v >= 0.6]
    if not strong:
        return "Moderate overall compatibility."
    parts = [f"{label} ({v:.0%})" for label, v in sorted(strong, key=lambda x: -x[1])]
    return "Strong match on: " + ", ".join(parts) + "."
