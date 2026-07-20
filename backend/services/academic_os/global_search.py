"""Global Search — universal semantic search across all platform entities."""
from __future__ import annotations

import math
import threading
from collections import defaultdict

from .models import SearchIndex, SearchResult

_MAX_INDEX = 50_000


def _tokenize(text: str) -> list[str]:
    return [t for t in text.lower().replace(",", " ").replace(".", " ").split() if len(t) > 1]


def _tf(tokens: list[str], term: str) -> float:
    count = tokens.count(term)
    return count / len(tokens) if tokens else 0.0


def _idf(n_docs: int, df: int) -> float:
    return math.log((1 + n_docs) / (1 + df)) + 1


def _excerpt(content: str, query_tokens: list[str], max_len: int = 150) -> str:
    lower = content.lower()
    best_pos = 0
    for token in query_tokens:
        pos = lower.find(token)
        if pos >= 0:
            best_pos = max(0, pos - 30)
            break
    snippet = content[best_pos: best_pos + max_len]
    return (snippet + "…") if len(content) > best_pos + max_len else snippet


class GlobalSearch:
    def __init__(self):
        self._lock   = threading.Lock()
        self._index: list[SearchIndex]              = []
        self._df:    dict[str, int]                 = defaultdict(int)  # term → doc frequency
        self._entity_keys: dict[tuple, int]         = {}  # (entity_type, entity_id) → index pos

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_entity(
        self,
        entity_type:  str,
        entity_id:    str,
        title:        str,
        content:      str      = "",
        tags:         list     | None = None,
        owner_cohort: str      = "general",
        metadata:     dict     | None = None,
    ) -> SearchIndex:
        entry = SearchIndex(
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            content=content,
            tags=tags or [],
            owner_cohort=owner_cohort,
            metadata=metadata or {},
        )
        key = (entity_type, entity_id)
        with self._lock:
            # Replace existing entry for same entity
            if key in self._entity_keys:
                old_idx = self._entity_keys[key]
                if old_idx < len(self._index):
                    old_entry = self._index[old_idx]
                    for tok in set(_tokenize(old_entry.searchable_text())):
                        self._df[tok] = max(0, self._df[tok] - 1)
                    self._index[old_idx] = entry
                    self._entity_keys[key] = old_idx
            else:
                if len(self._index) >= _MAX_INDEX:
                    removed = self._index.pop(0)
                    rkey = (removed.entity_type, removed.entity_id)
                    self._entity_keys.pop(rkey, None)
                    # rebuild entity_keys (shift indices)
                    self._entity_keys = {k: max(0, v - 1) for k, v in self._entity_keys.items()}
                self._entity_keys[key] = len(self._index)
                self._index.append(entry)
            # Update DF
            for tok in set(_tokenize(entry.searchable_text())):
                self._df[tok] += 1
        return entry

    def remove_entity(self, entity_type: str, entity_id: str) -> bool:
        key = (entity_type, entity_id)
        with self._lock:
            if key not in self._entity_keys:
                return False
            idx   = self._entity_keys.pop(key)
            entry = self._index.pop(idx)
            for tok in set(_tokenize(entry.searchable_text())):
                self._df[tok] = max(0, self._df[tok] - 1)
            # Re-index shifted positions
            self._entity_keys = {}
            for i, e in enumerate(self._index):
                self._entity_keys[(e.entity_type, e.entity_id)] = i
        return True

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query:        str,
        entity_types: list[str]  | None = None,
        owner_cohort: str        | None = None,
        limit:        int                = 20,
    ) -> list[SearchResult]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        with self._lock:
            entries  = list(self._index)
            n_docs   = len(entries)
            df_snap  = dict(self._df)

        results: list[SearchResult] = []
        for entry in entries:
            if entity_types and entry.entity_type not in entity_types:
                continue
            if owner_cohort and entry.owner_cohort not in (owner_cohort, "general"):
                continue
            score, matched = self._score(query_tokens, entry, n_docs, df_snap)
            if score > 0:
                results.append(SearchResult(
                    entity_type=entry.entity_type,
                    entity_id=entry.entity_id,
                    title=entry.title,
                    excerpt=_excerpt(entry.content or entry.title, query_tokens),
                    score=score,
                    matched_fields=matched,
                    metadata=entry.metadata,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    @staticmethod
    def _score(
        query_tokens: list[str],
        entry:        SearchIndex,
        n_docs:       int,
        df:           dict[str, int],
    ) -> tuple[float, list[str]]:
        title_tokens   = _tokenize(entry.title)
        content_tokens = _tokenize(entry.content)
        tag_tokens     = _tokenize(" ".join(entry.tags))
        all_tokens     = title_tokens + content_tokens + tag_tokens

        score   = 0.0
        matched = set()

        for term in query_tokens:
            idf = _idf(max(n_docs, 1), df.get(term, 0))
            if term in title_tokens:
                score  += _tf(title_tokens, term) * idf * 2.0
                matched.add("title")
            if term in content_tokens:
                score  += _tf(content_tokens, term) * idf * 1.0
                matched.add("content")
            if term in tag_tokens:
                score  += _tf(tag_tokens, term) * idf * 1.5
                matched.add("tags")

        return round(score, 6), sorted(matched)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            by_type: dict[str, int] = {}
            for e in self._index:
                by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1
        return {
            "total_indexed": len(self._index),
            "by_entity_type": by_type,
            "vocabulary_size": len(self._df),
        }
