"""Text processing utilities for the rule engine."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "that",
    "this", "these", "those", "it", "its", "i", "we", "you", "he", "she",
    "they", "their", "our", "my", "your", "his", "her", "not", "no", "nor",
    "so", "yet", "both", "either", "each", "more", "most", "other", "such",
    "than", "too", "very", "just", "if", "then", "else", "when", "where",
    "which", "who", "whom", "how", "what", "all", "any", "some", "none",
    "also", "well", "into", "over", "after", "before", "up", "out", "about",
    "through", "during", "between", "among", "per", "via", "vs", "et", "al",
})

_ACADEMIC_STOPWORDS: frozenset[str] = frozenset({
    "study", "studies", "result", "results", "paper", "research", "analysis",
    "data", "method", "methods", "approach", "approaches", "proposed", "using",
    "used", "based", "show", "shows", "shown", "present", "presents", "discuss",
    "discusses", "review", "reviews", "literature", "introduction", "conclusion",
    "conclusions", "abstract", "section", "table", "figure", "fig", "authors",
    "author", "work", "works", "model", "models", "framework", "technique",
    "techniques", "performance", "evaluation", "experiments", "experimental",
    "novel", "new", "significantly", "significant", "important", "different",
    "various", "several", "many", "large", "small", "high", "low", "number",
    "numbers", "thus", "however", "therefore", "moreover", "furthermore",
    "additionally", "finally", "first", "second", "third", "compared",
    "including", "indicate", "indicates", "suggest", "suggests", "possible",
    "existing", "recent", "previous", "current", "general", "specific",
})

ALL_STOPWORDS = _STOPWORDS | _ACADEMIC_STOPWORDS


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def remove_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_capitalization(text: str, mode: str = "title") -> str:
    """mode: 'title' | 'sentence' | 'lower' | 'upper'"""
    text = normalize_whitespace(text)
    if mode == "title":
        _minor = {"a", "an", "the", "and", "but", "or", "for", "nor", "on",
                   "at", "to", "by", "in", "of", "up", "as", "is", "vs"}
        words = text.split()
        result = []
        for i, w in enumerate(words):
            if i == 0 or w.lower() not in _minor:
                result.append(w.capitalize())
            else:
                result.append(w.lower())
        return " ".join(result)
    elif mode == "sentence":
        return text[0].upper() + text[1:].lower() if text else text
    elif mode == "lower":
        return text.lower()
    return text.upper()


def tokenize(text: str, min_len: int = 2, max_len: int = 50) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z\-']*[a-zA-Z]\b", text.lower())
    return [t for t in tokens if min_len <= len(t) <= max_len]


def remove_stopwords(tokens: list[str], extra: set[str] | None = None) -> list[str]:
    stops = ALL_STOPWORDS | (extra or set())
    return [t for t in tokens if t not in stops]


def extract_ngrams(tokens: list[str], n: int = 2) -> list[str]:
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def word_frequencies(text: str, remove_stops: bool = True) -> Counter:
    tokens = tokenize(text)
    if remove_stops:
        tokens = remove_stopwords(tokens)
    return Counter(tokens)


def truncate(text: str, max_chars: int = 200, suffix: str = "…") -> str:
    text = normalize_whitespace(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(suffix)].rstrip() + suffix


def slugify(text: str) -> str:
    text = remove_accents(text.lower())
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?]+(?:\s|$)", text))


def word_count(text: str) -> int:
    return len(text.split())


def char_count(text: str, include_spaces: bool = True) -> int:
    return len(text) if include_spaces else len(text.replace(" ", ""))


def extract_email_addresses(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s<>\"]+", text)
