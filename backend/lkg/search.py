"""Natural language graph search — intent-aware query over LKG nodes and edges."""
from __future__ import annotations

import logging
import re
from typing import Optional

from .graph_store import search_nodes
from .models import NODE_TYPES

logger = logging.getLogger("lkg.search")

# Known entity type hints in queries
TYPE_HINTS: list[tuple[list[str], str]] = [
    (["researcher", "author", "scientist", "professor", "phd", "postdoc"], "researcher"),
    (["institution", "university", "college", "lab", "department"], "institution"),
    (["paper", "publication", "article", "preprint"], "publication"),
    (["journal", "magazine"], "journal"),
    (["grant", "funding", "award", "fellowship"], "funding_program"),
    (["conference", "symposium", "workshop"], "conference"),
    (["dataset", "data"], "dataset"),
    (["software", "tool", "code", "library"], "software"),
    (["topic", "area", "field", "domain"], "topic"),
    (["keyword"], "keyword"),
    (["method", "methodology"], "method"),
    (["project", "initiative"], "project"),
    (["manuscript"], "manuscript"),
]

LOCATION_PREFIXES = ["in ", "from ", "at "]


def _extract_intent(query: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Extract: (clean_search_term, entity_type_hint, location_hint)
    Example: "AI researchers in Romania" → ("AI Romania", "researcher", "Romania")
    """
    text = query.lower()

    # Detect entity type
    entity_type = None
    for hints, etype in TYPE_HINTS:
        if any(h in text for h in hints):
            entity_type = etype
            break

    # Detect location
    location = None
    for prefix in LOCATION_PREFIXES:
        idx = text.find(prefix)
        if idx != -1:
            after = text[idx + len(prefix):].strip()
            location = after.split()[0].capitalize() if after.split() else None
            break

    # Remove stop words for cleaner search
    clean = re.sub(
        r"\b(find|show|who|which|what|the|a|an|is|are|for|on|about|give me|list)\b",
        " ", text,
    )
    clean = " ".join(clean.split())

    return clean, entity_type, location


async def natural_language_search(db, query: str, limit: int = 20) -> dict:
    """
    Search the Living Knowledge Graph using natural language.

    Approach:
      1. Extract entity type hint and location from query
      2. MongoDB text search with clean query terms
      3. AI interpretation of results (optional enrichment)

    EVIDENCE POLICY: only returns nodes that exist in the graph.
    Never invents results.
    """
    clean_query, entity_type, location = _extract_intent(query)

    types = [entity_type] if entity_type else None
    results = await search_nodes(db, clean_query, types=types, limit=limit * 2)

    # Filter by location if detected
    if location:
        filtered = [
            r for r in results
            if location.lower() in str(r.get("metadata", {})).lower()
            or location.lower() in r.get("label", "").lower()
        ]
        if filtered:
            results = filtered

    # Score and rank
    scored = []
    for r in results[:limit]:
        score = 1.0
        if entity_type and r.get("type") == entity_type:
            score += 2.0
        if r.get("confidence") == "high":
            score += 1.0
        scored.append({**r, "_relevance": score})

    scored.sort(key=lambda x: x.get("_relevance", 0), reverse=True)

    # Use AI to provide a natural-language interpretation of results
    interpretation = None
    if scored:
        try:
            from services.ai.llm import call_llm
            result_summary = "\n".join(
                f"- {r.get('label', 'Unknown')} ({r.get('type', '?')})" +
                (f" at {r['metadata'].get('institution', '')}" if r.get("metadata", {}).get("institution") else "")
                for r in scored[:8]
            )
            interpretation = await call_llm(
                system=(
                    "You summarize search results from an academic knowledge graph. "
                    "Only describe what is explicitly listed — never add information. "
                    "Be concise (2-3 sentences max)."
                ),
                user_msg=f"Query: {query}\n\nResults found:\n{result_summary}\n\nSummarize what was found.",
                feature="lkg.search",
                max_tokens=200,
            )
        except Exception:
            pass

    return {
        "query":           query,
        "intent":          {"entity_type": entity_type, "location": location, "clean_query": clean_query},
        "results":         [
            {k: v for k, v in r.items() if k != "_relevance"}
            for r in scored[:limit]
        ],
        "total_found":     len(scored),
        "interpretation":  interpretation,
        "source":          "Synaptiq LKG database — only existing graph nodes returned",
        "policy_note":     "Results are limited to entities present in the graph. No results are invented.",
    }
