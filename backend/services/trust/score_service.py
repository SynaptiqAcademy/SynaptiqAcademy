"""
Trust Score Service — computes a 0-100 Academic Trust Score.

Each factor produces an independent 0-100 sub-score.
Final score = weighted average across 14 factors.
Every factor includes an explanation so users understand exactly
why they have a certain score.

Collections read (read-only):
  users, publications, reviews, grant_applications, collaborations,
  projects, reputation_events, verification_profiles (existing)

Collections written:
  trust_scores (cache + history)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId

log = logging.getLogger("synaptiq.trust.score")

# ─── Factor weights (must sum to 100) ────────────────────────────────────────
WEIGHTS: dict[str, float] = {
    "identity":          15.0,
    "institution":       15.0,
    "publications":      12.0,
    "orcid":             10.0,
    "research_activity":  8.0,
    "review_activity":    7.0,
    "grants":             7.0,
    "citations":          6.0,
    "profile":            5.0,
    "reputation":         4.0,
    "collaborations":     4.0,
    "account_age":        3.0,
    "metadata_consistency": 2.0,
    "academic_integrity": 2.0,
}

# ─── Trust level bands ────────────────────────────────────────────────────────
LEVELS = [
    (0,  20,  "Unverified",     "Begin by verifying your email and linking your ORCID."),
    (21, 40,  "Basic",          "Add institutional affiliation and verify your first publication."),
    (41, 60,  "Established",    "Verified researcher with growing academic footprint."),
    (61, 80,  "Trusted",        "Well-established verified academic identity."),
    (81, 100, "Distinguished",  "Elite verification level — recognised across institutions."),
]


def _get_level(score: float) -> dict:
    for lo, hi, label, advice in LEVELS:
        if lo <= score <= hi:
            return {"label": label, "advice": advice, "min": lo, "max": hi}
    return {"label": "Distinguished", "advice": "", "min": 81, "max": 100}


def _pct(value: float, cap: float) -> float:
    """Return 0-100 as (value/cap)*100, clamped."""
    if cap <= 0:
        return 0.0
    return min(100.0, (value / cap) * 100.0)


async def compute_trust_score(user_id: str, db) -> dict:
    """
    Compute a full trust score breakdown for a user.
    Returns the breakdown + cached result written to trust_scores collection.
    """
    try:
        uid_obj = ObjectId(user_id)
    except Exception:
        uid_obj = None

    # ── Gather source data in parallel ───────────────────────────────────────
    user_q = db.users.find_one({"_id": uid_obj} if uid_obj else {"_id": user_id})
    vp_q   = db.verification_profiles.find_one({"user_id": user_id})
    tv_q   = db.trust_verifications.count_documents({"user_id": user_id, "status": "verified"})
    pub_q  = db.publications.count_documents({"owner_id": user_id})
    rev_q  = db.reviews.count_documents({"reviewer_id": user_id})
    grant_q = db.grant_applications.count_documents({"applicant_id": user_id})
    collab_q = db.collaborations.count_documents({"$or": [
        {"creator_id": user_id}, {"participants": user_id}
    ]})
    proj_q = db.projects.count_documents({"$or": [
        {"owner_id": user_id}, {"members": user_id}
    ]})
    rep_q = db.reputation_events.count_documents({"user_id": user_id})

    (user, vp, verified_count, pub_count, rev_count,
     grant_count, collab_count, proj_count, rep_count) = await asyncio.gather(
        user_q, vp_q, tv_q, pub_q, rev_q, grant_q, collab_q, proj_q, rep_q
    )

    now = datetime.now(timezone.utc)
    factors: dict[str, dict] = {}

    # ── 1. Identity (15) ─────────────────────────────────────────────────────
    id_score = 0.0
    id_reasons = []
    if user and user.get("email_verified"):
        id_score += 40; id_reasons.append("Email verified (+40)")
    if vp and vp.get("orcid_verified"):
        id_score += 35; id_reasons.append("ORCID verified (+35)")
    if vp and vp.get("identity_verified"):
        id_score += 25; id_reasons.append("Identity document verified (+25)")
    id_score = min(100.0, id_score)
    factors["identity"] = {
        "score": id_score, "weight": WEIGHTS["identity"],
        "label": "Identity Verification",
        "reasons": id_reasons or ["No identity verification on file."],
        "recommendation": None if id_score >= 75 else "Submit government-issued ID for full identity verification.",
    }

    # ── 2. Institution (15) ───────────────────────────────────────────────────
    inst_score = 0.0
    inst_reasons = []
    if vp and vp.get("institution_verified"):
        inst_score = 80.0; inst_reasons.append("Institutional affiliation verified (+80)")
    if user and user.get("institution"):
        inst_score = min(100.0, inst_score + 20.0); inst_reasons.append("Institution on profile (+20)")
    factors["institution"] = {
        "score": inst_score, "weight": WEIGHTS["institution"],
        "label": "Institution Verification",
        "reasons": inst_reasons or ["No institution on file."],
        "recommendation": None if inst_score >= 80 else "Request institutional affiliation verification.",
    }

    # ── 3. Publications (12) ──────────────────────────────────────────────────
    pub_score = _pct(pub_count, 10)  # 10 publications = 100
    factors["publications"] = {
        "score": pub_score, "weight": WEIGHTS["publications"],
        "label": "Publication Verification",
        "value": pub_count,
        "reasons": [f"{pub_count} publication(s) on record."],
        "recommendation": None if pub_count >= 5 else "Add and verify your publications via DOI.",
    }

    # ── 4. ORCID (10) ─────────────────────────────────────────────────────────
    orcid_score = 0.0
    orcid_reasons = []
    if user and user.get("orcid"):
        orcid_score += 50; orcid_reasons.append("ORCID linked (+50)")
    if vp and vp.get("orcid_verified"):
        orcid_score += 50; orcid_reasons.append("ORCID record validated (+50)")
    factors["orcid"] = {
        "score": min(100.0, orcid_score), "weight": WEIGHTS["orcid"],
        "label": "ORCID Completeness",
        "reasons": orcid_reasons or ["No ORCID linked."],
        "recommendation": None if orcid_score >= 100 else "Link and validate your ORCID iD.",
    }

    # ── 5. Research Activity (8) ──────────────────────────────────────────────
    activity_score = min(100.0, _pct(proj_count + pub_count, 20))
    factors["research_activity"] = {
        "score": activity_score, "weight": WEIGHTS["research_activity"],
        "label": "Research Activity",
        "value": proj_count,
        "reasons": [f"{proj_count} project(s), {pub_count} publication(s)."],
        "recommendation": None if activity_score >= 50 else "Create research projects and publish papers.",
    }

    # ── 6. Review Activity (7) ────────────────────────────────────────────────
    review_score = _pct(rev_count, 10)
    factors["review_activity"] = {
        "score": review_score, "weight": WEIGHTS["review_activity"],
        "label": "Peer Review Activity",
        "value": rev_count,
        "reasons": [f"{rev_count} review(s) completed."],
        "recommendation": None if rev_count >= 5 else "Complete peer reviews to raise this score.",
    }

    # ── 7. Grant Participation (7) ────────────────────────────────────────────
    grant_score = _pct(grant_count, 5)
    factors["grants"] = {
        "score": grant_score, "weight": WEIGHTS["grants"],
        "label": "Grant Participation",
        "value": grant_count,
        "reasons": [f"{grant_count} grant application(s)."],
        "recommendation": None if grant_count >= 2 else "Apply for research grants to strengthen this factor.",
    }

    # ── 8. Citations (6) ──────────────────────────────────────────────────────
    citation_count = 0
    if user:
        om = user.get("openalex_metrics") or {}
        citation_count = om.get("citation_count", 0) or 0
    cit_score = _pct(citation_count, 100)
    factors["citations"] = {
        "score": cit_score, "weight": WEIGHTS["citations"],
        "label": "Citation History",
        "value": citation_count,
        "reasons": [f"{citation_count} citation(s) tracked via OpenAlex."],
        "recommendation": None if citation_count >= 20 else "Publish high-quality research to accumulate citations.",
    }

    # ── 9. Profile Completeness (5) ───────────────────────────────────────────
    profile_fields = ["full_name", "institution", "bio", "country", "department", "position",
                      "research_interests", "expertise", "orcid"]
    completed = sum(1 for f in profile_fields if user and user.get(f)) if user else 0
    profile_score = _pct(completed, len(profile_fields))
    factors["profile"] = {
        "score": profile_score, "weight": WEIGHTS["profile"],
        "label": "Profile Completeness",
        "value": f"{completed}/{len(profile_fields)}",
        "reasons": [f"{completed} of {len(profile_fields)} profile fields completed."],
        "recommendation": None if profile_score >= 80 else "Complete your academic profile.",
    }

    # ── 10. Reputation (4) ───────────────────────────────────────────────────
    rep_score_raw = 0.0
    if user:
        rep_score_raw = float(user.get("reputation_score") or 0)
    rep_score = _pct(rep_score_raw, 500)
    factors["reputation"] = {
        "score": rep_score, "weight": WEIGHTS["reputation"],
        "label": "Community Reputation",
        "value": int(rep_score_raw),
        "reasons": [f"Reputation score: {int(rep_score_raw)}."],
        "recommendation": None if rep_score >= 50 else "Engage in collaborations and peer reviews.",
    }

    # ── 11. Collaborations (4) ───────────────────────────────────────────────
    collab_score = _pct(collab_count, 10)
    factors["collaborations"] = {
        "score": collab_score, "weight": WEIGHTS["collaborations"],
        "label": "Verified Collaborations",
        "value": collab_count,
        "reasons": [f"{collab_count} collaboration(s) on record."],
        "recommendation": None if collab_count >= 5 else "Build verified research collaborations.",
    }

    # ── 12. Account Age (3) ──────────────────────────────────────────────────
    age_months = 0
    if user and user.get("created_at"):
        created = user["created_at"]
        if isinstance(created, datetime):
            delta = now - created.replace(tzinfo=timezone.utc) if created.tzinfo is None else now - created
            age_months = delta.days // 30
    age_score = _pct(age_months, 24)  # 24 months = 100
    factors["account_age"] = {
        "score": age_score, "weight": WEIGHTS["account_age"],
        "label": "Account Age",
        "value": f"{age_months} months",
        "reasons": [f"Account is {age_months} month(s) old."],
        "recommendation": None,
    }

    # ── 13. Metadata Consistency (2) ─────────────────────────────────────────
    meta_score = 60.0  # default — can be enhanced with cross-platform checks
    if user and user.get("orcid") and user.get("institution"):
        meta_score = 80.0
    if vp and vp.get("orcid_verified") and vp.get("institution_verified"):
        meta_score = 100.0
    factors["metadata_consistency"] = {
        "score": meta_score, "weight": WEIGHTS["metadata_consistency"],
        "label": "Metadata Consistency",
        "reasons": ["Cross-platform identity consistency check."],
        "recommendation": None if meta_score >= 80 else "Ensure ORCID and institutional data match.",
    }

    # ── 14. Academic Integrity (2) ────────────────────────────────────────────
    fraud_flag_count = await db.trust_audit.count_documents({
        "user_id": user_id, "event": "fraud_flag"
    })
    integrity_score = max(0.0, 100.0 - fraud_flag_count * 25)
    factors["academic_integrity"] = {
        "score": integrity_score, "weight": WEIGHTS["academic_integrity"],
        "label": "Academic Integrity",
        "reasons": [f"{fraud_flag_count} integrity flag(s) on record."] if fraud_flag_count else ["No integrity issues detected."],
        "recommendation": None if fraud_flag_count == 0 else "Contact support to resolve integrity flags.",
    }

    # ── Weighted final score ──────────────────────────────────────────────────
    final_score = sum(
        factors[k]["score"] * (WEIGHTS[k] / 100.0)
        for k in factors
    )
    final_score = round(min(100.0, max(0.0, final_score)), 1)
    level_info = _get_level(final_score)

    result = {
        "user_id":     user_id,
        "score":       final_score,
        "level":       level_info["label"],
        "level_advice":level_info["advice"],
        "factors":     factors,
        "computed_at": now.isoformat(),
        "next_update": (now + timedelta(hours=24)).isoformat(),
    }

    # Cache in DB (upsert)
    await db.trust_scores.update_one(
        {"user_id": user_id},
        {"$set": {**result, "updated_at": now}},
        upsert=True,
    )

    return result


async def get_cached_trust_score(user_id: str, db) -> dict | None:
    """Return cached score if fresher than 24 hours, else None."""
    doc = await db.trust_scores.find_one({"user_id": user_id})
    if not doc:
        return None
    updated = doc.get("updated_at")
    if not isinstance(updated, datetime):
        return None
    age = datetime.now(timezone.utc) - updated.replace(tzinfo=timezone.utc)
    if age > timedelta(hours=24):
        return None
    doc.pop("_id", None)
    return doc
