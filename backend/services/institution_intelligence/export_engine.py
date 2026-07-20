"""Institution Intelligence Engine — Export Engine (Phase XV).

Generates structured reports in 4 formats (PDF/DOCX/EXCEL/POWERPOINT).
All formats are represented as structured dicts:
- PDF/DOCX: {"sections": [...]} with markdown-compatible text
- EXCEL:    {"sheets": {"Sheet": [[row]]}}
- PPTX:     {"slides": [{"title": ..., "content": [...]}]}
"""
from __future__ import annotations

import datetime

from .models import (
    BenchmarkResult, ExecutiveRecommendation, ExportFormat,
    ExportReportType, InstitutionForecast, InstitutionKPIs,
    InstitutionProfile, InstitutionRisk, OrganizationalInsight,
)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _section(title: str, content: str) -> dict:
    return {"title": title, "content": content}


# ── Section builders ──────────────────────────────────────────────────────────

def _kpi_section(kpis: InstitutionKPIs) -> dict:
    kd = kpis.to_dict()
    lines = "\n".join(f"- **{k.replace('_', ' ').title()}**: {v}" for k, v in kd.items())
    return _section("Institution KPIs", lines)


def _profile_section(profile: InstitutionProfile) -> dict:
    return _section("Institution Profile", "\n".join([
        f"- Name: {profile.name}",
        f"- Country: {profile.country}",
        f"- Type: {profile.institution_type.value}",
        f"- Total Researchers: {profile.total_researchers}",
        f"- Total Publications: {profile.total_publications}",
        f"- Total Citations: {profile.total_citations}",
        f"- Total Grants: {profile.total_grants}",
        f"- Total Grant Income: €{profile.total_grant_income:,.0f}",
        f"- Overall Score: {profile.overall_score:.3f}",
    ]))


def _risk_section(risks: list[InstitutionRisk]) -> dict:
    if not risks:
        return _section("Risk Intelligence", "No significant risks detected.")
    lines = "\n".join(
        f"- **[{r.severity.value.upper()}] {r.risk_type.value}**: {r.description}"
        for r in risks[:10]
    )
    return _section("Risk Intelligence", lines)


def _rec_section(recs: list[ExecutiveRecommendation]) -> dict:
    if not recs:
        return _section("Executive Recommendations", "No recommendations generated.")
    lines = "\n".join(
        f"- **[{r.priority.upper()}] {r.title}** ({r.audience.value})\n  {r.description}"
        for r in recs[:10]
    )
    return _section("Executive Recommendations", lines)


def _benchmark_section(benchmarks: list[BenchmarkResult]) -> dict:
    if not benchmarks:
        return _section("Benchmarking", "No benchmarking data available.")
    lines = "\n".join(
        f"- {b.metric}: {b.own_value:.2f} vs peer avg {b.peer_avg:.2f} "
        f"(P{b.percentile * 100:.0f} percentile, {b.trend})"
        for b in benchmarks
    )
    return _section("Benchmarking vs Peers", lines)


def _forecast_section(forecasts: list[InstitutionForecast]) -> dict:
    if not forecasts:
        return _section("Forecasts", "No forecasts generated.")
    lines = "\n".join(
        f"- {f.forecast_type.value}: baseline {f.baseline_value:.0f} → "
        f"{f.predicted_values[-1]:.0f} (yr{f.horizon_years}, {f.trend})"
        for f in forecasts
    )
    return _section("Predictive Analytics (3-Year Horizon)", lines)


def _dept_section(profile: InstitutionProfile) -> dict:
    if not profile.departments:
        return _section("Department Performance", "No department data available.")
    lines = "\n".join(
        f"- **{d.name}**: {d.researcher_count} researchers, {d.publication_count} pubs, "
        f"h-index avg {d.avg_h_index:.1f}, status: {d.status.value}"
        for d in profile.departments
    )
    return _section("Department Performance", lines)


def _insight_section(insights: list[OrganizationalInsight]) -> dict:
    if not insights:
        return _section("Organizational Intelligence", "No insights detected.")
    lines = "\n".join(
        f"- **[{i.severity.value.upper()}] {i.insight_type}** ({i.entity_name}): {i.message}"
        for i in insights[:10]
    )
    return _section("Organizational Intelligence", lines)


# ── Report builders ───────────────────────────────────────────────────────────

def _executive_report(
    profile: InstitutionProfile, kpis: InstitutionKPIs,
    risks: list[InstitutionRisk], recs: list[ExecutiveRecommendation],
    benchmarks: list[BenchmarkResult],
) -> dict:
    return {
        "title":    f"Executive Research Intelligence Report — {profile.name}",
        "date":     _now(),
        "sections": [
            _section("Executive Summary",
                     f"{profile.name} has {profile.total_researchers} researchers, "
                     f"{profile.total_publications} publications, and €{profile.total_grant_income:,.0f} in grants. "
                     f"Overall institutional score: {profile.overall_score:.3f}."),
            _profile_section(profile),
            _kpi_section(kpis),
            _benchmark_section(benchmarks[:5]),
            _risk_section(risks[:5]),
            _rec_section(recs[:5]),
        ],
    }


