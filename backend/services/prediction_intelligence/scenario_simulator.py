"""Academic Prediction — Multi-scenario simulation & what-if analysis (Phase XVIII)."""
from __future__ import annotations

import uuid

from .confidence_model import compute_confidence
from .models import (
    DecisionUrgency, Scenario, ScenarioComparison, ScenarioType,
    WhatIfAnalysis, WhatIfFactor,
)
from .publication_predictor import predict_publication, _quality_composite


# ── Scenario simulation ───────────────────────────────────────────────────────

def _apply_scenario_changes(base: dict, scenario_type: ScenarioType) -> dict:
    """Return a modified copy of the manuscript dict for the scenario."""
    m = dict(base)
    jnl = dict(m.get("target_journal") or {})

    if scenario_type == ScenarioType.SUBMIT_NOW:
        pass  # no changes

    elif scenario_type == ScenarioType.DELAY_3_MONTHS:
        m["methodology_score"]  = min(1.0, float(m.get("methodology_score", 0.5)) + 0.08)
        m["novelty_score"]      = min(1.0, float(m.get("novelty_score", 0.5)) + 0.05)
        m["statistical_quality"]= min(1.0, float(m.get("statistical_quality", 0.5)) + 0.06)

    elif scenario_type == ScenarioType.DELAY_6_MONTHS:
        m["methodology_score"]  = min(1.0, float(m.get("methodology_score", 0.5)) + 0.15)
        m["novelty_score"]      = min(1.0, float(m.get("novelty_score", 0.5)) + 0.08)
        m["statistical_quality"]= min(1.0, float(m.get("statistical_quality", 0.5)) + 0.10)
        m["reference_count"]    = int(m.get("reference_count", 30)) + 10

    elif scenario_type == ScenarioType.ADD_COLLABORATOR:
        authors = list(m.get("authors") or [])
        authors.append({"h_index": 15, "publication_count": 30, "name": "New Collaborator"})
        m["authors"] = authors

    elif scenario_type == ScenarioType.CHANGE_JOURNAL:
        jnl["acceptance_rate"]   = min(0.90, float(jnl.get("acceptance_rate", 0.30)) + 0.20)
        jnl["impact_factor"]     = max(1.0, float(jnl.get("impact_factor", 2.0)) * 0.6)
        jnl["avg_review_weeks"]  = max(4, int(jnl.get("avg_review_weeks", 12)) - 3)
        m["target_journal"] = jnl

    elif scenario_type == ScenarioType.IMPROVE_MANUSCRIPT:
        m["methodology_score"]   = min(1.0, float(m.get("methodology_score", 0.5)) + 0.12)
        m["novelty_score"]       = min(1.0, float(m.get("novelty_score", 0.5)) + 0.10)
        m["scope_match"]         = min(1.0, float(m.get("scope_match", 0.65)) + 0.10)

    elif scenario_type == ScenarioType.MORE_DATA:
        m["statistical_quality"] = min(1.0, float(m.get("statistical_quality", 0.5)) + 0.15)
        m["methodology_score"]   = min(1.0, float(m.get("methodology_score", 0.5)) + 0.08)
        m["novelty_score"]       = min(1.0, float(m.get("novelty_score", 0.5)) + 0.05)

    return m


_SCENARIO_METADATA: dict[ScenarioType, dict] = {
    ScenarioType.SUBMIT_NOW:        {"name": "Submit Now",        "delay_months": 0,  "pros": ["Immediate submission", "No delay cost"], "cons": ["Manuscript as-is quality"]},
    ScenarioType.DELAY_3_MONTHS:    {"name": "Delay 3 Months",    "delay_months": 3,  "pros": ["Improved methodology", "Stronger statistics"], "cons": ["3-month delay", "Competitor risk"]},
    ScenarioType.DELAY_6_MONTHS:    {"name": "Delay 6 Months",    "delay_months": 6,  "pros": ["Major quality improvement", "More references"], "cons": ["6-month delay", "Scooping risk"]},
    ScenarioType.ADD_COLLABORATOR:  {"name": "Add Collaborator",  "delay_months": 1,  "pros": ["Higher author reputation", "Better scope"], "cons": ["1-month onboarding delay"]},
    ScenarioType.CHANGE_JOURNAL:    {"name": "Change Journal",    "delay_months": 0,  "pros": ["Higher acceptance rate", "Faster review"], "cons": ["Lower impact factor"]},
    ScenarioType.IMPROVE_MANUSCRIPT:{"name": "Improve Manuscript","delay_months": 2,  "pros": ["Better quality score", "Scope alignment"], "cons": ["2-month revision delay"]},
    ScenarioType.MORE_DATA:         {"name": "More Data",         "delay_months": 4,  "pros": ["Stronger evidence", "Better statistics"], "cons": ["4-month data collection"]},
}


