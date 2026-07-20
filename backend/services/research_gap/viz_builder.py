"""Visualization builder for Research Gap Intelligence.

Produces 10 JSON-ready data structures for frontend rendering.
All outputs are framework-agnostic (Recharts, D3, custom).
"""
from __future__ import annotations

import math
from collections import Counter

from .models import (
    DetectedGap, GapType, GapSeverity, CompetitiveLandscape,
    GapAnalysisResult, OpportunityScore,
)


def build_all_visualizations(
    gaps: list[DetectedGap],
    landscape: CompetitiveLandscape,
    papers: list | None = None,
    saturation_map: dict | None = None,
) -> dict:
    """Build all 10 visualization data structures."""
    p = papers or []
    sm = saturation_map or {}
    return {
        "research_gap_map": build_research_gap_map(gaps),
        "knowledge_map": build_knowledge_map(gaps),
        "topic_evolution": build_topic_evolution(landscape),
        "gap_timeline": build_gap_timeline(gaps, p),
        "evidence_matrix": build_evidence_matrix(gaps),
        "concept_network": build_concept_network(gaps),
        "research_cluster_map": build_research_cluster_map(gaps),
        "novelty_heatmap": build_novelty_heatmap(gaps),
        "opportunity_matrix": build_opportunity_matrix(gaps),
        "research_roadmap_viz": build_research_roadmap_viz(gaps),
    }


def build_research_gap_map(gaps: list[DetectedGap]) -> dict:
    """2D bubble map: x=novelty, y=impact, size=feasibility, colour=gap_type."""
    nodes = [
        {
            "id": g.gap_id,
            "label": g.title[:50],
            "gap_type": g.gap_type.value,
            "x": round(g.opportunity_score.novelty_score, 3),
            "y": round(g.opportunity_score.research_impact, 3),
            "size": round(g.opportunity_score.feasibility_score, 3),
            "overall_score": round(g.opportunity_score.overall_score, 3),
            "severity": g.severity.value,
            "competition_level": g.competition_level.value,
        }
        for g in gaps
    ]
    return {
        "type": "research_gap_map",
        "axes": {"x": "Novelty Score", "y": "Research Impact", "size": "Feasibility"},
        "nodes": nodes,
        "total_gaps": len(nodes),
    }


def build_knowledge_map(gaps: list[DetectedGap]) -> dict:
    """Concept relationship network from gap types and keywords."""
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()

    for g in gaps:
        node_id = g.gap_type.value
        if node_id not in seen_nodes:
            nodes.append({
                "id": node_id,
                "label": g.gap_type.value.replace("_", " ").title(),
                "size": round(g.opportunity_score.overall_score * 40 + 10, 1),
                "color_group": _gap_type_color_group(g.gap_type),
            })
            seen_nodes.add(node_id)

    # Co-occurrence edges: gap types that share evidence keywords
    for i, g1 in enumerate(gaps):
        for g2 in gaps[i + 1:]:
            shared = set(g1.supporting_evidence) & set(g2.supporting_evidence)
            if shared or _types_are_related(g1.gap_type, g2.gap_type):
                edges.append({
                    "source": g1.gap_type.value,
                    "target": g2.gap_type.value,
                    "weight": len(shared) + 1,
                })

    return {"type": "knowledge_map", "nodes": nodes, "edges": edges}


def build_topic_evolution(landscape: CompetitiveLandscape) -> dict:
    """Timeline of topic maturity from competitive landscape data."""
    emerging = [{"topic": t, "status": "emerging", "trend": "rising"} for t in landscape.emerging_topics]
    declining = [{"topic": t, "status": "declining", "trend": "falling"} for t in landscape.declining_topics]
    established = [{"topic": t, "status": "established", "trend": "stable"} for t in landscape.competition_hotspots]

    all_topics = emerging + established + declining
    return {
        "type": "topic_evolution",
        "topics": all_topics,
        "maturity": landscape.research_maturity.value,
        "density": landscape.publication_density.value,
        "field_growth": landscape.field_growth_rate,
    }


