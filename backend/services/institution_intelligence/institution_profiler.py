"""Institution Intelligence Engine — Institution Profiler (Phase XV).

Builds a comprehensive InstitutionProfile from raw input data.
All scoring is deterministic and requires no external calls.
"""
from __future__ import annotations

import re
import uuid
from collections import defaultdict
from typing import Any

from .models import (
    DepartmentProfile, DepartmentStatus, InstitutionInput,
    InstitutionKPIs, InstitutionProfile, InstitutionType,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _safe_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if x]
    return []


def _infer_type(type_str: str) -> InstitutionType:
    t = type_str.lower()
    if "hospital" in t or "clinical" in t:
        return InstitutionType.HOSPITAL
    if "company" in t or "industry" in t or "corporate" in t:
        return InstitutionType.COMPANY
    if "government" in t or "ministry" in t:
        return InstitutionType.GOVERNMENT
    if "institute" in t or "research center" in t:
        return InstitutionType.RESEARCH_INSTITUTE
    if "ngo" in t or "foundation" in t:
        return InstitutionType.NGO
    return InstitutionType.UNIVERSITY


# ── Department builder ────────────────────────────────────────────────────────

def _build_department(
    name: str,
    researchers: list[dict],
    grants: list[dict],
) -> DepartmentProfile:
    dept_researchers = [
        r for r in researchers
        if (r.get("department") or "").lower() == name.lower()
    ]
    dept_grants = [
        g for g in grants
        if (g.get("department") or "").lower() == name.lower()
    ]

    n = len(dept_researchers)
    pub_count  = sum(_safe_int(r.get("publication_count", 0)) for r in dept_researchers)
    cite_count = sum(_safe_int(r.get("citation_count", 0)) for r in dept_researchers)
    h_values   = [_safe_float(r.get("h_index", 0)) for r in dept_researchers]
    avg_h      = sum(h_values) / max(len(h_values), 1)
    intl_vals  = [_safe_float(r.get("international_collab_ratio", 0)) for r in dept_researchers]
    avg_intl   = sum(intl_vals) / max(len(intl_vals), 1)
    grant_count = len(dept_grants)
    grant_income = sum(_safe_float(g.get("amount", 0)) for g in dept_grants)

    # Determine status from KPIs
    pub_per_researcher = pub_count / max(n, 1)
    if pub_per_researcher > 4 and avg_h > 8:
        status = DepartmentStatus.HIGH_PERFORMING
    elif pub_per_researcher < 1 and avg_h < 2:
        status = DepartmentStatus.UNDERPERFORMING
    elif pub_per_researcher > 3:
        status = DepartmentStatus.PERFORMING
    else:
        status = DepartmentStatus.STABLE

    # Research domains
    domains: list[str] = []
    for r in dept_researchers:
        domains.extend(_safe_list(r.get("research_areas") or r.get("domains") or []))
    unique_domains = sorted(set(domains))[:5]

    # Top researchers by h-index
    sorted_r = sorted(dept_researchers, key=lambda r: -_safe_float(r.get("h_index", 0)))
    top = [r.get("full_name") or r.get("name") or str(r.get("_id", ""))
           for r in sorted_r[:3] if r]

    strengths: list[str] = []
    weaknesses: list[str] = []
    if avg_intl > 0.4:
        strengths.append("High international collaboration rate")
    if grant_income > 500000:
        strengths.append("Strong grant income")
    if avg_h > 10:
        strengths.append("High research impact (h-index)")
    if pub_per_researcher < 1:
        weaknesses.append("Low publication output per researcher")
    if avg_intl < 0.1:
        weaknesses.append("Limited international collaboration")
    if not strengths:
        strengths.append("Stable research output")

    return DepartmentProfile(
        name=name,
        researcher_count=n,
        publication_count=pub_count,
        citation_count=cite_count,
        grant_count=grant_count,
        grant_income=grant_income,
        avg_h_index=round(avg_h, 2),
        collaboration_score=round(avg_intl, 3),
        international_ratio=round(avg_intl, 3),
        publication_growth=0.0,   # would need historical data
        status=status,
        strengths=strengths,
        weaknesses=weaknesses,
        top_researchers=top,
        research_domains=unique_domains,
    )


# ── Main profiler ─────────────────────────────────────────────────────────────

def build_institution_profile(inp: InstitutionInput) -> InstitutionProfile:
    """Build a full InstitutionProfile from InstitutionInput."""
    inst_id = inp.metadata.get("institution_id") or str(uuid.uuid4())[:8]
    researchers = inp.researchers
    grants      = inp.grants
    n = len(researchers)

    # Aggregate researcher metrics
    total_pubs  = sum(_safe_int(r.get("publication_count", 0)) for r in researchers)
    total_cites = sum(_safe_int(r.get("citation_count", 0)) for r in researchers)
    total_grant_income = sum(_safe_float(g.get("amount", 0)) for g in grants)

    h_values = [_safe_float(r.get("h_index", 0)) for r in researchers]
    avg_h    = sum(h_values) / max(len(h_values), 1)

    intl_vals  = [_safe_float(r.get("international_collab_ratio", 0)) for r in researchers]
    avg_intl   = sum(intl_vals) / max(len(intl_vals), 1)

    # Research areas (union of all researcher domains)
    all_areas: list[str] = []
    for r in researchers:
        all_areas.extend(_safe_list(r.get("research_areas") or r.get("domains") or []))
    unique_areas = sorted({a.lower() for a in all_areas if a})[:15]

    # Top researchers
    sorted_researchers = sorted(researchers, key=lambda r: -_safe_float(r.get("h_index", 0)))
    top_researchers = [
        r.get("full_name") or r.get("name") or str(r.get("_id", ""))
        for r in sorted_researchers[:10] if r
    ]

    # Departments
    dept_names = inp.departments or sorted({
        r.get("department") or r.get("faculty") or "General"
        for r in researchers
        if r.get("department") or r.get("faculty")
    })
    dept_profiles = [_build_department(d, researchers, grants) for d in dept_names[:10]]

    # International partners (unique countries from researchers)
    countries = sorted({r.get("country", "") for r in researchers if r.get("country")})

    # Overall score: composite of key metrics
    pub_score    = min(total_pubs / max(n * 3, 1), 1.0)
    cite_score   = min(total_cites / max(n * 100, 1), 1.0)
    h_score      = min(avg_h / 15.0, 1.0)
    intl_score   = avg_intl
    grant_score  = min(len(grants) / max(n * 0.5, 1), 1.0)
    overall = round((pub_score * 0.25 + cite_score * 0.25 + h_score * 0.2 +
                     intl_score * 0.15 + grant_score * 0.15), 3)

    try:
        inst_type = _infer_type(inp.institution_type)
    except Exception:
        inst_type = InstitutionType.UNIVERSITY

    return InstitutionProfile(
        institution_id=inst_id,
        name=inp.name,
        institution_type=inst_type,
        country=inp.country,
        founding_year=inp.founding_year,
        total_researchers=n,
        total_publications=total_pubs,
        total_citations=total_cites,
        total_grants=len(grants),
        total_grant_income=total_grant_income,
        departments=dept_profiles,
        research_areas=unique_areas,
        top_researchers=top_researchers,
        international_partners=countries,
        overall_score=overall,
    )
