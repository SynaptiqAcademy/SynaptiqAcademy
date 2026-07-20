"""
10-factor weighted Integrity Score (0-100).
Weights must sum to 1.0.
"""

_WEIGHTS = {
    "identity":             0.15,
    "publications":         0.20,
    "citations":            0.10,
    "grants":               0.10,
    "collaboration":        0.08,
    "metadata":             0.12,
    "verification_coverage": 0.10,
    "profile_consistency":  0.08,
    "institution":          0.05,
    "activity":             0.02,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def compute_integrity_score(
    identity_result: dict,
    publication_result: dict,
    citation_result: dict,
    grant_result: dict,
    collab_count: int = 0,
    pub_total: int = 0,
    pub_with_doi: int = 0,
    is_verified: bool = False,
    verification_level: int = 0,
    activity_score: int = 50,
) -> dict:
    factors: dict[str, float] = {}

    # 1. Identity (15%)
    factors["identity"] = _clamp(identity_result.get("score", 0))

    # 2. Publications (20%)
    factors["publications"] = _clamp(publication_result.get("score", 50))

    # 3. Citations (10%)
    factors["citations"] = _clamp(citation_result.get("score", 50))

    # 4. Grants (10%)
    factors["grants"] = _clamp(grant_result.get("score", 50))

    # 5. Collaboration (8%) — simple proxy: 10+ collabs = 80, 5+ = 60, 1+ = 40
    if collab_count >= 10:
        factors["collaboration"] = 80.0
    elif collab_count >= 5:
        factors["collaboration"] = 60.0
    elif collab_count >= 1:
        factors["collaboration"] = 40.0
    else:
        factors["collaboration"] = 20.0

    # 6. Metadata completeness (12%) — DOI coverage of publications
    if pub_total > 0:
        doi_coverage = pub_with_doi / pub_total
        factors["metadata"] = _clamp(doi_coverage * 90 + 10)
    else:
        factors["metadata"] = 50.0

    # 7. Verification coverage (10%) — from trust/verification system
    if is_verified:
        factors["verification_coverage"] = _clamp(30 + verification_level * 10)
    else:
        factors["verification_coverage"] = 20.0

    # 8. Profile consistency (8%) — checks passed ratio in identity
    id_checks = identity_result.get("checks", [])
    if id_checks:
        passed = sum(1 for c in id_checks if c.get("passed"))
        factors["profile_consistency"] = _clamp(passed / len(id_checks) * 100)
    else:
        factors["profile_consistency"] = 30.0

    # 9. Institution (5%) — ROR check
    ror_check = next((c for c in id_checks if c["check"] == "institution_in_ror"), None)
    factors["institution"] = 80.0 if (ror_check and ror_check.get("passed")) else 20.0

    # 10. Activity (2%) — proxy from caller
    factors["activity"] = _clamp(float(activity_score))

    # Weighted sum
    total = sum(_WEIGHTS[k] * factors[k] for k in _WEIGHTS)
    final = round(_clamp(total), 1)

    # Grade
    if final >= 90:
        grade = "A+"
    elif final >= 80:
        grade = "A"
    elif final >= 70:
        grade = "B"
    elif final >= 60:
        grade = "C"
    elif final >= 50:
        grade = "D"
    else:
        grade = "F"

    return {
        "overall_score": final,
        "grade": grade,
        "factors": {k: round(v, 1) for k, v in factors.items()},
        "weights": _WEIGHTS,
        "weighted_contributions": {k: round(_WEIGHTS[k] * factors[k], 2) for k in _WEIGHTS},
    }