def build_gap_timeline(gaps: list[DetectedGap], papers: list) -> dict:
    """Temporal distribution of when gap-relevant papers were published."""
    year_counts: Counter = Counter()
    for p in papers:
        yr = getattr(p, "year", None)
        if yr:
            year_counts[yr] += 1

    timeline = [{"year": yr, "papers": cnt} for yr, cnt in sorted(year_counts.items())]

    # Annotate with gap milestone events
    gap_annotations = []
    for g in gaps[:5]:
        gap_annotations.append({
            "label": g.title[:40],
            "gap_type": g.gap_type.value,
            "severity": g.severity.value,
        })

    return {
        "type": "gap_timeline",
        "publications_per_year": timeline,
        "gap_annotations": gap_annotations,
        "corpus_size": len(papers),
    }


def build_evidence_matrix(gaps: list[DetectedGap]) -> dict:
    """Matrix showing which gaps have evidence, publications, and contradictions."""
    rows = []
    for g in gaps:
        rows.append({
            "gap_id": g.gap_id,
            "gap_title": g.title[:45],
            "gap_type": g.gap_type.value,
            "evidence_count": len(g.supporting_evidence),
            "publication_count": len(g.supporting_publications),
            "contradiction_count": len(g.contradicting_evidence),
            "confidence": round(g.confidence_score, 2),
            "has_methodology": bool(g.methodology_recommendation.research_design),
            "has_rqs": bool(g.research_questions),
        })
    return {
        "type": "evidence_matrix",
        "rows": rows,
        "columns": ["gap_title", "evidence_count", "publication_count", "contradiction_count", "confidence"],
    }


def build_concept_network(gaps: list[DetectedGap]) -> dict:
    """Network of concepts extracted from gap descriptions and evidence."""
    word_freq: Counter = Counter()
    for g in gaps:
        words = _extract_keywords(g.title + " " + g.description)
        word_freq.update(words)

    top_words = [w for w, _ in word_freq.most_common(20) if len(w) > 4]
    nodes = [{"id": w, "label": w, "size": word_freq[w]} for w in top_words]

    edges: list[dict] = []
    for i, w1 in enumerate(top_words):
        for w2 in top_words[i + 1:]:
            # Co-occurrence in same gap
            count = sum(
                1 for g in gaps
                if w1 in (g.title + g.description).lower()
                and w2 in (g.title + g.description).lower()
            )
            if count >= 2:
                edges.append({"source": w1, "target": w2, "weight": count})

    return {"type": "concept_network", "nodes": nodes, "edges": edges[:30]}


def build_research_cluster_map(gaps: list[DetectedGap]) -> dict:
    """Group gaps into thematic clusters by gap type."""
    clusters: dict[str, list[dict]] = {}
    for g in gaps:
        key = g.gap_type.value
        if key not in clusters:
            clusters[key] = []
        clusters[key].append({
            "gap_id": g.gap_id,
            "title": g.title[:50],
            "overall_score": round(g.opportunity_score.overall_score, 3),
        })

    cluster_list = [
        {
            "cluster_id": k,
            "label": k.replace("_", " ").title(),
            "gaps": v,
            "cluster_size": len(v),
            "avg_score": round(sum(g["overall_score"] for g in v) / len(v), 3),
        }
        for k, v in clusters.items()
    ]
    cluster_list.sort(key=lambda c: -c["avg_score"])

    return {"type": "research_cluster_map", "clusters": cluster_list}


def build_novelty_heatmap(gaps: list[DetectedGap]) -> dict:
    """Heatmap of novelty scores across gap types and severity levels."""
    cells: list[dict] = []
    for g in gaps:
        cells.append({
            "gap_type": g.gap_type.value,
            "severity": g.severity.value,
            "novelty_score": round(g.opportunity_score.novelty_score, 3),
            "funding_potential": round(g.opportunity_score.funding_potential, 3),
            "citation_potential": round(g.opportunity_score.citation_potential, 3),
            "overall_score": round(g.opportunity_score.overall_score, 3),
        })
    return {"type": "novelty_heatmap", "cells": cells}


