"""General content quality and completeness validators."""
from __future__ import annotations

import re
from typing import Any


def validate_profile_completeness(profile: dict) -> dict[str, Any]:
    """Returns per-field completeness and an overall score (0–100)."""
    checks: list[tuple[str, str, int, bool]] = [
        ("avatar", "avatar_url", 10, bool(profile.get("avatar_url"))),
        ("biography", "bio", 10, bool(profile.get("bio") and len(profile.get("bio", "")) >= 50)),
        ("institution", "institution", 10, bool(profile.get("institution"))),
        ("keywords", "research_keywords", 10, bool(profile.get("research_keywords"))),
        ("methods", "research_methods", 5, bool(profile.get("research_methods"))),
        ("social_links", "social_links", 5, bool(profile.get("social_links"))),
        ("availability", "availability", 5, bool(profile.get("availability"))),
        ("orcid", "orcid_id", 15, bool(profile.get("orcid_id"))),
        ("publications", "publications_count", 15,
         (profile.get("publications_count") or 0) > 0 or bool(profile.get("openalex_id"))),
        ("employment", "employment", 10, bool(profile.get("employment"))),
        ("education", "education", 5, bool(profile.get("education"))),
    ]

    fields: dict[str, dict[str, Any]] = {}
    total_pts = 0
    earned_pts = 0
    missing: list[str] = []

    for name, field_key, pts, present in checks:
        fields[name] = {"field": field_key, "points": pts, "complete": present}
        total_pts += pts
        if present:
            earned_pts += pts
        else:
            missing.append(name)

    score = round(earned_pts / total_pts * 100, 1) if total_pts else 0.0
    return {
        "score": score,
        "earned_points": earned_pts,
        "total_points": total_pts,
        "fields": fields,
        "missing_fields": missing,
        "is_complete": len(missing) == 0,
    }


def validate_required_fields(data: dict, required_fields: list[str]) -> dict[str, Any]:
    """Check that all required fields are present and non-empty."""
    missing: list[str] = []
    present: list[str] = []
    for f in required_fields:
        val = data.get(f)
        if val is None or val == "" or val == [] or val == {}:
            missing.append(f)
        else:
            present.append(f)
    return {
        "valid": len(missing) == 0,
        "missing": missing,
        "present": present,
        "completeness": round(len(present) / len(required_fields) * 100, 1) if required_fields else 100.0,
    }


def detect_duplicates(items: list[dict], key: str) -> list[dict[str, Any]]:
    """Find duplicate items by a key field. Returns list of {value, indices}."""
    seen: dict[str, list[int]] = {}
    for i, item in enumerate(items):
        val = str(item.get(key, "")).strip().lower()
        if val:
            seen.setdefault(val, []).append(i)
    return [
        {"value": v, "indices": idxs, "count": len(idxs)}
        for v, idxs in seen.items()
        if len(idxs) > 1
    ]


def validate_text_length(
    text: str,
    field_name: str,
    min_chars: int = 0,
    max_chars: int = 10_000,
    min_words: int = 0,
) -> dict[str, Any]:
    chars = len(text)
    words = len(text.split())
    errors: list[str] = []
    if chars < min_chars:
        errors.append(f"{field_name} must be at least {min_chars} characters (got {chars}).")
    if chars > max_chars:
        errors.append(f"{field_name} must not exceed {max_chars} characters (got {chars}).")
    if words < min_words:
        errors.append(f"{field_name} must be at least {min_words} words (got {words}).")
    return {
        "valid": len(errors) == 0,
        "char_count": chars,
        "word_count": words,
        "errors": errors,
    }


def detect_plagiarism_indicators(text: str) -> dict[str, Any]:
    """Heuristic plagiarism indicators — NOT a plagiarism check tool."""
    indicators: list[str] = []

    # Inconsistent tense
    past = len(re.findall(r"\b(?:was|were|had|did|showed|found|investigated)\b", text, re.IGNORECASE))
    present = len(re.findall(r"\b(?:is|are|has|show|find|investigate)\b", text, re.IGNORECASE))
    if past > 3 and present > 3 and abs(past - present) < 2:
        indicators.append("Mixed verb tenses may indicate text from multiple sources.")

    # Very long sentences (sometimes copied from papers)
    long_sentences = [s for s in re.split(r"[.!?]", text) if len(s.split()) > 60]
    if long_sentences:
        indicators.append(f"{len(long_sentences)} sentence(s) are unusually long (>60 words).")

    # Inconsistent formatting/spacing
    if re.search(r"[^\x00-\x7F]", text):
        indicators.append("Non-ASCII characters detected; check for copy-paste formatting issues.")

    return {
        "indicators_count": len(indicators),
        "indicators": indicators,
        "note": "These are heuristic style indicators only, not plagiarism detection.",
    }


def validate_orcid_profile(profile: dict) -> dict[str, Any]:
    """Check ORCID-specific profile fields."""
    issues: list[str] = []
    recommendations: list[str] = []

    if not profile.get("orcid_id"):
        issues.append("ORCID iD is not connected.")
        recommendations.append("Connect your ORCID iD in Profile → Settings to verify your identity.")
    else:
        if not profile.get("openalex_id"):
            recommendations.append(
                "Import publications from ORCID/OpenAlex to populate your publication record."
            )
        if not profile.get("orcid_name"):
            recommendations.append("Ensure your name on ORCID matches your platform profile.")

    return {
        "orcid_connected": bool(profile.get("orcid_id")),
        "publications_imported": bool(profile.get("openalex_id")),
        "issues": issues,
        "recommendations": recommendations,
    }
