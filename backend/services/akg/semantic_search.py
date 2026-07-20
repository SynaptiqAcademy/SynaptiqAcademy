"""Semantic search over the AKG using TF-IDF scoring.

No LLM calls. Pure rule-based keyword expansion + cosine similarity over
stored entity embeddings (stored as keyword-frequency dicts in akg_entities).
"""
from __future__ import annotations
import math
import re
from lkg.unified import get_unified_graph


def _tokenise(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z][a-z0-9]*", text)
    stopwords = {"the", "a", "an", "and", "or", "of", "in", "on", "at", "to",
                 "for", "with", "by", "from", "is", "are", "was", "be"}
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def _tfidf_vector(doc_tokens: list[str]) -> dict[str, float]:
    tf: dict[str, int] = {}
    for t in doc_tokens:
        tf[t] = tf.get(t, 0) + 1
    total = max(len(doc_tokens), 1)
    return {k: v / total for k, v in tf.items()}


def _cosine(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    keys = set(vec_a) & set(vec_b)
    if not keys:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    return dot / (mag_a * mag_b) if mag_a * mag_b else 0.0


def _entity_text(entity: dict) -> str:
    etype = entity.get("type") or entity.get("entity_type", "")
    parts = [
        entity.get("label", ""),
        etype.replace("_", " "),
    ]
    props = entity.get("properties", {})
    for field in ("description", "keywords", "research_interests", "expertise",
                  "tags", "topics", "research_area", "department", "headline"):
        val = props.get(field)
        if isinstance(val, list):
            parts.extend(val)
        elif isinstance(val, str):
            parts.append(val)
    return " ".join(str(p) for p in parts)


async def semantic_search(query: str, db,
                           entity_types: list[str] | None = None,
                           limit: int = 20) -> list[dict]:
    """Score all entities by TF-IDF cosine similarity to query."""
    query_tokens = _tokenise(query)
    if not query_tokens:
        return []
    query_vec = _tfidf_vector(query_tokens)

    akg_filter: dict = {}
    if entity_types:
        akg_filter["entity_type"] = {"$in": entity_types}

    # Pre-filter: at least one query token appears in the entity text fields
    if len(query_tokens) <= 5:
        regex_parts = [{"label": {"$regex": t, "$options": "i"}} for t in query_tokens[:3]]
        prop_parts  = [{"properties.keywords": {"$regex": t, "$options": "i"}} for t in query_tokens[:3]]
        prop_parts2 = [{"properties.description": {"$regex": t, "$options": "i"}} for t in query_tokens[:3]]
        akg_filter["$or"] = regex_parts + prop_parts + prop_parts2

    candidates = await get_unified_graph().find_nodes(db, akg_filter, limit=500)

    scored: list[tuple[float, dict]] = []
    for doc in candidates:
        doc_text  = _entity_text(doc)
        doc_vec   = _tfidf_vector(_tokenise(doc_text))
        sim       = _cosine(query_vec, doc_vec)
        if sim > 0:
            doc.pop("_id", None)
            doc["search_score"] = round(sim, 4)
            doc["match_reason"] = _explain(query_tokens, doc)
            scored.append((sim, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def _explain(query_tokens: list[str], entity: dict) -> str:
    text = _entity_text(entity).lower()
    hits = [t for t in query_tokens if t in text]
    if not hits:
        return "Semantic match"
    return f"Matches: {', '.join(hits[:5])}"


async def search_suggestions(prefix: str, db, limit: int = 10) -> list[str]:
    """Autocomplete on entity labels."""
    if len(prefix) < 2:
        return []
    docs = await get_unified_graph().find_nodes(
        db, {"label": {"$regex": f"^{re.escape(prefix)}", "$options": "i"}}, limit=limit
    )
    return [d["label"] for d in docs if d.get("label")]
