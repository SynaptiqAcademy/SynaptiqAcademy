from datetime import datetime, timezone
from bson import ObjectId

from services.reviewer_marketplace.reviewer_service import compute_reviewer_score


async def compute_review_quality(report_id: str, db) -> dict:
    report = await db["review_reports"].find_one({"_id": ObjectId(report_id)})
    if not report:
        return {}

    review_sections = report.get("review_sections") or []
    summary_comments = report.get("summary_comments") or ""

    # Completeness (0-25)
    non_empty_sections = [
        s for s in review_sections
        if s.get("comments") and str(s["comments"]).strip()
    ]
    expected_sections = max(len(review_sections), 1)
    completeness = (len(non_empty_sections) / expected_sections) * 25
    if summary_comments and summary_comments.strip():
        completeness = min(25, completeness + 5)

    # Depth (0-25)
    total_chars = sum(
        len(str(s.get("comments", "")))
        for s in review_sections
        if s.get("comments")
    )
    depth = min(25, total_chars / 50)

    # Timeliness (0-25)
    assignment_id = report.get("assignment_id")
    timeliness = 0
    if assignment_id:
        try:
            assignment = await db["review_assignments"].find_one(
                {"_id": ObjectId(str(assignment_id))}
            ) or {}
        except Exception:
            assignment = {}

        due_date = assignment.get("due_date")
        submitted_at = report.get("submitted_at")

        if due_date and submitted_at:
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date)
            if isinstance(submitted_at, str):
                submitted_at = datetime.fromisoformat(submitted_at)

            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)

            delta_days = (submitted_at - due_date).total_seconds() / 86400
            if delta_days <= 0:
                timeliness = 25
            elif delta_days <= 1:
                timeliness = 15
            elif delta_days <= 3:
                timeliness = 5
            else:
                timeliness = 0
        else:
            timeliness = 15
    else:
        timeliness = 15

    # Structure (0-25)
    sections_with_scores = [s for s in review_sections if s.get("score") is not None]
    if not review_sections:
        structure = 0
    elif len(sections_with_scores) == len(review_sections):
        structure = 25
    elif sections_with_scores:
        structure = 15
    else:
        structure = 0

    quality_score = round(
        min(100.0, completeness + depth + timeliness + structure), 2
    )

    await db["review_reports"].update_one(
        {"_id": ObjectId(report_id)},
        {"$set": {"quality_score": quality_score}},
    )

    return {
        "completeness": round(completeness, 2),
        "depth": round(depth, 2),
        "timeliness": timeliness,
        "structure": structure,
        "quality_score": quality_score,
    }


async def update_reviewer_stats(reviewer_user_id: str, db) -> dict:
    # Average rating
    pipeline_rating = [
        {"$match": {"reviewer_user_id": reviewer_user_id}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    rating_result = await db["review_ratings"].aggregate(pipeline_rating).to_list(length=1)
    average_rating = round((rating_result[0]["avg_rating"] or 0) if rating_result else 0, 2)

    # Assignment stats
    assignments = await db["review_assignments"].find(
        {"reviewer_user_id": reviewer_user_id}
    ).to_list(length=1000)

    total_invited = len(assignments)
    total_accepted = sum(1 for a in assignments if a.get("status") in ("accepted", "completed", "withdrawn"))
    total_completed = sum(1 for a in assignments if a.get("status") == "completed")
    total_declined = sum(1 for a in assignments if a.get("status") == "declined")

    acceptance_rate = round(total_accepted / max(total_invited, 1), 4)
    response_rate = round((total_accepted + total_declined) / max(total_invited, 1), 4)

    # On-time rate: completed on time / total completed
    on_time_count = 0
    completed_assignments = [a for a in assignments if a.get("status") == "completed"]
    for assignment in completed_assignments:
        due_date = assignment.get("due_date")
        completed_at = assignment.get("completed_at")
        if due_date and completed_at:
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date)
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at)
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            if completed_at <= due_date:
                on_time_count += 1
        else:
            on_time_count += 1

    on_time_rate = round(on_time_count / max(total_completed, 1), 4)

    now = datetime.now(timezone.utc)
    stats = {
        "reviews_completed": total_completed,
        "average_rating": average_rating,
        "acceptance_rate": acceptance_rate,
        "response_rate": response_rate,
        "on_time_rate": on_time_rate,
        "updated_at": now,
    }

    await db["reviewer_profiles"].update_one(
        {"user_id": reviewer_user_id},
        {"$set": stats},
    )

    new_score = await compute_reviewer_score(reviewer_user_id, db)
    stats["reviewer_score"] = new_score

    return stats
