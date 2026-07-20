"""Academic Prediction — Research trend forecasting engine (Phase XVIII)."""
from __future__ import annotations

from .confidence_model import compute_confidence
from .models import ResearchTrend, TrendForecastResult

# Curated trend database with domain-level signals
_TREND_DB: list[dict] = [
    {"topic": "Large Language Models",          "type": "hot",      "score": 0.97, "growth": 0.45, "funding": ["NSF", "ERC", "DARPA"]},
    {"topic": "Foundation Models",              "type": "emerging", "score": 0.93, "growth": 0.40, "funding": ["NIH", "ERC", "UKRI"]},
    {"topic": "AI for Science",                 "type": "emerging", "score": 0.91, "growth": 0.38, "funding": ["NSF", "ERC", "Wellcome"]},
    {"topic": "Multimodal AI",                  "type": "hot",      "score": 0.89, "growth": 0.35, "funding": ["NSF", "EU Horizon"]},
    {"topic": "Quantum Computing",              "type": "emerging", "score": 0.85, "growth": 0.30, "funding": ["NSF", "ERC", "BMBF"]},
    {"topic": "Federated Learning",             "type": "emerging", "score": 0.80, "growth": 0.28, "funding": ["EU Horizon", "NSF"]},
    {"topic": "Explainable AI",                 "type": "emerging", "score": 0.82, "growth": 0.25, "funding": ["DARPA", "ERC"]},
    {"topic": "Climate AI",                     "type": "hot",      "score": 0.88, "growth": 0.32, "funding": ["ERC", "Wellcome", "ARPA-E"]},
    {"topic": "Synthetic Biology",              "type": "emerging", "score": 0.78, "growth": 0.22, "funding": ["NIH", "ERC", "BBSRC"]},
    {"topic": "Digital Twins",                  "type": "emerging", "score": 0.76, "growth": 0.20, "funding": ["EU Horizon", "Innovate UK"]},
    {"topic": "Neuromorphic Computing",         "type": "emerging", "score": 0.72, "growth": 0.18, "funding": ["DARPA", "EU Horizon"]},
    {"topic": "Drug Discovery AI",              "type": "hot",      "score": 0.86, "growth": 0.33, "funding": ["NIH", "Wellcome", "Pharma"]},
    {"topic": "Graph Neural Networks",          "type": "hot",      "score": 0.83, "growth": 0.27, "funding": ["NSF", "ERC"]},
    {"topic": "Causal Inference",               "type": "emerging", "score": 0.75, "growth": 0.20, "funding": ["NIH", "NSF"]},
    {"topic": "Responsible AI",                 "type": "hot",      "score": 0.87, "growth": 0.30, "funding": ["EU Horizon", "UKRI", "NSF"]},
    {"topic": "Traditional Statistics Only",    "type": "declining","score": 0.35, "growth": -0.10, "funding": []},
    {"topic": "Manual Literature Review",       "type": "declining","score": 0.30, "growth": -0.15, "funding": []},
    {"topic": "Single-centre Observational Studies", "type": "declining", "score": 0.28, "growth": -0.12, "funding": []},
    {"topic": "Non-reproducible Research",      "type": "declining","score": 0.15, "growth": -0.20, "funding": []},
    {"topic": "Protein Structure Prediction",   "type": "hot",      "score": 0.90, "growth": 0.35, "funding": ["Wellcome", "NIH", "ERC"]},
]

_FUTURE_METHODOLOGIES: list[dict] = [
    {"method": "AI-assisted peer review",       "adoption": 0.65, "timeline": "1-3y"},
    {"method": "Automated reproducibility checks", "adoption": 0.70, "timeline": "1-2y"},
    {"method": "Multi-modal data fusion",       "adoption": 0.75, "timeline": "1-3y"},
    {"method": "Federated multi-site studies",  "adoption": 0.60, "timeline": "2-4y"},
    {"method": "Simulation-augmented datasets", "adoption": 0.55, "timeline": "2-5y"},
]