def build_opportunity_matrix(gaps: list[DetectedGap]) -> dict:
    """2×2 matrix: feasibility vs impact; quadrant labels."""
    quadrants: dict[str, list[dict]] = {
        "quick_wins": [],         # high feasibility, high impact
        "major_bets": [],         # low feasibility, high impact
        "incremental": [],        # high feasibility, low impact
        "low_priority": [],       # low feasibility, low impact
    }
    for g in gaps:
        feasibility = g.opportunity_score.feasibility_score
        impact = g.opportunity_score.research_impact
        if feasibility >= 0.55 and impact >= 0.60:
            q = "quick_wins"
        elif feasibility < 0.55 and impact >= 0.60:
            q = "major_bets"
        elif feasibility >= 0.55 and impact < 0.60:
            q = "incremental"
        else:
            q = "low_priority"
        quadrants[q].append({
            "gap_id": g.gap_id,
            "title": g.title[:45],
            "feasibility": round(feasibility, 2),
            "impact": round(impact, 2),
        })

    return {
        "type": "opportunity_matrix",
        "axes": {"x": "Feasibility", "y": "Research Impact"},
        "quadrants": quadrants,
    }


def build_research_roadmap_viz(gaps: list[DetectedGap]) -> dict:
    """Sequential priority roadmap: phase each gap by priority tier."""
    critical = [g for g in gaps if g.severity == GapSeverity.CRITICAL]
    high = [g for g in gaps if g.severity == GapSeverity.HIGH]
    medium = [g for g in gaps if g.severity == GapSeverity.MEDIUM]
    low = [g for g in gaps if g.severity == GapSeverity.LOW]

    phases = []
    for i, (tier, label, duration) in enumerate([
        (critical, "Immediate Priorities", "0–12 months"),
        (high, "Short-Term Opportunities", "1–2 years"),
        (medium, "Medium-Term Research", "2–4 years"),
        (low, "Long-Term Exploration", "4+ years"),
    ], start=1):
        if tier:
            phases.append({
                "phase": i,
                "label": label,
                "duration": duration,
                "gaps": [{"gap_id": g.gap_id, "title": g.title[:50]} for g in tier[:5]],
                "gap_count": len(tier),
            })

    return {"type": "research_roadmap_viz", "phases": phases}


# ── Helpers ────────────────────────────────────────────────────────────────────

_STOPWORDS = frozenset([
    "the", "and", "for", "this", "that", "with", "from", "are", "been",
    "have", "has", "was", "were", "not", "but", "can", "may", "will",
    "also", "into", "its", "their", "which", "than", "more", "such",
])


def _extract_keywords(text: str) -> list[str]:
    words = text.lower().split()
    return [
        w.strip(".,;:()") for w in words
        if len(w) > 4 and w not in _STOPWORDS
    ]


def _types_are_related(t1: GapType, t2: GapType) -> bool:
    related_groups = [
        {GapType.AI_GAP, GapType.TECHNOLOGICAL, GapType.DIGITAL_TRANSFORMATION},
        {GapType.HEALTHCARE, GapType.POPULATION, GapType.EMPIRICAL},
        {GapType.POLICY, GapType.PRACTICAL, GapType.EDUCATIONAL},
        {GapType.SUSTAINABILITY, GapType.INNOVATION, GapType.INDUSTRY},
        {GapType.THEORETICAL, GapType.METHODOLOGICAL, GapType.EMPIRICAL},
        {GapType.REGIONAL, GapType.POPULATION, GapType.INTERDISCIPLINARY},
    ]
    return any(t1 in g and t2 in g for g in related_groups)


def _gap_type_color_group(gap_type: GapType) -> str:
    groups = {
        "empirical": [GapType.EMPIRICAL, GapType.METHODOLOGICAL, GapType.THEORETICAL],
        "applied": [GapType.PRACTICAL, GapType.INDUSTRY, GapType.POLICY],
        "demographic": [GapType.REGIONAL, GapType.POPULATION, GapType.HEALTHCARE],
        "innovation": [GapType.TECHNOLOGICAL, GapType.AI_GAP, GapType.INNOVATION, GapType.DIGITAL_TRANSFORMATION],
        "strategic": [GapType.INTERDISCIPLINARY, GapType.SUSTAINABILITY, GapType.FUTURE_RESEARCH],
        "temporal": [GapType.TEMPORAL, GapType.EDUCATIONAL],
    }
    for group, types in groups.items():
        if gap_type in types:
            return group
    return "other"
