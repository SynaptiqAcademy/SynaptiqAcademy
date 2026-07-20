"""
SIE — Synaptiq Intelligence Engine REST API
35 endpoints at /api/sie (user) — no admin router needed (uses existing RBAC).

Collections created: sie_goals, sie_roadmaps, sie_missions, sie_career,
                     sie_memory, sie_automations, sie_daily_agenda,
                     sie_weekly_plan, sie_recommendations, sie_commands,
                     sie_progress_snapshots
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from worker import enqueue_job
from worker.models import Job
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db

from services.sie.memory_engine        import get_memory, update_memory, add_memory_event, enrich_memory_from_platform
from services.sie.goal_engine          import create_goal, get_goals, update_goal, delete_goal, evaluate_goal
from services.sie.roadmap_engine       import generate_roadmap, get_roadmaps, get_roadmap, advance_stage
from services.sie.mission_engine       import create_mission, get_missions, update_mission, complete_mission, generate_missions_from_goal
from services.sie.career_engine        import get_career_profile, update_career_profile, get_promotion_readiness, get_career_roadmap
from services.sie.agenda_engine        import get_daily_agenda, generate_daily_agenda, get_weekly_plan, generate_weekly_plan
from services.sie.recommendation_engine import generate_recommendations, get_recommendations, dismiss_recommendation, rate_recommendation
from services.sie.automation_engine    import (create_automation, get_automations, update_automation,
                                               delete_automation, run_automation, seed_default_automations)
from services.sie.progress_engine      import get_progress_overview, take_snapshot
from services.sie.command_engine       import process_command, get_command_history
from services.sie.orchestrator         import get_platform_context, synthesize_insights
from repo.shim import make_db_proxy

router = APIRouter(prefix="/api/sie", tags=["sie"])


# ─── Pydantic models ──────────────────────────────────────────────────────────

class GoalIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    type: str = "other"
    priority: int = Field(3, ge=1, le=5)
    deadline: Optional[str] = None
    dependencies: list[str] = []

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    deadline: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = None
    dependencies: Optional[list[str]] = None

class RoadmapIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    topic: str = ""
    research_questions: list[str] = []
    target_journal: str = ""
    backup_journals: list[str] = []

class RoadmapStageUpdate(BaseModel):
    stage_key: str
    completion: int = Field(..., ge=0, le=100)

class MissionIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    type: str = "other"
    priority: int = Field(3, ge=1, le=5)
    difficulty: int = Field(3, ge=1, le=5)
    estimated_hours: float = 4.0
    goal_id: Optional[str] = None
    due_date: Optional[str] = None

class MissionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    estimated_hours: Optional[float] = None
    completion: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = None
    due_date: Optional[str] = None

class CareerUpdate(BaseModel):
    current_position: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None
    years_in_position: Optional[int] = None
    target_position: Optional[str] = None
    target_timeline_years: Optional[int] = None
    skills: Optional[list[str]] = None
    certifications: Optional[list[str]] = None
    training: Optional[list[str]] = None
    phd_students_supervised: Optional[int] = None
    teaching_courses: Optional[int] = None
    editorial_roles: Optional[list[str]] = None
    notes: Optional[str] = None

class MemoryUpdate(BaseModel):
    research_interests: Optional[list[str]] = None
    writing_style: Optional[str] = None
    preferred_journals: Optional[list[str]] = None
    methodologies: Optional[list[str]] = None
    stats_methods: Optional[list[str]] = None
    teaching_interests: Optional[list[str]] = None
    career_goals: Optional[list[str]] = None
    preferred_conferences: Optional[list[str]] = None
    grant_agencies: Optional[list[str]] = None
    language: Optional[str] = None
    notes: Optional[str] = None
    ai_preferences: Optional[dict] = None

class MemoryEvent(BaseModel):
    event_type: str
    data: dict = {}

class AutomationIn(BaseModel):
    name: str = ""
    type: str = "deadline_reminder"
    schedule: str = "weekly"
    config: dict = {}

class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None

class CommandIn(BaseModel):
    command: str = Field(..., min_length=2, max_length=500)

class RatingIn(BaseModel):
    rating: int = Field(..., ge=1, le=5)


# ─── Command Center Overview ───────────────────────────────────────────────────

@router.get("/overview")
async def overview(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    ctx, insights = await __import__("asyncio").gather(
        get_platform_context(user_id, db),
        synthesize_insights(user_id, db),
    )
    return {"context": ctx, "insights": insights}


# ─── Command Center ───────────────────────────────────────────────────────────

@router.post("/command")
async def command(body: CommandIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    user_name = user.get("name", "Researcher")
    return await process_command(user_id, body.command, user_name, db)


@router.get("/command/history")
async def command_history(limit: int = Query(20, ge=1, le=100), user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_command_history(str(user["_id"]), db, limit)


# ─── Goals ────────────────────────────────────────────────────────────────────

@router.post("/goals")
async def create_goal_ep(body: GoalIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await create_goal(str(user["_id"]), body.model_dump(), db)


@router.get("/goals")
async def list_goals(status: Optional[str] = None, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_goals(str(user["_id"]), db, status)


@router.put("/goals/{goal_id}")
async def update_goal_ep(goal_id: str, body: GoalUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = await update_goal(str(user["_id"]), goal_id, updates, db)
    if not result:
        raise HTTPException(404, "Goal not found")
    return result


@router.delete("/goals/{goal_id}")
async def delete_goal_ep(goal_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    ok = await delete_goal(str(user["_id"]), goal_id, db)
    if not ok:
        raise HTTPException(404, "Goal not found")
    return {"deleted": goal_id}


@router.post("/goals/{goal_id}/evaluate")
async def evaluate_goal_ep(goal_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    result = await evaluate_goal(str(user["_id"]), goal_id, db)
    if not result:
        raise HTTPException(404, "Goal not found")
    return result


# ─── Roadmaps ─────────────────────────────────────────────────────────────────

@router.post("/roadmaps/generate")
async def generate_roadmap_ep(body: RoadmapIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await generate_roadmap(str(user["_id"]), body.model_dump(), db)


@router.get("/roadmaps")
async def list_roadmaps(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_roadmaps(str(user["_id"]), db)


@router.get("/roadmaps/{roadmap_id}")
async def get_roadmap_ep(roadmap_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    result = await get_roadmap(str(user["_id"]), roadmap_id, db)
    if not result:
        raise HTTPException(404, "Roadmap not found")
    return result


@router.put("/roadmaps/{roadmap_id}/stage")
async def advance_stage_ep(roadmap_id: str, body: RoadmapStageUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    result = await advance_stage(str(user["_id"]), roadmap_id, body.stage_key, body.completion, db)
    if not result:
        raise HTTPException(404, "Roadmap not found")
    return result


# ─── Missions ─────────────────────────────────────────────────────────────────

@router.post("/missions")
async def create_mission_ep(body: MissionIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await create_mission(str(user["_id"]), body.model_dump(), db)


@router.get("/missions")
async def list_missions(
    status: Optional[str] = None,
    goal_id: Optional[str] = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    return await get_missions(str(user["_id"]), db, status, goal_id)


@router.put("/missions/{mission_id}")
async def update_mission_ep(mission_id: str, body: MissionUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = await update_mission(str(user["_id"]), mission_id, updates, db)
    if not result:
        raise HTTPException(404, "Mission not found")
    return result


@router.post("/missions/{mission_id}/complete")
async def complete_mission_ep(mission_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    result = await complete_mission(str(user["_id"]), mission_id, db)
    if not result:
        raise HTTPException(404, "Mission not found")
    return result


@router.post("/goals/{goal_id}/missions/generate")
async def generate_missions_ep(goal_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    missions = await generate_missions_from_goal(str(user["_id"]), goal_id, db)
    return {"generated": len(missions), "missions": missions}


# ─── Career ───────────────────────────────────────────────────────────────────

@router.get("/career/profile")
async def career_profile(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_career_profile(str(user["_id"]), db)


@router.put("/career/profile")
async def update_career(body: CareerUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    return await update_career_profile(str(user["_id"]), updates, db)


@router.get("/career/readiness")
async def career_readiness(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_promotion_readiness(str(user["_id"]), db)


@router.get("/career/roadmap")
async def career_roadmap_ep(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_career_roadmap(str(user["_id"]), db)


# ─── Agenda ───────────────────────────────────────────────────────────────────

@router.get("/agenda/daily")
async def daily_agenda(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_daily_agenda(str(user["_id"]), db)


@router.post("/agenda/daily/refresh")
async def refresh_daily(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await generate_daily_agenda(str(user["_id"]), db)


@router.get("/agenda/weekly")
async def weekly_plan(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_weekly_plan(str(user["_id"]), db)


@router.post("/agenda/weekly/refresh")
async def refresh_weekly(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await generate_weekly_plan(str(user["_id"]), db)


# ─── Memory ───────────────────────────────────────────────────────────────────

@router.get("/memory")
async def get_memory_ep(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_memory(str(user["_id"]), db)


@router.put("/memory")
async def update_memory_ep(body: MemoryUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    return await update_memory(str(user["_id"]), updates, db)


@router.post("/memory/enrich")
async def enrich_memory_ep(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    uid = str(user["_id"])
    await enqueue_job(Job(job_type="memory.enrich", payload={"user_id": uid}, user_id=uid), db)
    return {"status": "enrichment_queued"}


@router.post("/memory/events")
async def add_event(body: MemoryEvent, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    await add_memory_event(str(user["_id"]), body.event_type, body.data, db)
    return {"added": True}


# ─── Recommendations ──────────────────────────────────────────────────────────

@router.get("/recommendations")
async def list_recommendations(category: Optional[str] = None, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_recommendations(str(user["_id"]), db, category)


@router.post("/recommendations/refresh")
async def refresh_recommendations(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    recs = await generate_recommendations(str(user["_id"]), db)
    return {"generated": len(recs)}


@router.post("/recommendations/{rec_id}/dismiss")
async def dismiss_rec(rec_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    ok = await dismiss_recommendation(str(user["_id"]), rec_id, db)
    return {"dismissed": ok}


@router.post("/recommendations/{rec_id}/rate")
async def rate_rec(rec_id: str, body: RatingIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    ok = await rate_recommendation(str(user["_id"]), rec_id, body.rating, db)
    return {"rated": ok}


# ─── Automations ──────────────────────────────────────────────────────────────

@router.get("/automations")
async def list_automations(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    user_id = str(user["_id"])
    await seed_default_automations(user_id, db)
    return await get_automations(user_id, db)


@router.post("/automations")
async def create_automation_ep(body: AutomationIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await create_automation(str(user["_id"]), body.model_dump(), db)


@router.put("/automations/{automation_id}")
async def update_automation_ep(automation_id: str, body: AutomationUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = await update_automation(str(user["_id"]), automation_id, updates, db)
    if not result:
        raise HTTPException(404, "Automation not found")
    return result


@router.delete("/automations/{automation_id}")
async def delete_automation_ep(automation_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    ok = await delete_automation(str(user["_id"]), automation_id, db)
    if not ok:
        raise HTTPException(404, "Automation not found")
    return {"deleted": automation_id}


@router.post("/automations/{automation_id}/run")
async def run_automation_ep(automation_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await run_automation(str(user["_id"]), automation_id, db)


# ─── Progress ─────────────────────────────────────────────────────────────────

@router.get("/progress/overview")
async def progress_overview(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await get_progress_overview(str(user["_id"]), db)


@router.post("/progress/snapshot")
async def progress_snapshot(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await take_snapshot(str(user["_id"]), db)
