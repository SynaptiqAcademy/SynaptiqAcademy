from datetime import datetime, timezone
from bson import ObjectId
import logging

log = logging.getLogger(__name__)

# ── 60-type event catalogue ─────────────────────────────────────────────────

EVENT_CATALOGUE = {
    # Research
    "publication_created":             {"category": "research",      "label": "Publication Created",             "icon": "FileText",    "color": "#0369A1"},
    "publication_accepted":            {"category": "research",      "label": "Publication Accepted",            "icon": "CheckCircle2","color": "#059669"},
    "publication_published":           {"category": "research",      "label": "Publication Published",           "icon": "BookOpen",    "color": "#059669"},
    "preprint_uploaded":               {"category": "research",      "label": "Preprint Uploaded",               "icon": "Upload",      "color": "#7C3AED"},
    "dataset_published":               {"category": "research",      "label": "Dataset Published",               "icon": "Database",    "color": "#0369A1"},
    "software_released":               {"category": "research",      "label": "Software Released",               "icon": "Code2",       "color": "#7C3AED"},
    "patent_registered":               {"category": "research",      "label": "Patent Registered",               "icon": "Shield",      "color": "#D97706"},
    "conference_paper_accepted":       {"category": "research",      "label": "Conference Paper Accepted",       "icon": "Mic",         "color": "#059669"},
    "book_published":                  {"category": "research",      "label": "Book Published",                  "icon": "BookOpen",    "color": "#0369A1"},
    "book_chapter_published":          {"category": "research",      "label": "Book Chapter Published",          "icon": "BookOpen",    "color": "#0369A1"},
    # Teaching
    "course_created":                  {"category": "teaching",      "label": "Course Created",                  "icon": "GraduationCap","color": "#7C3AED"},
    "course_updated":                  {"category": "teaching",      "label": "Course Updated",                  "icon": "PenTool",     "color": "#7C3AED"},
    "lesson_published":                {"category": "teaching",      "label": "Lesson Published",                "icon": "BookOpen",    "color": "#7C3AED"},
    "assessment_created":              {"category": "teaching",      "label": "Assessment Created",              "icon": "ClipboardList","color": "#7C3AED"},
    "teaching_award":                  {"category": "teaching",      "label": "Teaching Award",                  "icon": "Award",       "color": "#D97706"},
    "teaching_certification":          {"category": "teaching",      "label": "Teaching Certification",          "icon": "BadgeCheck",  "color": "#059669"},
    "student_supervision":             {"category": "teaching",      "label": "Student Supervision",             "icon": "Users",       "color": "#7C3AED"},
    # Grants
    "grant_submitted":                 {"category": "grant",         "label": "Grant Submitted",                 "icon": "Send",        "color": "#D97706"},
    "grant_approved":                  {"category": "grant",         "label": "Grant Approved",                  "icon": "CheckCircle2","color": "#059669"},
    "grant_completed":                 {"category": "grant",         "label": "Grant Completed",                 "icon": "CheckSquare", "color": "#059669"},
    "funding_received":                {"category": "grant",         "label": "Funding Received",                "icon": "DollarSign",  "color": "#059669"},
    "research_project_started":        {"category": "grant",         "label": "Research Project Started",        "icon": "Play",        "color": "#0369A1"},
    "research_project_completed":      {"category": "grant",         "label": "Research Project Completed",      "icon": "CheckSquare", "color": "#059669"},
    "repository_upload":               {"category": "grant",         "label": "Repository Upload",               "icon": "HardDrive",   "color": "#7C3AED"},
    "repository_version_released":     {"category": "grant",         "label": "Repository Version Released",     "icon": "Tag",         "color": "#7C3AED"},
    # Collaboration
    "workspace_created":               {"category": "collaboration", "label": "Workspace Created",               "icon": "Folder",      "color": "#0369A1"},
    "new_collaborator":                {"category": "collaboration", "label": "New Collaborator",                "icon": "UserPlus",    "color": "#0369A1"},
    "invitation_accepted":             {"category": "collaboration", "label": "Invitation Accepted",             "icon": "Mail",        "color": "#059669"},
    "international_collaboration":     {"category": "collaboration", "label": "International Collaboration",     "icon": "Globe",       "color": "#0369A1"},
    "institution_partnership":         {"category": "collaboration", "label": "Institution Partnership",         "icon": "Building2",   "color": "#0369A1"},
    # Review
    "review_completed":                {"category": "review",        "label": "Review Completed",                "icon": "FileCheck",   "color": "#059669"},
    "reviewer_invitation":             {"category": "review",        "label": "Reviewer Invitation",             "icon": "Mail",        "color": "#D97706"},
    "editorial_board_appointment":     {"category": "review",        "label": "Editorial Board Appointment",     "icon": "Star",        "color": "#D97706"},
    "editor_appointment":              {"category": "review",        "label": "Editor Appointment",              "icon": "PenLine",     "color": "#D97706"},
    "peer_review_milestone":           {"category": "review",        "label": "Peer Review Milestone",           "icon": "Trophy",      "color": "#D97706"},
    # Verification
    "trust_score_increased":           {"category": "verification",  "label": "Trust Score Increased",           "icon": "TrendingUp",  "color": "#059669"},
    "badge_earned":                    {"category": "verification",  "label": "Badge Earned",                    "icon": "BadgeCheck",  "color": "#D97706"},
    "verification_approved":           {"category": "verification",  "label": "Verification Approved",           "icon": "ShieldCheck", "color": "#059669"},
    "academic_passport_updated":       {"category": "verification",  "label": "Academic Passport Updated",       "icon": "Fingerprint", "color": "#0369A1"},
    "identity_verified":               {"category": "verification",  "label": "Identity Verified",               "icon": "UserCheck",   "color": "#059669"},
    "institution_verified":            {"category": "verification",  "label": "Institution Verified",            "icon": "Building2",   "color": "#059669"},
    "integrity_report_completed":      {"category": "verification",  "label": "Integrity Report Completed",      "icon": "FileSearch",  "color": "#0369A1"},
    # Recognition
    "award_received":                  {"category": "recognition",   "label": "Award Received",                  "icon": "Award",       "color": "#D97706"},
    "promotion":                       {"category": "recognition",   "label": "Promotion",                       "icon": "TrendingUp",  "color": "#D97706"},
    "academic_title":                  {"category": "recognition",   "label": "Academic Title",                  "icon": "GraduationCap","color": "#D97706"},
    "membership":                      {"category": "recognition",   "label": "Membership",                      "icon": "Users",       "color": "#0369A1"},
    "professional_certification":      {"category": "recognition",   "label": "Professional Certification",      "icon": "BadgeCheck",  "color": "#059669"},
    "keynote_speaker":                 {"category": "recognition",   "label": "Keynote Speaker",                 "icon": "Mic",         "color": "#D97706"},
    "conference_organizer":            {"category": "recognition",   "label": "Conference Organizer",            "icon": "CalendarDays","color": "#0369A1"},
    # Community
    "citation_milestone":              {"category": "community",     "label": "Citation Milestone",              "icon": "TrendingUp",  "color": "#D97706"},
    "download_milestone":              {"category": "community",     "label": "Download Milestone",              "icon": "Download",    "color": "#0369A1"},
    "profile_views":                   {"category": "community",     "label": "Profile Views",                   "icon": "Eye",         "color": "#0369A1"},
    "followers_milestone":             {"category": "community",     "label": "New Followers",                   "icon": "UserPlus",    "color": "#0369A1"},
    "recommendations":                 {"category": "community",     "label": "Recommendations",                 "icon": "ThumbsUp",    "color": "#059669"},
    # AI
    "ai_manuscript_generated":         {"category": "ai",            "label": "AI Manuscript Generated",         "icon": "Sparkles",    "color": "#7C3AED"},
    "ai_review_completed":             {"category": "ai",            "label": "AI Review Completed",             "icon": "Sparkles",    "color": "#7C3AED"},
    "ai_statistical_analysis":         {"category": "ai",            "label": "AI Statistical Analysis",         "icon": "BarChart2",   "color": "#7C3AED"},
    "ai_literature_review":            {"category": "ai",            "label": "AI Literature Review",            "icon": "BookOpen",    "color": "#7C3AED"},
    "ai_collaboration_recommendation": {"category": "ai",            "label": "AI Collaboration Recommendation", "icon": "Sparkles",    "color": "#7C3AED"},
    "ai_abstract_generated":           {"category": "ai",            "label": "AI Abstract Generated",           "icon": "Sparkles",    "color": "#7C3AED"},
}

