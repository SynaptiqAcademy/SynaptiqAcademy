"""Academic Prediction — Strategic decision advisor (Phase XVIII)."""
from __future__ import annotations

from .confidence_model import compute_confidence
from .models import DecisionUrgency, StrategicDecision
from .publication_predictor import predict_publication, _quality_composite


_QUESTION_PATTERNS: dict[str, str] = {
    "submit":       "submission",
    "journal":      "journal_selection",
    "collaborat":   "collaboration",
    "grant":        "grant",
    "method":       "methodology",
    "data":         "data_collection",
    "statistic":    "statistics",
    "revise":       "revision",
    "delay":        "delay",
    "open access":  "open_access",
    "review":       "revision",
}


def _classify_question(question: str) -> str:
    q = question.lower()
    for keyword, category in _QUESTION_PATTERNS.items():
        if keyword in q:
            return category
    return "general"


def _advise_submission(profile: dict) -> StrategicDecision:
    pred = predict_publication(profile)
    acc  = pred.acceptance.value
    q    = pred.manuscript_score

    if acc >= 0.65:
        rec = "Submit now. Your manuscript shows strong acceptance probability."
        urgency = DecisionUrgency.IMMEDIATE
        actions = ["Finalize formatting per journal guidelines", "Prepare cover letter"]
        risk    = "Delay may allow competitors to publish first."
        outcome = f"Expected acceptance probability: {round(acc*100)}%"
    elif acc >= 0.40:
        rec = "Submit now or after minor revisions within 2–4 weeks."
        urgency = DecisionUrgency.SOON
        actions = ["Polish abstract and conclusions", "Verify statistical reporting", "Strengthen novelty statement"]
        risk    = "Submitting without revisions risks major revision request."
        outcome = f"Expected acceptance probability: {round(acc*100)}% (minor revisions common)"
    else:
        rec = "Revise before submission — acceptance probability is currently low."
        urgency = DecisionUrgency.CAN_WAIT
        actions = ["Strengthen methodology section", "Add more supporting data", "Consider alternative journal tier"]
        risk    = "Submitting now likely leads to desk rejection or major revision."
        outcome = f"After revisions, expected acceptance: {min(0.95, acc + 0.20):.0%}"

    return StrategicDecision(
        question="Should I submit now?",
        recommendation=rec,
        confidence=round(pred.overall_confidence, 3),
        urgency=urgency.value,
        evidence=[
            f"Manuscript quality score: {round(q*100)}%",
            f"Predicted acceptance: {round(acc*100)}%",
            f"Desk rejection risk: {round(pred.desk_rejection.value*100)}%",
        ],
        action_items=actions,
        alternatives=[
            {"option": "Delay 3 months", "expected_gain": "+8–15% acceptance probability"},
            {"option": "Change journal",  "expected_gain": "+15–25% acceptance rate (lower impact)"},
        ],
        risk_if_ignored=risk,
        expected_outcome=outcome,
    )


def _advise_journal(profile: dict) -> StrategicDecision:
    from .journal_predictor import predict_journals
    result = predict_journals(profile)
    best   = result.best_journal
    return StrategicDecision(
        question="Which journal should I target?",
        recommendation=f"Target {best.journal_name} (acc={round(best.acceptance_probability*100)}%, scope={round(best.scope_match*100)}%).",
        confidence=round(result.confidence, 3),
        urgency=DecisionUrgency.SOON.value,
        evidence=[f"Ranked {len(result.all_matches)} journals", f"Best fit: {best.journal_name}"],
        action_items=["Review journal aims and scope", "Check recent accepted papers", "Prepare cover letter emphasising fit"],
        alternatives=[
            {"option": result.highest_impact.journal_name,   "description": "Highest impact factor"},
            {"option": result.fastest_publication.journal_name, "description": "Fastest publication"},
        ],
        risk_if_ignored="Wrong journal choice leads to desk rejection and 2–6 month delays.",
        expected_outcome=f"Acceptance probability {round(best.acceptance_probability*100)}% at {best.journal_name}.",
    )


def _advise_collaboration(profile: dict) -> StrategicDecision:
    from .collaboration_forecaster import forecast_collaboration
    fc   = forecast_collaboration(profile)
    succ = fc.success_probability.value
    return StrategicDecision(
        question="Should I add collaborators?",
        recommendation=(
            "Collaboration is strongly recommended — predicted success probability is high."
            if succ >= 0.65 else
            "Collaboration is worth pursuing — ensure shared research goals before committing."
            if succ >= 0.45 else
            "Collaboration requires more alignment — refine shared agenda first."
        ),
        confidence=round(fc.confidence, 3),
        urgency=(DecisionUrgency.SOON.value if succ >= 0.5 else DecisionUrgency.CAN_WAIT.value),
        evidence=[f"Collaboration success: {round(succ*100)}%", fc.overall_recommendation],
        action_items=["Define roles and authorship upfront", "Set milestones", "Agree on data sharing"],
        alternatives=[{"option": "Solo submission", "description": "Lower impact, faster decisions"}],
        risk_if_ignored="Missing collaboration opportunity may reduce citation impact and grant competitiveness.",
        expected_outcome=f"Predicted collaboration success: {round(succ*100)}%.",
    )


def _advise_grant(profile: dict) -> StrategicDecision:
    from .grant_predictor import predict_grant
    gp   = predict_grant(profile)
    prob = gp.funding_probability.value
    return StrategicDecision(
        question="Should I pursue this grant?",
        recommendation=(
            f"Apply — funding probability is {'high' if prob >= 0.35 else 'moderate' if prob >= 0.20 else 'challenging'} at {round(prob*100)}%."
        ),
        confidence=round(gp.confidence, 3),
        urgency=(DecisionUrgency.IMMEDIATE.value if prob >= 0.35 else DecisionUrgency.SOON.value),
        evidence=[f"Funding probability: {round(prob*100)}%", f"Competitiveness: {round(gp.competitiveness.value*100)}%"],
        action_items=gp.required_improvements[:3],
        alternatives=[{"option": "Alternative funding scheme", "description": "Lower competition, faster review"}],
        risk_if_ignored="Not applying means no funding opportunity this cycle.",
        expected_outcome=f"Expected funding probability: {round(prob*100)}%.",
    )


def _advise_general(profile: dict) -> StrategicDecision:
    pred = predict_publication(profile)
    return StrategicDecision(
        question="General academic strategy",
        recommendation="Focus on manuscript quality and strategic journal selection for maximum impact.",
        confidence=round(pred.overall_confidence, 3),
        urgency=DecisionUrgency.SOON.value,
        evidence=[f"Manuscript score: {round(pred.manuscript_score*100)}%"],
        action_items=["Review top journals in your domain", "Build collaboration network", "Strengthen grant portfolio"],
        alternatives=[],
        risk_if_ignored="No strategic planning reduces academic impact and career progression.",
        expected_outcome="Improved academic output and impact with strategic planning.",
    )


def advise(question: str, profile: dict) -> StrategicDecision:
    """Route to the appropriate strategic advisor based on question content."""
    category = _classify_question(question)
    advisors = {
        "submission":       _advise_submission,
        "journal_selection": _advise_journal,
        "collaboration":    _advise_collaboration,
        "grant":            _advise_grant,
        "general":          _advise_general,
    }
    fn = advisors.get(category, _advise_general)
    decision = fn(profile)
    decision.question = question
    return decision
