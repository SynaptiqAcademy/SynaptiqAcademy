import asyncio
from datetime import datetime, timezone
from bson import ObjectId


MILESTONE_DEFINITIONS = [
    # Publications
    {"key": "first_publication",       "label": "First Publication",                "category": "research",      "event_type": "publication_published", "threshold": 1,    "field": "pub_count"},
    {"key": "ten_publications",        "label": "10 Publications",                  "category": "research",      "event_type": "publication_published", "threshold": 10,   "field": "pub_count"},
    {"key": "fifty_publications",      "label": "50 Publications",                  "category": "research",      "event_type": "publication_published", "threshold": 50,   "field": "pub_count"},
    {"key": "hundred_publications",    "label": "100 Publications",                 "category": "research",      "event_type": "publication_published", "threshold": 100,  "field": "pub_count"},
    # Citations
    {"key": "first_citation",          "label": "First Citation",                   "category": "community",     "event_type": "citation_milestone",    "threshold": 1,    "field": "citation_count"},
    {"key": "ten_citations",           "label": "10 Citations",                     "category": "community",     "event_type": "citation_milestone",    "threshold": 10,   "field": "citation_count"},
    {"key": "fifty_citations",         "label": "50 Citations",                     "category": "community",     "event_type": "citation_milestone",    "threshold": 50,   "field": "citation_count"},
    {"key": "hundred_citations",       "label": "100 Citations",                    "category": "community",     "event_type": "citation_milestone",    "threshold": 100,  "field": "citation_count"},
    {"key": "five_hundred_citations",  "label": "500 Citations",                    "category": "community",     "event_type": "citation_milestone",    "threshold": 500,  "field": "citation_count"},
    {"key": "thousand_citations",      "label": "1,000 Citations",                  "category": "community",     "event_type": "citation_milestone",    "threshold": 1000, "field": "citation_count"},
    # Grants
    {"key": "first_grant",             "label": "First Grant Approved",             "category": "grant",         "event_type": "grant_approved",        "threshold": 1,    "field": "grant_count"},
    {"key": "five_grants",             "label": "5 Grants Approved",                "category": "grant",         "event_type": "grant_approved",        "threshold": 5,    "field": "grant_count"},
    {"key": "large_grant",             "label": "Grant Over €100k",                 "category": "grant",         "event_type": "funding_received",      "threshold": 1,    "field": "large_grant_count"},
    # Collaboration
    {"key": "first_collaboration",     "label": "First Collaboration",              "category": "collaboration", "event_type": "new_collaborator",      "threshold": 1,    "field": "collab_count"},
    {"key": "first_international",     "label": "First International Collaboration","category": "collaboration", "event_type": "international_collaboration", "threshold": 1, "field": "intl_count"},
    # Review
    {"key": "first_review",            "label": "First Peer Review",                "category": "review",        "event_type": "review_completed",      "threshold": 1,    "field": "review_count"},
    {"key": "ten_reviews",             "label": "10 Peer Reviews",                  "category": "review",        "event_type": "peer_review_milestone", "threshold": 10,   "field": "review_count"},
    {"key": "fifty_reviews",           "label": "50 Peer Reviews",                  "category": "review",        "event_type": "peer_review_milestone", "threshold": 50,   "field": "review_count"},
    # Teaching
    {"key": "first_course",            "label": "First Course Created",             "category": "teaching",      "event_type": "course_created",        "threshold": 1,    "field": "course_count"},
    # Verification
    {"key": "first_badge",             "label": "First Badge Earned",               "category": "verification",  "event_type": "badge_earned",          "threshold": 1,    "field": "badge_count"},
    {"key": "full_verification",       "label": "Fully Verified Researcher",        "category": "verification",  "event_type": "verification_approved", "threshold": 5,    "field": "verified_count"},
]


def _ser(doc: dict | None) -> dict | None:
    if not doc:
        return None
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def _get_metrics(user_id: str, db) -> dict:
    pub_count, grant_count, collab_count, review_count, badge_count, verified_count = await asyncio.gather(
        db.publications.count_documents({"user_id": user_id}),
        db.grant_applications.count_documents({"user_id": user_id, "status": "approved"}),
        db.collaborations.count_documents({"user_id": user_id}),
        db.reviews.count_documents({"reviewer_id": user_id}),
        db.trust_badges.count_documents({"user_id": user_id}),
        db.trust_verifications.count_documents({"user_id": user_id, "status": "verified"}),
    )

    # Citation count from research_analytics (collection may not exist — returns 0)
    citation_doc = await db.research_analytics.find_one({"user_id": user_id})
    citation_count = (citation_doc or {}).get("total_citations", 0)

    # International collaborations
    intl_count = await db.collaborations.count_documents(
        {"user_id": user_id, "is_international": True}
    )

    # Large grants (>100k)
    large_grant_count = await db.grant_applications.count_documents({
        "user_id": user_id,
        "status": "approved",
        "$or": [{"budget": {"$gte": 100000}}, {"amount": {"$gte": 100000}}],
    })

    course_count = await db.courses.count_documents({"instructor_id": user_id})

    return {
        "pub_count":        pub_count,
        "grant_count":      grant_count,
        "collab_count":     collab_count,
        "review_count":     review_count,
        "badge_count":      badge_count,
        "verified_count":   verified_count,
        "citation_count":   citation_count,
        "intl_count":       intl_count,
        "large_grant_count":large_grant_count,
        "course_count":     course_count,
    }


async def evaluate_milestones(user_id: str, db) -> list[dict]:
    from services.timeline.event_service import record_event

    metrics = await _get_metrics(user_id, db)
    now = datetime.now(timezone.utc)
    awarded = []

    for mdef in MILESTONE_DEFINITIONS:
        if metrics.get(mdef["field"], 0) >= mdef["threshold"]:
            existing = await db.timeline_milestones.find_one(
                {"user_id": user_id, "milestone_key": mdef["key"]}
            )
            if not existing:
                doc = {
                    "user_id": user_id,
                    "milestone_key": mdef["key"],
                    "label": mdef["label"],
                    "category": mdef["category"],
                    "event_type": mdef["event_type"],
                    "achieved_at": now,
                    "metric_value": metrics.get(mdef["field"], 0),
                    "threshold": mdef["threshold"],
                }
                await db.timeline_milestones.insert_one(doc)
                await record_event(
                    user_id=user_id,
                    event_type=mdef["event_type"],
                    title=f"Milestone: {mdef['label']}",
                    db=db,
                    description=f"Reached milestone: {mdef['label']}",
                    importance="milestone",
                    source="system",
                )
                awarded.append(_ser(doc))

    return awarded


async def get_milestones(user_id: str, db) -> list[dict]:
    await evaluate_milestones(user_id, db)
    cursor = db.timeline_milestones.find({"user_id": user_id}).sort("achieved_at", -1)
    return [_ser(m) async for m in cursor]
