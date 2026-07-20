"""
SIE Orchestrator — central platform context gatherer and insight synthesizer.
Reads from all existing Synaptiq collections to build a unified intelligence picture.
Does NOT call any HTTP endpoints; queries MongoDB directly.
"""
import asyncio
from datetime import datetime, timezone, timedelta


async def get_platform_context(user_id: str, db) -> dict:
    """Gather cross-module data for a single user in parallel."""
    now = datetime.now(timezone.utc)
    year = now.year

    (
        user,
        total_pubs, pubs_this_year,
        total_grants, approved_grants,
        total_collabs,
        integrity_report,
        active_goals, pending_missions,
        memory,
        rec_count,
    ) = await asyncio.gather(
        db.users.find_one({"_id": __import__("bson").ObjectId(user_id)}),
        db.publications.count_documents({"user_id": user_id}),
        db.publications.count_documents({"user_id": user_id, "year": year}),
        db.grant_applications.count_documents({"user_id": user_id}),
        db.grant_applications.count_documents({"user_id": user_id, "status": "approved"}),
        db.collaborations.count_documents({"user_id": user_id}),
        db.integrity_reports.find_one({"user_id": user_id}, sort=[("generated_at", -1)]),
        db.sie_goals.count_documents({"user_id": user_id, "status": "active"}),
        db.sie_missions.count_documents({"user_id": user_id, "status": "pending"}),
        db.sie_memory.find_one({"user_id": user_id}),
        db.sie_recommendations.count_documents({"user_id": user_id, "dismissed": False}),
    )

    grant_success = round((approved_grants / total_grants) * 100) if total_grants > 0 else 0

    return {
        "user": {
            "name": user.get("name", "") if user else "",
            "email": user.get("email", "") if user else "",
            "institution": user.get("institution", "") if user else "",
            "role": user.get("role", "user") if user else "user",
        },
        "research": {
            "total_publications": total_pubs,
            "publications_this_year": pubs_this_year,
            "total_collaborations": total_collabs,
        },
        "grants": {
            "total": total_grants,
            "approved": approved_grants,
            "success_rate_pct": grant_success,
        },
        "integrity": {
            "score": integrity_report.get("overall_score", 0) if integrity_report else 0,
            "grade": integrity_report.get("grade", "N/A") if integrity_report else "N/A",
        },
        "sie": {
            "active_goals": active_goals,
            "pending_missions": pending_missions,
            "recommendations": rec_count,
            "memory_configured": bool(memory and memory.get("research_interests")),
        },
        "generated_at": now.isoformat(),
    }


async def synthesize_insights(user_id: str, db) -> list[dict]:
    """Generate cross-module insight bullets."""
    ctx = await get_platform_context(user_id, db)
    insights = []

    r = ctx["research"]
    g = ctx["grants"]
    s = ctx["sie"]
    i = ctx["integrity"]

    if r["total_publications"] == 0:
        insights.append({"level": "warning", "text": "No publications found. Start a research roadmap to plan your first paper."})
    elif r["publications_this_year"] == 0:
        insights.append({"level": "warning", "text": f"No publications in {datetime.now().year}. Consider activating a writing mission."})

    if g["total"] > 0 and g["success_rate_pct"] < 30:
        insights.append({"level": "warning", "text": f"Grant success rate is {g['success_rate_pct']}%. Use Grant Hub to improve proposal quality."})

    if s["active_goals"] == 0:
        insights.append({"level": "info", "text": "No active goals. Define your research goals to unlock AI planning and missions."})

    if s["pending_missions"] > 10:
        insights.append({"level": "info", "text": f"You have {s['pending_missions']} pending missions. Focus on the top 3 highest-priority ones."})

    if i["score"] > 0 and i["score"] < 50:
        insights.append({"level": "warning", "text": f"Integrity score is {i['score']}/100. Visit the Integrity Engine to resolve verification gaps."})

    if not s["memory_configured"]:
        insights.append({"level": "info", "text": "Configure AI Memory to unlock personalised recommendations."})

    if not insights:
        insights.append({"level": "success", "text": "Platform health is strong. Keep progressing on your active missions."})

    return insights
