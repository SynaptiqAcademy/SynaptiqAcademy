"""
AI-Assisted Verification Engine

Supports 22 verification types with multi-source validation.

Provider architecture:
  - PublicORCIDProvider      — ORCID public API (no auth)
  - CrossrefProvider         — CrossRef public API (no auth)
  - OpenAlexProvider         — OpenAlex public API (no auth)
  - RuleBasedProvider        — internal rule checks
  - AdminProvider            — manual admin overrides

All external calls have timeouts and graceful fallbacks.
No commercial API keys required for the base layer.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

log = logging.getLogger("synaptiq.trust.engine")

# ─── Verification type catalogue ─────────────────────────────────────────────
VERIFICATION_TYPES = {
    "researcher_identity":          {"label": "Researcher Identity",        "expiry_days": 365, "max_confidence": 90},
    "institution_affiliation":      {"label": "Institution Affiliation",     "expiry_days": 365, "max_confidence": 95},
    "department":                   {"label": "Department",                  "expiry_days": 365, "max_confidence": 85},
    "academic_position":            {"label": "Academic Position",           "expiry_days": 730, "max_confidence": 90},
    "orcid":                        {"label": "ORCID",                       "expiry_days": 730, "max_confidence": 99},
    "email_domain":                 {"label": "Email Domain",                "expiry_days": 365, "max_confidence": 95},
    "publication":                  {"label": "Publication",                 "expiry_days": 1825,"max_confidence": 98},
    "doi":                          {"label": "DOI Validation",             "expiry_days": 1825,"max_confidence": 99},
    "crossref_metadata":            {"label": "Crossref Metadata",          "expiry_days": 365, "max_confidence": 96},
    "openalex_metadata":            {"label": "OpenAlex Metadata",          "expiry_days": 365, "max_confidence": 95},
    "reviewer_activity":            {"label": "Reviewer Activity",           "expiry_days": 365, "max_confidence": 88},
    "editorial_board_membership":   {"label": "Editorial Board Membership",  "expiry_days": 365, "max_confidence": 85},
    "grant_participation":          {"label": "Grant Participation",         "expiry_days": 365, "max_confidence": 90},
    "research_project":             {"label": "Research Project",            "expiry_days": 365, "max_confidence": 85},
    "conference_speaker":           {"label": "Conference Speaker",          "expiry_days": 1825,"max_confidence": 88},
    "teaching_experience":          {"label": "Teaching Experience",         "expiry_days": 365, "max_confidence": 85},
    "professional_certifications":  {"label": "Professional Certifications", "expiry_days": 730, "max_confidence": 90},
    "research_awards":              {"label": "Research Awards",             "expiry_days": 1825,"max_confidence": 85},
    "patent_ownership":             {"label": "Patent Ownership",            "expiry_days": 3650,"max_confidence": 98},
    "laboratory_membership":        {"label": "Laboratory Membership",       "expiry_days": 365, "max_confidence": 85},
    "research_group_membership":    {"label": "Research Group Membership",   "expiry_days": 365, "max_confidence": 85},
    "academic_society_membership":  {"label": "Academic Society Membership", "expiry_days": 730, "max_confidence": 88},
}

_ORCID_RE   = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
_DOI_RE     = re.compile(r"^10\.\d{4,9}/\S+$")
_TIMEOUT    = httpx.Timeout(8.0)


async def _fetch_orcid_public(orcid: str) -> dict:
    """Fetch public ORCID record (no auth needed for public profiles)."""
    url = f"https://pub.orcid.org/v3.0/{orcid}/record"
    headers = {"Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return {"ok": True, "data": r.json()}
            return {"ok": False, "status": r.status_code}
    except Exception as exc:
        log.debug("ORCID fetch failed: %s", exc)
        return {"ok": False, "error": str(exc)}


async def _fetch_crossref(doi: str) -> dict:
    """Fetch DOI metadata from CrossRef (no auth needed)."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": "Synaptiq/1.0 (https://synaptiq.app; mailto:support@synaptiq.app)"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return {"ok": True, "data": r.json()}
            return {"ok": False, "status": r.status_code}
    except Exception as exc:
        log.debug("CrossRef fetch failed: %s", exc)
        return {"ok": False, "error": str(exc)}