_FUTURE_TECHNOLOGIES: list[dict] = [
    {"technology": "AI co-pilots for writing",  "readiness": 0.90, "timeline": "now"},
    {"technology": "Autonomous lab robots",     "readiness": 0.55, "timeline": "2-5y"},
    {"technology": "Real-time citation networks","readiness": 0.80, "timeline": "1-2y"},
    {"technology": "Graph-based literature maps","readiness": 0.85, "timeline": "now"},
    {"technology": "Predictive peer review",    "readiness": 0.60, "timeline": "2-4y"},
]


def _domain_relevance(trend_topic: str, domains: list[str]) -> float:
    """Return relevance score of a trend topic to a list of research domains."""
    if not domains:
        return 0.5
    topic_terms = set(trend_topic.lower().split())
    for d in domains:
        domain_terms = set(d.lower().split())
        if topic_terms & domain_terms:
            return 0.9
    return 0.3


def forecast_trends(profile: dict | None = None, top_k: int = 8) -> TrendForecastResult:
    """Forecast research trends. Optionally personalised to profile domains."""
    p = profile or {}
    domains = list(p.get("research_domains") or [])
    kws     = [kw.lower() for kw in (p.get("keywords") or [])]
    all_terms = domains + kws

    emerging   : list[ResearchTrend] = []
    declining  : list[ResearchTrend] = []
    hot        : list[ResearchTrend] = []

    for entry in _TREND_DB:
        relevance = _domain_relevance(entry["topic"], all_terms) if all_terms else 0.70
        final_score = min(1.0, entry["score"] * (0.5 + relevance * 0.5))
        conf = compute_confidence(0.7, final_score, "trend_emergence")
        trend = ResearchTrend(
            topic=entry["topic"],
            trend_type=entry["type"],
            score=round(final_score, 3),
            growth_rate=entry["growth"],
            confidence=round(conf, 3),
            evidence=[
                f"Global trend score: {entry['score']}",
                f"Domain relevance to your research: {round(relevance * 100)}%",
            ],
            time_horizon="3y",
            related_funding=entry["funding"],
        )
        if entry["type"] == "emerging":
            emerging.append(trend)
        elif entry["type"] == "declining":
            declining.append(trend)
        elif entry["type"] == "hot":
            hot.append(trend)

    emerging.sort(key=lambda t: -t.score)
    hot.sort(key=lambda t: -t.score)
    declining.sort(key=lambda t: t.score)  # lowest first

    avg_conf = sum(t.confidence for t in emerging + hot) / max(len(emerging) + len(hot), 1)

    return TrendForecastResult(
        emerging_topics=emerging[:top_k],
        declining_topics=declining[:top_k],
        hot_topics=hot[:top_k],
        funding_priorities=[
            {"priority": "AI and Machine Learning", "funding_growth": "high", "agencies": ["NSF", "ERC", "UKRI"]},
            {"priority": "Climate & Sustainability", "funding_growth": "high", "agencies": ["ERC", "ARPA-E", "Wellcome"]},
            {"priority": "Health & Biomedical AI",  "funding_growth": "very_high", "agencies": ["NIH", "Wellcome", "ERC"]},
            {"priority": "Quantum Technologies",    "funding_growth": "moderate", "agencies": ["EU Horizon", "BMBF"]},
        ],
        journal_trends=[
            {"trend": "AI-themed special issues proliferating across all disciplines", "impact": "high"},
            {"trend": "Open Access mandates expanding globally", "impact": "high"},
            {"trend": "Data availability statements becoming mandatory", "impact": "medium"},
        ],
        conference_trends=[
            {"trend": "Hybrid / virtual formats here to stay", "impact": "medium"},
            {"trend": "Workshop acceptance rates growing faster than main tracks", "impact": "medium"},
            {"trend": "AI ethics track added to most major venues", "impact": "high"},
        ],
        future_methodologies=_FUTURE_METHODOLOGIES,
        future_technologies=_FUTURE_TECHNOLOGIES,
        confidence=round(avg_conf, 3),
    )
