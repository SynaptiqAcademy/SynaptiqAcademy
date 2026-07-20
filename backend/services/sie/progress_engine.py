"""
SIE Progress Engine — tracks goal completion, research productivity, and career progression.
Aggregates data from all Synaptiq collections without duplicating any existing logic.
"""
import asyncio
from datetime import datetime, timezone, timedelta


async def get_progress_overview(user_id: str, db) -> dict:
    now = datetime.now(timezone.utc)
    year = now.year
    last_year = year - 1

    (
        total_pubs, pubs_this_year, pubs_last_year,
        total_grants, approved_grants, grants_this_year,
        total_collabs, active_goals, completed_goals,
        total_missions, completed_missions, pending_missions,
        integrity_report, memory,
    ) = await asyncio.gather(
        db.publications.count_documents({"user_id": user_id}),
        db.publications.count_documents({"user_id": user_id, "year": year}),
        db.publications.count_documents({"user_id": user_id, "year": last_year}),
        db.grant_applications.count_documents({"user_id": user_id}),
        db.grant_applications.count_documents({"user_id": user_id, "status": "approved"}),
        db.grant_applications.count_documents({"user_id": user_id, "year": year}),
        db.collaborations.count_documents({"user_id": user_id}),
        db.sie_goals.count_documents({"user_id": user_id, "status": "active"}),
        db.sie_goals.count_documents({"user_id": user_id, "status": "completed"}),
        db.sie_missions.count_documents({"user_id": user_id}),
        db.sie_missions.count_documents({"user_id": user_id, "status": "completed"}),
        db.sie_missions.count_documents({"user_id": user_id, "status": "pending"}),
        db.integrity_reports.find_one({"user_id": user_id}, sort=[("generated_at", -1)]),
        db.sie_memory.find_one({"user_id": user_id}),
    )

    pub_growth = 0
    if pubs_last_year > 0:
        pub_growth = round(((pubs_this_year - pubs_last_year) / pubs_last_year) * 100)
    elif pubs_this_year > 0:
        pub_growth = 100

    grant_success_rate = round((approved_grants / total_grants) * 100) if total_grants > 0 else 0
    mission_completion_rate = round((completed_missions / total_missions) * 100) if total_missions > 0 else 0
    goal_completion_rate = round((completed_goals / max(1, active_goals + completed_goals)) * 100)

    integrity_score = integrity_report.get("overall_score", 0) if integrity_report else 0

    # Goal progress averages
    goals_cursor = db.sie_goals.find({"user_id": user_id, "status": "active"})
    goals = await goals_cursor.to_list(50)
    avg_goal_progress = round(sum(g.get("progress", 0) for g in goals) / max(1, len(goals)))

    snapshots = await db.sie_progress_snapshots.find({"user_id": user_id}).sort("date", -1).to_list(30)

    summary = {
        "publications_total": total_pubs,
        "publications_this_year": pubs_this_year,
        "publication_growth_pct": pub_growth,
        "grants_total": total_grants,
        "grants_approved": approved_grants,
        "grant_success_rate_pct": grant_success_rate,
        "collaborations_total": total_collabs,
        "active_goals": active_goals,
        "completed_goals": completed_goals,
        "avg_goal_progress_pct": avg_goal_progress,
        "goal_completion_rate_pct": goal_completion_rate,
        "total_missions": total_missions,
        "completed_missions": completed_missions,
        "pending_missions": pending_missions,
        "mission_completion_rate_pct": mission_completion_rate,
        "integrity_score": integrity_score,
        "memory_configured": bool(memory and memory.get("research_interests")),
    }

    return {
        "user_id": user_id,
        "summary": summary,
        "history": [
            {
                "date": s.get("date"),
                "pubs": s.get("publications_total", 0),
                "goals_progress": s.get("avg_goal_progress_pct", 0),
                "missions_completed": s.get("completed_missions", 0),
            }
            for s in snapshots
        ],
        "generated_at": now.isoformat(),
    }


async def take_snapshot(user_id: str, db) -> dict:
    overview = await get_progress_overview(user_id, db)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot = {
        "user_id": user_id,
        "date": today,
        **overview["summary"],
        "created_at": datetime.now(timezone.utc),
    }
    await db.sie_progress_snapshots.replace_one(
        {"user_id": user_id, "date": today},
        snapshot,
        upsert=True,
    )
    return {"snapshot_date": today, "summary": overview["summary"]}
