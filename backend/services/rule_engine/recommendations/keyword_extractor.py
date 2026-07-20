"""TF-based keyword extraction without external ML dependencies."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ..utils.text_utils import tokenize, remove_stopwords, extract_ngrams, ALL_STOPWORDS

_MIN_KEYWORD_LEN = 3
_MAX_KEYWORD_LEN = 40

_ACADEMIC_BOOST = frozenset({
    "neural", "machine", "learning", "deep", "artificial", "intelligence",
    "algorithm", "computational", "quantum", "genome", "protein", "molecular",
    "climate", "carbon", "ecosystem", "biodiversity", "renewable", "sustainable",
    "epidemiology", "pandemic", "vaccine", "immunology", "oncology", "genomics",
    "blockchain", "distributed", "federated", "differential", "stochastic",
    "bayesian", "regression", "classification", "clustering", "optimization",
})


def extract_keywords(
    text: str,
    top_n: int = 10,
    include_bigrams: bool = True,
    title: str = "",
) -> list[str]:
    """Extract top-N keywords from text using frequency + position weighting.

    Title terms receive a 2× boost.
    Academic-domain terms receive a 1.5× boost.
    """
    tokens = remove_stopwords(tokenize(text))
    title_tokens = set(remove_stopwords(tokenize(title)))

    freq: Counter[str] = Counter(tokens)
    bigrams: Counter[str] = Counter()
    if include_bigrams:
        bg = extract_ngrams(tokens, n=2)
        bigrams.update(bg)

    scores: dict[str, float] = {}

    for term, count in freq.items():
        if len(term) < _MIN_KEYWORD_LEN or len(term) > _MAX_KEYWORD_LEN:
            continue
        score = float(count)
        if term in title_tokens:
            score *= 2.0
        if term in _ACADEMIC_BOOST:
            score *= 1.5
        scores[term] = score

    if include_bigrams:
        for bigram, count in bigrams.items():
            parts = bigram.split()
            if any(p in ALL_STOPWORDS for p in parts):
                continue
            if any(len(p) < 3 for p in parts):
                continue
            score = float(count) * 1.2  # bigrams slightly preferred
            if any(p in title_tokens for p in parts):
                score *= 2.0
            scores[bigram] = score

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    seen_terms: set[str] = set()
    result: list[str] = []

    for term, _ in ranked:
        lower = term.lower()
        # Skip if term is a substring of already-added term or vice versa
        dominated = any(lower in existing or existing in lower for existing in seen_terms)
        if not dominated:
            result.append(term)
            seen_terms.add(lower)
        if len(result) >= top_n:
            break

    return result


def extract_keywords_from_abstract(
    abstract: str,
    title: str = "",
    top_n: int = 8,
) -> list[str]:
    return extract_keywords(abstract, top_n=top_n, include_bigrams=True, title=title)


def extract_keywords_scored(text: str, top_n: int = 10, title: str = "") -> list[dict[str, Any]]:
    """Return keywords with raw relevance scores for transparency."""
    tokens = remove_stopwords(tokenize(text))
    title_tokens = set(remove_stopwords(tokenize(title)))
    freq: Counter[str] = Counter(tokens)
    bigrams = Counter(extract_ngrams(tokens, n=2))

    scores: dict[str, float] = {}
    for term, count in {**dict(freq), **dict(bigrams)}.items():
        parts = term.split()
        if any(p in ALL_STOPWORDS or len(p) < 3 for p in parts):
            continue
        score = float(count)
        if any(p in title_tokens for p in parts):
            score *= 2.0
        if any(p in _ACADEMIC_BOOST for p in parts):
            score *= 1.5
        if len(parts) == 2:
            score *= 1.2
        scores[term] = score

    ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_n * 2]
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for term, score in ranked:
        lower = term.lower()
        if not any(lower in e or e in lower for e in seen):
            result.append({"keyword": term, "relevance": round(score, 2)})
            seen.add(lower)
        if len(result) >= top_n:
            break
    return result


def suggest_additional_keywords(
    existing_keywords: list[str],
    text: str,
    top_n: int = 5,
) -> list[str]:
    """Suggest keywords not already in the existing list."""
    existing_lower = {k.lower() for k in existing_keywords}
    candidates = extract_keywords(text, top_n=top_n + len(existing_keywords) + 5)
    return [k for k in candidates if k.lower() not in existing_lower][:top_n]
