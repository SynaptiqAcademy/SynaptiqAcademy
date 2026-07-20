"""Academic Prediction — Journal ranking & selection predictor (Phase XVIII)."""
from __future__ import annotations

from .confidence_model import compute_confidence
from .models import JournalMatch, JournalPredictionResult

# Built-in journal database (12 representative journals)
_JOURNAL_DB: list[dict] = [
    {
        "name": "Nature",
        "domains": ["biology", "physics", "chemistry", "interdisciplinary"],
        "impact_factor": 69.5,
        "acceptance_rate": 0.08,
        "avg_review_weeks": 8,
        "scope_keywords": ["breakthrough", "discovery", "fundamental", "paradigm"],
        "tier": 1,
    },
    {
        "name": "Science",
        "domains": ["biology", "physics", "chemistry", "interdisciplinary"],
        "impact_factor": 56.9,
        "acceptance_rate": 0.07,
        "avg_review_weeks": 10,
        "scope_keywords": ["discovery", "fundamental", "groundbreaking", "transformative"],
        "tier": 1,
    },
    {
        "name": "PNAS",
        "domains": ["biology", "chemistry", "physics", "social science", "computer science"],
        "impact_factor": 12.8,
        "acceptance_rate": 0.17,
        "avg_review_weeks": 12,
        "scope_keywords": ["significant", "broad interest", "multidisciplinary"],
        "tier": 2,
    },
    {
        "name": "Nature Communications",
        "domains": ["biology", "physics", "chemistry", "materials", "computer science"],
        "impact_factor": 16.6,
        "acceptance_rate": 0.33,
        "avg_review_weeks": 14,
        "scope_keywords": ["new findings", "original", "advance"],
        "tier": 2,
    },
    {
        "name": "Scientific Reports",
        "domains": ["biology", "physics", "chemistry", "engineering", "computer science"],
        "impact_factor": 4.6,
        "acceptance_rate": 0.55,
        "avg_review_weeks": 10,
        "scope_keywords": ["valid", "sound methodology", "reproducible"],
        "tier": 3,
    },
    {
        "name": "PLOS ONE",
        "domains": ["all"],
        "impact_factor": 3.7,
        "acceptance_rate": 0.69,
        "avg_review_weeks": 9,
        "scope_keywords": ["methodologically sound", "valid", "reproducible"],
        "tier": 3,
    },
    {
        "name": "Journal of Machine Learning Research",
        "domains": ["computer science", "machine learning", "AI", "statistics"],
        "impact_factor": 6.0,
        "acceptance_rate": 0.25,
        "avg_review_weeks": 20,
        "scope_keywords": ["machine learning", "algorithm", "neural network", "deep learning"],
        "tier": 2,
    },
    {
        "name": "NeurIPS",
        "domains": ["computer science", "machine learning", "AI", "neural networks"],
        "impact_factor": 9.5,
        "acceptance_rate": 0.26,
        "avg_review_weeks": 16,
        "scope_keywords": ["deep learning", "neural", "optimization", "representation"],
        "tier": 1,
    },
    {
        "name": "Nature Medicine",
        "domains": ["medicine", "biology", "clinical", "biomedical"],
        "impact_factor": 87.2,
        "acceptance_rate": 0.05,
        "avg_review_weeks": 10,
        "scope_keywords": ["clinical", "medical", "patient", "therapeutic", "health"],
        "tier": 1,
    },
    {
        "name": "BMJ",
        "domains": ["medicine", "clinical", "public health", "epidemiology"],
        "impact_factor": 39.9,
        "acceptance_rate": 0.06,
        "avg_review_weeks": 8,
        "scope_keywords": ["clinical", "medical", "health", "patient", "trial"],
        "tier": 1,
    },
    {
        "name": "Frontiers in Psychology",
        "domains": ["psychology", "social science", "neuroscience", "cognitive"],
        "impact_factor": 4.2,
        "acceptance_rate": 0.61,
        "avg_review_weeks": 11,
        "scope_keywords": ["psychology", "behavior", "cognitive", "mental", "neuroscience"],
        "tier": 3,
    },
    {
        "name": "Sustainability",
        "domains": ["sustainability", "environmental", "ecology", "social science", "economics"],
        "impact_factor": 3.9,
        "acceptance_rate": 0.65,
        "avg_review_weeks": 12,
        "scope_keywords": ["sustainable", "environment", "green", "climate", "ecology"],
        "tier": 3,
    },
]


