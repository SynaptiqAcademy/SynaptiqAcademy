"""
Rule-based risk detection engine. 12 patterns. No definitive accusations —
every flag is a potential concern with a confidence level and recommended action.
"""
from datetime import datetime, timezone


_RISK_LEVELS = ("low", "medium", "high", "critical")


def _flag(key: str, level: str, title: str, description: str,
          confidence: int, action: str, data: dict | None = None) -> dict:
    return {
        "key": key, "level": level, "title": title,
        "description": description, "confidence": confidence,
        "action": action, "data": data or {},
        "flagged_at": datetime.now(timezone.utc).isoformat(),
    }


async def detect_risks(
    user_id: str,
    db,
    identity_result: dict,
    publication_result: dict,
    citation_result: dict,
    grant_result: dict,
) -> list[dict]:
    flags: list[dict] = []

    # ── Pattern 1: Retracted publications ─────────────────────────────────────
    retracted = publication_result.get("retracted_count", 0)
    if retracted > 0:
        flags.append(_flag(
            "retracted_publications", "critical",
            "Retracted Publication Detected",
            f"{retracted} publication(s) flagged as retracted in OpenAlex.",
            90,
            "Review retracted works and update publication list accordingly.",
            {"count": retracted},
        ))

    # ── Pattern 2: Duplicate DOIs ─────────────────────────────────────────────
    dup_dois = publication_result.get("duplicate_dois", [])
    if dup_dois:
        flags.append(_flag(
            "duplicate_dois", "high",
            "Duplicate DOIs in Publication List",
            f"{len(dup_dois)} DOI(s) appear more than once in the publication record.",
            85,
            "Remove duplicate publication entries.",
            {"dois": dup_dois[:5]},
        ))

    # ── Pattern 3: High self-citation ratio ───────────────────────────────────
    self_ratio = citation_result.get("self_citation_ratio", 0.0)
    if self_ratio > 0.4:
        level = "critical" if self_ratio > 0.6 else "high"
        flags.append(_flag(
            "high_self_citation", level,
            "Elevated Self-Citation Ratio",
            f"Self-citation indicators at {self_ratio:.0%}, which may inflate impact metrics.",
            int(self_ratio * 100),
            "Review citing works to confirm citations are from independent sources.",
            {"ratio": round(self_ratio, 3)},
        ))

    # ── Pattern 4: ORCID absent or invalid ───────────────────────────────────
    orcid_check = next((c for c in identity_result.get("checks", [])
                        if c["check"] in ("orcid_valid", "orcid_present")), None)
    if orcid_check and not orcid_check.get("passed"):
        flags.append(_flag(
            "missing_orcid", "medium",
            "ORCID Not Verified",
            "No verified ORCID iD — identity cannot be cross-checked with the global researcher registry.",
            70,
            "Register at orcid.org and add your ORCID to your Synaptiq profile.",
        ))

    # ── Pattern 5: Institution not in ROR ────────────────────────────────────
    ror_check = next((c for c in identity_result.get("checks", [])
                      if c["check"] == "institution_in_ror"), None)
    if ror_check and not ror_check.get("passed"):
        flags.append(_flag(
            "institution_not_in_ror", "low",
            "Institution Not Found in ROR",
            "The declared institution could not be matched in the Research Organization Registry.",
            55,
            "Verify institution name spelling or update to the official ROR name.",
        ))

    # ── Pattern 6: Email domain not academic ─────────────────────────────────
    email_check = next((c for c in identity_result.get("checks", [])
                        if c["check"] == "academic_email_domain"), None)
    if email_check and not email_check.get("passed"):
        flags.append(_flag(
            "non_academic_email", "low",
            "Non-Academic Email Domain",
            "The registered email does not use a recognized academic domain (.edu, .ac.uk, etc.).",
            50,
            "Consider adding your institutional email address to your profile.",
            {"domain": email_check.get("data", {}).get("domain")},
        ))

    # ── Pattern 7: Majority publications unverifiable ─────────────────────────
    pub_total = publication_result.get("total", 0)
    pub_failed = publication_result.get("failed", 0) + publication_result.get("no_doi", 0)
    if pub_total > 2 and pub_failed / pub_total > 0.6:
        flags.append(_flag(
            "publications_unverifiable", "medium",
            "Most Publications Cannot Be Externally Verified",
            f"{pub_failed}/{pub_total} publications lack DOIs or could not be found in external databases.",
            65,
            "Add DOIs to publications so they can be verified in Crossref and OpenAlex.",
            {"unverifiable": pub_failed, "total": pub_total},
        ))

    # ── Pattern 8: DOI resolution failures ───────────────────────────────────
    doi_failures = sum(
        1 for c in publication_result.get("checks", [])
        if c.get("status") == "failed"
    )
    if doi_failures >= 2:
        flags.append(_flag(
            "doi_resolution_failures", "medium",
            "Multiple DOI Resolution Failures",
            f"{doi_failures} publication DOI(s) could not be resolved — these may be invalid.",
            70,
            "Verify DOI accuracy for failed publications.",
            {"count": doi_failures},
        ))

    # ── Pattern 9: Name mismatch with ORCID ──────────────────────────────────
    name_check = next((c for c in identity_result.get("checks", [])
                       if c["check"] == "name_matches_orcid"), None)
    if name_check and not name_check.get("passed"):
        flags.append(_flag(
            "name_mismatch_orcid", "medium",
            "Name Does Not Match ORCID Record",
            "The profile name differs significantly from the name registered in ORCID.",
            75,
            "Ensure your full name in Synaptiq matches your ORCID profile exactly.",
            name_check.get("data", {}),
        ))

    # ── Pattern 10: Institution mismatch with ORCID ──────────────────────────
    inst_orcid_check = next((c for c in identity_result.get("checks", [])
                             if c["check"] == "institution_matches_orcid"), None)
    if inst_orcid_check and not inst_orcid_check.get("passed"):
        flags.append(_flag(
            "institution_mismatch_orcid", "low",
            "Institution May Not Match ORCID Affiliation",
            "The declared institution differs from the most recent ORCID employment record.",
            55,
            "Update your institution in Synaptiq or in ORCID to ensure consistency.",
            inst_orcid_check.get("data", {}),
        ))

    # ── Pattern 11: Low profile completeness ─────────────────────────────────
    profile_check = next((c for c in identity_result.get("checks", [])
                          if c["check"] == "profile_completeness"), None)
    if profile_check:
        ratio = profile_check.get("data", {}).get("ratio", 1.0)
        if ratio < 0.4:
            flags.append(_flag(
                "low_profile_completeness", "low",
                "Profile Significantly Incomplete",
                "Key academic fields (department, position, research interests) are missing.",
                60,
                "Complete your researcher profile to improve credibility and discoverability.",
                profile_check.get("data", {}),
            ))

    # ── Pattern 12: Grants with unrecognized funders ──────────────────────────
    if grant_result.get("total", 0) > 0:
        unrecognized = grant_result.get("total", 0) - grant_result.get("funder_recognized", 0)
        if unrecognized / max(grant_result["total"], 1) > 0.7:
            flags.append(_flag(
                "grants_unrecognized_funders", "low",
                "Most Grant Funders Not in Recognized Registry",
                "The majority of recorded funders could not be matched to the known funder list.",
                50,
                "Add official funder names to grant records for improved verification.",
                {"unrecognized": unrecognized, "total": grant_result["total"]},
            ))

    return flags
