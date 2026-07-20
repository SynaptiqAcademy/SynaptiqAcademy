"""Institution Intelligence Engine — Main Façade (Phase XV).

InstitutionIntelligenceEngine wraps all 11 service modules.
Accepts raw dicts / lists from MongoDB, returns serializable dicts.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from .benchmarking_engine import benchmark, benchmark_summary
from .decision_support import generate_recommendations
from .export_engine import generate_export
from .institution_profiler import build_institution_profile
from .knowledge_graph import build_knowledge_graph
from .kpi_engine import compute_kpis
from .models import (
    ExportFormat, ExportReportType, ForecastType, InstitutionInput,
    RecommendationAudience, VizType,
)
from .monitoring_engine import monitor
from .organizational_intelligence import detect_organizational_insights
from .portfolio_analyzer import analyse_portfolio, portfolio_summary
from .prediction_engine import predict_institution
from .resource_optimizer import optimise_resources
from .risk_engine import detect_risks
from .talent_intelligence import identify_talent, serialize_talent
from .telemetry import get_telemetry
from .visualization_builder import build_visualization


class InstitutionIntelligenceEngine:
    """AI Chief Research Officer — strategic intelligence engine for institutions."""

    def _parse_input(self, data: dict) -> InstitutionInput:
        return InstitutionInput(
            name=data.get("name") or data.get("institution_name") or "",
            institution_type=data.get("institution_type") or data.get("type") or "university",
            country=data.get("country") or "",
            founding_year=int(data.get("founding_year") or 0),
            researchers=data.get("researchers") or [],
            grants=data.get("grants") or [],
            publications=data.get("publications") or [],
            projects=data.get("projects") or [],
            departments=data.get("departments") or [],
            total_budget=float(data.get("total_budget") or 0),
            total_students=int(data.get("total_students") or 0),
            metadata=data.get("metadata") or {},
        )

    def _timed(self, counter: str):
        """Context manager that records telemetry for a service call."""
        class _Timer:
            def __init__(self_, c: str) -> None:
                self_._counter = c
                self_._start   = 0.0
            def __enter__(self_):
                self_._start = time.monotonic()
                return self_
            def __exit__(self_, *_):
                elapsed = time.monotonic() - self_._start
                tel = get_telemetry()
                tel.record(self_._counter)
                tel.record_latency(elapsed)
        return _Timer(counter)

    # ── Public API ─────────────────────────────────────────────────────────────

    def build_profile(self, data: dict) -> dict:
        with self._timed("profile_builds"):
            inp     = self._parse_input(data)
            profile = build_institution_profile(inp)
            kpis    = compute_kpis(inp)
            profile.kpis = kpis
        return profile.to_dict()

    def compute_kpis(self, data: dict) -> dict:
        with self._timed("kpi_computations"):
            inp  = self._parse_input(data)
            kpis = compute_kpis(inp)
        return kpis.to_dict()

    def organizational_intelligence(self, data: dict) -> dict:
        with self._timed("org_intelligence_runs"):
            inp      = self._parse_input(data)
            insights = detect_organizational_insights(inp)
        return {
            "insights":       [i.to_dict() for i in insights],
            "total":          len(insights),
            "by_severity":    {
                sev: sum(1 for i in insights if i.severity.value == sev)
                for sev in ["critical", "high", "medium", "low", "minimal"]
            },
        }

    def predict(self, data: dict, horizon: int = 3) -> dict:
        with self._timed("predictions"):
            inp       = self._parse_input(data)
            forecasts = predict_institution(inp, horizon=horizon)
        return {
            "forecasts":      [f.to_dict() for f in forecasts],
            "horizon_years":  horizon,
            "total":          len(forecasts),
        }

    def optimise_resources(self, data: dict) -> dict:
        with self._timed("resource_optimizations"):
            inp   = self._parse_input(data)
            kpis  = compute_kpis(inp)
            allocs = optimise_resources(inp, kpis)
        return {
            "allocations": [a.to_dict() for a in allocs],
            "total": len(allocs),
        }

    def talent_intelligence(self, data: dict) -> dict:
        with self._timed("talent_analyses"):
            inp    = self._parse_input(data)
            talent = identify_talent(inp)
        return serialize_talent(talent)

    def analyse_portfolio(self, data: dict) -> dict:
        with self._timed("portfolio_analyses"):
            inp       = self._parse_input(data)
            portfolio = analyse_portfolio(inp)
            summary   = portfolio_summary(portfolio)
        return {
            "portfolio": [p.to_dict() for p in portfolio],
            "summary":   summary,
        }

    def benchmark_institution(self, data: dict) -> dict:
        with self._timed("benchmarks"):
            inp    = self._parse_input(data)
            kpis   = compute_kpis(inp)
            n      = len(inp.researchers)
            results = benchmark(kpis, n)
            summary = benchmark_summary(results)
        return {
            "benchmarks": [r.to_dict() for r in results],
            "summary":    summary,
        }

    def detect_risks(self, data: dict) -> dict:
        with self._timed("risk_detections"):
            inp   = self._parse_input(data)
            risks = detect_risks(inp)
        return {
            "risks":   [r.to_dict() for r in risks],
            "total":   len(risks),
            "by_severity": {
                sev: sum(1 for r in risks if r.severity.value == sev)
                for sev in ["critical", "high", "medium", "low", "minimal"]
            },
        }

    def recommendations(self, data: dict, audiences: list[str] | None = None) -> dict:
        with self._timed("decision_support_runs"):
            inp    = self._parse_input(data)
            kpis   = compute_kpis(inp)
            aud    = [RecommendationAudience(a) for a in (audiences or [])] if audiences else None
            recs   = generate_recommendations(inp, kpis, audiences=aud)
        return {
            "recommendations": [r.to_dict() for r in recs],
            "total":           len(recs),
            "by_audience":     {
                a: [r.to_dict() for r in recs if r.audience.value == a]
                for a in set(r.audience.value for r in recs)
            },
        }

    def monitor(self, data: dict) -> dict:
        with self._timed("monitoring_runs"):
            inp    = self._parse_input(data)
            kpis   = compute_kpis(inp)
            alerts = monitor(inp, kpis)
        return {
            "alerts":    [a.to_dict() for a in alerts],
            "total":     len(alerts),
            "by_type":   {
                t: sum(1 for a in alerts if a.alert_type.value == t)
                for t in set(a.alert_type.value for a in alerts)
            },
        }

    def knowledge_graph(self, data: dict, max_nodes: int = 200) -> dict:
        with self._timed("knowledge_graph_builds"):
            inp   = self._parse_input(data)
            graph = build_knowledge_graph(inp, max_nodes=max_nodes)
        return graph.to_dict()

    def visualization(self, viz_type: str, data: dict) -> dict:
        with self._timed("visualization_builds"):
            inp     = self._parse_input(data)
            kpis    = compute_kpis(inp)
            profile = build_institution_profile(inp)
            profile.kpis = kpis
            portfolio = analyse_portfolio(inp)
            risks   = detect_risks(inp)
            talent  = identify_talent(inp)
            forecasts = predict_institution(inp)
            return build_visualization(
                viz_type=viz_type,
                profile=profile, kpis=kpis, inp=inp,
                portfolio=portfolio, risks=risks,
                talent=serialize_talent(talent),
                forecasts=forecasts,
            )

    def export_report(
        self,
        data: dict,
        report_type: str = "executive",
        export_format: str = "pdf",
    ) -> dict:
        with self._timed("export_generations"):
            inp     = self._parse_input(data)
            kpis    = compute_kpis(inp)
            profile = build_institution_profile(inp)
            profile.kpis = kpis
            risks   = detect_risks(inp)
            recs    = generate_recommendations(inp, kpis)
            results = benchmark(kpis, len(inp.researchers))
            forecasts = predict_institution(inp)
        try:
            rt = ExportReportType(report_type)
        except ValueError:
            rt = ExportReportType.EXECUTIVE
        try:
            ef = ExportFormat(export_format)
        except ValueError:
            ef = ExportFormat.PDF
        return generate_export(rt, ef, profile, kpis, risks, recs, results, forecasts)

    def full_analysis(self, data: dict) -> dict:
        """Run all engines in one call — for comprehensive institutional intelligence."""
        inp     = self._parse_input(data)
        kpis    = compute_kpis(inp)
        profile = build_institution_profile(inp)
        profile.kpis = kpis
        return {
            "profile":              profile.to_dict(),
            "kpis":                 kpis.to_dict(),
            "organizational":       [i.to_dict() for i in detect_organizational_insights(inp)],
            "risks":                [r.to_dict() for r in detect_risks(inp)],
            "recommendations":      [r.to_dict() for r in generate_recommendations(inp, kpis)],
            "benchmarks":           benchmark_summary(benchmark(kpis, len(inp.researchers))),
            "forecasts":            [f.to_dict() for f in predict_institution(inp)],
            "talent":               serialize_talent(identify_talent(inp)),
            "portfolio_summary":    portfolio_summary(analyse_portfolio(inp)),
            "alerts":               [a.to_dict() for a in monitor(inp, kpis)],
        }

    def admin_analytics(self, institutions: list[dict]) -> dict:
        """Platform-level analytics across multiple institutions."""
        if not institutions:
            return {"total_institutions": 0}
        profiles = []
        for inst in institutions:
            try:
                inp = self._parse_input(inst)
                p   = build_institution_profile(inp)
                p.kpis = compute_kpis(inp)
                profiles.append(p)
            except Exception:
                continue
        avg_score    = sum(p.overall_score for p in profiles) / max(len(profiles), 1)
        total_researchers = sum(p.total_researchers for p in profiles)
        top_by_score = sorted(profiles, key=lambda p: -p.overall_score)[:5]
        countries    = list({p.country for p in profiles if p.country})
        return {
            "total_institutions":   len(profiles),
            "total_researchers":    total_researchers,
            "average_score":        round(avg_score, 3),
            "top_institutions":     [p.to_dict() for p in top_by_score],
            "countries":            countries,
        }


# ── Async singleton ───────────────────────────────────────────────────────────

_engine_instance: InstitutionIntelligenceEngine | None = None
_engine_lock = asyncio.Lock()


async def get_institution_engine() -> InstitutionIntelligenceEngine:
    global _engine_instance
    if _engine_instance is None:
        async with _engine_lock:
            if _engine_instance is None:
                _engine_instance = InstitutionIntelligenceEngine()
    return _engine_instance


def reset_institution_engine() -> None:
    global _engine_instance
    _engine_instance = None
