"""Academic Prediction — Collaboration outcome forecaster (Phase XVIII)."""
from __future__ import annotations

from .confidence_model import compute_confidence, data_completeness, signal_quality
from .models import CollaborationForecast, PredictionType, _make_prediction

_COLLAB_KEYS = ["collaborators", "collaboration_type", "duration_planned_months",
                "domains", "geographic_spread"]


def forecast_collaboration(profile: dict) -> CollaborationForecast:
    p = profile or {}

    collabs  = p.get("collaborators") or []
    avg_h    = (sum(c.get("h_index", 0) for c in collabs) / max(len(collabs), 1)) if collabs else 0
    team_q   = min(avg_h / 20.0, 1.0)
    prior    = 0.20 if p.get("prior_collaboration_history", False) else 0.0
    domains  = list(p.get("domains") or [])
    intdisc  = min(len(set(domains)) / 4.0, 1.0) * 0.15
    dur      = float(p.get("duration_planned_months", 12))
    dur_score = min(dur / 36.0, 1.0)
    geo_spread = int(p.get("geographic_spread", 1))
    geo_boost  = min(geo_spread / 5.0, 1.0) * 0.10

    success = max(0.05, min(0.95,
        0.45 + team_q * 0.25 + prior + intdisc + dur_score * 0.05 + geo_boost
    ))

    # Expected publications (per year of collaboration)
    pub_output = max(0.1, min(10.0, (team_q * 3.0 + len(collabs) * 0.5) * (dur / 12.0) * 0.5))

    # Expected citation impact boost (%)
    cit_boost = max(0.0, min(1.0, team_q * 0.40 + intdisc * 0.30 + geo_boost * 2.0))

    # Grant competitiveness boost
    grant_boost = max(0.0, min(1.0, team_q * 0.30 + (len(collabs) / 10.0) * 0.20 + prior * 0.5))

    # Team productivity
    team_prod = max(0.0, min(1.0, success * 0.6 + team_q * 0.4))

    # Research longevity (probability collaboration leads to long-term partnership)
    longevity = max(0.0, min(1.0, prior * 0.3 + dur_score * 0.4 + team_q * 0.3))

    # Interdisciplinary impact
    interdisciplinary = max(0.0, min(1.0, intdisc * 4.0 + geo_boost * 2.0))

    dc   = data_completeness(p, _COLLAB_KEYS)
    sq   = signal_quality(team_q, success, dur_score)
    conf = compute_confidence(dc, sq, "collaboration_success")

    team_names = [c.get("name", f"Collaborator {i+1}") for i, c in enumerate(collabs[:3])]
    evidence = [
        f"Team quality (avg h-index): {round(avg_h, 1)}",
        f"Prior collaboration history: {'Yes' if p.get('prior_collaboration_history') else 'No'}",
        f"Collaboration domains: {', '.join(domains[:3]) or 'Not specified'}",
        f"Geographic spread: {geo_spread} countries",
    ]

    rec = (
        "Strong team — proceed with collaboration plan."
        if success >= 0.65 else
        "Moderate fit — establish shared research agenda before committing."
        if success >= 0.45 else
        "Consider expanding team quality or aligning research goals first."
    )

    return CollaborationForecast(
        success_probability=_make_prediction(
            PredictionType.COLLABORATION_SUCCESS, success, conf,
            evidence=evidence,
            recommendations=["Define clear authorship agreements", "Set milestone checkpoints"],
            reasoning=f"Success probability from team quality, history, and interdisciplinarity.",
        ),
        expected_publications=_make_prediction(
            PredictionType.CITATION_VELOCITY, pub_output, conf * 0.85,
            unit="publications", clamp_probability=False,
            evidence=[f"Duration: {int(dur)} months", f"Team size: {len(collabs)}"],
            reasoning="Expected joint publication output scaled by team quality and duration.",
        ),
        expected_citation_impact=_make_prediction(
            PredictionType.CITATION_GROWTH, cit_boost, conf * 0.80,
            evidence=[f"Interdisciplinary factor: {round(intdisc, 2)}"],
            reasoning="Citation impact boost from international and interdisciplinary exposure.",
        ),
        grant_competitiveness_boost=_make_prediction(
            PredictionType.GRANT_SCORE, grant_boost, conf * 0.80,
            evidence=[f"Collaboration breadth: {len(collabs)} partners"],
            reasoning="Grant panels reward multi-institutional, international teams.",
        ),
        team_productivity=_make_prediction(
            PredictionType.COLLABORATION_SUCCESS, team_prod, conf,
            evidence=[f"Team quality: {round(team_q, 2)}"],
            reasoning="Team productivity from success probability × team quality.",
        ),
        research_longevity=_make_prediction(
            PredictionType.COLLABORATION_SUCCESS, longevity, conf * 0.75,
            evidence=[f"Planned duration: {int(dur)} months", "Prior history: " + ("Yes" if p.get("prior_collaboration_history") else "No")],
            reasoning="Long-term partnership probability from prior history and planned duration.",
        ),
        interdisciplinary_impact=_make_prediction(
            PredictionType.TREND_EMERGENCE, interdisciplinary, conf * 0.75,
            evidence=[f"Domains: {len(set(domains))}"],
            reasoning="Interdisciplinary impact driven by domain diversity and geographic spread.",
        ),
        overall_recommendation=rec,
        confidence=round(conf, 3),
    )
