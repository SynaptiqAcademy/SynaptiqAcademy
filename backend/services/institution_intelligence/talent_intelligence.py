"""Institution Intelligence Engine — Academic Talent Intelligence (Phase XV).

Identifies future leaders, high-potential researchers, promotion candidates,
mentorship opportunities, training needs, succession risks, and retention risks.
"""
from __future__ import annotations

from typing import Any

from .models import InstitutionInput, TalentProfile


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


_POSITION_STAGE = {
    "phd student": "doctoral", "phd candidate": "doctoral",
    "postdoc": "postdoc", "postdoctoral researcher": "postdoc",
    "junior researcher": "early_career", "assistant professor": "early_career",
    "associate professor": "mid_career", "lecturer": "early_career",
    "senior lecturer": "mid_career", "professor": "senior",
    "full professor": "senior", "research director": "senior",
    "emeritus": "emeritus",
}


def _career_stage(r: dict) -> str:
    pos = (r.get("position") or "").lower()
    for key, stage in _POSITION_STAGE.items():
        if key in pos:
            return stage
    return "mid_career"


def _talent_score(r: dict, avg_h: float, avg_pub: float) -> float:
    h       = _sf(r.get("h_index", 0))
    pubs    = _si(r.get("publication_count", 0))
    intl    = _sf(r.get("international_collab_ratio", 0))
    collab  = _sf(r.get("collaboration_count", 0))
    avail   = _sf(r.get("availability", 0.5))
    h_score   = min(h / max(avg_h * 2, 1), 1.0)
    pub_score = min(pubs / max(avg_pub * 2, 1), 1.0)
    return round(h_score * 0.35 + pub_score * 0.30 + intl * 0.20 + min(collab / 10, 1.0) * 0.10 + avail * 0.05, 3)


def identify_talent(inp: InstitutionInput) -> dict[str, list[TalentProfile]]:
    """
    Returns a dict with keys:
      future_leaders, high_potential, promotion_candidates,
      retention_risks, mentorship_providers, training_needs,
      succession_planning
    """
    researchers = inp.researchers
    if not researchers:
        return {k: [] for k in [
            "future_leaders", "high_potential", "promotion_candidates",
            "retention_risks", "mentorship_providers", "training_needs",
            "succession_planning",
        ]}

    h_vals   = [_sf(r.get("h_index", 0)) for r in researchers]
    pub_vals = [float(_si(r.get("publication_count", 0))) for r in researchers]
    avg_h    = _mean(h_vals)
    avg_pub  = _mean(pub_vals)

    future_leaders: list[TalentProfile]         = []
    high_potential: list[TalentProfile]         = []
    promotion_candidates: list[TalentProfile]   = []
    retention_risks: list[TalentProfile]        = []
    mentorship_providers: list[TalentProfile]   = []
    training_needs: list[TalentProfile]         = []
    succession_planning: list[TalentProfile]    = []

    for r in researchers:
        rid   = str(r.get("_id") or r.get("id") or "")
        name  = r.get("full_name") or r.get("name") or rid
        dept  = r.get("department") or "General"
        stage = _career_stage(r)
        h     = _sf(r.get("h_index", 0))
        pubs  = _si(r.get("publication_count", 0))
        avail = _sf(r.get("availability", 1.0))
        score = _talent_score(r, avg_h, avg_pub)

        tp = TalentProfile(user_id=rid, name=name, department=dept,
                           career_stage=stage, h_index=h,
                           publication_count=pubs, score=score)

        # Future leaders: senior performance + leadership indicators
        if h > avg_h * 1.5 and pubs > avg_pub * 1.5 and stage in ("senior", "mid_career"):
            tp.talent_tag = "future_leader"
            tp.recommendation = "Nominate for leadership training; include in institutional committees."
            tp.rationale = f"h={h:.0f} (avg={avg_h:.1f}), {pubs} publications — top 10% institutional profile."
            future_leaders.append(tp)

        # High potential: early career but outperforming
        elif stage in ("early_career", "postdoc", "doctoral") and score > 0.6:
            tp.talent_tag = "high_potential"
            tp.recommendation = "Provide mentoring, conference support, and co-PI opportunities."
            tp.rationale = f"Exceptional output for career stage: h={h:.0f}, {pubs} pubs, score={score:.2f}."
            high_potential.append(tp)

        # Promotion candidates
        if stage == "early_career" and h > avg_h * 0.8 and pubs > avg_pub * 0.8:
            tp.talent_tag = "promotion_candidate"
            tp.recommendation = "Review for promotion to associate professor within 12-18 months."
            tp.rationale = "Research metrics meet promotion threshold; career stage aligns."
            promotion_candidates.append(tp)

        # Retention risks: high performers with low availability
        if avail < 0.3 and h > avg_h:
            tp.talent_tag = "retention_risk"
            tp.recommendation = "Conduct retention interview; review workload and compensation."
            tp.rationale = f"Low availability ({avail:.0%}) despite above-average impact (h={h:.0f})."
            retention_risks.append(tp)

        # Mentorship providers: senior, available, high impact
        if stage in ("senior", "mid_career") and avail > 0.6 and h > avg_h:
            tp.talent_tag = "mentorship_provider"
            tp.recommendation = "Assign 2-3 early-career mentees; recognise in performance review."
            tp.rationale = "Senior researcher with availability and demonstrated excellence."
            mentorship_providers.append(tp)

        # Training needs: active but low output
        if pubs == 0 and avail > 0.5 and stage not in ("doctoral",):
            tp.talent_tag = "training_needed"
            tp.recommendation = "Enrol in research skills and academic writing programmes."
            tp.rationale = "Active researcher with no publications — likely needs skill support."
            training_needs.append(tp)

        # Succession planning: senior researchers approaching emeritus
        if stage in ("senior",) and h > avg_h * 1.2:
            tp.talent_tag = "succession_critical"
            tp.recommendation = "Document expertise; identify and groom successor within 2 years."
            tp.rationale = "High-impact senior researcher; institutional knowledge at risk if not captured."
            succession_planning.append(tp)

    def _sort(lst: list[TalentProfile]) -> list[TalentProfile]:
        return sorted(lst, key=lambda t: -t.score)

    return {
        "future_leaders":       _sort(future_leaders)[:10],
        "high_potential":       _sort(high_potential)[:10],
        "promotion_candidates": _sort(promotion_candidates)[:10],
        "retention_risks":      _sort(retention_risks)[:10],
        "mentorship_providers": _sort(mentorship_providers)[:10],
        "training_needs":       _sort(training_needs)[:10],
        "succession_planning":  _sort(succession_planning)[:10],
    }


def serialize_talent(talent: dict[str, list[TalentProfile]]) -> dict[str, list[dict]]:
    return {k: [t.to_dict() for t in v] for k, v in talent.items()}
