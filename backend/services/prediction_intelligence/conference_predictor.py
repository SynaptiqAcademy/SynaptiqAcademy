"""Academic Prediction — Conference outcome predictor (Phase XVIII)."""
from __future__ import annotations

from .confidence_model import compute_confidence, data_completeness, signal_quality
from .models import ConferencePrediction, PredictionType, _make_prediction

_CONF_KEYS = ["manuscript_quality", "novelty_score", "presenter_experience",
              "conference_tier", "domain_match"]

# Built-in conference database (simplified)
_CONFERENCE_DB: list[dict] = [
    {"name": "NeurIPS",    "tier": 1, "acceptance_rate": 0.26, "networking": 0.95, "domains": ["machine learning", "AI", "deep learning"]},
    {"name": "ICML",       "tier": 1, "acceptance_rate": 0.22, "networking": 0.92, "domains": ["machine learning", "optimization"]},
    {"name": "CVPR",       "tier": 1, "acceptance_rate": 0.25, "networking": 0.90, "domains": ["computer vision", "image recognition"]},
    {"name": "ACL",        "tier": 1, "acceptance_rate": 0.24, "networking": 0.88, "domains": ["NLP", "computational linguistics"]},
    {"name": "ICLR",       "tier": 1, "acceptance_rate": 0.32, "networking": 0.93, "domains": ["deep learning", "representation learning"]},
    {"name": "EMNLP",      "tier": 2, "acceptance_rate": 0.30, "networking": 0.82, "domains": ["NLP", "natural language processing"]},
    {"name": "IJCAI",      "tier": 2, "acceptance_rate": 0.15, "networking": 0.80, "domains": ["AI", "machine learning"]},
    {"name": "MICCAI",     "tier": 1, "acceptance_rate": 0.30, "networking": 0.85, "domains": ["medical imaging", "biomedical", "clinical AI"]},
    {"name": "ECCV",       "tier": 1, "acceptance_rate": 0.28, "networking": 0.87, "domains": ["computer vision", "image processing"]},
    {"name": "SIGKDD",     "tier": 1, "acceptance_rate": 0.19, "networking": 0.88, "domains": ["data mining", "knowledge discovery"]},
]


def predict_conference(profile: dict) -> list[ConferencePrediction]:
    """Predict conference outcomes for top matching conferences."""
    p = profile or {}
    q          = float(p.get("manuscript_quality", 0.55))
    novelty    = float(p.get("novelty_score", 0.50))
    exp        = float(p.get("presenter_experience", 0.50))
    domain_kws = [kw.lower() for kw in (p.get("keywords") or [])]
    target_tier = int(p.get("conference_tier", 2))

    results: list[ConferencePrediction] = []
    for conf in _CONFERENCE_DB:
        if abs(conf["tier"] - target_tier) > 1:
            continue  # only adjacent tiers

        # Domain match
        if domain_kws:
            conf_terms = set()
            for d in conf["domains"]:
                conf_terms.update(d.lower().split())
            ms_terms = set()
            for kw in domain_kws:
                ms_terms.update(kw.split())
            scope = min(1.0, len(ms_terms & conf_terms) / max(len(ms_terms), 1) + 0.15)
        else:
            scope = 0.50

        base_acc = conf["acceptance_rate"]
        acc      = max(0.02, min(0.95, base_acc + (q - 0.5) * 0.35 + (novelty - 0.5) * 0.15))

        networking  = float(conf["networking"]) * scope
        career_imp  = (acc * 0.4 + min(1.0 - conf["tier"] / 3.0, 0.7) * 0.4 + exp * 0.2)
        pub_opp     = max(0.2, acc * 0.7 + scope * 0.3)

        dc   = data_completeness(p, _CONF_KEYS)
        conf_val = compute_confidence(dc, signal_quality(q, novelty, scope), "publication_acceptance")

        results.append(ConferencePrediction(
            conference_name=conf["name"],
            acceptance_probability=_make_prediction(
                PredictionType.PUBLICATION_ACCEPTANCE, acc, conf_val,
                evidence=[f"Acceptance rate: {round(base_acc*100)}%", f"Domain match: {round(scope*100)}%"],
                reasoning=f"Quality {round(q,2)} × scope {round(scope,2)} adjusted from base {round(base_acc,2)}.",
            ),
            presentation_quality=_make_prediction(
                PredictionType.COLLABORATION_SUCCESS, exp, conf_val * 0.9,
                evidence=[f"Presenter experience score: {round(exp,2)}"],
                reasoning="Presentation quality derived from presenter experience signal.",
            ),
            networking_value=_make_prediction(
                PredictionType.COLLABORATION_SUCCESS, networking, conf_val,
                evidence=[f"Conference networking score: {conf['networking']}"],
                reasoning="Networking value scaled by conference prestige and domain alignment.",
            ),
            future_collaborations=_make_prediction(
                PredictionType.COLLABORATION_SUCCESS, networking * 0.7, conf_val * 0.85,
                reasoning="Future collaborations proportional to networking value and domain overlap.",
            ),
            career_impact=_make_prediction(
                PredictionType.PROMOTION_READINESS, max(0.0, min(1.0, career_imp)), conf_val,
                reasoning="Career impact from acceptance × prestige tier × presenter experience.",
            ),
            publication_opportunities=_make_prediction(
                PredictionType.COLLABORATION_SUCCESS, max(0.0, min(1.0, pub_opp)), conf_val,
                reasoning="Publication follow-up probability from acceptance and scope match.",
            ),
            overall_score=round((acc * 0.4 + networking * 0.3 + career_imp * 0.3), 3),
            recommendation=(
                f"Submit to {conf['name']} — "
                f"{'strong' if acc >= 0.4 else 'moderate'} acceptance fit."
            ),
        ))

    results.sort(key=lambda r: -r.overall_score)
    return results[:5]
