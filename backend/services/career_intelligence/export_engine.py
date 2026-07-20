"""Academic Career Intelligence — Export Engine (Phase XVI).

Generates 6 report types × 3 export formats (PDF/DOCX/Markdown).
All outputs are serializable dicts; actual PDF/DOCX generation is handled by the frontend.
"""
from __future__ import annotations

import datetime

from .models import (
    CareerProfile, CareerRoadmap, ExportFormat, ExportReportType,
    ProductivityMetrics, PromotionReadiness,
)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


# ── Section builders ──────────────────────────────────────────────────────────

def _profile_section(profile: CareerProfile) -> dict:
    return {
        "title": "Researcher Profile",
        "content": (
            f"Name: {profile.name or 'N/A'}\n"
            f"Institution: {profile.institution or 'N/A'}\n"
            f"Department: {profile.department or 'N/A'}\n"
            f"Career Stage: {profile.career_stage.value.replace('_', ' ').title()}\n"
            f"Years Active: {profile.years_active}\n"
            f"H-index: {profile.h_index}\n"
            f"Publications: {profile.publication_count}\n"
            f"Citations: {profile.citation_count}\n"
            f"Grants: {profile.grant_count}\n"
        ),
    }


def _productivity_section(productivity: ProductivityMetrics | None) -> dict:
    if not productivity:
        return {"title": "Research Productivity", "content": "No productivity data available."}
    return {
        "title": "Research Productivity",
        "content": (
            f"Publications per year: {productivity.publications_per_year}\n"
            f"Citation growth rate: {productivity.citation_growth_rate}\n"
            f"Research diversity: {productivity.research_diversity} areas\n"
            f"Output score: {productivity.output_score}\n"
            f"Impact score: {productivity.impact_score}\n"
            f"Overall productivity: {productivity.overall_productivity}\n"
        ),
    }


def _roadmap_section(roadmap: CareerRoadmap | None) -> dict:
    if not roadmap:
        return {"title": "Career Roadmap", "content": "No roadmap generated."}
    lines = [roadmap.summary, "", f"Horizon: {roadmap.horizon.value}", ""]
    for m in roadmap.milestones[:10]:
        lines.append(f"Year {m.year} [{m.priority.upper()}]: {m.description}")
    return {"title": "Career Roadmap", "content": "\n".join(lines)}


def _promotion_section(readiness: PromotionReadiness | None) -> dict:
    if not readiness:
        return {"title": "Promotion Readiness", "content": "No promotion assessment performed."}
    met_str  = "\n".join(f"  ✓ {r}" for r in readiness.requirements_met)
    miss_str = "\n".join(f"  ✗ {r}" for r in readiness.requirements_missing)
    return {
        "title": "Promotion Readiness",
        "content": (
            f"Target: {readiness.target.value.replace('_', ' ').title()}\n"
            f"Overall Readiness: {readiness.overall_readiness:.0%}\n"
            f"Estimated time to readiness: {readiness.estimated_months} months\n\n"
            f"Requirements Met:\n{met_str or '  (none)'}\n\n"
            f"Requirements Missing:\n{miss_str or '  (none)'}\n"
        ),
    }


def _recommendations_section(recommendations: dict | None) -> dict:
    if not recommendations:
        return {"title": "Personalized Recommendations", "content": "No recommendations generated."}
    lines = []
    for cat, recs in recommendations.items():
        lines.append(f"\n{cat.replace('_', ' ').title()}:")
        for r in recs[:3]:
            lines.append(f"  • {r.get('title', '')}: {r.get('reason', '')}")
    return {"title": "Personalized Recommendations", "content": "\n".join(lines)}


def _risk_section(risks: list[dict] | None) -> dict:
    if not risks:
        return {"title": "Career Risk Analysis", "content": "No risks detected."}
    lines = []
    for r in risks[:6]:
        lines.append(f"[{r.get('severity', 'medium').upper()}] {r.get('risk_type', '')}")
        lines.append(f"  {r.get('description', '')}")
        lines.append(f"  Mitigation: {r.get('mitigation', '')}\n")
    return {"title": "Career Risk Analysis", "content": "\n".join(lines)}


def _skill_section(skill_report: dict | None) -> dict:
    if not skill_report:
        return {"title": "Skill Gap Analysis", "content": "No skill assessment performed."}
    strengths = ", ".join(skill_report.get("top_strengths", [])[:5])
    critical  = ", ".join(skill_report.get("critical_gaps", [])[:5])
    return {
        "title": "Skill Gap Analysis",
        "content": (
            f"Overall Skill Score: {skill_report.get('overall_skill_score', 0):.2f}\n"
            f"Top Strengths: {strengths or 'None detected'}\n"
            f"Critical Gaps: {critical or 'None detected'}\n"
        ),
    }


