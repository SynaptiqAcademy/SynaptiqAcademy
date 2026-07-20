"""Benchmark Suite — evaluate intelligence engines against curated test cases."""
from __future__ import annotations

import time

# Each case: {"input": dict, "expected_outcome": str, optional quality_floor / quality_ceiling}
_BENCHMARK_CASES: dict[str, list[dict]] = {
    "publication_predictor": [
        {"input": {"methodology_score": 0.95, "novelty_score": 0.90, "prior_submissions": 0},
         "expected_outcome": "high_acceptance",  "quality_floor":   0.55},
        {"input": {"methodology_score": 0.25, "novelty_score": 0.20, "prior_submissions": 6},
         "expected_outcome": "low_acceptance",   "quality_ceiling": 0.45},
        {"input": {"methodology_score": 0.65, "novelty_score": 0.60, "prior_submissions": 1},
         "expected_outcome": "moderate_acceptance"},
    ],
    "journal_predictor": [
        {"input": {"methodology_score": 0.85, "novelty_score": 0.80}, "min_results": 3,
         "expected_outcome": "ranked_list"},
        {"input": {"keywords": ["deep learning", "neural networks"]},  "min_results": 1,
         "expected_outcome": "ranked_list"},
    ],
    "career_forecaster": [
        {"input": {"current_h_index": 3, "citations_per_year": 15, "career_stage": "phd_student"},
         "expected_outcome": "growing_h", "horizon": "3y"},
        {"input": {"current_h_index": 28, "citations_per_year": 180, "career_stage": "full_professor"},
         "expected_outcome": "high_h_sustained", "horizon": "5y"},
    ],
    "grant_predictor": [
        {"input": {"novelty_score": 0.88, "methodology_rigor": 0.90, "pi_h_index": 22,
                   "budget_justification_score": 0.85},
         "expected_outcome": "high_probability", "quality_floor": 0.25},
        {"input": {"novelty_score": 0.15, "methodology_rigor": 0.18, "pi_h_index": 1},
         "expected_outcome": "low_probability",  "quality_ceiling": 0.35},
    ],
    "trend_forecaster": [
        {"input": None,                                                  "expected_outcome": "has_emerging", "min_emerging": 1},
        {"input": {"research_domains": ["machine learning"]},           "expected_outcome": "domain_relevant"},
    ],
    "collaboration_forecaster": [
        {"input": {"prior_collaboration_history": True, "domains": ["NLP", "CV"],
                   "collaborators": [{"h_index": 15, "publications": 30, "domain": "NLP"}]},
         "expected_outcome": "positive_forecast"},
    ],
    "institution_forecaster": [
        {"input": {"avg_faculty_h_index": 20, "publications_per_year": 400,
                   "citations_per_year": 7000, "active_grants": 70},
         "expected_outcome": "growing_output", "horizon": "3y"},
    ],
}


# ── Per-engine evaluators ──────────────────────────────────────────────────────

def _eval_publication(case: dict) -> tuple[bool, float]:
    from services.prediction_intelligence.publication_predictor import predict_publication
    result = predict_publication(case["input"])
    acc    = result.acceptance.value
    eo     = case["expected_outcome"]
    if eo == "high_acceptance":
        return acc >= case.get("quality_floor", 0.50), acc
    if eo == "low_acceptance":
        return acc <= case.get("quality_ceiling", 0.45), round(1.0 - acc, 4)
    return True, round(max(acc, 1.0 - acc), 4)


def _eval_journal(case: dict) -> tuple[bool, float]:
    from services.prediction_intelligence.journal_predictor import predict_journals
    result = predict_journals(case["input"])
    n      = len(result.all_matches)
    return n >= case.get("min_results", 1), round(min(n / 5, 1.0), 4)


