"""
Integrity Engine orchestrator — runs all analyzers in parallel, computes score,
persists result to `integrity_reports`, logs to `integrity_provider_logs`.
"""
import asyncio
from datetime import datetime, timezone
from bson import ObjectId

from services.integrity.identity_analyzer   import analyze_identity
from services.integrity.publication_analyzer import analyze_publications
from services.integrity.citation_analyzer    import analyze_citations
from services.integrity.grant_analyzer       import analyze_grants
from services.integrity.risk_detector        import detect_risks
from services.integrity.score_engine         import compute_integrity_score


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_integrity_analysis(user_id: str, db) -> dict:
    """
    Full integrity analysis. Called either inline or from BackgroundTasks.
    Returns the full report dict (also persisted to integrity_reports collection).
    """
    started_at = _now()

    # Mark job as in-progress
    await db.integrity_jobs.update_one(
        {"user_id": user_id},
        {"$set": {"status": "running", "started_at": started_at}},
        upsert=True,
    )

    try:
        # Run all domain analyzers in parallel
        identity_res, pub_res, cit_res, grant_res = await asyncio.gather(
            analyze_identity(user_id, db),
            analyze_publications(user_id, db),
            analyze_citations(user_id, db),
            analyze_grants(user_id, db),
        )

        # Supplementary data for score engine
        collab_count = await db.collaborations.count_documents({"user_id": user_id})
        pubs_all = await db.publications.find(
            {"user_id": user_id}, {"doi": 1}
        ).to_list(length=200)
        pub_total = len(pubs_all)
        pub_with_doi = sum(1 for p in pubs_all if p.get("doi"))

        # Verification level
        trust_record = await db.trust_profiles.find_one({"user_id": user_id})
        is_verified = bool(trust_record and trust_record.get("verification_level", 0) > 0)
        v_level = (trust_record or {}).get("verification_level", 0)

        # Risk flags
        risk_flags = await detect_risks(
            user_id, db, identity_res, pub_res, cit_res, grant_res
        )

        # Integrity score
        score_result = compute_integrity_score(
            identity_result=identity_res,
            publication_result=pub_res,
            citation_result=cit_res,
            grant_result=grant_res,
            collab_count=collab_count,
            pub_total=pub_total,
            pub_with_doi=pub_with_doi,
            is_verified=is_verified,
            verification_level=v_level,
        )

        completed_at = _now()
        report = {
            "user_id":        user_id,
            "status":         "complete",
            "generated_at":   completed_at,
            "started_at":     started_at,
            "integrity_score": score_result["overall_score"],
            "grade":           score_result["grade"],
            "score_factors":   score_result["factors"],
            "score_weights":   score_result["weights"],
            "score_contributions": score_result["weighted_contributions"],
            "identity":        identity_res,
            "publications":    pub_res,
            "citations":       cit_res,
            "grants":          grant_res,
            "risk_flags":      risk_flags,
            "risk_count":      len(risk_flags),
            "critical_risks":  sum(1 for r in risk_flags if r["level"] == "critical"),
            "high_risks":      sum(1 for r in risk_flags if r["level"] == "high"),
        }

        # Persist / overwrite report
        await db.integrity_reports.update_one(
            {"user_id": user_id},
            {"$set": report},
            upsert=True,
        )

        # Mark job complete
        await db.integrity_jobs.update_one(
            {"user_id": user_id},
            {"$set": {"status": "complete", "completed_at": completed_at,
                      "integrity_score": score_result["overall_score"]}},
        )

        return report

    except Exception as exc:
        err_msg = str(exc)
        await db.integrity_jobs.update_one(
            {"user_id": user_id},
            {"$set": {"status": "error", "error": err_msg, "completed_at": _now()}},
        )
        raise


async def get_report(user_id: str, db) -> dict | None:
    doc = await db.integrity_reports.find_one({"user_id": user_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return doc


async def get_job_status(user_id: str, db) -> dict:
    job = await db.integrity_jobs.find_one({"user_id": user_id})
    if not job:
        return {"user_id": user_id, "status": "not_started"}
    job.pop("_id", None)
    return job