# ── Report type builders ──────────────────────────────────────────────────────

def _build_sections(
    report_type: ExportReportType,
    profile: CareerProfile,
    roadmap: CareerRoadmap | None = None,
    readiness: PromotionReadiness | None = None,
    recommendations: dict | None = None,
    risks: list[dict] | None = None,
    productivity: ProductivityMetrics | None = None,
    skill_report: dict | None = None,
) -> list[dict]:
    sections: list[dict] = [
        {"title": "Report", "content": f"Generated: {_now()}\nType: {report_type.value}"}
    ]

    if report_type == ExportReportType.CAREER_REPORT:
        sections += [
            _profile_section(profile),
            _productivity_section(productivity),
            _roadmap_section(roadmap),
            _risk_section(risks),
            _recommendations_section(recommendations),
        ]
    elif report_type == ExportReportType.PROMOTION_PORTFOLIO:
        sections += [
            _profile_section(profile),
            _productivity_section(productivity),
            _promotion_section(readiness),
            _skill_section(skill_report),
            _recommendations_section(recommendations),
        ]
    elif report_type == ExportReportType.RESEARCH_DEVELOPMENT:
        sections += [
            _profile_section(profile),
            _roadmap_section(roadmap),
            _skill_section(skill_report),
            _recommendations_section(recommendations),
        ]
    elif report_type == ExportReportType.PROFESSIONAL_DEVELOPMENT:
        sections += [
            _profile_section(profile),
            _skill_section(skill_report),
            _recommendations_section(recommendations),
            _risk_section(risks),
        ]
    elif report_type == ExportReportType.TEACHING_DEVELOPMENT:
        teaching_content = (
            f"Teaching Areas: {', '.join(profile.teaching_areas) or 'None recorded'}\n"
            "Recommended actions: Pursue HEA fellowship; seek peer observation;\n"
            "attend teaching excellence conferences."
        )
        sections += [
            _profile_section(profile),
            {"title": "Teaching Development Plan", "content": teaching_content},
            _recommendations_section(recommendations),
        ]
    elif report_type == ExportReportType.GRANT_DEVELOPMENT:
        grant_content = (
            f"Current grants: {profile.grant_count}\n"
            f"Total grant income: €{profile.grant_income:,.0f}\n"
            "Priority actions: Identify funding calls; build consortium; improve track record."
        )
        sections += [
            _profile_section(profile),
            {"title": "Grant Development Plan", "content": grant_content},
            _recommendations_section(recommendations),
            _risk_section(risks),
        ]
    else:
        sections += [_profile_section(profile)]

    return sections


# ── Format adapters ───────────────────────────────────────────────────────────

def _to_pdf(sections: list[dict], title: str) -> dict:
    return {"format": "pdf", "title": title, "sections": sections}


def _to_docx(sections: list[dict], title: str) -> dict:
    return {"format": "docx", "title": title, "sections": sections}


def _to_markdown(sections: list[dict], title: str) -> dict:
    md_parts = [f"# {title}\n"]
    for sec in sections:
        md_parts.append(f"## {sec['title']}\n\n{sec['content']}\n")
    return {"format": "markdown", "title": title, "content": "\n".join(md_parts)}


# ── Public function ───────────────────────────────────────────────────────────

def generate_export(
    report_type: str | ExportReportType,
    export_format: str | ExportFormat,
    profile: CareerProfile,
    roadmap: CareerRoadmap | None = None,
    readiness: PromotionReadiness | None = None,
    recommendations: dict | None = None,
    risks: list[dict] | None = None,
    productivity: ProductivityMetrics | None = None,
    skill_report: dict | None = None,
) -> dict:
    """Generate a career intelligence export report."""
    try:
        rt = ExportReportType(report_type) if isinstance(report_type, str) else report_type
    except ValueError:
        rt = ExportReportType.CAREER_REPORT

    try:
        ef = ExportFormat(export_format) if isinstance(export_format, str) else export_format
    except ValueError:
        ef = ExportFormat.PDF

    title = f"{rt.value.replace('_', ' ').title()} — {profile.name or 'Researcher'}"
    sections = _build_sections(rt, profile, roadmap, readiness, recommendations,
                               risks, productivity, skill_report)

    if ef == ExportFormat.MARKDOWN:
        return _to_markdown(sections, title)
    if ef == ExportFormat.DOCX:
        return _to_docx(sections, title)
    return _to_pdf(sections, title)