def simulate_scenarios(
    manuscript: dict,
    scenario_types: list[str] | None = None,
) -> ScenarioComparison:
    """Compare multiple submission scenarios for the same manuscript."""
    m = manuscript or {}

    if scenario_types:
        try:
            types = [ScenarioType(t) for t in scenario_types]
        except ValueError:
            types = [ScenarioType.SUBMIT_NOW, ScenarioType.DELAY_3_MONTHS, ScenarioType.IMPROVE_MANUSCRIPT]
    else:
        types = [ScenarioType.SUBMIT_NOW, ScenarioType.DELAY_3_MONTHS,
                 ScenarioType.ADD_COLLABORATOR, ScenarioType.IMPROVE_MANUSCRIPT]

    scenarios: list[Scenario] = []
    comp_matrix: dict[str, dict] = {
        "acceptance_probability": {},
        "expected_review_weeks":  {},
        "citation_velocity_y1":   {},
        "long_term_impact":       {},
        "delay_months":           {},
    }

    for st in types:
        modified = _apply_scenario_changes(m, st)
        pred = predict_publication(modified)
        meta = _SCENARIO_METADATA[st]

        acc      = pred.acceptance.value
        rev_wk   = pred.expected_review_weeks.value
        cit_y1   = pred.citation_velocity_y1.value
        lt_imp   = pred.long_term_impact.value
        delay_mo = meta["delay_months"]

        # Combined utility score
        util = (acc * 0.45 + min(cit_y1 / 10.0, 1.0) * 0.30 +
                min(lt_imp / 10.0, 1.0) * 0.25 - delay_mo / 24.0 * 0.15)

        scen = Scenario(
            scenario_id=str(uuid.uuid4()),
            name=meta["name"],
            scenario_type=st.value,
            description=f"{meta['name']}: {delay_mo}-month delay, acceptance {round(acc*100)}%",
            key_metrics={
                "acceptance_probability": round(acc, 3),
                "expected_review_weeks":  round(rev_wk, 1),
                "citation_velocity_y1":   round(cit_y1, 2),
                "long_term_impact":       round(lt_imp, 2),
                "delay_months":           delay_mo,
                "utility_score":          round(util, 3),
            },
            confidence=round(pred.overall_confidence, 3),
            pros=meta["pros"],
            cons=meta["cons"],
        )
        scenarios.append(scen)
        comp_matrix["acceptance_probability"][meta["name"]] = round(acc, 3)
        comp_matrix["expected_review_weeks"][meta["name"]]  = round(rev_wk, 1)
        comp_matrix["citation_velocity_y1"][meta["name"]]   = round(cit_y1, 2)
        comp_matrix["long_term_impact"][meta["name"]]       = round(lt_imp, 2)
        comp_matrix["delay_months"][meta["name"]]           = delay_mo

    best = max(scenarios, key=lambda s: s.key_metrics["utility_score"])
    avg_conf = sum(s.confidence for s in scenarios) / max(len(scenarios), 1)

    return ScenarioComparison(
        scenarios=scenarios,
        comparison_matrix=comp_matrix,
        recommended_scenario=best.name,
        reasoning=(
            f"'{best.name}' maximises the utility score "
            f"(acceptance × impact − delay cost). "
            f"Acceptance probability: {round(best.key_metrics['acceptance_probability']*100)}%."
        ),
        confidence=round(avg_conf, 3),
    )


# ── What-if analysis ──────────────────────────────────────────────────────────