CATEGORY_COLORS = {
    "research":      "#0369A1",
    "teaching":      "#7C3AED",
    "grant":         "#059669",
    "collaboration": "#0F2847",
    "review":        "#D97706",
    "verification":  "#059669",
    "recognition":   "#D97706",
    "community":     "#0369A1",
    "ai":            "#7C3AED",
}

CATEGORIES = list(CATEGORY_COLORS.keys())


def _ser(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _ser(v)
        elif isinstance(v, list):
            out[k] = [
                _ser(i) if isinstance(i, dict) else (str(i) if isinstance(i, ObjectId) else i)
                for i in v
            ]
        else:
            out[k] = v
    return out


async def record_event(
    user_id: str,
    event_type: str,
    title: str,
    db,
    description: str = "",
    metadata: dict | None = None,
    visibility: str = "public",
    importance: str = "normal",
    source: str = "auto",
    source_id: str | None = None,
    source_collection: str | None = None,
    occurred_at: datetime | None = None,
    tags: list | None = None,
) -> dict:
    cat_info = EVENT_CATALOGUE.get(
        event_type,
        {"category": "research", "label": event_type, "icon": "Circle", "color": "#0369A1"},
    )
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "event_type": event_type,
        "category": cat_info["category"],
        "label": cat_info["label"],
        "icon": cat_info["icon"],
        "color": cat_info["color"],
        "title": title,
        "description": description,
        "metadata": metadata or {},
        "visibility": visibility,
        "importance": importance,
        "is_milestone": importance == "milestone",
        "source": source,
        "source_id": source_id,
        "source_collection": source_collection,
        "occurred_at": occurred_at or now,
        "created_at": now,
        "updated_at": now,
        "tags": tags or [],
    }
    await db.timeline_events.insert_one(doc)
    return _ser(doc)


