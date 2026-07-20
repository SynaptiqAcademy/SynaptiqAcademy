"""Academic index calculators — H-index, G-index, I10-index, citation variants."""
from __future__ import annotations


def calculate_h_index(citation_counts: list[int]) -> int:
    """Standard H-index: largest h s.t. h papers each have ≥ h citations."""
    if not citation_counts:
        return 0
    sorted_desc = sorted(citation_counts, reverse=True)
    h = 0
    for i, c in enumerate(sorted_desc, start=1):
        if c >= i:
            h = i
        else:
            break
    return h


def calculate_g_index(citation_counts: list[int]) -> int:
    """G-index: largest g s.t. top g papers together have ≥ g² citations."""
    if not citation_counts:
        return 0
    sorted_desc = sorted(citation_counts, reverse=True)
    cumulative = 0
    g = 0
    for i, c in enumerate(sorted_desc, start=1):
        cumulative += c
        if cumulative >= i * i:
            g = i
        else:
            break
    return g


def calculate_i10_index(citation_counts: list[int]) -> int:
    """Count of publications with ≥ 10 citations."""
    return sum(1 for c in citation_counts if c >= 10)


def calculate_i100_index(citation_counts: list[int]) -> int:
    return sum(1 for c in citation_counts if c >= 100)


def calculate_m_quotient(h_index: int, career_years: float) -> float:
    """M-quotient: h-index / career_length_years. Normalises for career stage."""
    if career_years <= 0:
        return float(h_index)
    return round(h_index / career_years, 3)


def calculate_ar_index(citation_counts: list[int], publication_ages_years: list[float]) -> float:
    """AR-index: sqrt(sum of citations/age for top-h papers)."""
    h = calculate_h_index(citation_counts)
    if h == 0:
        return 0.0
    pairs = sorted(zip(citation_counts, publication_ages_years), reverse=True)
    top_h = pairs[:h]
    s = sum(c / max(age, 0.5) for c, age in top_h)
    import math
    return round(math.sqrt(s), 3)


def citation_summary(citation_counts: list[int]) -> dict:
    """Return full citation index summary."""
    total = sum(citation_counts)
    n = len(citation_counts)
    return {
        "h_index": calculate_h_index(citation_counts),
        "g_index": calculate_g_index(citation_counts),
        "i10_index": calculate_i10_index(citation_counts),
        "i100_index": calculate_i100_index(citation_counts),
        "total_citations": total,
        "publication_count": n,
        "avg_citations_per_pub": round(total / n, 2) if n else 0.0,
        "max_citations": max(citation_counts, default=0),
        "median_citations": _median(citation_counts),
    }


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return (s[mid - 1] + s[mid]) / 2.0 if n % 2 == 0 else float(s[mid])
