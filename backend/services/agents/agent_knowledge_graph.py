"""Knowledge Graph Agent (Phase XIII) — entity and relationship extraction."""
from __future__ import annotations

import re
import time
from collections import Counter

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_CONCEPT_PATTERNS = [
    re.compile(r"\b(?:machine learning|deep learning|artificial intelligence|neural network)\b", re.IGNORECASE),
    re.compile(r"\b(?:natural language processing|nlp|text mining|information retrieval)\b", re.IGNORECASE),
    re.compile(r"\b(?:randomised controlled trial|rct|quasi[-\s]experiment|longitudinal study)\b", re.IGNORECASE),
    re.compile(r"\b(?:structural equation modelling?|sem|path analysis|confirmatory factor analysis)\b", re.IGNORECASE),
    re.compile(r"\b(?:grounded theory|thematic analysis|content analysis|discourse analysis)\b", re.IGNORECASE),
    re.compile(r"\b(?:systematic review|meta[-\s]analysis|scoping review|narrative review)\b", re.IGNORECASE),
    re.compile(r"\b(?:climate change|sustainability|renewable energy|carbon emissions)\b", re.IGNORECASE),
    re.compile(r"\b(?:public health|epidemiology|cardiovascular|mental health)\b", re.IGNORECASE),
    re.compile(r"\b(?:education technology|e[-\s]learning|blended learning|digital pedagogy)\b", re.IGNORECASE),
]

_AUTHOR_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:,?\s*\d{4}|\s*et\s+al\.?)", re.IGNORECASE)
_CONCEPT_WORD_RE = re.compile(r"\b[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,})?\b")

_RELATION_PATTERNS = [
    (re.compile(r"(\w+)\s+affects?\s+(\w+)", re.IGNORECASE),   "affects"),
    (re.compile(r"(\w+)\s+mediates?\s+(\w+)", re.IGNORECASE),  "mediates"),
    (re.compile(r"(\w+)\s+moderates?\s+(\w+)", re.IGNORECASE), "moderates"),
    (re.compile(r"(\w+)\s+predicts?\s+(\w+)", re.IGNORECASE),  "predicts"),
    (re.compile(r"(\w+)\s+causes?\s+(\w+)", re.IGNORECASE),    "causes"),
]


@AgentRegistry.register
class KnowledgeGraphAgent(AcademicAgent):
    agent_id = "knowledge_graph_agent_v1"
    agent_type = AgentType.KNOWLEDGE_GRAPH
    name = "Knowledge Graph Agent"
    domain = "Knowledge Graph & Entity Extraction"
    capabilities = [
        "entity_extraction", "concept_mapping", "relationship_detection",
        "author_network_building", "topic_clustering",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content

        # Extract named concepts using patterns
        concepts: list[str] = []
        for pattern in _CONCEPT_PATTERNS:
            concepts.extend(m.group(0) for m in pattern.finditer(text))

        # Author mentions
        authors = [m.group(1) for m in _AUTHOR_RE.finditer(text)]
        top_authors = [a for a, _ in Counter(authors).most_common(10)]

        # Relationships
        relationships: list[dict] = []
        for rx, rel_type in _RELATION_PATTERNS:
            for m in rx.finditer(text):
                relationships.append({
                    "source": m.group(1).lower(),
                    "target": m.group(2).lower(),
                    "relation": rel_type,
                })

        # Build simple graph nodes/edges
        unique_concepts = list(dict.fromkeys(c.lower() for c in concepts))[:20]
        nodes = [{"id": c, "type": "concept", "label": c} for c in unique_concepts]
        nodes += [{"id": f"author:{a}", "type": "author", "label": a} for a in top_authors[:10]]
        edges = [{"source": r["source"], "target": r["target"], "label": r["relation"]}
                 for r in relationships[:20]]

        # Thematic clusters (group concepts by co-occurrence)
        clusters: dict[str, list[str]] = {}
        if any("machine" in c or "learn" in c or "neural" in c for c in unique_concepts):
            clusters["AI/ML"] = [c for c in unique_concepts if any(kw in c for kw in ["machine", "learn", "neural", "nlp"])]
        if any("health" in c or "clinical" in c or "patient" in c for c in unique_concepts):
            clusters["Health/Medicine"] = [c for c in unique_concepts if any(kw in c for kw in ["health", "clinical", "patient", "epidemi"])]
        if any("method" in c or "analy" in c or "statist" in c for c in unique_concepts):
            clusters["Methodology"] = [c for c in unique_concepts if any(kw in c for kw in ["method", "analy", "statist", "review"])]

        confidence = min(0.85, 0.35 + 0.08 * min(len(unique_concepts), 5) + 0.05 * bool(relationships))

        output = {
            "total_concepts": len(unique_concepts),
            "concepts": unique_concepts[:15],
            "total_relationships": len(relationships),
            "relationships": relationships[:10],
            "top_authors": top_authors[:8],
            "thematic_clusters": {k: v[:5] for k, v in clusters.items()},
            "graph": {
                "nodes": nodes[:20],
                "edges": edges[:15],
            },
            "recommendations": [
                "Use VOSviewer or CiteSpace to visualise the full knowledge graph",
                "Identify central nodes — they represent core concepts to cite",
                "Isolated concepts may represent novelty opportunities",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Extracted {len(unique_concepts)} concepts, {len(relationships)} relationships, "
                f"{len(top_authors)} authors, {len(clusters)} thematic clusters."
            ),
            evidence=unique_concepts[:5] + [r["relation"] for r in relationships[:3]],
            t0=t0,
        )