async def get_events(
    user_id: str,
    db,
    category: str | None = None,
    event_type: str | None = None,
    importance: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = None,
    milestones_only: bool = False,
    limit: int = 50,
    skip: int = 0,
) -> list[dict]:
    filt: dict = {"user_id": user_id}
    if category:
        filt["category"] = category
    if event_type:
        filt["event_type"] = event_type
    if importance:
        filt["importance"] = importance
    if milestones_only:
        filt["is_milestone"] = True
    if start_date or end_date:
        filt["occurred_at"] = {}
        if start_date:
            filt["occurred_at"]["$gte"] = start_date
        if end_date:
            filt["occurred_at"]["$lte"] = end_date
    if search:
        filt["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search.lower()]}},
        ]
    cursor = db.timeline_events.find(filt).sort("occurred_at", -1).skip(skip).limit(limit)
    return [_ser(e) async for e in cursor]


async def get_public_events(target_user_id: str, db, limit: int = 50, skip: int = 0) -> list[dict]:
    cursor = (
        db.timeline_events
        .find({"user_id": target_user_id, "visibility": "public"})
        .sort("occurred_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [_ser(e) async for e in cursor]


async def get_event(event_id: str, user_id: str, db) -> dict | None:
    try:
        oid = ObjectId(event_id)
    except Exception:
        return None
    doc = await db.timeline_events.find_one({"_id": oid, "user_id": user_id})
    return _ser(doc)


async def update_event(event_id: str, user_id: str, updates: dict, db) -> dict | None:
    try:
        oid = ObjectId(event_id)
    except Exception:
        return None
    updates["updated_at"] = datetime.now(timezone.utc)
    await db.timeline_events.update_one({"_id": oid, "user_id": user_id}, {"$set": updates})
    return _ser(await db.timeline_events.find_one({"_id": oid}))


async def delete_event(event_id: str, user_id: str, db) -> bool:
    try:
        oid = ObjectId(event_id)
    except Exception:
        return False
    res = await db.timeline_events.delete_one(
        {"_id": oid, "user_id": user_id, "source": "manual"}
    )
    return res.deleted_count > 0


async def get_stats(user_id: str, db) -> dict:
    total = await db.timeline_events.count_documents({"user_id": user_id})
    milestones = await db.timeline_events.count_documents({"user_id": user_id, "is_milestone": True})
    breakdown = {}
    for cat in CATEGORIES:
        breakdown[cat] = await db.timeline_events.count_documents({"user_id": user_id, "category": cat})
    cursor = db.timeline_events.find({"user_id": user_id}).sort("occurred_at", -1).limit(1)
    latest = None
    async for doc in cursor:
        latest = _ser(doc)
    earliest = None
    cursor2 = db.timeline_events.find({"user_id": user_id}).sort("occurred_at", 1).limit(1)
    async for doc in cursor2:
        earliest = _ser(doc)
    return {
        "total_events": total,
        "milestone_count": milestones,
        "category_breakdown": breakdown,
        "latest_event": latest,
        "earliest_event": earliest,
    }


async def sync_from_existing(user_id: str, db) -> dict:
    now = datetime.now(timezone.utc)
    synced = 0
    skipped = 0

    async def _synced(sid: str, col: str) -> bool:
        return bool(await db.timeline_events.find_one(
            {"user_id": user_id, "source_id": sid, "source_collection": col}
        ))

    # Publications
    async for doc in db.publications.find({"user_id": user_id}):
        sid = str(doc["_id"])
        if not await _synced(sid, "publications"):
            await record_event(
                user_id=user_id, event_type="publication_published",
                title=doc.get("title", "Publication"), db=db,
                source="sync", source_id=sid, source_collection="publications",
                occurred_at=doc.get("published_at") or doc.get("created_at") or now,
                metadata={"doi": doc.get("doi", ""), "journal": doc.get("journal", "")},
            )
            synced += 1
        else:
            skipped += 1

    # Courses
    async for doc in db.courses.find({"instructor_id": user_id}):
        sid = str(doc["_id"])
        if not await _synced(sid, "courses"):
            await record_event(
                user_id=user_id, event_type="course_created",
                title=doc.get("title", "Course"), db=db,
                source="sync", source_id=sid, source_collection="courses",
                occurred_at=doc.get("created_at") or now,
            )
            synced += 1
        else:
            skipped += 1

    # Grant applications
    async for doc in db.grant_applications.find({"user_id": user_id}):
        sid = str(doc["_id"])
        if not await _synced(sid, "grant_applications"):
            evt = "grant_approved" if doc.get("status") == "approved" else "grant_submitted"
            await record_event(
                user_id=user_id, event_type=evt,
                title=doc.get("title", doc.get("grant_title", "Grant")), db=db,
                source="sync", source_id=sid, source_collection="grant_applications",
                occurred_at=doc.get("submitted_at") or doc.get("created_at") or now,
                metadata={"funder": doc.get("funder", ""), "amount": doc.get("budget", doc.get("amount", 0))},
            )
            synced += 1
        else:
            skipped += 1

    # Collaborations
    async for doc in db.collaborations.find({"user_id": user_id}):
        sid = str(doc["_id"])
        if not await _synced(sid, "collaborations"):
            await record_event(
                user_id=user_id, event_type="new_collaborator",
                title=doc.get("title", "Collaboration"), db=db,
                source="sync", source_id=sid, source_collection="collaborations",
                occurred_at=doc.get("created_at") or now,
            )
            synced += 1
        else:
            skipped += 1

    # Peer reviews
    async for doc in db.reviews.find({"reviewer_id": user_id}):
        sid = str(doc["_id"])
        if not await _synced(sid, "reviews"):
            await record_event(
                user_id=user_id, event_type="review_completed",
                title=doc.get("title", "Peer Review Completed"), db=db,
                source="sync", source_id=sid, source_collection="reviews",
                occurred_at=doc.get("completed_at") or doc.get("created_at") or now,
            )
            synced += 1
        else:
            skipped += 1

    # Trust badges
    async for doc in db.trust_badges.find({"user_id": user_id}):
        sid = str(doc["_id"])
        if not await _synced(sid, "trust_badges"):
            await record_event(
                user_id=user_id, event_type="badge_earned",
                title=f"Badge Earned: {doc.get('label', 'Badge')}", db=db,
                source="sync", source_id=sid, source_collection="trust_badges",
                occurred_at=doc.get("issued_at") or now,
                metadata={"badge_key": doc.get("badge_key", "")},
            )
            synced += 1
        else:
            skipped += 1

    # Trust verifications (approved only)
    async for doc in db.trust_verifications.find({"user_id": user_id, "status": "verified"}):
        sid = str(doc["_id"])
        if not await _synced(sid, "trust_verifications"):
            v_label = doc.get("label", doc.get("verification_type", "Verification"))
            await record_event(
                user_id=user_id, event_type="verification_approved",
                title=f"Verification Approved: {v_label}", db=db,
                source="sync", source_id=sid, source_collection="trust_verifications",
                occurred_at=doc.get("updated_at") or doc.get("created_at") or now,
                metadata={"verification_type": doc.get("verification_type", "")},
            )
            synced += 1
        else:
            skipped += 1

    return {"synced": synced, "skipped": skipped}