def _eval_career(case: dict) -> tuple[bool, float]:
    from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
    _map = {"1y": ForecastHorizon.ONE_YEAR, "3y": ForecastHorizon.THREE_YEAR,
            "5y": ForecastHorizon.FIVE_YEAR, "10y": ForecastHorizon.TEN_YEAR}
    h      = _map.get(case.get("horizon", "3y"), ForecastHorizon.THREE_YEAR)
    result = forecast_career(case["input"], h)
    init_h = case["input"].get("current_h_index", 0)
    passed = result.h_index.value >= init_h
    quality = round(min(result.h_index.value / max(init_h * 1.5, 1), 1.0), 4)
    return passed, quality


def _eval_grant(case: dict) -> tuple[bool, float]:
    from services.prediction_intelligence.grant_predictor import predict_grant
    result = predict_grant(case["input"])
    prob   = result.funding_probability.value
    eo     = case["expected_outcome"]
    if eo == "high_probability":
        return prob >= case.get("quality_floor", 0.25), prob
    return prob <= case.get("quality_ceiling", 0.35), round(1.0 - prob, 4)


def _eval_trend(case: dict) -> tuple[bool, float]:
    from services.prediction_intelligence.trend_forecaster import forecast_trends
    result = forecast_trends(case["input"])
    n      = len(result.emerging_topics)
    return n >= case.get("min_emerging", 1), round(min(n / 5, 1.0), 4)


def _eval_collaboration(case: dict) -> tuple[bool, float]:
    from services.prediction_intelligence.collaboration_forecaster import forecast_collaboration
    result = forecast_collaboration(case["input"])
    return result.success_probability.value > 0.0, round(result.success_probability.value, 4)


def _eval_institution(case: dict) -> tuple[bool, float]:
    from services.prediction_intelligence.institution_forecaster import forecast_institution, ForecastHorizon
    _map = {"1y": ForecastHorizon.ONE_YEAR, "3y": ForecastHorizon.THREE_YEAR, "5y": ForecastHorizon.FIVE_YEAR}
    h      = _map.get(case.get("horizon", "3y"), ForecastHorizon.THREE_YEAR)
    result = forecast_institution(case["input"], h)
    return result.publication_output.value > 0, round(min(result.publication_output.value / 1000, 1.0), 4)


_EVALUATORS = {
    "publication_predictor":   _eval_publication,
    "journal_predictor":       _eval_journal,
    "career_forecaster":       _eval_career,
    "grant_predictor":         _eval_grant,
    "trend_forecaster":        _eval_trend,
    "collaboration_forecaster": _eval_collaboration,
    "institution_forecaster":  _eval_institution,
}


def run_benchmark(engine_type: str) -> dict:
    cases = _BENCHMARK_CASES.get(engine_type, [])
    if not cases:
        return {"engine_type": engine_type, "status": "no_cases", "score": 0.0, "passed": 0, "total": 0}

    evaluator    = _EVALUATORS.get(engine_type)
    passed_count = 0
    quality_sum  = 0.0
    results      = []
    t0           = time.monotonic()

    for i, case in enumerate(cases):
        if evaluator is None:
            passed, quality = True, 0.70
        else:
            try:
                passed, quality = evaluator(case)
            except Exception as exc:
                passed, quality = False, 0.0
                results.append({"case": i, "passed": False, "quality": 0.0, "error": str(exc)})
                continue
        if passed:
            passed_count += 1
        quality_sum += quality
        results.append({"case": i, "passed": passed, "quality": round(quality, 4)})

    total   = len(cases)
    score   = round(quality_sum / total, 4) if total else 0.0
    elapsed = round(time.monotonic() - t0, 4)
    return {
        "engine_type": engine_type,
        "status":      "completed",
        "score":       score,
        "passed":      passed_count,
        "total":       total,
        "pass_rate":   round(passed_count / total, 4) if total else 0.0,
        "elapsed_seconds": elapsed,
        "results":     results,
    }


def run_all_benchmarks() -> dict:
    results = {et: run_benchmark(et) for et in _BENCHMARK_CASES}
    scores  = [r["score"] for r in results.values()]
    return {
        "engines":       results,
        "overall_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "ran_at":        time.time(),
    }
