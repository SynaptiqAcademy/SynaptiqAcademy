"""Research Collaboration Intelligence — Visualization Builder (Phase XIV).

Produces structured data for all 9 visualization types that the frontend
(D3.js / Recharts) can consume directly.
"""
from __future__ import annotations

from collections import defaultdict

from .models import (
    CollabMatch, ResearcherProfile, ResearchNetwork,
    VisualizationData, VisualizationType,
)


def network_graph(network: ResearchNetwork) -> VisualizationData:
    """D3-force-compatible JSON graph."""
    return VisualizationData(
        viz_type=VisualizationType.NETWORK_GRAPH,
        data=network.to_dict(),
        metadata={"format": "d3-force", "directed": False},
    )


def collaboration_heatmap(
    profiles: list[ResearcherProfile],
    matches: list[CollabMatch],
) -> VisualizationData:
    """NxN compatibility matrix for a heatmap chart."""
    uid_to_name = {p.user_id: p.name or p.user_id for p in profiles}
    score_map: dict[tuple[str, str], float] = {}
    for m in matches:
        score_map[(m.researcher_a_id, m.researcher_b_id)] = m.overall_score
        score_map[(m.researcher_b_id, m.researcher_a_id)] = m.overall_score

    rows: list[dict] = []
    for pa in profiles:
        for pb in profiles:
            if pa.user_id == pb.user_id:
                score = 1.0
            else:
                score = score_map.get((pa.user_id, pb.user_id), 0.0)
            rows.append({
                "x": uid_to_name[pb.user_id],
                "y": uid_to_name[pa.user_id],
                "value": round(score, 3),
            })

    return VisualizationData(
        viz_type=VisualizationType.HEATMAP,
        data={"matrix": rows, "labels": list(uid_to_name.values())},
        metadata={"format": "heatmap-matrix", "metric": "compatibility_score"},
    )


def expertise_map(profiles: list[ResearcherProfile]) -> VisualizationData:
    """Bubble chart: expertise areas sized by # researchers."""
    domain_counts: dict[str, int] = defaultdict(int)
    for p in profiles:
        for d in p.domains:
            domain_counts[d.lower()] += 1

    bubbles = [
        {"id": d, "label": d.replace("_", " ").title(), "value": count}
        for d, count in sorted(domain_counts.items(), key=lambda x: -x[1])[:30]
    ]
    return VisualizationData(
        viz_type=VisualizationType.EXPERTISE_MAP,
        data={"bubbles": bubbles},
        metadata={"format": "bubble-chart"},
    )


def institution_network(profiles: list[ResearcherProfile]) -> VisualizationData:
    """Sankey-compatible edges between institutions, sized by co-researcher count."""
    inst_pairs: dict[tuple[str, str], int] = defaultdict(int)
    inst_list = [p.institution for p in profiles if p.institution]

    for i, pa in enumerate(profiles):
        for pb in profiles[i + 1:]:
            if pa.institution and pb.institution and pa.institution != pb.institution:
                key = tuple(sorted([pa.institution, pb.institution]))
                inst_pairs[key] += 1  # type: ignore

    links = [
        {"source": pair[0], "target": pair[1], "value": count}
        for pair, count in sorted(inst_pairs.items(), key=lambda x: -x[1])[:20]
    ]
    all_institutions = sorted({p.institution for p in profiles if p.institution})

    return VisualizationData(
        viz_type=VisualizationType.INSTITUTION_NET,
        data={"nodes": [{"id": i} for i in all_institutions], "links": links},
        metadata={"format": "sankey"},
    )


def country_network(profiles: list[ResearcherProfile]) -> VisualizationData:
    """Chord-compatible edges between countries."""
    country_pairs: dict[tuple[str, str], int] = defaultdict(int)
    for i, pa in enumerate(profiles):
        for pb in profiles[i + 1:]:
            if pa.country and pb.country and pa.country != pb.country:
                key = tuple(sorted([pa.country, pb.country]))
                country_pairs[key] += 1  # type: ignore

    links = [
        {"source": pair[0], "target": pair[1], "value": count}
        for pair, count in sorted(country_pairs.items(), key=lambda x: -x[1])[:15]
    ]
    return VisualizationData(
        viz_type=VisualizationType.COUNTRY_NET,
        data={"links": links},
        metadata={"format": "chord"},
    )


def cluster_map(network: ResearchNetwork) -> VisualizationData:
    """Group nodes by cluster for a cluster map."""
    return VisualizationData(
        viz_type=VisualizationType.CLUSTER_MAP,
        data={"clusters": network.clusters, "nodes": [n.to_dict() for n in network.nodes]},
        metadata={"format": "cluster-map"},
    )


def compatibility_matrix(
    profiles: list[ResearcherProfile],
    matches: list[CollabMatch],
) -> VisualizationData:
    """Full compatibility matrix as a table."""
    uid_to_name = {p.user_id: p.name or p.user_id for p in profiles}
    score_map: dict[tuple[str, str], dict] = {}
    for m in matches:
        entry = {
            "overall": m.overall_score,
            "similarity": m.research_similarity,
            "complementarity": m.complementarity,
            "collab_type": m.collab_type.value,
        }
        score_map[(m.researcher_a_id, m.researcher_b_id)] = entry
        score_map[(m.researcher_b_id, m.researcher_a_id)] = entry

    rows = []
    for pa in profiles:
        row = {"researcher": uid_to_name[pa.user_id]}
        for pb in profiles:
            if pa.user_id == pb.user_id:
                row[uid_to_name[pb.user_id]] = {"overall": 1.0}
            else:
                row[uid_to_name[pb.user_id]] = score_map.get((pa.user_id, pb.user_id), {"overall": 0.0})
        rows.append(row)

    return VisualizationData(
        viz_type=VisualizationType.COMPATIBILITY,
        data={"rows": rows},
        metadata={"format": "matrix-table"},
    )


def impact_projection(
    profile: ResearcherProfile,
    collaboration_added: bool = False,
) -> VisualizationData:
    """Projected citation/h-index trajectory with/without collaboration."""
    base_h     = profile.h_index
    base_cites = profile.citation_count
    growth_rate = 0.1 + profile.productivity_score * 0.1  # 10-20% annual
    collab_mult = 1.4 if collaboration_added else 1.0

    years = list(range(0, 6))
    projections = []
    for y in years:
        proj_cites = round(base_cites * (1 + growth_rate) ** y * collab_mult, 1)
        proj_h     = round(base_h   * (1 + growth_rate * 0.5) ** y * (collab_mult ** 0.3), 1)
        projections.append({
            "year": f"Year {y}",
            "citations": proj_cites,
            "h_index": proj_h,
            "scenario": "with collaboration" if collaboration_added else "baseline",
        })

    return VisualizationData(
        viz_type=VisualizationType.IMPACT_PROJECTION,
        data={"projections": projections, "user_id": profile.user_id},
        metadata={"format": "line-chart", "units": {"citations": "count", "h_index": "score"}},
    )
