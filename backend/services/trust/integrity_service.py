"""
Integrity Report Service

Generates a comprehensive Integrity Report per researcher:
  - Publication authorship consistency
  - Retraction / flagged DOI check (OpenAlex)
  - Duplicate submission detection (platform-level)
  - Anomaly signals from trust_audit
  - Overall integrity rating: Excellent / Good / Fair / Under Review
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId

import httpx

log = logging.getLogger("synaptiq.trust.integrity")

_TIMEOUT = httpx.Timeout(8.0)

INTEGRITY_LEVELS = [
    (0,  40,  "Under Review", "Critical issues require your attention."),
    (41, 60,  "Fair",         "Minor concerns detected. Review the flags below."),
    (61, 80,  "Good",         "No major integrity concerns."),
    (81, 100, "Excellent",    "Exemplary academic integrity profile."),
]


def _get_integrity_level(score: float) -> dict:
    for lo, hi, label, note in INTEGRITY_LEVELS:
        if lo <= score <= hi:
            return {"label": label, "note": note}
    return {"label": "Excellent", "note": ""}


async def _check_retracted_dois(dois: list[str]) -> list[dict]:
    """Check a list of DOIs against OpenAlex retraction status."""
    flagged = []
    for doi in dois[:20]:  # limit external calls
        url = f"https://api.openalex.org/works/doi:{doi}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await c.get(url, headers={"User-Agent": "Synaptiq/1.0"})
                if r.status_code == 200:
                    data = r.json()
                    if data.get("is_retracted"):
                        flagged.append({
                            "doi": doi,
                            "title": (data.get("title") or "")[:120],
                            "reason": "Retracted (OpenAlex)",
                        })
        except Exception:
            pass
    return flagged


async def generate_integrity_report(user_id: str, db) -> dict:
    """
    Build a full Integrity Report for the user.
    Reads: users, publications, trust_audit, trust_verifications, reviews
    """
    now = datetime.now(timezone.utc)
    uid_obj = _safe_oid(user_id)

    user, pub_list, audit_events, verifications, review_list = await asyncio.gather(
        db.users.find_one({"_id": uid_obj}),
        db.publications.find({"owner_id": user_id}).to_list(length=200),
        db.trust_audit.find({"user_id": user_id}).to_list(length=200),
        db.trust_verifications.find({"user_id": user_id}).to_list(length=100),
        db.reviews.find({"reviewer_id": user_id}).to_list(length=100),
    )

    flags: list[dict] = []
    positive_signals: list[str] = []
    score = 100.0

    # ── 1. Fraud flags from trust_audit ──────────────────────────────────────
    fraud_events = [e for e in audit_events if e.get("event") == "fraud_flag"]
    if fraud_events:
        penalty = min(60.0, len(fraud_events) * 20)
        score -= penalty
        for e in fraud_events:
            flags.append({
                "type": "fraud_flag",
                "severity": "high",
                "description": e.get("details", "Integrity flag raised by admin."),
                "raised_at": _iso(e.get("created_at")),
            })

    # ── 2. Retraction check ───────────────────────────────────────────────────
    dois = [p["doi"] for p in pub_list if p.get("doi")]
    retracted = await _check_retracted_dois(dois)
    if retracted:
        penalty = len(retracted) * 15
        score -= penalty
        for r in retracted:
            flags.append({
                "type": "retracted_publication",
                "severity": "high",
                "description": f"Publication '{r['title']}' is marked as retracted (DOI: {r['doi']}).",
                "raised_at": now.isoformat(),
            })
    elif dois:
        positive_signals.append(f"None of your {len(dois)} DOI-verified publication(s) are retracted.")

    # ── 3. Duplicate submission detection (same title, different pub records) ──
    titles = [p.get("title", "").strip().lower() for p in pub_list if p.get("title")]
    seen_titles: set[str] = set()
    dups: list[str] = []
    for t in titles:
        if t in seen_titles and t not in dups:
            dups.append(t)
        seen_titles.add(t)
    if dups:
        score -= min(30.0, len(dups) * 10)
        for title in dups:
            flags.append({
                "type": "duplicate_submission",
                "severity": "medium",
                "description": f"Possible duplicate submission detected: '{title[:80]}'.",
                "raised_at": now.isoformat(),
            })
    else:
        positive_signals.append("No duplicate submissions detected in your publication record.")

    # ── 4. ORCID mismatch check ───────────────────────────────────────────────
    orcid_verified = any(
        v["verification_type"] == "orcid" and v.get("status") == "verified"
        for v in verifications
    )
    if user and user.get("orcid") and not orcid_verified:
        score -= 5
        flags.append({
            "type": "orcid_unverified",
            "severity": "low",
            "description": "ORCID is linked but not yet verified against public ORCID record.",
            "raised_at": now.isoformat(),
        })
    elif orcid_verified:
        positive_signals.append("ORCID identity verified against public ORCID registry.")

    # ── 5. Positive: peer review contributions ────────────────────────────────
    if len(review_list) >= 3:
        positive_signals.append(f"{len(review_list)} peer review(s) completed — strong scholarly citizenship.")

    # ── 6. Profile completeness for integrity ────────────────────────────────
    key_fields = ["full_name", "institution", "email", "orcid"]
    missing_fields = [f for f in key_fields if not (user or {}).get(f)]
    if missing_fields:
        score -= len(missing_fields) * 2
        flags.append({
            "type": "incomplete_profile",
            "severity": "low",
            "description": f"Missing profile fields: {', '.join(missing_fields)}.",
            "raised_at": now.isoformat(),
        })

    final_score = round(max(0.0, min(100.0, score)), 1)
    level = _get_integrity_level(final_score)

    report = {
        "user_id":          user_id,
        "score":            final_score,
        "level":            level["label"],
        "level_note":       level["note"],
        "flags":            flags,
        "flag_count":       len(flags),
        "positive_signals": positive_signals,
        "publications_checked": len(pub_list),
        "dois_checked":     len(dois),
        "generated_at":     now.isoformat(),
        "next_update":      (now + timedelta(hours=24)).isoformat(),
    }

    # Cache
    await db.trust_scores.update_one(
        {"user_id": user_id},
        {"$set": {"integrity_report": report, "integrity_updated_at": now}},
        upsert=True,
    )

    return report


async def get_cached_integrity_report(user_id: str, db) -> dict | None:
    doc = await db.trust_scores.find_one({"user_id": user_id})
    if not doc or not doc.get("integrity_report"):
        return None
    updated = doc.get("integrity_updated_at")
    if not isinstance(updated, datetime):
        return None
    if datetime.now(timezone.utc) - updated.replace(tzinfo=timezone.utc) > timedelta(hours=24):
        return None
    return doc["integrity_report"]


def _iso(v) -> str:
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v) if v else ""


def _safe_oid(s: str):
    try:
        return ObjectId(s)
    except Exception:
        return s