async def _fetch_openalex_doi(doi: str) -> dict:
    """Fetch work metadata from OpenAlex (no auth needed)."""
    url = f"https://api.openalex.org/works/doi:{doi}"
    headers = {"User-Agent": "Synaptiq/1.0"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return {"ok": True, "data": r.json()}
            return {"ok": False, "status": r.status_code}
    except Exception as exc:
        log.debug("OpenAlex fetch failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ─── Per-type validation logic ────────────────────────────────────────────────

async def validate_orcid(user_id: str, orcid: str, user: dict, db) -> dict:
    if not orcid or not _ORCID_RE.match(orcid.strip()):
        return _result(0, "invalid_format", "ORCID format is invalid (expected XXXX-XXXX-XXXX-XXXX).")

    resp = await _fetch_orcid_public(orcid.strip())
    if resp["ok"]:
        data = resp["data"]
        # Verify the name loosely matches
        given  = ((data.get("person") or {}).get("name") or {}).get("given-names", {}).get("value", "")
        family = ((data.get("person") or {}).get("name") or {}).get("family-name", {}).get("value", "")
        remote_name = f"{given} {family}".strip().lower()
        local_name  = (user.get("full_name") or "").lower()

        name_match = any(part in remote_name for part in local_name.split() if len(part) > 2) if local_name else True
        confidence = 95 if name_match else 75
        notes = f"ORCID public record found. Name match: {'yes' if name_match else 'partial'}."
        return _result(confidence, "orcid_public_api", notes, extra={"orcid": orcid, "remote_name": f"{given} {family}"})
    else:
        return _result(0, "orcid_not_found", f"ORCID record not found or private (status {resp.get('status', 'unknown')}).")


async def validate_doi(user_id: str, doi: str, user: dict, db) -> dict:
    if not doi or not _DOI_RE.match(doi.strip()):
        return _result(0, "invalid_format", "DOI format is invalid (expected 10.xxxx/...).")

    doi_clean = doi.strip()
    crossref, openalex = await asyncio.gather(
        _fetch_crossref(doi_clean),
        _fetch_openalex_doi(doi_clean),
    )

    sources_hit = []
    if crossref["ok"]:
        sources_hit.append("crossref")
    if openalex["ok"]:
        sources_hit.append("openalex")

    if not sources_hit:
        return _result(0, "doi_not_found", "DOI not found in CrossRef or OpenAlex.")

    # Check author match
    confidence = 80
    title = ""
    if crossref["ok"]:
        work = (crossref["data"].get("message") or {})
        title = (work.get("title") or [""])[0]
        authors = work.get("author") or []
        local_family = (user.get("full_name") or "").split()[-1].lower() if user.get("full_name") else ""
        if local_family and any(local_family in (a.get("family") or "").lower() for a in authors):
            confidence = 95
            sources_hit.append("author_match")

    notes = f"DOI verified via {', '.join(sources_hit)}. Title: {title[:120]}."
    return _result(confidence, "+".join(sources_hit[:2] or ["api"]), notes, extra={"doi": doi_clean, "title": title})


async def validate_email_domain(user_id: str, email: str, user: dict, db) -> dict:
    """Verify institutional email domain against known academic TLDs."""
    if not email or "@" not in email:
        return _result(0, "invalid_format", "Invalid email.")
    domain = email.split("@", 1)[1].lower()
    academic_tlds = (".edu", ".ac.uk", ".ac.", ".edu.", "university", "college", "research", "institute")
    is_academic = any(domain.endswith(tld) or tld in domain for tld in academic_tlds)
    if is_academic:
        return _result(85, "domain_check", f"Email domain '{domain}' matches known academic pattern.")
    return _result(40, "domain_check", f"Email domain '{domain}' not recognised as institutional.")


async def validate_from_db_count(
    user_id: str, db, *, collection: str, field: str, min_count: int = 1,
    source: str = "platform_data", label: str = ""
) -> dict:
    """Generic validator: check that a user has ≥ min_count records in a collection."""
    count = await db[collection].count_documents({field: user_id})
    if count >= min_count:
        confidence = min(95, 60 + count * 5)
        return _result(confidence, source, f"{count} {label or collection} record(s) found on platform.")
    return _result(0, source, f"No {label or collection} records found. Platform data required.")


# ─── Dispatch table ───────────────────────────────────────────────────────────

async def run_ai_validation(v_type: str, user_id: str, payload: dict, db) -> dict:
    """
    Run AI/automated validation for a given verification type.
    Returns {confidence, source, notes, extra}.
    """
    user = await db.users.find_one({"_id": _safe_oid(user_id)}) or {}

    if v_type == "orcid":
        return await validate_orcid(user_id, payload.get("orcid", user.get("orcid", "")), user, db)
    if v_type in ("doi", "publication"):
        return await validate_doi(user_id, payload.get("doi", ""), user, db)
    if v_type == "email_domain":
        return await validate_email_domain(user_id, user.get("email", ""), user, db)
    if v_type == "crossref_metadata":
        doi = payload.get("doi", "")
        if doi:
            resp = await _fetch_crossref(doi)
            if resp["ok"]:
                return _result(90, "crossref", "CrossRef metadata validated.")
        return _result(0, "crossref", "DOI required for CrossRef metadata validation.")
    if v_type == "openalex_metadata":
        doi = payload.get("doi", "")
        if doi:
            resp = await _fetch_openalex_doi(doi)
            if resp["ok"]:
                return _result(88, "openalex", "OpenAlex metadata validated.")
        return _result(0, "openalex", "DOI required for OpenAlex metadata validation.")
    if v_type == "reviewer_activity":
        return await validate_from_db_count(
            user_id, db, collection="reviews", field="reviewer_id",
            min_count=3, source="platform_data", label="reviews"
        )
    if v_type == "grant_participation":
        return await validate_from_db_count(
            user_id, db, collection="grant_applications", field="applicant_id",
            min_count=1, source="platform_data", label="grant applications"
        )
    if v_type == "research_project":
        return await validate_from_db_count(
            user_id, db, collection="projects", field="owner_id",
            min_count=1, source="platform_data", label="projects"
        )
    if v_type == "teaching_experience":
        return await validate_from_db_count(
            user_id, db, collection="teaching_lessons", field="creator_id",
            min_count=1, source="platform_data", label="lessons"
        )
    if v_type in ("researcher_identity", "institution_affiliation", "department",
                  "academic_position", "editorial_board_membership",
                  "conference_speaker", "professional_certifications",
                  "research_awards", "patent_ownership", "laboratory_membership",
                  "research_group_membership", "academic_society_membership"):
        return _result(
            0, "manual_required",
            "This verification type requires document upload and manual admin review.",
        )

    return _result(0, "unknown_type", f"Unknown verification type: {v_type}.")


def _result(confidence: int, source: str, notes: str, extra: dict | None = None) -> dict:
    return {
        "confidence": confidence,
        "source":     source,
        "notes":      notes,
        "extra":      extra or {},
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


def _safe_oid(s: str):
    from bson import ObjectId
    try:
        return ObjectId(s)
    except Exception:
        return s
