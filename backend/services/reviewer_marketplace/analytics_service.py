from datetime import datetime, timezone, timedelta


async def get_reviewer_analytics(user_id: str, db) -> dict:
    assignments = await db["review_assignments"].find(
        {"reviewer_user_id": user_id}
    ).to_list(length=1000)

    total_invited = len(assignments)
    total_accepted = sum(
        1 for a in assignments if a.get("status") in ("accepted", "completed", "withdrawn")
    )
    total_completed = sum(1 for a in assignments if a.get("status") == "completed")
    total_declined = sum(1 for a in assignments if a.get("status") == "declined")

    acceptance_rate = round(total_accepted / max(total_invited, 1) * 100, 2)
    completion_rate = round(total_completed / max(total_accepted, 1) * 100, 2)

    pipeline_rating = [
        {"$match": {"reviewer_user_id": user_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}},
    ]
    rating_result = await db["review_ratings"].aggregate(pipeline_rating).to_list(length=1)
    average_rating = round((rating_result[0]["avg"] or 0) if rating_result else 0, 2)

    # Reviews by type
    completed_request_ids = [
        a.get("request_id") for a in assignments if a.get("status") == "completed" and a.get("request_id")
    ]
    type_counts = {}
    if completed_request_ids:
        from bson import ObjectId
        requests_cursor = db["review_requests"].find(
            {"_id": {"$in": [ObjectId(rid) for rid in completed_request_ids]}},
            {"review_type": 1},
        )
        requests_list = await requests_cursor.to_list(length=len(completed_request_ids))
        for req in requests_list:
            rtype = req.get("review_type", "unknown")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1

    # Reviews by month (last 12 months)
    now = datetime.now(timezone.utc)
    twelve_months_ago = now - timedelta(days=365)
    monthly_counts = {}
    for assignment in assignments:
        completed_at = assignment.get("completed_at")
        if completed_at and assignment.get("status") == "completed":
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at)
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            if completed_at >= twelve_months_ago:
                month_key = completed_at.strftime("%Y-%m")
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

    return {
        "total_invited": total_invited,
        "total_accepted": total_accepted,
        "total_completed": total_completed,
        "total_declined": total_declined,
        "acceptance_rate": acceptance_rate,
        "completion_rate": completion_rate,
        "average_rating": average_rating,
        "reviews_by_type": type_counts,
        "reviews_by_month": monthly_counts,
    }


async def get_requester_analytics(user_id: str, db) -> dict:
    requests = await db["review_requests"].find(
        {"requester_user_id": user_id}
    ).to_list(length=1000)

    total_requests = len(requests)
    status_breakdown = {}
    for req in requests:
        status = req.get("status", "unknown")
        status_breakdown[status] = status_breakdown.get(status, 0) + 1

    # Average time to first assignment (from created_at to first invited_at)
    time_to_assignment_days = []
    for req in requests:
        req_id = str(req["_id"])
        assignment = await db["review_assignments"].find_one(
            {"request_id": req_id},
            sort=[("invited_at", 1)],
        )
        if assignment and assignment.get("invited_at") and req.get("created_at"):
            created = req["created_at"]
            invited = assignment["invited_at"]
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            if isinstance(invited, str):
                invited = datetime.fromisoformat(invited)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if invited.tzinfo is None:
                invited = invited.replace(tzinfo=timezone.utc)
            delta = (invited - created).total_seconds() / 86400
            if delta >= 0:
                time_to_assignment_days.append(delta)

    avg_time_to_assignment = (
        round(sum(time_to_assignment_days) / len(time_to_assignment_days), 2)
        if time_to_assignment_days
        else 0
    )

    # Average rating given by this requester
    pipeline_rating = [
        {"$match": {"rater_user_id": user_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}},
    ]
    rating_result = await db["review_ratings"].aggregate(pipeline_rating).to_list(length=1)
    avg_reviewer_rating_given = round(
        (rating_result[0]["avg"] or 0) if rating_result else 0, 2
    )

    return {
        "total_requests": total_requests,
        "status_breakdown": status_breakdown,
        "avg_time_to_assignment_days": avg_time_to_assignment,
        "avg_reviewer_rating_given": avg_reviewer_rating_given,
    }


async def get_platform_review_analytics(db) -> dict:
    # Requests by status
    pipeline_status = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_result = await db["review_requests"].aggregate(pipeline_status).to_list(length=50)
    requests_by_status = {doc["_id"]: doc["count"] for doc in status_result}
    total_review_requests = sum(requests_by_status.values())

    # Active reviewers
    total_reviewers_active = await db["reviewer_profiles"].count_documents(
        {"reviewer_status": "active"}
    )

    # Average reviewer score
    pipeline_avg_score = [
        {"$match": {"reviewer_status": "active"}},
        {"$group": {"_id": None, "avg_score": {"$avg": "$reviewer_score"}}},
    ]
    avg_score_result = await db["reviewer_profiles"].aggregate(pipeline_avg_score).to_list(length=1)
    avg_reviewer_score = round(
        (avg_score_result[0]["avg_score"] or 0) if avg_score_result else 0, 2
    )

    # Average time from request created_at to first assignment invited_at
    pipeline_match_time = [
        {"$group": {"_id": "$request_id", "first_invited": {"$min": "$invited_at"}}}
    ]
    assignment_times = await db["review_assignments"].aggregate(pipeline_match_time).to_list(length=1000)

    match_times_days = []
    for entry in assignment_times:
        req_id = entry.get("_id")
        first_invited = entry.get("first_invited")
        if req_id and first_invited:
            from bson import ObjectId
            try:
                req = await db["review_requests"].find_one(
                    {"_id": ObjectId(str(req_id))}, {"created_at": 1}
                )
                if req and req.get("created_at"):
                    created = req["created_at"]
                    if isinstance(created, str):
                        created = datetime.fromisoformat(created)
                    if isinstance(first_invited, str):
                        first_invited = datetime.fromisoformat(first_invited)
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    if first_invited.tzinfo is None:
                        first_invited = first_invited.replace(tzinfo=timezone.utc)
                    delta = (first_invited - created).total_seconds() / 86400
                    if delta >= 0:
                        match_times_days.append(delta)
            except Exception:
                pass

    avg_match_time = (
        round(sum(match_times_days) / len(match_times_days), 2)
        if match_times_days
        else 0
    )

    # Top research areas
    pipeline_areas = [
        {"$unwind": "$research_areas"},
        {"$group": {"_id": "$research_areas", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_areas_result = await db["reviewer_profiles"].aggregate(pipeline_areas).to_list(length=10)
    top_research_areas = [{"area": doc["_id"], "count": doc["count"]} for doc in top_areas_result]

    return {
        "total_review_requests": total_review_requests,
        "requests_by_status": requests_by_status,
        "total_reviewers_active": total_reviewers_active,
        "avg_reviewer_score": avg_reviewer_score,
        "avg_match_time_days": avg_match_time,
        "top_research_areas": top_research_areas,
    }