def _accreditation_report(profile: InstitutionProfile, kpis: InstitutionKPIs) -> dict:
    return {
        "title":    f"Accreditation Report — {profile.name}",
        "date":     _now(),
        "sections": [
            _profile_section(profile),
            _kpi_section(kpis),
            _dept_section(profile),
            _section("Research Quality Indicators", "\n".join([
                f"- Average FWCI: {kpis.avg_fwci:.3f}",
                f"- Q1 Publication Ratio: {kpis.q1_ratio:.1%}",
                f"- Open Science Score: {kpis.open_science_score:.3f}",
                f"- Doctoral Activity Score: {kpis.doctoral_activity_score:.3f}",
            ])),
        ],
    }


def _research_strategy_report(
    profile: InstitutionProfile, kpis: InstitutionKPIs,
    forecasts: list[InstitutionForecast], recs: list[ExecutiveRecommendation],
) -> dict:
    return {
        "title":    f"Research Strategy Report — {profile.name}",
        "date":     _now(),
        "sections": [
            _section("Strategic Overview",
                     f"This report outlines the 3-year research strategy for {profile.name}."),
            _kpi_section(kpis),
            _forecast_section(forecasts),
            _rec_section(recs),
        ],
    }


def _grant_strategy_report(
    profile: InstitutionProfile, kpis: InstitutionKPIs,
    recs: list[ExecutiveRecommendation],
) -> dict:
    grant_recs = [r for r in recs if "grant" in r.category or r.audience.value == "grant_office"]
    return {
        "title":    f"Grant Strategy Report — {profile.name}",
        "date":     _now(),
        "sections": [
            _section("Grant Performance Overview", "\n".join([
                f"- Total Grants: {profile.total_grants}",
                f"- Total Grant Income: €{profile.total_grant_income:,.0f}",
                f"- Grant Success Rate: {kpis.grant_success_rate:.0%}",
                f"- Sustainability Score: {kpis.sustainability_score:.3f}",
            ])),
            _rec_section(grant_recs or recs[:3]),
        ],
    }


def _department_report(profile: InstitutionProfile, kpis: InstitutionKPIs) -> dict:
    return {
        "title":    f"Department Performance Report — {profile.name}",
        "date":     _now(),
        "sections": [_dept_section(profile), _kpi_section(kpis)],
    }


# ── Format converters ─────────────────────────────────────────────────────────

def _to_pdf(report: dict) -> dict:
    return {
        "format":   "pdf",
        "filename": f"{report['title'].replace(' ', '_').replace('/', '-')[:50]}.pdf",
        "content":  report,
    }


def _to_docx(report: dict) -> dict:
    return {
        "format":   "docx",
        "filename": f"{report['title'].replace(' ', '_').replace('/', '-')[:50]}.docx",
        "content":  report,
    }


def _to_excel(report: dict) -> dict:
    sheets: dict[str, list[list]] = {}
    for section in report.get("sections", []):
        title   = section["title"]
        content = section.get("content", "")
        rows    = [["Field", "Value"]]
        for line in content.split("\n"):
            line = line.strip("- ").strip()
            if ": " in line:
                k, v = line.split(": ", 1)
                rows.append([k.strip("*"), v])
        sheets[title[:31]] = rows
    return {
        "format":   "excel",
        "filename": f"{report['title'].replace(' ', '_')[:40]}.xlsx",
        "sheets":   sheets,
    }


def _to_pptx(report: dict) -> dict:
    slides = [{"title": "Title Slide", "content": [report["title"], report["date"]]}]
    for section in report.get("sections", []):
        bullets = [line.strip("- ").strip() for line in section["content"].split("\n")
                   if line.strip() and not line.startswith("#")][:6]
        slides.append({"title": section["title"], "content": bullets})
    return {
        "format":   "powerpoint",
        "filename": f"{report['title'].replace(' ', '_')[:40]}.pptx",
        "slides":   slides,
    }


# ── Public function ───────────────────────────────────────────────────────────

def generate_export(
    report_type: ExportReportType,
    export_format: ExportFormat,
    profile: InstitutionProfile,
    kpis: InstitutionKPIs,
    risks: list[InstitutionRisk] | None = None,
    recs: list[ExecutiveRecommendation] | None = None,
    benchmarks: list[BenchmarkResult] | None = None,
    forecasts: list[InstitutionForecast] | None = None,
    insights: list[OrganizationalInsight] | None = None,
) -> dict:
    """Generate an export report of the requested type and format."""
    r  = risks      or []
    rc = recs       or []
    b  = benchmarks or []
    f  = forecasts  or []

    if report_type == ExportReportType.EXECUTIVE:
        report = _executive_report(profile, kpis, r, rc, b)
    elif report_type == ExportReportType.ACCREDITATION:
        report = _accreditation_report(profile, kpis)
    elif report_type == ExportReportType.RESEARCH_STRATEGY:
        report = _research_strategy_report(profile, kpis, f, rc)
    elif report_type == ExportReportType.GRANT_STRATEGY:
        report = _grant_strategy_report(profile, kpis, rc)
    elif report_type in (ExportReportType.DEPARTMENT, ExportReportType.FACULTY):
        report = _department_report(profile, kpis)
    elif report_type == ExportReportType.BENCHMARK:
        report = {
            "title": f"Benchmarking Report — {profile.name}",
            "date": _now(),
            "sections": [_benchmark_section(b), _kpi_section(kpis)],
        }
    else:
        report = _executive_report(profile, kpis, r, rc, b)

    converters = {
        ExportFormat.PDF:       _to_pdf,
        ExportFormat.DOCX:      _to_docx,
        ExportFormat.EXCEL:     _to_excel,
        ExportFormat.POWERPOINT: _to_pptx,
    }
    return converters.get(export_format, _to_pdf)(report)
