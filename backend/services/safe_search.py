"""Safe text search for MongoDB.

Every search box, filter and query parameter that ends up in a `$regex`
goes through here. The value is treated strictly as text:

- anything that isn't a string (e.g. a JSON object smuggled in a body) is
  converted to its text form, so it can never become a query operator;
- Unicode is normalised (NFC), control characters dropped, whitespace
  collapsed, and the length capped (MAX_QUERY_LEN);
- regex metacharacters are escaped, so the pattern is a literal,
  case-insensitive substring match: no user-supplied regex runs, and a
  literal pattern can't backtrack catastrophically.

Names and academic terms in any script (é, ș, ü, 中文, ...) match as typed.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

MAX_QUERY_LEN = 100


def normalize_search(value: Any, max_len: int = MAX_QUERY_LEN) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = unicodedata.normalize("NFC", value)
    value = "".join(ch if unicodedata.category(ch)[0] != "C" else " " for ch in value)
    value = " ".join(value.split())
    return value[:max_len].strip()


def contains(value: Any, max_len: int = MAX_QUERY_LEN) -> dict:
    """Case-insensitive literal substring match."""
    return {"$regex": re.escape(normalize_search(value, max_len)), "$options": "i"}


def exact(value: Any, max_len: int = MAX_QUERY_LEN) -> dict:
    """Case-insensitive literal whole-value match."""
    return {"$regex": "^" + re.escape(normalize_search(value, max_len)) + "$", "$options": "i"}


def contains_any(terms: Any, max_terms: int = 20, max_len: int = MAX_QUERY_LEN) -> dict:
    """Case-insensitive match of any of several literal terms. Each term is
    normalised and escaped; only the alternation between them is pattern
    syntax, so this is still literal matching with no backtracking risk."""
    if isinstance(terms, (str, bytes)) or not isinstance(terms, (list, tuple, set)):
        terms = [terms]
    parts = [re.escape(t) for t in (normalize_search(x, max_len) for x in list(terms)[:max_terms]) if t]
    return {"$regex": "|".join(parts), "$options": "i"}
