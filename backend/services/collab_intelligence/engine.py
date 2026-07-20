"""Research Collaboration Intelligence Engine — Main façade + async singleton (Phase XIV)."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from .admin_analytics import (
    grant_collaboration_stats,
    interdisciplinary_metrics,
    international_collaboration_map,
    platform_collaboration_stats,
    research_communities,
    top_collaborators,
    top_institutions,
)
from .insight_generator import generate_insights
from .introduction_generator import generate_introduction
from .matching_engine import match_researchers, rank_matches
from .models import (
    CollabMatch, ResearcherProfile, TeamType, VisualizationType,
)
from .network_analyzer import analyze_researcher_position, build_network
from .opportunity_detector import detect_opportunities
from .prediction_engine import predict_collaboration
from .recommendation_engine import generate_recommendations, serialize_recommendations
from .researcher_profiler import build_researcher_profile
from .social_graph import build_social_graph
from .team_optimizer import build_team
from .team_simulator import simulate_team
from .telemetry import get_telemetry
from .visualization_builder import (
    cluster_map, collaboration_heatmap, compatibility_matrix,
    country_network, expertise_map, impact_projection, institution_network, network_graph,
)


class CollabIntelligenceEngine:
    """
    Main façade for the Research Collaboration Intelligence Engine.

    All methods accept lightweight dicts (MongoDB documents) or
    pre-built ResearcherProfile objects and return serializable dicts.
    """

    # ── Profile ───────────────────────────────────────────────────────────────

    def build_profile(self, user_doc: dict) -> ResearcherProfile:
        tel = get_telemetry()
        tel.record("profile_builds")
        return build_researcher_profile(user_doc)

    def profile_to_dict(self, user_doc: dict) -> dict:
        return self.build_profile(user_doc).to_dict()

    # ── Matching ──────────────────────────────────────────────────────────────

    def match(
        self,
        user_a: dict,
        user_b: dict,
    ) -> dict:
        tel = get_telemetry()
        tel.record("match_computations")
        t0 = time.monotonic()
        pa = build_researcher_profile(user_a)
        pb = build_researcher_profile(user_b)
        m = match_researchers(pa, pb)
        tel.record_latency(time.monotonic() - t0)
        return m.to_dict()

    def rank_candidates(
        self,
        source_user: dict,
        candidate_users: list[dict],
        top_n: int = 10,
    ) -> list[dict]:
        tel = get_telemetry()
        tel.record("match_computations")
        source = build_researcher_profile(source_user)
        candidates = [build_researcher_profile(u) for u in candidate_users]
        matches = rank_matches(source, candidates, top_n)
        return [m.to_dict() for m in matches]

    # ── Opportunities ─────────────────────────────────────────────────────────

    def find_opportunities(
        self,
        source_user: dict,
        candidate_users: list[dict],
        top_n: int = 10,
    ) -> list[dict]:
        tel = get_telemetry()
        tel.record("opportunity_scans")
        source = build_researcher_profile(source_user)
        candidates = [build_researcher_profile(u) for u in candidate_users]
        opps = detect_opportunities(source, candidates, top_n)
        return [o.to_dict() for o in opps]

    # ── Team building ─────────────────────────────────────────────────────────

    def build_team(
        self,
        candidate_users: list[dict],
        objective: str,
        team_type: str = "interdisciplinary",
        required_concepts: list[str] | None = None,
        max_size: int | None = None,
    ) -> dict:
        tel = get_telemetry()
        tel.record("team_builds")
        candidates = [build_researcher_profile(u) for u in candidate_users]
        try:
            tt = TeamType(team_type)
        except ValueError:
            tt = TeamType.INTERDISCIPLINARY
        team = build_team(candidates, objective, tt, required_concepts, max_size)
        return team.to_dict()

    # ── Team simulation ───────────────────────────────────────────────────────

    def simulate_team(
        self,
        team_users: list[dict],
        objective: str,
    ) -> dict:
        tel = get_telemetry()
        tel.record("team_simulations")
        profiles = [build_researcher_profile(u) for u in team_users]
        sim = simulate_team(profiles, objective)
        return sim.to_dict()

    # ── Smart introductions ───────────────────────────────────────────────────

    def introduce(
        self,
        user_a: dict,
        user_b: dict,
    ) -> dict:
        tel = get_telemetry()
        tel.record("introductions")
        pa = build_researcher_profile(user_a)
        pb = build_researcher_profile(user_b)
        intro = generate_introduction(pa, pb)
        return intro.to_dict()

    # ── Network analysis ──────────────────────────────────────────────────────

    def analyze_network(
        self,
        user_docs: list[dict],
        similarity_threshold: float = 0.35,
    ) -> dict:
        tel = get_telemetry()
        tel.record("network_analyses")
        profiles = [build_researcher_profile(u) for u in user_docs]
        network = build_network(profiles, similarity_threshold)
        return network.to_dict()

    def researcher_network_position(
        self,
        source_user: dict,
        all_users: list[dict],
    ) -> dict:
        source = build_researcher_profile(source_user)
        profiles = [build_researcher_profile(u) for u in all_users]
        network = build_network(profiles)
        return analyze_researcher_position(source, network)

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(
        self,
        user_a: dict,
        user_b: dict,
    ) -> dict:
        tel = get_telemetry()
        tel.record("predictions")
        pa = build_researcher_profile(user_a)
        pb = build_researcher_profile(user_b)
        pred = predict_collaboration(pa, pb)
        return pred.to_dict()

    # ── Recommendations ───────────────────────────────────────────────────────

    def recommendations(
        self,
        source_user: dict,
        candidate_users: list[dict],
        include_types: list[str] | None = None,
        top_n: int = 10,
    ) -> dict:
        tel = get_telemetry()
        tel.record("recommendation_runs")
        source = build_researcher_profile(source_user)
        candidates = [build_researcher_profile(u) for u in candidate_users]
        recs = generate_recommendations(source, candidates, include_types, top_n)
        return serialize_recommendations(recs)

    # ── Insights ──────────────────────────────────────────────────────────────

    def insights(
        self,
        source_user: dict,
        all_users: list[dict] | None = None,
    ) -> list[dict]:
        tel = get_telemetry()
        tel.record("insight_runs")
        source = build_researcher_profile(source_user)
        profiles = [build_researcher_profile(u) for u in (all_users or [])]
        return [i.to_dict() for i in generate_insights(source, profiles)]

    # ── Social graph ──────────────────────────────────────────────────────────

    def social_graph(
        self,
        user_docs: list[dict],
        include_topics: bool = True,
        include_methods: bool = True,
        include_institutions: bool = True,
    ) -> dict:
        profiles = [build_researcher_profile(u) for u in user_docs]
        graph = build_social_graph(profiles, include_topics, include_methods, include_institutions)
        return graph.to_dict()

    # ── Visualizations ────────────────────────────────────────────────────────

    def visualization(
        self,
        viz_type: str,
        user_docs: list[dict],
        source_user: dict | None = None,
    ) -> dict:
        profiles = [build_researcher_profile(u) for u in user_docs]

        if viz_type == VisualizationType.NETWORK_GRAPH.value:
            net = build_network(profiles)
            return network_graph(net).to_dict()

        if viz_type == VisualizationType.HEATMAP.value:
            from .matching_engine import rank_matches
            matches: list[CollabMatch] = []
            for i, pa in enumerate(profiles):
                for pb in profiles[i + 1:]:
                    from .matching_engine import match_researchers
                    matches.append(match_researchers(pa, pb))
            return collaboration_heatmap(profiles, matches).to_dict()

        if viz_type == VisualizationType.EXPERTISE_MAP.value:
            return expertise_map(profiles).to_dict()

        if viz_type == VisualizationType.INSTITUTION_NET.value:
            return institution_network(profiles).to_dict()

        if viz_type == VisualizationType.COUNTRY_NET.value:
            return country_network(profiles).to_dict()

        if viz_type == VisualizationType.CLUSTER_MAP.value:
            net = build_network(profiles)
            return cluster_map(net).to_dict()

        if viz_type == VisualizationType.IMPACT_PROJECTION.value:
            if source_user:
                src = build_researcher_profile(source_user)
                return impact_projection(src, collaboration_added=True).to_dict()

        return {"error": f"Unknown visualization type: {viz_type}"}

    # ── Admin analytics ───────────────────────────────────────────────────────

    def admin_analytics(self, user_docs: list[dict]) -> dict:
        profiles = [build_researcher_profile(u) for u in user_docs]
        matches: list[CollabMatch] = []
        for i, pa in enumerate(profiles):
            for pb in profiles[i + 1:]:
                matches.append(match_researchers(pa, pb))

        network = build_network(profiles)

        return {
            "platform_stats":             platform_collaboration_stats(profiles, matches),
            "top_collaborators":          top_collaborators(profiles),
            "top_institutions":           top_institutions(profiles),
            "research_communities":       research_communities(network),
            "international_map":          international_collaboration_map(profiles),
            "interdisciplinary_metrics":  interdisciplinary_metrics(profiles),
            "grant_collaboration_stats":  grant_collaboration_stats(profiles),
            "telemetry":                  get_telemetry().snapshot(),
        }


# ── Async singleton ───────────────────────────────────────────────────────────

_lock     = asyncio.Lock()
_instance: CollabIntelligenceEngine | None = None


async def get_collab_engine() -> CollabIntelligenceEngine:
    global _instance
    if _instance is None:
        async with _lock:
            if _instance is None:
                _instance = CollabIntelligenceEngine()
    return _instance


def reset_collab_engine() -> None:
    global _instance
    _instance = None
