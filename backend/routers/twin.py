"""
Digital Research Twin API — /api/twin/*

Private by default — all endpoints require authentication.
The authenticated user can only access their own twin.
Admins cannot access other users' twins via this API.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy

from twin import (
    twin_store, profile_builder, working_style as ws_module,
    goal_tracker, health_engine, simulation_engine,
    event_processor, recommendation_engine, temporal_engine, explainability,
)
from twin.twin_store import ensure_indexes

logger = logging.getLogger("twin.router")
router = APIRouter(prefix="/api/twin", tags=["digital-research-twin"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _uid(user: dict) -> str:
    return str(user["_id"])


# ── Full twin sync ────────────────────────────────────────────────────────────

@router.post("/sync")
async def sync_twin(user=Depends(get_current_user), db=Depends(get_db)):
    """
    Rebuild the twin from verified platform data.
    Call this after profile updates, ORCID sync, or major activity changes.
    """
    db = make_db_proxy(db, user)
    uid   = _uid(user)
    twin  = await twin_store.get_twin(db, uid)
    privacy = twin.get("privacy", {})

    excluded_ms   = privacy.get("excluded_manuscript_ids", [])
    excluded_proj = privacy.get("excluded_project_ids", [])

    # Build profile
    profile = await profile_builder.build_research_profile(db, uid, user, excluded_ms, excluded_proj)
    # Build working style
    ws      = await ws_module.analyze_working_style(db, uid)
    # Activity summary
    ms_count   = await db.manuscripts.count_documents({"user_id": uid})
    proj_count = await db.projects.count_documents({"user_id": uid})
    collab_count = await db.collaborations.count_documents({
        "$or": [{"requester_id": uid}, {"recipient_id": uid}], "status": "accepted"
    })
    grant_count = await db.grants.count_documents({"user_id": uid})

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    await twin_store.upsert_twin(db, uid, {
        "profile":       profile,
        "working_style": ws,
        "activity_summary": {
            "manuscripts_count":    ms_count,
            "projects_count":       proj_count,
            "collaborations_count": collab_count,
            "grants_count":         grant_count,
            "last_computed":        now,
        },
        "last_sync": now,
    })

    await twin_store.log_event(db, uid, "twin_synced", "Full twin rebuild completed", [
        {"source": "Synaptiq platform", "detail": f"ms:{ms_count} proj:{proj_count} collab:{collab_count} grants:{grant_count}"}
    ])

    return {"status": "ok", "synced_at": now.isoformat(), "activity_summary": {
        "manuscripts": ms_count, "projects": proj_count,
        "collaborations": collab_count, "grants": grant_count,
    }}


# ── Full twin view ─────────────────────────────────────────────────────────────

@router.get("/me")
async def get_my_twin(user=Depends(get_current_user), db=Depends(get_db)):
    """Return the complete twin document for the authenticated user."""
    db = make_db_proxy(db, user)
    twin = await twin_store.get_twin(db, _uid(user))
    return twin


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_profile(user=Depends(get_current_user), db=Depends(get_db)):
    """Research identity and domain profile derived from verified activity."""
    db = make_db_proxy(db, user)
    twin = await twin_store.get_twin(db, _uid(user))
    return {
        "profile":      twin.get("profile", {}),
        "last_sync":    twin.get("last_sync"),
        "policy_note":  "All domains and interests derived from verified platform data only.",
        "source":       "Synaptiq platform — manuscripts, projects, profile, LKG",
    }


# ── Working style ──────────────────────────────────────────────────────────────

@router.get("/working-style")
async def get_working_style(user=Depends(get_current_user), db=Depends(get_db)):
    """Observed working patterns from platform activity."""
    db = make_db_proxy(db, user)
    twin = await twin_store.get_twin(db, _uid(user))
    ws   = twin.get("working_style", {})
    if not ws.get("observations"):
        ws = await ws_module.analyze_working_style(db, _uid(user))
    return ws


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def get_health(user=Depends(get_current_user), db=Depends(get_db)):
    """Research health indicators — platform activity indicators only."""
    db = make_db_proxy(db, user)
    return await health_engine.compute_health(db, _uid(user), user)


# ── Goals ────────────────────────────────────────────────────────────────────

@router.get("/goals")
async def list_goals(
    status: Optional[str] = Query(None, regex="^(active|completed|paused|abandoned)$"),
    user=Depends(get_current_user), db=Depends(get_db),
):
    """List goals with auto-tracked progress."""
    db = make_db_proxy(db, user)
    return await goal_tracker.get_goals_summary(db, _uid(user))


class GoalCreate(BaseModel):
    title:         str
    category:      str = "other"
    target_value:  int = 1
    unit:          str = "items"
    deadline:      Optional[str] = None
    description:   Optional[str] = None


@router.post("/goals")
async def create_goal(body: GoalCreate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    from pydantic import validator
    goal_data = body.model_dump()
    if goal_data.get("deadline"):
        from datetime import datetime
        try:
            goal_data["deadline"] = datetime.fromisoformat(goal_data["deadline"])
        except Exception:
            goal_data.pop("deadline", None)
    goal_id = await twin_store.create_goal(db, _uid(user), goal_data)
    return {"goal_id": goal_id, "status": "created"}


class GoalUpdate(BaseModel):
    title:         Optional[str] = None
    target_value:  Optional[int] = None
    current_value: Optional[int] = None
    status:        Optional[str] = None
    unit:          Optional[str] = None


@router.put("/goals/{goal_id}")
async def update_goal(goal_id: str, body: GoalUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    ok = await twin_store.update_goal(db, goal_id, _uid(user), updates)
    if not ok:
        raise HTTPException(404, "Goal not found")
    return {"status": "updated"}


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    ok = await twin_store.delete_goal(db, goal_id, _uid(user))
    if not ok:
        raise HTTPException(404, "Goal not found")
    return {"status": "deleted"}


# ── Timeline ──────────────────────────────────────────────────────────────────

@router.get("/timeline")
async def get_timeline(user=Depends(get_current_user), db=Depends(get_db)):
    """Chronological timeline of platform activity."""
    db = make_db_proxy(db, user)
    return await temporal_engine.build_timeline(db, _uid(user))


@router.get("/timeline/domains")
async def get_domain_evolution(user=Depends(get_current_user), db=Depends(get_db)):
    """How research domains appeared and evolved over time."""
    db = make_db_proxy(db, user)
    return {"domains": await temporal_engine.get_domain_evolution(db, _uid(user))}


# ── Recommendations ───────────────────────────────────────────────────────────

@router.get("/recommendations")
async def get_recommendations(user=Depends(get_current_user), db=Depends(get_db)):
    """Personalized recommendations derived from Twin intelligence."""
    db = make_db_proxy(db, user)
    twin = await twin_store.get_twin(db, _uid(user))
    if not twin.get("privacy", {}).get("personalization_enabled", True):
        return {"recommendations": [], "disabled": True, "note": "Personalization is disabled. Re-enable in Twin Settings."}
    recs = await recommendation_engine.generate_recommendations(db, _uid(user), twin)
    return {
        "recommendations": recs,
        "count":           len(recs),
        "source":          "Digital Research Twin — verified platform data only",
        "policy_note":     "All recommendations trace to verified evidence. No fabricated statistics used.",
    }


# ── AI context (for agent integration) ───────────────────────────────────────

@router.get("/ai-context")
async def get_ai_context(user=Depends(get_current_user), db=Depends(get_db)):
    """Compact twin context for AI agents. Agents read this, never write back."""
    db = make_db_proxy(db, user)
    twin = await twin_store.get_twin(db, _uid(user))
    if not twin.get("privacy", {}).get("personalization_enabled", True):
        return {"personalization_enabled": False}
    return await recommendation_engine.get_ai_context(db, _uid(user), twin)


# ── Simulations ───────────────────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    type:             str  # "journal" | "timing" | "collaborator"
    journal_name:     Optional[str] = None
    delay_months:     Optional[int] = None
    institution_name: Optional[str] = None


@router.post("/simulation")
async def run_simulation(body: SimulationRequest, user=Depends(get_current_user), db=Depends(get_db)):
    """Run a what-if simulation. Never fabricates outcomes."""
    db = make_db_proxy(db, user)
    uid = _uid(user)
    if body.type == "journal":
        if not body.journal_name:
            raise HTTPException(400, "journal_name required for journal simulation")
        return await simulation_engine.simulate_journal_submission(db, uid, body.journal_name)
    elif body.type == "timing":
        delay = body.delay_months or 2
        return await simulation_engine.simulate_timing_impact(db, uid, delay)
    elif body.type == "collaborator":
        if not body.institution_name:
            raise HTTPException(400, "institution_name required for collaborator simulation")
        return await simulation_engine.simulate_collaborator_opportunity(db, uid, body.institution_name)
    else:
        raise HTTPException(400, f"Unknown simulation type: {body.type}. Use: journal, timing, collaborator")


# ── Events ────────────────────────────────────────────────────────────────────

@router.get("/events")
async def get_events(
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user), db=Depends(get_db),
):
    """Twin event log — shows what triggered updates."""
    db = make_db_proxy(db, user)
    return {"events": await twin_store.list_events(db, _uid(user), limit)}


class EventRequest(BaseModel):
    event_type: str
    payload:    dict = {}


@router.post("/events")
async def emit_event(body: EventRequest, user=Depends(get_current_user), db=Depends(get_db)):
    """Emit a platform event to the twin (for real-time incremental updates)."""
    db = make_db_proxy(db, user)
    await event_processor.process_event(db, _uid(user), body.event_type, body.payload)
    return {"status": "processed"}


# ── Explainability ─────────────────────────────────────────────────────────────

@router.get("/explain/domain/{domain}")
async def explain_domain(domain: str, user=Depends(get_current_user), db=Depends(get_db)):
    """Explain why a research domain was identified."""
    db = make_db_proxy(db, user)
    twin = await twin_store.get_twin(db, _uid(user))
    domains = twin.get("profile", {}).get("research_domains", [])
    match   = next((d for d in domains if d["domain"].lower() == domain.lower()), None)
    if not match:
        return {"found": False, "domain": domain, "message": "Domain not found in your Twin profile"}
    return {"found": True, "explanation": explainability.build_domain_explanation(domain, match.get("evidence", []))}


@router.get("/explain/working-style/{pattern_index}")
async def explain_working_style(pattern_index: int, user=Depends(get_current_user), db=Depends(get_db)):
    """Explain a specific working style observation."""
    db = make_db_proxy(db, user)
    twin = await twin_store.get_twin(db, _uid(user))
    obs  = twin.get("working_style", {}).get("observations", [])
    if pattern_index >= len(obs):
        raise HTTPException(404, "Working style observation not found")
    o = obs[pattern_index]
    return {"explanation": explainability.build_working_style_explanation(
        o.get("pattern", ""), o.get("evidence", []), o.get("observed_count", 0)
    )}


@router.get("/explain/health/{indicator_id}")
async def explain_health(indicator_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    """Explain a health indicator."""
    db = make_db_proxy(db, user)
    health = await health_engine.compute_health(db, _uid(user), user)
    ind    = next((i for i in health["indicators"] if i["id"] == indicator_id), None)
    if not ind:
        raise HTTPException(404, "Indicator not found")
    return {"explanation": explainability.build_health_explanation(indicator_id, ind)}


# ── Version history ───────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(
    limit: int = Query(10, ge=1, le=50),
    user=Depends(get_current_user), db=Depends(get_db),
):
    """Version history of twin updates (via event log)."""
    db = make_db_proxy(db, user)
    return {"history": await twin_store.get_version_history(db, _uid(user), limit)}


# ── User control — privacy, corrections, exclusions ──────────────────────────

class PrivacyUpdate(BaseModel):
    share_with_institution: Optional[bool] = None
    personalization_enabled: Optional[bool] = None


@router.put("/settings/privacy")
async def update_privacy(body: PrivacyUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await twin_store.update_privacy(db, _uid(user), updates)
    return {"status": "updated"}


class CorrectionRequest(BaseModel):
    field: str
    value: str


@router.post("/settings/correct")
async def correct_insight(body: CorrectionRequest, user=Depends(get_current_user), db=Depends(get_db)):
    """User correction for a derived Twin field."""
    db = make_db_proxy(db, user)
    await twin_store.add_correction(db, _uid(user), body.field, body.value)
    return {"status": "correction_saved", "field": body.field}


@router.post("/settings/reset")
async def reset_preferences(user=Depends(get_current_user), db=Depends(get_db)):
    """Reset all learned AI preferences and working style observations."""
    db = make_db_proxy(db, user)
    await twin_store.reset_preferences(db, _uid(user))
    return {"status": "reset", "cleared": ["working_style", "ai_context", "corrections"]}


class ExcludeRequest(BaseModel):
    item_type: str  # "manuscript" | "project"
    item_id:   str


@router.post("/settings/exclude")
async def exclude_item(body: ExcludeRequest, user=Depends(get_current_user), db=Depends(get_db)):
    """Exclude a project or manuscript from Twin analysis."""
    db = make_db_proxy(db, user)
    await twin_store.exclude_item(db, _uid(user), body.item_type, body.item_id)
    return {"status": "excluded", "item_type": body.item_type, "item_id": body.item_id}


# ── Startup index init ─────────────────────────────────────────────────────────

@router.on_event("startup")
async def _startup():
    pass  # ensure_indexes called from server startup
