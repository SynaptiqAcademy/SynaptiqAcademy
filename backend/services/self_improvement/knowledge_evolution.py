"""Knowledge Evolution Engine — detect and integrate emerging academic knowledge."""
from __future__ import annotations

import threading
import time
from collections import defaultdict

from .models import KnowledgeUpdate

_KNOWN_FIELDS: set = {
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "robotics", "bioinformatics", "quantum computing",
    "climate science", "neuroscience", "materials science",
    "synthetic biology", "genomics", "drug discovery", "epidemiology",
    "computational biology", "astrophysics", "nanotechnology",
}

_KNOWN_METHODOLOGIES: set = {
    "transformer", "cnn", "rnn", "lstm", "bert", "gpt", "rag",
    "meta-learning", "federated learning", "reinforcement learning",
    "bayesian inference", "causal inference", "graph neural networks",
    "diffusion models", "contrastive learning", "active learning",
    "zero-shot learning", "few-shot learning",
}

_KNOWN_JOURNALS: set = {
    "nature", "science", "pnas", "nature communications", "scientific reports",
    "plos one", "cell", "lancet", "nejm", "jmlr", "neurips", "icml",
}

_KNOWN_CONFERENCES: set = {
    "neurips", "icml", "cvpr", "acl", "iclr", "emnlp", "ijcai",
    "iccv", "aaai", "kdd", "sigkdd", "eccv",
}

_KNOWN_TECHNOLOGIES: set = {
    "gpu", "tpu", "quantum processor", "edge computing", "cloud computing",
    "blockchain", "iot", "5g", "hpc", "neuromorphic",
}

_CATEGORY_SETS: dict[str, set] = {
    "research_field": _KNOWN_FIELDS,
    "methodology":    _KNOWN_METHODOLOGIES,
    "journal":        _KNOWN_JOURNALS,
    "conference":     _KNOWN_CONFERENCES,
    "technology":     _KNOWN_TECHNOLOGIES,
}


def _bigrams(word_list: list[str]) -> set[str]:
    return {f"{word_list[i]} {word_list[i+1]}" for i in range(len(word_list) - 1)}


class KnowledgeEvolutionEngine:
    def __init__(self):
        self._lock:     threading.Lock            = threading.Lock()
        self._updates:  dict[str, KnowledgeUpdate] = {}   # key → update
        self._evidence: dict[str, int]            = defaultdict(int)

    def ingest_text(self, text: str, source: str = "user") -> list[KnowledgeUpdate]:
        """Scan text for concepts not yet in known sets; register as candidates."""
        word_list  = text.lower().split()
        candidates = set(word_list) | _bigrams(word_list)
        detected   = []

        for cat, known in _CATEGORY_SETS.items():
            for term in candidates:
                if len(term) < 4 or term in known:
                    continue
                if any(k in term or term in k for k in known):
                    key = f"{cat}:{term}"
                    with self._lock:
                        self._evidence[key] += 1
                        if key not in self._updates:
                            upd = KnowledgeUpdate(
                                category=cat,
                                item=term,
                                evidence_count=1,
                                confidence=0.10,
                                status="detected",
                            )
                            self._updates[key] = upd
                            detected.append(upd)
                        else:
                            upd = self._updates[key]
                            upd.evidence_count += 1
                            upd.confidence = round(min(upd.evidence_count / 10, 0.95), 4)
        return detected

    def detect_from_keywords(self, keywords: list[str]) -> list[KnowledgeUpdate]:
        return self.ingest_text(" ".join(keywords))

    def get_pending_updates(self, min_confidence: float = 0.0) -> list[KnowledgeUpdate]:
        with self._lock:
            return [u for u in self._updates.values()
                    if u.status == "detected" and u.confidence >= min_confidence]

    def validate_update(self, update_id: str) -> KnowledgeUpdate | None:
        with self._lock:
            for upd in self._updates.values():
                if upd.update_id == update_id:
                    upd.status = "validated"
                    return upd
        return None

    def integrate_update(self, update_id: str) -> bool:
        with self._lock:
            for upd in self._updates.values():
                if upd.update_id == update_id and upd.status == "validated":
                    upd.status        = "integrated"
                    upd.integrated_at = time.time()
                    cat_set = _CATEGORY_SETS.get(upd.category)
                    if cat_set is not None:
                        cat_set.add(upd.item)
                    return True
        return False

    def reject_update(self, update_id: str) -> bool:
        with self._lock:
            for upd in self._updates.values():
                if upd.update_id == update_id:
                    upd.status = "rejected"
                    return True
        return False

    def get_all_updates(self) -> list[KnowledgeUpdate]:
        with self._lock:
            return list(self._updates.values())

    def summary(self) -> dict:
        with self._lock:
            all_u = list(self._updates.values())
        by_status: dict[str, int] = {}
        for u in all_u:
            by_status[u.status] = by_status.get(u.status, 0) + 1
        return {
            "total": len(all_u),
            "by_status": by_status,
            "known_fields":        len(_KNOWN_FIELDS),
            "known_methodologies": len(_KNOWN_METHODOLOGIES),
            "known_journals":      len(_KNOWN_JOURNALS),
            "known_conferences":   len(_KNOWN_CONFERENCES),
            "known_technologies":  len(_KNOWN_TECHNOLOGIES),
        }