def _scope_overlap(manuscript_keywords: list[str], journal: dict) -> float:
    """Compute scope match [0, 1] from keyword overlap with journal domains + scope keywords."""
    if not manuscript_keywords:
        return 0.50
    jnl_terms = set()
    for d in journal.get("domains", []):
        jnl_terms.update(d.lower().split())
    for kw in journal.get("scope_keywords", []):
        jnl_terms.update(kw.lower().split())

    ms_terms = set()
    for kw in manuscript_keywords:
        ms_terms.update(kw.lower().split())

    if "all" in journal.get("domains", []):
        return 0.75  # PLOS ONE / open-scope journals

    overlap = len(ms_terms & jnl_terms)
    return min(1.0, overlap / max(len(ms_terms), 1) + 0.10)


def _compute_reviewer_concerns(manuscript: dict, journal: dict) -> list[str]:
    concerns: list[str] = []
    q = float(manuscript.get("methodology_score", 0.5))
    if q < 0.5:
        concerns.append("Methodology rigour insufficient for this journal's standards.")
    if float(manuscript.get("novelty_score", 0.5)) < 0.5:
        concerns.append("Novelty and significance need stronger justification.")
    if float(manuscript.get("statistical_quality", 0.5)) < 0.5:
        concerns.append("Statistical analysis requires improvement.")
    if int(manuscript.get("reference_count", 30)) < 20:
        concerns.append("Literature review appears incomplete; insufficient references.")
    return concerns or ["Standard peer-review process anticipated."]


def predict_journals(manuscript: dict, max_results: int = 8) -> JournalPredictionResult:
    """Rank all built-in journals for a manuscript and return structured result."""
    m   = manuscript or {}
    kws = m.get("keywords") or []
    q   = float(m.get("methodology_score", 0.5)) * 0.5 + float(m.get("novelty_score", 0.5)) * 0.5

    matches: list[JournalMatch] = []
    for jnl in _JOURNAL_DB:
        scope      = _scope_overlap(kws, jnl)
        base_acc   = float(jnl["acceptance_rate"])
        acc        = max(0.01, min(0.98, base_acc + (q - 0.5) * 0.30 + (scope - 0.5) * 0.20))
        rej_risk   = max(0.01, min(0.95, 1.0 - acc))
        speed      = float(jnl["avg_review_weeks"])
        # recommendation score: balance acceptance, impact, speed, scope
        rec_score = (
            acc * 0.35 +
            min(jnl["impact_factor"] / 100.0, 1.0) * 0.25 +
            (1.0 - speed / 30.0) * 0.20 +
            scope * 0.20
        )
        matches.append(JournalMatch(
            journal_name=jnl["name"],
            acceptance_probability=round(acc, 3),
            impact_score=round(min(jnl["impact_factor"] / 100.0, 1.0), 3),
            publication_speed_weeks=speed,
            rejection_risk=round(rej_risk, 3),
            scope_match=round(scope, 3),
            reviewer_concerns=_compute_reviewer_concerns(m, jnl),
            editor_concerns=(["Broad-interest justification needed."] if jnl["tier"] == 1 else []),
            recommendation_score=round(rec_score, 3),
        ))

    matches.sort(key=lambda j: -j.recommendation_score)
    top = matches[:max_results]

    best         = top[0]
    highest_imp  = max(top, key=lambda j: j.impact_score)
    fastest      = min(top, key=lambda j: j.publication_speed_weeks)
    lowest_rej   = min(top, key=lambda j: j.rejection_risk)

    dc   = 0.5 + min(len(kws) / 10.0, 0.5)
    conf = compute_confidence(dc, signal_quality_val(q, best.scope_match), "publication_acceptance")

    return JournalPredictionResult(
        best_journal=best,
        highest_impact=highest_imp,
        fastest_publication=fastest,
        lowest_rejection=lowest_rej,
        all_matches=top,
        confidence=round(conf, 3),
        reasoning=(
            f"Ranked {len(_JOURNAL_DB)} journals; best overall: {best.journal_name} "
            f"(acc={round(best.acceptance_probability*100)}%, "
            f"rec_score={best.recommendation_score})."
        ),
    )


def signal_quality_val(*vals: float) -> float:
    v = [max(0.0, min(1.0, x)) for x in vals if x is not None]
    return sum(v) / max(len(v), 1)
