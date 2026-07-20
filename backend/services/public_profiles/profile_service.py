import asyncio
from datetime import datetime, timezone
from bson import ObjectId


def _str_id(doc: dict) -> dict:
    """Convert _id ObjectId to string in-place."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def get_full_profile(user_id: str, db, viewer_id: str = None) -> dict:
    """Aggregate all profile data from multiple collections."""
    (
        user,
        profile_doc,
        research_impact,
        research_reputation,
        pub_count,
        proj_count,
        collab_count,
        follower_count,
        showcase_raw,
    ) = await asyncio.gather(
        db.users.find_one({"_id": ObjectId(user_id)}),
        db.public_profiles.find_one({"user_id": user_id}),
        db.research_impact.find_one({"user_id": user_id}),
        db.research_reputation.find_one({"user_id": user_id}),
        db.publications.count_documents({"owner_id": user_id}),
        db.projects.count_documents(
            {"$or": [{"created_by": user_id}, {"members.user_id": user_id}]}
        ),
        db.collaborations.count_documents(
            {"$or": [{"created_by": user_id}, {"participants.user_id": user_id}]}
        ),
        db.profile_followers.count_documents({"following_id": user_id}),
        _get_showcase_list(user_id, db),
    )

    if not user:
        return {}

    # Build impact block
    impact = {}
    if research_impact:
        impact = {
            "sis_total": research_impact.get("sis_total") or 0,
            "h_index": research_impact.get("h_index") or 0,
            "i10_index": research_impact.get("i10_index") or 0,
            "total_citations": research_impact.get("total_citations") or 0,
            "components": research_impact.get("components") or {},
        }

    # Build reputation block
    reputation = {}
    if research_reputation:
        badges = research_reputation.get("badges") or []
        earned_badges = [b for b in badges if b.get("earned")]
        reputation = {
            "overall_score": research_reputation.get("overall_score") or 0,
            "level_name": research_reputation.get("level_name") or "",
            "level_number": research_reputation.get("level_number") or 0,
            "badges": earned_badges,
            "global_rank": research_reputation.get("global_rank"),
            "country_rank": research_reputation.get("country_rank"),
            "institution_rank": research_reputation.get("institution_rank"),
        }

    # Serialize showcase
    showcase = []
    for item in showcase_raw:
        if "_id" in item:
            item["_id"] = str(item["_id"])
        showcase.append(item)

    orcid_val = user.get("orcid")
    orcid_id = None
    if isinstance(orcid_val, dict):
        orcid_id = orcid_val.get("orcid_id")

    return {
        "user_id": user_id,
        "slug": profile_doc["slug"] if profile_doc else None,
        "full_name": user.get("full_name"),
        "avatar_url": user.get("avatar_url"),
        "academic_title": user.get("academic_title") or user.get("role"),
        "career_stage": user.get("career_stage"),
        "institution": user.get("institution"),
        "institution_id": user.get("institution_id"),
        "department": user.get("department"),
        "country": user.get("country"),
        "biography": user.get("biography"),
        "research_interests": user.get("research_interests") or [],
        "keywords": user.get("keywords") or [],
        "website": user.get("website"),
        "orcid_id": orcid_id,
        "email": user.get("email"),
        "impact": impact,
        "reputation": reputation,
        "stats": {
            "publications": pub_count,
            "projects": proj_count,
            "collaborations": collab_count,
            "followers": follower_count,
            "citations": (research_impact or {}).get("total_citations") or 0,
            "h_index": (research_impact or {}).get("h_index") or 0,
        },
        "showcase": showcase,
        "visibility_settings": profile_doc["visibility_settings"] if profile_doc else {},
        "view_count": (profile_doc.get("view_count") or 0) if profile_doc else 0,
    }


async def _get_showcase_list(user_id: str, db) -> list:
    cursor = db.profile_showcases.find({"user_id": user_id}).sort("order", 1)
    return await cursor.to_list(length=50)


async def get_publications_for_profile(user_id: str, db) -> list:
    """Fetch publications and manuscripts, merge, deduplicate by title."""
    pub_cursor = db.publications.find({"owner_id": user_id}).sort("year", -1)
    pubs = await pub_cursor.to_list(length=200)

    manuscript_cursor = db.manuscripts.find(
        {"user_id": user_id, "status": {"$in": ["published", "accepted"]}}
    ).sort("year", -1)
    manuscripts = await manuscript_cursor.to_list(length=200)

    result = []
    seen_titles = set()

    for pub in pubs:
        title = pub.get("title") or ""
        title_lower = title.lower().strip()
        if title_lower and title_lower in seen_titles:
            continue
        if title_lower:
            seen_titles.add(title_lower)
        result.append({
            "id": str(pub["_id"]),
            "title": title,
            "year": pub.get("year"),
            "journal": pub.get("journal") or pub.get("venue"),
            "pub_type": pub.get("pub_type") or pub.get("type") or "article",
            "citation_count": pub.get("citation_count") or pub.get("citations") or 0,
            "source": "publications",
        })

    for ms in manuscripts:
        title = ms.get("title") or ""
        title_lower = title.lower().strip()
        if title_lower and title_lower in seen_titles:
            continue
        if title_lower:
            seen_titles.add(title_lower)
        result.append({
            "id": str(ms["_id"]),
            "title": title,
            "year": ms.get("year"),
            "journal": ms.get("journal") or ms.get("venue"),
            "pub_type": ms.get("pub_type") or ms.get("type") or "article",
            "citation_count": ms.get("citation_count") or ms.get("citations") or 0,
            "source": "manuscripts",
        })

    # Sort merged list by year desc
    result.sort(key=lambda x: x.get("year") or 0, reverse=True)
    return result


async def get_impact_for_profile(user_id: str, db) -> dict:
    """Return full research_impact doc or empty dict."""
    doc = await db.research_impact.find_one({"user_id": user_id})
    if not doc:
        return {}
    doc["_id"] = str(doc["_id"])
    return doc


async def get_projects_for_profile(user_id: str, db) -> list:
    """Return up to 10 projects where user is creator or member."""
    cursor = db.projects.find(
        {"$or": [{"created_by": user_id}, {"members.user_id": user_id}]}
    ).sort("created_at", -1).limit(10)
    projects = await cursor.to_list(length=10)
    result = []
    for p in projects:
        result.append({
            "id": str(p["_id"]),
            "title": p.get("title") or "",
            "status": p.get("status") or "",
            "description": p.get("description") or "",
            "created_at": p.get("created_at"),
        })
    return result


async def get_grants_for_profile(user_id: str, db) -> list:
    """Fetch grant_applications joined with grants, plus grant_collaborations."""
    app_cursor = db.grant_applications.find({"user_id": user_id}).sort("submitted_at", -1)
    applications = await app_cursor.to_list(length=100)

    result = []
    for app in applications:
        grant_title = app.get("grant_title") or ""
        funder = app.get("funder") or ""
        # Try to join with grants collection for title/funder if not present
        grant_id = app.get("grant_id")
        if grant_id and (not grant_title or not funder):
            try:
                grant_doc = await db.grants.find_one({"_id": ObjectId(str(grant_id))})
                if grant_doc:
                    grant_title = grant_title or grant_doc.get("title") or ""
                    funder = funder or grant_doc.get("funder") or grant_doc.get("funding_agency") or ""
            except Exception:
                pass
        result.append({
            "id": str(app["_id"]),
            "grant_title": grant_title,
            "funder": funder,
            "status": app.get("status") or "",
            "amount_requested": app.get("amount_requested") or app.get("budget") or 0,
            "submitted_at": app.get("submitted_at"),
            "source": "application",
        })

    # Also fetch grant_collaborations where user is lead or member
    collab_cursor = db.grant_collaborations.find(
        {"$or": [{"lead_user_id": user_id}, {"members.user_id": user_id}]}
    ).sort("created_at", -1).limit(20)
    grant_collabs = await collab_cursor.to_list(length=20)
    for gc in grant_collabs:
        result.append({
            "id": str(gc["_id"]),
            "grant_title": gc.get("grant_title") or gc.get("title") or "",
            "funder": gc.get("funder") or "",
            "status": gc.get("status") or "",
            "amount_requested": gc.get("amount_requested") or 0,
            "submitted_at": gc.get("submitted_at") or gc.get("created_at"),
            "source": "collaboration",
        })

    return result


async def get_collaborations_for_profile(user_id: str, db) -> dict:
    """Return total count and recent 5 collaborations."""
    query = {"$or": [{"created_by": user_id}, {"participants.user_id": user_id}]}
    total = await db.collaborations.count_documents(query)
    cursor = db.collaborations.find(query).sort("created_at", -1).limit(5)
    docs = await cursor.to_list(length=5)
    recent = []
    for d in docs:
        recent.append({
            "id": str(d["_id"]),
            "title": d.get("title") or "",
            "status": d.get("status") or "",
            "created_at": d.get("created_at"),
        })
    return {"total": total, "recent": recent}


async def get_teaching_for_profile(user_id: str, db) -> dict:
    """Return total lessons count and distinct teaching areas."""
    query = {"$or": [{"created_by": user_id}, {"user_id": user_id}]}
    total_lessons = await db.teaching_lessons.count_documents(query)

    # Get distinct research/subject areas
    cursor = db.teaching_lessons.find(query, {"research_area": 1, "subject_area": 1, "topic": 1})
    lessons = await cursor.to_list(length=500)
    areas = set()
    for lesson in lessons:
        for field in ("research_area", "subject_area", "topic"):
            val = lesson.get(field)
            if val and isinstance(val, str):
                areas.add(val)

    # Teaching score from reputation or analytics
    teaching_score = None
    rep_doc = await db.research_reputation.find_one({"user_id": user_id}, {"teaching_score": 1})
    if rep_doc:
        teaching_score = rep_doc.get("teaching_score")

    if teaching_score is None:
        analytics_doc = await db.teaching_analytics.find_one({"user_id": user_id}, {"score": 1, "rating": 1})
        if analytics_doc:
            teaching_score = analytics_doc.get("score") or analytics_doc.get("rating")

    return {
        "total_lessons": total_lessons,
        "teaching_areas": sorted(list(areas)),
        "teaching_score": teaching_score,
    }


async def get_reputation_for_profile(user_id: str, db) -> dict:
    """Return reputation summary with defaults if not found."""
    doc = await db.research_reputation.find_one({"user_id": user_id})
    if not doc:
        return {
            "overall_score": 0,
            "level_name": "",
            "level_number": 0,
            "badges": [],
            "global_rank": None,
            "country_rank": None,
            "institution_rank": None,
        }
    badges = doc.get("badges") or []
    earned_badges = [b for b in badges if b.get("earned")]
    return {
        "overall_score": doc.get("overall_score") or 0,
        "level_name": doc.get("level_name") or "",
        "level_number": doc.get("level_number") or 0,
        "badges": earned_badges,
        "global_rank": doc.get("global_rank"),
        "country_rank": doc.get("country_rank"),
        "institution_rank": doc.get("institution_rank"),
    }


async def get_timeline_for_profile(user_id: str, db) -> list:
    """Merge events from publications, projects, grants, badges; sort desc; return top 30."""

    async def fetch_pub_events():
        cursor = db.publications.find({"owner_id": user_id}, {"title": 1, "year": 1}).sort("year", -1).limit(20)
        docs = await cursor.to_list(length=20)
        events = []
        for d in docs:
            year = d.get("year")
            date_str = f"{year}-01-01" if year else None
            if date_str:
                events.append({
                    "type": "publication",
                    "date": date_str,
                    "title": d.get("title") or "",
                    "id": str(d["_id"]),
                })
        return events

    async def fetch_project_events():
        cursor = db.projects.find(
            {"$or": [{"created_by": user_id}, {"members.user_id": user_id}]},
            {"title": 1, "created_at": 1}
        ).sort("created_at", -1).limit(5)
        docs = await cursor.to_list(length=5)
        events = []
        for d in docs:
            created_at = d.get("created_at")
            if created_at:
                date_str = str(created_at)[:10] if created_at else None
                events.append({
                    "type": "project",
                    "date": date_str,
                    "title": d.get("title") or "",
                    "id": str(d["_id"]),
                })
        return events

    async def fetch_grant_events():
        cursor = db.grant_applications.find(
            {"user_id": user_id},
            {"grant_title": 1, "submitted_at": 1}
        ).sort("submitted_at", -1).limit(5)
        docs = await cursor.to_list(length=5)
        events = []
        for d in docs:
            submitted_at = d.get("submitted_at")
            if submitted_at:
                date_str = str(submitted_at)[:10]
                events.append({
                    "type": "grant",
                    "date": date_str,
                    "title": d.get("grant_title") or "",
                    "id": str(d["_id"]),
                })
        return events

    async def fetch_badge_events():
        doc = await db.research_reputation.find_one({"user_id": user_id}, {"badges": 1})
        if not doc:
            return []
        badges = doc.get("badges") or []
        events = []
        for b in badges:
            if b.get("earned") and b.get("awarded_at"):
                awarded_at = b["awarded_at"]
                date_str = str(awarded_at)[:10]
                events.append({
                    "type": "badge",
                    "date": date_str,
                    "title": b.get("name") or b.get("badge_name") or "Badge earned",
                })
        return events

    all_events_lists = await asyncio.gather(
        fetch_pub_events(),
        fetch_project_events(),
        fetch_grant_events(),
        fetch_badge_events(),
    )

    merged = []
    for event_list in all_events_lists:
        merged.extend(event_list)

    # Sort by date desc
    def sort_key(event):
        date = event.get("date") or "0000-01-01"
        return date

    merged.sort(key=sort_key, reverse=True)
    return merged[:30]
