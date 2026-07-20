"""
Report Generation Engine — produces executive summaries in CSV and JSON format.
PDF/Excel export requires optional dependencies; this engine provides structured
data that client-side libraries can render to those formats.
"""
import asyncio
import csv
import io
import json
from datetime import datetime, timezone


async def generate_report(institution: str, report_type: str, db) -> dict:
    from services.iip.health_engine import compute_health_score
    from services.iip.publication_engine import get_publication_overview
    from services.iip.grant_engine import get_grant_overview
    from services.iip.faculty_engine import get_faculty_overview
    from services.iip.risk_engine import detect_institutional_risks
    from services.iip.collaboration_engine import get_collaboration_overview
    from services.iip.financial_engine import get_financial_overview
    from services.iip.benchmark_engine import get_benchmark_overview

    health, pubs, grants, faculty, risks, collab, financial, benchmarks = await asyncio.gather(
        compute_health_score(institution, db),
        get_publication_overview(institution, db),
        get_grant_overview(institution, db),
        get_faculty_overview(institution, db),
        detect_institutional_risks(institution, db),
        get_collaboration_overview(institution, db),
        get_financial_overview(institution, db),
        get_benchmark_overview(institution, db),
    )

    report = {
        "report_type": report_type,
        "institution": institution,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "publications": pubs,
        "grants": grants,
        "faculty": faculty,
        "risks": risks,
        "collaboration": collab,
        "financial": financial,
        "benchmarks": benchmarks,
        "executive_summary": _build_executive_summary(health, pubs, grants, faculty, risks),
    }

    # Persist metadata
    meta = {
        "institution": institution,
        "report_type": report_type,
        "health_score": health["score"],
        "grade": health["grade"],
        "risk_count": len(risks),
        "critical_count": sum(1 for r in risks if r["level"] == "critical"),
        "generated_at": report["generated_at"],
    }
    await db.iip_reports.insert_one(meta)
    meta.pop("_id", None)

    return report


def _build_executive_summary(health: dict, pubs: dict, grants: dict, faculty: dict, risks: list) -> str:
    score = health.get("score", 0)
    grade = health.get("grade", "N/A")
    critical_count = sum(1 for r in risks if r["level"] == "critical")
    high_count = sum(1 for r in risks if r["level"] == "high")

    summary = (
        f"Executive Summary — {health.get('institution', 'Institution')} | "
        f"Health Score: {score}/100 (Grade {grade})\n\n"
        f"Faculty: {faculty.get('total', 0)} researchers, "
        f"{faculty.get('engagement_rate', 0):.0f}% active.\n"
        f"Publications: {pubs.get('total', 0)} total, "
        f"{pubs.get('q1q2_pct', 0):.1f}% Q1/Q2, "
        f"{pubs.get('avg_citations', 0):.1f} avg citations.\n"
        f"Grants: {grants.get('total', 0)} applications, "
        f"{grants.get('success_rate', 0):.1f}% success rate, "
        f"€{grants.get('total_funding', 0):,.0f} approved.\n"
        f"Risks: {critical_count} critical, {high_count} high-priority flagged.\n"
    )
    return summary


def export_to_csv(report: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["INSTITUTION INTELLIGENCE REPORT"])
    writer.writerow(["Institution", report["institution"]])
    writer.writerow(["Generated", report["generated_at"]])
    writer.writerow([])

    writer.writerow(["HEALTH SCORE"])
    writer.writerow(["Overall Score", report["health"]["score"]])
    writer.writerow(["Grade", report["health"]["grade"]])
    writer.writerow(["Faculty Count", report["health"]["faculty_count"]])
    writer.writerow([])

    writer.writerow(["HEALTH INDICATORS"])
    writer.writerow(["Indicator", "Value", "Weight", "Contribution"])
    for ind in report["health"].get("indicators", []):
        writer.writerow([ind["label"], ind["value"], ind["weight"], ind["contribution"]])
    writer.writerow([])

    writer.writerow(["PUBLICATIONS"])
    pub = report["publications"]
    writer.writerow(["Total", pub.get("total", 0)])
    writer.writerow(["Q1/Q2 %", pub.get("q1q2_pct", 0)])
    writer.writerow(["Avg Citations", pub.get("avg_citations", 0)])
    writer.writerow(["Growth %", pub.get("growth_rate_pct", 0)])
    writer.writerow([])

    writer.writerow(["GRANTS"])
    g = report["grants"]
    writer.writerow(["Total Applications", g.get("total", 0)])
    writer.writerow(["Approved", g.get("approved", 0)])
    writer.writerow(["Success Rate %", g.get("success_rate", 0)])
    writer.writerow(["Total Funding", g.get("total_funding", 0)])
    writer.writerow([])

    writer.writerow(["RISK FLAGS"])
    writer.writerow(["Level", "Title", "Metric", "Value", "Action"])
    for r in report.get("risks", []):
        writer.writerow([r["level"], r["title"], r["metric"], r["value"], r["action"]])

    return output.getvalue()


def export_to_json(report: dict) -> str:
    return json.dumps(report, indent=2, default=str)


async def list_reports(institution: str, db, limit: int = 20) -> list:
    docs = await db.iip_reports.find(
        {"institution": institution},
        {"_id": 0},
    ).sort("generated_at", -1).limit(limit).to_list(length=limit)
    return docs