_WHAT_IF_EFFECTS: dict[WhatIfFactor, dict] = {
    WhatIfFactor.INTERNATIONAL_COLLABORATION: {
        "novelty_score":        +0.06,
        "citation_growth":      +0.20,
        "desc": "International collaboration boosts visibility and citation impact.",
    },
    WhatIfFactor.OPEN_ACCESS: {
        "citation_growth":      +0.25,
        "desc": "Open Access publications typically receive 1.25× more citations.",
    },
    WhatIfFactor.INCREASE_SAMPLE_SIZE: {
        "statistical_quality":  +0.15,
        "methodology_score":    +0.08,
        "desc": "Larger sample increases statistical power and methodology credibility.",
    },
    WhatIfFactor.CHANGE_METHODOLOGY: {
        "methodology_score":    +0.12,
        "novelty_score":        +0.08,
        "desc": "Methodological change may increase novelty perception.",
    },
    WhatIfFactor.IMPROVE_STATISTICS: {
        "statistical_quality":  +0.18,
        "methodology_score":    +0.06,
        "desc": "Better statistical analysis reduces major revision risk.",
    },
    WhatIfFactor.DELAY_SUBMISSION: {
        "methodology_score":    +0.10,
        "reference_count":      +8,
        "desc": "Delayed submission allows manuscript polish and additional references.",
    },
    WhatIfFactor.ADD_AUTHOR: {
        "author_h_boost":       15,
        "desc": "Adding a high-h-index co-author increases acceptance probability.",
    },
}


def what_if_analysis(manuscript: dict, factor: str) -> WhatIfAnalysis:
    """Run a what-if analysis for a single modification factor."""
    m = manuscript or {}
    try:
        wif = WhatIfFactor(factor)
    except ValueError:
        wif = WhatIfFactor.IMPROVE_STATISTICS

    base_pred = predict_publication(m)
    effects   = _WHAT_IF_EFFECTS[wif]

    # Apply effects to a copy
    modified = dict(m)
    for key, delta in effects.items():
        if key == "author_h_boost":
            authors = list(m.get("authors") or [])
            authors.append({"h_index": delta, "publication_count": 25, "name": "Added Author"})
            modified["authors"] = authors
        elif key == "citation_growth":
            jnl = dict(m.get("target_journal") or {})
            jnl["impact_factor"] = float(jnl.get("impact_factor", 2.0)) * (1 + delta)
            modified["target_journal"] = jnl
        elif key != "desc":
            current = float(modified.get(key, 0.5))
            if isinstance(delta, float):
                modified[key] = min(1.0, current + delta)
            else:
                modified[key] = int(current) + int(delta)

    modified_pred = predict_publication(modified)
    delta_acc   = modified_pred.acceptance.value - base_pred.acceptance.value
    delta_lt    = modified_pred.long_term_impact.value - base_pred.long_term_impact.value
    net_benefit = delta_acc * 0.60 + min(delta_lt / 5.0, 0.4) * 0.40

    conf = compute_confidence(0.7, min(abs(net_benefit) + 0.3, 1.0), "publication_acceptance")

    rec = (
        f"Applying '{wif.value}' is {'beneficial' if net_benefit > 0 else 'neutral/detrimental'}. "
        f"Acceptance probability change: {'+' if delta_acc >= 0 else ''}{round(delta_acc*100, 1)}%. "
        + effects["desc"]
    )

    return WhatIfAnalysis(
        base_scenario={"manuscript_score": base_pred.manuscript_score},
        what_if_factor=wif.value,
        base_prediction={
            "acceptance_probability": base_pred.acceptance.value,
            "long_term_impact":       base_pred.long_term_impact.value,
        },
        modified_prediction={
            "acceptance_probability": modified_pred.acceptance.value,
            "long_term_impact":       modified_pred.long_term_impact.value,
        },
        delta_summary={
            "acceptance_change": round(delta_acc, 3),
            "impact_change":     round(delta_lt, 3),
            "net_benefit":       round(net_benefit, 3),
        },
        net_benefit=round(net_benefit, 3),
        recommendation=rec,
        confidence=round(conf, 3),
    )
