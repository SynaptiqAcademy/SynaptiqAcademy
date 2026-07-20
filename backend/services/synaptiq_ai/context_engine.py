"""Context Engine — builds the user's full platform context for AI prompt injection.

Pulls from ALL platform collections and returns a structured context dict.
Results are cached in ai_context_cache for 30 minutes to avoid repeated DB round-trips.
"""
from __future__ import annotations

import ast
import logging
from datetime import datetime, timezone, timedelta

from bson import ObjectId

logger = logging.getLogger("synaptiq.ai.context_engine")


def _safe_str(val) -> str:
    """Convert ObjectId or any value to string safely."""
    if val is None:
        return ""
    return str(val)


def _oid_to_str(doc: dict) -> dict:
    """Convert _id ObjectId to string id field in a document copy."""
    if doc is None:
        return {}
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    # Recursively convert any nested ObjectId values
    for k, v in out.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
    return out


def _parse_research_areas(raw) -> list[str]:
    """Parse research_areas which may be a Python string list or actual list."""
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (ValueError, SyntaxError):
            pass
        # Fallback: treat as comma-separated
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


async def build_user_context(user_id: str, db) -> dict:
    """
    Pull from ALL platform collections and return a structured context dict.
    Each query is wrapped in try/except to be resilient to empty/missing collections.

    Returns:
    {
      "profile": {...},          # from users
      "manuscripts": [...],      # last 10
      "projects": [...],         # member of
      "collaborations": [...],   # member of
      "grants_applied": [...],   # grant_applications
      "reputation": {...},       # research_reputation
      "impact": {...},           # research_impact
      "memory": [...],           # ai_memory (active items)
      "recent_journals_viewed": [],
      "teaching": [...],         # teaching_lessons created by user
      "summary": str,
    }
    """
    context: dict = {
        "profile": {},
        "manuscripts": [],
        "projects": [],
        "collaborations": [],
        "grants_applied": [],
        "reputation": {},
        "impact": {},
        "memory": [],
        "recent_journals_viewed": [],
        "teaching": [],
        "summary": "",
    }

    # ── Profile ───────────────────────────────────────────────────────────────
    try:
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            context["profile"] = {
                "id": user_id,
                "full_name": user_doc.get("full_name", ""),
                "email": user_doc.get("email", ""),
                "academic_role": user_doc.get("academic_role", ""),
                "institution": user_doc.get("institution", ""),
                "country": user_doc.get("country", ""),
                "research_areas": user_doc.get("research_areas") or [],
                "research_keywords": user_doc.get("research_keywords") or [],
                "orcid": user_doc.get("orcid", ""),
                "bio": (user_doc.get("bio") or "")[:500],
                "plan_code": user_doc.get("plan_code", "free"),
            }
    except Exception as exc:
        logger.warning("context_engine: profile fetch failed user=%s err=%s", user_id, exc)

    # ── Manuscripts ───────────────────────────────────────────────────────────
    try:
        ms_cursor = db.manuscripts.find(
            {"$or": [{"lead_author_id": user_id}, {"authors": user_id}]}
        ).sort("created_at", -1).limit(10)
        manuscripts = await ms_cursor.to_list(10)
        context["manuscripts"] = [
            {
                "id": str(m["_id"]),
                "title": m.get("title", ""),
                "status": m.get("status", ""),
                "manuscript_type": m.get("manuscript_type", ""),
                "created_at": m.get("created_at", ""),
            }
            for m in manuscripts
        ]
    except Exception as exc:
        logger.warning("context_engine: manuscripts fetch failed user=%s err=%s", user_id, exc)

    # ── Projects ──────────────────────────────────────────────────────────────
    try:
        proj_cursor = db.projects.find(
            {"$or": [{"owner_id": user_id}, {"members": user_id}]}
        ).sort("created_at", -1).limit(10)
        projects = await proj_cursor.to_list(10)
        context["projects"] = [
            {
                "id": str(p["_id"]),
                "title": p.get("title", ""),
                "description": (p.get("description") or "")[:300],
                "status": p.get("status", ""),
                "visibility": p.get("visibility", ""),
            }
            for p in projects
        ]
    except Exception as exc:
        logger.warning("context_engine: projects fetch failed user=%s err=%s", user_id, exc)

    # ── Collaborations ────────────────────────────────────────────────────────
    try:
        collab_cursor = db.collaborations.find(
            {"$or": [{"creator_id": user_id}, {"members": user_id}]}
        ).sort("created_at", -1).limit(10)
        collabs = await collab_cursor.to_list(10)
        context["collaborations"] = [
            {
                "id": str(c["_id"]),
                "title": c.get("title", ""),
                "research_area": c.get("research_area", ""),
                "skills_needed": c.get("skills_needed") or [],
                "status": c.get("status", ""),
            }
            for c in collabs
        ]
    except Exception as exc:
        logger.warning("context_engine: collaborations fetch failed user=%s err=%s", user_id, exc)

    # ── Grant Applications ────────────────────────────────────────────────────
    try:
        apps_cursor = db.grant_applications.find({"user_id": user_id}).sort("submitted_at", -1).limit(10)
        apps = await apps_cursor.to_list(10)
        grant_ids = [ObjectId(a["grant_id"]) for a in apps if a.get("grant_id")]
        grants_map: dict[str, dict] = {}
        if grant_ids:
            grants_docs = await db.grants.find({"_id": {"$in": grant_ids}}).to_list(10)
            for g in grants_docs:
                grants_map[str(g["_id"])] = g
        context["grants_applied"] = [
            {
                "application_id": str(a["_id"]),
                "grant_id": a.get("grant_id", ""),
                "status": a.get("status", ""),
                "submitted_at": a.get("submitted_at", ""),
                "grant_title": grants_map.get(a.get("grant_id", ""), {}).get("title", ""),
                "grant_agency": grants_map.get(a.get("grant_id", ""), {}).get("agency", ""),
            }
            for a in apps
        ]
    except Exception as exc:
        logger.warning("context_engine: grant_applications fetch failed user=%s err=%s", user_id, exc)

    # ── Research Reputation ───────────────────────────────────────────────────
    try:
        rep_doc = await db.research_reputation.find_one({"user_id": user_id})
        if rep_doc:
            context["reputation"] = {
                "overall_score": rep_doc.get("overall_score", 0),
                "publication_score": rep_doc.get("publication_score", 0),
                "collaboration_score": rep_doc.get("collaboration_score", 0),
                "impact_score": rep_doc.get("impact_score", 0),
                "engagement_score": rep_doc.get("engagement_score", 0),
                "level": rep_doc.get("level", ""),
                "badges": rep_doc.get("badges") or [],
                "rank": rep_doc.get("rank"),
            }
    except Exception as exc:
        logger.warning("context_engine: reputation fetch failed user=%s err=%s", user_id, exc)

    # ── Research Impact ───────────────────────────────────────────────────────
    try:
        impact_doc = await db.research_impact.find_one({"user_id": user_id})
        if impact_doc:
            context["impact"] = {
                "sis_total": impact_doc.get("sis_total", 0),
                "h_index": impact_doc.get("h_index", 0),
                "publication_count": impact_doc.get("publication_count", 0),
                "collaboration_count": impact_doc.get("collaboration_count", 0),
                "citation_count": impact_doc.get("citation_count", 0),
                "sis_rank": impact_doc.get("sis_rank"),
                "sis_percentile": impact_doc.get("sis_percentile"),
            }
    except Exception as exc:
        logger.warning("context_engine: impact fetch failed user=%s err=%s", user_id, exc)

    # ── AI Memory (active items) ──────────────────────────────────────────────
    try:
        mem_cursor = db.ai_memory.find({"user_id": user_id, "is_active": True}).sort("created_at", -1).limit(20)
        memories = await mem_cursor.to_list(20)
        context["memory"] = [
            {
                "id": str(m["_id"]),
                "memory_type": m.get("memory_type", "general"),
                "content": m.get("content", ""),
                "created_at": m.get("created_at", ""),
            }
            for m in memories
        ]
    except Exception as exc:
        logger.warning("context_engine: ai_memory fetch failed user=%s err=%s", user_id, exc)

    # ── Teaching Lessons ──────────────────────────────────────────────────────
    try:
        teach_cursor = db.teaching_lessons.find({"creator_id": user_id}).sort("created_at", -1).limit(10)
        lessons = await teach_cursor.to_list(10)
        context["teaching"] = [
            {
                "id": str(t["_id"]),
                "title": t.get("title", ""),
                "subject": t.get("subject", ""),
                "status": t.get("status", ""),
                "created_at": t.get("created_at", ""),
            }
            for t in lessons
        ]
    except Exception as exc:
        logger.warning("context_engine: teaching fetch failed user=%s err=%s", user_id, exc)

    # ── Recent Journals Viewed (placeholder — future ai_usage_analytics) ──────
    context["recent_journals_viewed"] = []

    # ── Build Summary ─────────────────────────────────────────────────────────
    context["summary"] = _build_summary(context)

    return context


