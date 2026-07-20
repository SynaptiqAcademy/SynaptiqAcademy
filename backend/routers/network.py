"""Academic Collaboration & Discovery Network — /api/network"""
from fastapi import APIRouter, Depends, Query
from worker import enqueue_job
from worker.models import Job, Priority
from pydantic import BaseModel, Field
from typing import Optional, List
from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy

from services.network import (
    discovery_engine as discovery,
    matching_engine as matching,
    group_engine as groups,
    mentorship_engine as mentorship,
    community_engine as community,
    collaboration_engine as collab,
    event_engine as events,
    activity_engine as activity,
    analytics_engine as analytics,
    recommendation_engine as recs,
    saved_engine as saved,
)

router = APIRouter(prefix="/api/network", tags=["network"])


def _uid(user): return str(user["_id"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    description: str = ""
    type: str = "research_group"
    discipline: str = ""
    keywords: List[str] = Field(default_factory=list)
    visibility: str = "public"
    institution: str = ""
    country: str = ""
    max_members: int = 50


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discipline: Optional[str] = None
    keywords: Optional[List[str]] = None
    visibility: Optional[str] = None
    max_members: Optional[int] = None


class CollabCreate(BaseModel):
    title: str
    description: str = ""
    type: str = "co_author"
    discipline: str = ""
    skills_required: List[str] = Field(default_factory=list)
    duration: str = ""
    commitment: str = ""
    remote: bool = True
    compensation: str = "unpaid"
    deadline: str = ""
    slots: int = 1
    tags: List[str] = Field(default_factory=list)
    institution: str = ""
    country: str = ""


class CollabApplicationCreate(BaseModel):
    message: str = ""
    cv_summary: str = ""
    skills: List[str] = Field(default_factory=list)


class ApplicationRespond(BaseModel):
    status: str


class MentorProfileCreate(BaseModel):
    bio: str = ""
    expertise_areas: List[str] = Field(default_factory=list)
    availability: str = "limited"
    max_mentees: int = 3
    career_stage: str = ""
    institution: str = ""
    languages: List[str] = Field(default_factory=list)


class MentorshipRequestCreate(BaseModel):
    mentor_user_id: str
    message: str = ""
    goals: List[str] = Field(default_factory=list)
    duration_months: int = 6


class MentorRating(BaseModel):
    mentor_user_id: str
    rating: float


class CommunityCreate(BaseModel):
    name: str
    description: str = ""
    topic: str = "research_methods"
    tags: List[str] = Field(default_factory=list)
    visibility: str = "public"
    moderation: str = "owner"


class PostCreate(BaseModel):
    community_id: str
    title: str = ""
    content: str
    type: str = "discussion"
    tags: List[str] = Field(default_factory=list)


class EventCreate(BaseModel):
    title: str
    description: str = ""
    type: str = "seminar"
    discipline: str = ""
    location: str = ""
    online: bool = True
    link: str = ""
    start_date: str = ""
    end_date: str = ""
    timezone: str = "UTC"
    capacity: int = 0
    registration_required: bool = False
    tags: List[str] = Field(default_factory=list)


class ActivityCreate(BaseModel):
    type: str
    title: str
    description: str = ""
    link: str = ""
    metadata: dict = Field(default_factory=dict)
    visibility: str = "public"


class SaveItem(BaseModel):
    item_type: str
    item_id: str
    title: str = ""
    description: str = ""
    notes: str = ""


class SavedNotes(BaseModel):
    notes: str


class UnsaveItem(BaseModel):
    item_type: str
    item_id: str


# ── Discovery home ───────────────────────────────────────────────────────────

@router.get("/stats")
async def network_stats(db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    return await discovery.get_discovery_stats(db)


# ── People discovery ─────────────────────────────────────────────────────────

@router.get("/people")
async def search_people(
    q: Optional[str] = None,
    institution: Optional[str] = None,
    country: Optional[str] = None,
    career_stage: Optional[str] = None,
    discipline: Optional[str] = None,
    verification_level: Optional[int] = None,
    min_trust_score: Optional[float] = None,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    filters = {
        "q": q, "institution": institution, "country": country,
        "career_stage": career_stage, "discipline": discipline,
        "verification_level": verification_level, "min_trust_score": min_trust_score,
    }
    return await discovery.search_people(db, {k: v for k, v in filters.items() if v is not None}, page, limit)


# ── Institution discovery ────────────────────────────────────────────────────

@router.get("/institutions")
async def search_institutions(
    q: Optional[str] = None,
    country: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    filters = {"q": q, "country": country, "type": type}
    return await discovery.search_institutions(db, {k: v for k, v in filters.items() if v is not None}, page, limit)


# ── Project discovery ────────────────────────────────────────────────────────

@router.get("/projects")
async def search_projects(
    q: Optional[str] = None,
    discipline: Optional[str] = None,
    methodology: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    filters = {"q": q, "discipline": discipline, "methodology": methodology}
    return await discovery.search_projects(db, {k: v for k, v in filters.items() if v is not None}, page, limit)


# ── AI matching ──────────────────────────────────────────────────────────────

@router.get("/matches")
async def get_matches(
    limit: int = 30,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await matching.get_matches_for_user(_uid(user), db, limit)


@router.get("/matches/institutions")
async def get_institution_matches(
    limit: int = 10,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await matching.get_institution_matches(_uid(user), db, limit)


# ── Research groups ──────────────────────────────────────────────────────────

@router.get("/groups")
async def list_groups(
    q: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    filters = {"q": q, "type": type}
    return await groups.list_groups(db, {k: v for k, v in filters.items() if v is not None}, _uid(user), page, limit)


@router.post("/groups")
async def create_group(body: GroupCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await groups.create_group(_uid(user), body.model_dump(), db)


@router.get("/groups/mine")
async def my_groups(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await groups.get_my_groups(_uid(user), db)


@router.get("/groups/{group_id}")
async def get_group(group_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    g = await groups.get_group(group_id, db)
    if not g:
        from fastapi import HTTPException
        raise HTTPException(404, "Group not found")
    return g


@router.patch("/groups/{group_id}")
async def update_group(group_id: str, body: GroupUpdate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    return await groups.update_group(group_id, _uid(user), updates, db)


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return {"deleted": await groups.delete_group(group_id, _uid(user), db)}


@router.post("/groups/{group_id}/join")
async def join_group(group_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await groups.join_group(group_id, _uid(user), db)


@router.post("/groups/{group_id}/leave")
async def leave_group(group_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await groups.leave_group(group_id, _uid(user), db)


@router.get("/groups/{group_id}/members")
async def group_members(group_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await groups.get_group_members(group_id, db)


# ── Open collaborations ──────────────────────────────────────────────────────

@router.get("/collaborations")
async def list_collaborations(
    q: Optional[str] = None,
    type: Optional[str] = None,
    discipline: Optional[str] = None,
    remote: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    filters = {"q": q, "type": type, "discipline": discipline, "remote": remote}
    return await collab.list_collaborations(db, {k: v for k, v in filters.items() if v is not None}, page, limit)


@router.post("/collaborations")
async def create_collaboration(body: CollabCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await collab.create_collaboration(_uid(user), body.model_dump(), db)


@router.get("/collaborations/mine")
async def my_collaborations(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await collab.get_my_collaborations(_uid(user), db)


@router.get("/collaborations/{collab_id}")
async def get_collaboration(collab_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    c = await collab.get_collaboration(collab_id, db)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(404, "Collaboration not found")
    return c


@router.post("/collaborations/{collab_id}/apply")
async def apply_to_collaboration(
    collab_id: str, body: CollabApplicationCreate,
    db=Depends(get_db), user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await collab.apply_to_collaboration(collab_id, _uid(user), body.model_dump(), db)


@router.get("/collaborations/{collab_id}/applications")
async def collaboration_applications(
    collab_id: str, db=Depends(get_db), user=Depends(get_current_user)
):
    db = make_db_proxy(db, user)
    return await collab.get_collaboration_applications(collab_id, _uid(user), db)


@router.post("/collaborations/applications/{app_id}/respond")
async def respond_application(
    app_id: str, body: ApplicationRespond,
    db=Depends(get_db), user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await collab.respond_to_application(app_id, _uid(user), body.status, db)


@router.post("/collaborations/{collab_id}/close")
async def close_collaboration(collab_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return {"closed": await collab.close_collaboration(collab_id, _uid(user), db)}


# ── Mentorship ───────────────────────────────────────────────────────────────

@router.get("/mentors")
async def list_mentors(
    q: Optional[str] = None,
    expertise_area: Optional[str] = None,
    availability: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    filters = {"q": q, "expertise_area": expertise_area, "availability": availability}
    return await mentorship.list_mentors(db, {k: v for k, v in filters.items() if v is not None}, _uid(user), page, limit)


@router.get("/mentors/me")
async def get_my_mentor_profile(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await mentorship.get_mentor_profile(_uid(user), db)


@router.post("/mentors/me")
async def create_mentor_profile(body: MentorProfileCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await mentorship.create_mentor_profile(_uid(user), body.model_dump(), db)


@router.patch("/mentors/me")
async def update_mentor_profile(body: MentorProfileCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await mentorship.update_mentor_profile(_uid(user), body.model_dump(), db)


@router.post("/mentors/request")
async def request_mentorship(body: MentorshipRequestCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await mentorship.create_mentorship_request(_uid(user), body.mentor_user_id, body.model_dump(), db)


@router.get("/mentors/requests")
async def my_mentorship_requests(
    role: str = "mentee",
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await mentorship.get_my_requests(_uid(user), db, role)


@router.post("/mentors/requests/{request_id}/respond")
async def respond_mentorship(
    request_id: str, body: ApplicationRespond,
    db=Depends(get_db), user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await mentorship.respond_to_request(request_id, _uid(user), body.status, db)


@router.post("/mentors/rate")
async def rate_mentor(body: MentorRating, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await mentorship.rate_mentor(_uid(user), body.mentor_user_id, body.rating, db)


# ── Communities ──────────────────────────────────────────────────────────────

@router.get("/communities")
async def list_communities(
    q: Optional[str] = None,
    topic: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    filters = {"q": q, "topic": topic}
    return await community.list_communities(db, {k: v for k, v in filters.items() if v is not None}, _uid(user), page, limit)


@router.post("/communities")
async def create_community(body: CommunityCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await community.create_community(_uid(user), body.model_dump(), db)


@router.get("/communities/mine")
async def my_communities(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await community.get_my_communities(_uid(user), db)


@router.get("/communities/{community_id}")
async def get_community(community_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    c = await community.get_community(community_id, db)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(404, "Community not found")
    return c


@router.post("/communities/{community_id}/join")
async def join_community(community_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await community.join_community(community_id, _uid(user), db)


@router.post("/communities/{community_id}/leave")
async def leave_community(community_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await community.leave_community(community_id, _uid(user), db)


@router.post("/communities/posts")
async def create_post(body: PostCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await community.create_post(body.community_id, _uid(user), body.model_dump(), db)


@router.get("/communities/{community_id}/posts")
async def list_posts(
    community_id: str,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await community.list_posts(community_id, db, page, limit)


# ── Events ───────────────────────────────────────────────────────────────────

@router.get("/events")
async def list_events(
    q: Optional[str] = None,
    type: Optional[str] = None,
    online: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    filters = {"q": q, "type": type, "online": online}
    return await events.list_events(db, {k: v for k, v in filters.items() if v is not None}, page, limit)


@router.post("/events")
async def create_event(body: EventCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await events.create_event(_uid(user), body.model_dump(), db)


@router.get("/events/mine")
async def my_events(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await events.get_my_events(_uid(user), db)


@router.get("/events/{event_id}")
async def get_event(event_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    e = await events.get_event(event_id, db)
    if not e:
        from fastapi import HTTPException
        raise HTTPException(404, "Event not found")
    return e


@router.post("/events/{event_id}/register")
async def register_event(event_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await events.register_for_event(event_id, _uid(user), db)


@router.post("/events/{event_id}/unregister")
async def unregister_event(event_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await events.unregister_from_event(event_id, _uid(user), db)


# ── Activity feed ─────────────────────────────────────────────────────────────

@router.get("/activity")
async def get_feed(
    page: int = 1,
    limit: int = 30,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await activity.get_feed(db, _uid(user), page, limit)


@router.post("/activity")
async def post_activity(body: ActivityCreate, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await activity.post_activity(_uid(user), body.type, body.model_dump(), db)


@router.get("/activity/mine")
async def my_activity(
    page: int = 1,
    limit: int = 20,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await activity.get_user_activity(_uid(user), db, page, limit)


@router.delete("/activity/{activity_id}")
async def delete_activity(activity_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return {"deleted": await activity.delete_activity(activity_id, _uid(user), db)}


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics/overview")
async def network_overview(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await analytics.get_network_overview(_uid(user), db)


@router.get("/analytics/platform")
async def platform_stats(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await analytics.get_platform_network_stats(db)


@router.get("/analytics/collaborations")
async def collab_analytics(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await analytics.get_collaboration_analytics(_uid(user), db)


@router.get("/analytics/groups")
async def group_analytics(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await analytics.get_group_analytics(_uid(user), db)


# ── Recommendations ───────────────────────────────────────────────────────────

@router.get("/recommendations")
async def get_recommendations(
    category: Optional[str] = None,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await recs.get_recommendations(_uid(user), db, category)


@router.post("/recommendations/generate")
async def generate_recommendations(
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    await enqueue_job(Job(job_type="recommendation.generate", payload={"entity_id": uid}, user_id=uid), db)
    return {"status": "generating"}


@router.post("/recommendations/{rec_id}/dismiss")
async def dismiss_recommendation(rec_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return {"dismissed": await recs.dismiss_recommendation(rec_id, _uid(user), db)}


# ── Saved opportunities ───────────────────────────────────────────────────────

@router.get("/saved")
async def get_saved(
    item_type: Optional[str] = None,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    return await saved.get_saved(_uid(user), db, item_type)


@router.post("/saved")
async def save_item(body: SaveItem, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await saved.save_item(_uid(user), body.item_type, body.item_id, body.model_dump(), db)


@router.delete("/saved")
async def unsave_item(body: UnsaveItem, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return {"unsaved": await saved.unsave_item(_uid(user), body.item_type, body.item_id, db)}


@router.patch("/saved/{saved_id}/notes")
async def update_saved_notes(saved_id: str, body: SavedNotes, db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    return await saved.update_notes(saved_id, _uid(user), body.notes, db)


# ── Network settings ──────────────────────────────────────────────────────────

@router.get("/settings")
async def get_network_settings(db=Depends(get_db), user=Depends(get_current_user)):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    settings = await db["network_settings"].find_one({"user_id": uid})
    if not settings:
        settings = {
            "user_id": uid,
            "profile_visibility": "public",
            "show_in_discovery": True,
            "allow_mentorship_requests": True,
            "allow_collaboration_requests": True,
            "email_on_match": True,
            "email_on_request": True,
            "notification_frequency": "daily",
            "discovery_categories": ["collaborator", "mentor", "community", "event"],
            "blocked_users": [],
        }
    else:
        settings.pop("_id", None)
    return settings


@router.put("/settings")
async def update_network_settings(
    settings: dict,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    settings.pop("user_id", None)
    settings["user_id"] = uid
    await db["network_settings"].replace_one({"user_id": uid}, settings, upsert=True)
    return settings
