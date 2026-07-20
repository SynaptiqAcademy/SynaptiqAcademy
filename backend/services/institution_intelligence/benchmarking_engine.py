"""Institution Intelligence Engine — Benchmarking Engine (Phase XV).

Compares institution KPIs against a synthetic peer benchmark.
Pure Python, deterministic.
"""
from __future__ import annotations

from .models import BenchmarkResult, InstitutionKPIs


# ── Synthetic peer benchmarks ─────────────────────────────────────────────────
# (representative averages for mid-tier European research universities)

_PEER_BENCHMARKS: dict[str, tuple[float, float]] = {
    # metric: (peer_average, top_quartile)
    "publication_output_per_researcher": (3.0, 6.0),
    "publication_growth":                (0.05, 0.12),
    "citation_growth":                   (0.06, 0.15),
    "avg_h_index":                       (8.0, 16.0),
    "avg_fwci":                          (1.0, 2.0),
    "grant_success_rate":                (0.35, 0.60),
    "q1_ratio":                          (0.35, 0.65),
    "collaboration_score":               (0.30, 0.60),
    "internationalization_score":        (0.30, 0.60),
    "innovation_score":                  (0.20, 0.45),
    "open_science_score":                (0.30, 0.55),
    "research_efficiency":               (0.30, 0.65),
    "sustainability_score":              (0.35, 0.65),
    "reputation_score":                  (0.40, 0.75),
    "faculty_performance":               (0.40, 0.70),
    "department_performance":            (0.35, 0.65),
    "doctoral_activity_score":           (0.25, 0.50),
}


def _percentile(value: float, peer_avg: float, top: float) -> float:
    """Approximate percentile based on triangular distribution."""
    if value <= 0:
        return 0.0
    if value >= top:
        return 0.95
    if value <= peer_avg:
        return max(0.0, 0.50 * (value / max(peer_avg, 0.001)))
    return 0.50 + 0.45 * ((value - peer_avg) / max(top - peer_avg, 0.001))


def _trend(value: float, peer_avg: float) -> str:
    if value > peer_avg * 1.1:
        return "above_average"
    if value < peer_avg * 0.9:
        return "below_average"
    return "average"


def _recommendation(metric: str, percentile: float, own: float, peer_avg: float) -> str:
    if percentile >= 0.75:
        return f"Leading position — maintain and leverage for reputation."
    if percentile >= 0.50:
        return f"At peer average — targeted investment could push to top quartile."
    return f"Below average (own={own:.2f} vs peer={peer_avg:.2f}) — prioritise improvement."


def benchmark(kpis: InstitutionKPIs, n_researchers: int) -> list[BenchmarkResult]:
    """Compare institution KPIs against synthetic peer benchmarks."""
    results: list[BenchmarkResult] = []

    def _add(metric_key: str, own_value: float) -> None:
        if metric_key not in _PEER_BENCHMARKS:
            return
        peer_avg, peer_top = _PEER_BENCHMARKS[metric_key]
        pct   = _percentile(own_value, peer_avg, peer_top)
        delta = round(own_value - peer_avg, 3)
        results.append(BenchmarkResult(
            metric=metric_key,
            own_value=round(own_value, 3),
            peer_avg=peer_avg,
            peer_top=peer_top,
            percentile=round(pct, 3),
            trend=_trend(own_value, peer_avg),
            delta_vs_peer=delta,
            recommendation=_recommendation(metric_key, pct, own_value, peer_avg),
        ))

    # Normalise publication output per researcher
    pub_per_r = kpis.publication_output / max(n_researchers, 1)
    _add("publication_output_per_researcher", pub_per_r)
    _add("publication_growth",                kpis.publication_growth)
    _add("citation_growth",                   kpis.citation_growth)
    _add("avg_h_index",                       kpis.avg_h_index)
    _add("avg_fwci",                          kpis.avg_fwci)
    _add("grant_success_rate",                kpis.grant_success_rate)
    _add("q1_ratio",                          kpis.q1_ratio)
    _add("collaboration_score",               kpis.collaboration_score)
    _add("internationalization_score",        kpis.internationalization_score)
    _add("innovation_score",                  kpis.innovation_score)
    _add("open_science_score",                kpis.open_science_score)
    _add("research_efficiency",               kpis.research_efficiency)
    _add("sustainability_score",              kpis.sustainability_score)
    _add("reputation_score",                  kpis.reputation_score)
    _add("faculty_performance",               kpis.faculty_performance)
    _add("department_performance",            kpis.department_performance)
    _add("doctoral_activity_score",           kpis.doctoral_activity_score)

    return sorted(results, key=lambda r: r.percentile)


def benchmark_summary(results: list[BenchmarkResult]) -> dict:
    if not results:
        return {"strengths": [], "weaknesses": [], "overall_percentile": 0.0}
    avg_pct    = sum(r.percentile for r in results) / len(results)
    strengths  = sorted([r for r in results if r.percentile >= 0.65],
                        key=lambda r: -r.percentile)[:5]
    weaknesses = sorted([r for r in results if r.percentile < 0.35],
                        key=lambda r: r.percentile)[:5]
    return {
        "overall_percentile": round(avg_pct, 3),
        "strengths":          [r.to_dict() for r in strengths],
        "weaknesses":         [r.to_dict() for r in weaknesses],
        "total_metrics":      len(results),
        "above_average":      sum(1 for r in results if r.percentile >= 0.50),
        "below_average":      sum(1 for r in results if r.percentile < 0.50),
    }