def _build_summary(ctx: dict) -> str:
    """Construct a plain-English paragraph summarising the user's platform presence."""
    profile = ctx.get("profile") or {}
    name = profile.get("full_name") or "The researcher"
    role = profile.get("academic_role") or "researcher"
    institution = profile.get("institution") or ""
    country = profile.get("country") or ""
    research_areas = profile.get("research_areas") or []
    research_keywords = profile.get("research_keywords") or []

    n_manuscripts = len(ctx.get("manuscripts") or [])
    n_projects = len(ctx.get("projects") or [])
    n_collabs = len(ctx.get("collaborations") or [])
    n_grants = len(ctx.get("grants_applied") or [])
    n_teaching = len(ctx.get("teaching") or [])

    impact = ctx.get("impact") or {}
    reputation = ctx.get("reputation") or {}

    parts: list[str] = []

    # Identity line
    identity = f"{name} is a {role}"
    if institution:
        identity += f" at {institution}"
    if country:
        identity += f" ({country})"
    parts.append(identity + ".")

    # Research areas
    if research_areas:
        areas_str = ", ".join(research_areas[:5])
        parts.append(f"Their primary research areas are {areas_str}.")
    if research_keywords:
        kw_str = ", ".join(research_keywords[:8])
        parts.append(f"Key research keywords: {kw_str}.")

    # Platform activity
    activity_parts = []
    if n_manuscripts > 0:
        activity_parts.append(f"{n_manuscripts} manuscript{'s' if n_manuscripts != 1 else ''}")
    if n_projects > 0:
        activity_parts.append(f"{n_projects} project{'s' if n_projects != 1 else ''}")
    if n_collabs > 0:
        activity_parts.append(f"{n_collabs} collaboration{'s' if n_collabs != 1 else ''}")
    if n_grants > 0:
        activity_parts.append(f"{n_grants} grant application{'s' if n_grants != 1 else ''}")
    if n_teaching > 0:
        activity_parts.append(f"{n_teaching} teaching lesson{'s' if n_teaching != 1 else ''}")
    if activity_parts:
        parts.append(f"They have {', '.join(activity_parts)} on the platform.")

    # Impact metrics
    sis = impact.get("sis_total")
    h_idx = impact.get("h_index")
    pub_count = impact.get("publication_count")
    if sis is not None:
        parts.append(f"Synaptiq Impact Score: {sis}/10000.")
    if h_idx is not None:
        parts.append(f"H-index: {h_idx}.")
    if pub_count is not None:
        parts.append(f"Publication count: {pub_count}.")

    # Reputation
    rep_score = reputation.get("overall_score")
    rep_level = reputation.get("level")
    if rep_score is not None:
        rep_str = f"Reputation score: {rep_score}"
        if rep_level:
            rep_str += f" (level: {rep_level})"
        parts.append(rep_str + ".")

    # Memory hints
    memories = ctx.get("memory") or []
    if memories:
        goals = [m["content"] for m in memories if m.get("memory_type") in ("research_goal", "career_goal", "publication_goal")]
        if goals:
            parts.append(f"Stated goals: {'; '.join(goals[:3])}.")

    return " ".join(parts)


async def get_or_refresh_context(user_id: str, db, max_age_minutes: int = 30) -> dict:
    """Return cached context if fresh, else recompute and cache."""
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=max_age_minutes)).isoformat()

    try:
        cached = await db.ai_context_cache.find_one({"user_id": user_id})
        if cached and cached.get("computed_at", "") > cutoff:
            stored = cached.get("context")
            if stored and isinstance(stored, dict):
                return stored
    except Exception as exc:
        logger.warning("context_engine: cache read failed user=%s err=%s", user_id, exc)

    # Recompute
    context = await build_user_context(user_id, db)

    try:
        await db.ai_context_cache.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "context": context,
                "computed_at": now.isoformat(),
            }},
            upsert=True,
        )
    except Exception as exc:
        logger.warning("context_engine: cache write failed user=%s err=%s", user_id, exc)

    return context
