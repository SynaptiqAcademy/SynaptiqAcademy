"""Academic Career Intelligence — Goal Manager (Phase XVI).

Evaluates user-defined goals, computes progress, assigns status and recommendations.
"""
from __future__ import annotations

from typing import Any

from .models import CareerGoal, CareerProfile, GoalStatus, GoalType


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _progress_from_values(current: Any, target: Any) -> float:
    try:
        c = float(current) if current is not None else 0.0
        t = float(target)  if target  is not None else 1.0
        return _clamp(c / max(t, 0.001))
    except (TypeError, ValueError):
        return 0.0


def _status(progress: float, deadline_months: int) -> GoalStatus:
    if progress >= 1.0:
        return GoalStatus.COMPLETED
    if progress > 0.5:
        return GoalStatus.IN_PROGRESS
    # Threshold: if < 20% progress with less than 6 months remaining → at_risk
    if progress < 0.2 and deadline_months < 6:
        return GoalStatus.AT_RISK
    if progress > 0.0:
        return GoalStatus.IN_PROGRESS
    return GoalStatus.NOT_STARTED


def _recommendation(goal: CareerGoal, profile: CareerProfile) -> str:
    gtype  = goal.goal_type
    prog   = goal.progress
    target = goal.target_value

    if gtype == GoalType.PUBLICATION:
        remaining = max(0, int(target or 0) - profile.publication_count)
        if remaining == 0:
            return "Goal achieved — maintain your publication rate."
        return f"Submit {remaining} more paper(s). Prioritise drafts in progress."

    if gtype == GoalType.H_INDEX:
        gap = max(0, float(target or 0) - profile.h_index)
        return f"H-index gap: {gap:.0f}. Increase citation visibility via open access and collaborations."

    if gtype == GoalType.GRANT:
        return "Apply to at least 2 grant calls in the next 6 months. Use internal review process."

    if gtype == GoalType.DEGREE:
        if prog < 0.5:
            return "Focus on completing core chapters; schedule committee meeting within 3 months."
        return "Finalize dissertation; arrange submission and viva date."

    if gtype == GoalType.PROMOTION:
        return "Review promotion criteria; compile evidence portfolio; identify internal sponsor."

    if gtype == GoalType.COLLABORATION:
        rem = max(0, int(target or 0) - profile.collaboration_count)
        return f"Initiate {rem} more collaboration(s) via conference networking or research matchmaking."

    if gtype == GoalType.TEACHING:
        return "Seek peer observation opportunities; attend teaching excellence workshops."

    if gtype == GoalType.SKILL:
        return f"Enrol in targeted course or workshop for '{goal.description}'."

    return "Review timeline and break goal into smaller milestones."


def _infer_current(goal_type: GoalType, profile: CareerProfile) -> Any:
    mapping = {
        GoalType.PUBLICATION:   profile.publication_count,
        GoalType.H_INDEX:       profile.h_index,
        GoalType.GRANT:         profile.grant_count,
        GoalType.COLLABORATION: profile.collaboration_count,
        GoalType.CITATION:      profile.citation_count,
    }
    return mapping.get(goal_type)


def _infer_milestones(goal: CareerGoal, profile: CareerProfile) -> list[str]:
    if goal.goal_type == GoalType.PUBLICATION:
        return ["Draft manuscript", "Submit to journal", "Address reviewer comments",
                "Accept/revise", "Publication"]
    if goal.goal_type == GoalType.GRANT:
        return ["Identify call", "Write concept note", "Internal review",
                "Submit application", "Interview / Award"]
    if goal.goal_type == GoalType.H_INDEX:
        return ["Increase publication count", "Improve visibility (open access)",
                "Present at conferences", "Accumulate citations"]
    if goal.goal_type == GoalType.DEGREE:
        return ["Complete coursework", "Write chapters", "Internal review",
                "Submit thesis", "Defend dissertation"]
    if goal.goal_type == GoalType.PROMOTION:
        return ["Meet publication threshold", "Secure grant funding",
                "Teaching portfolio", "Gather references", "Submit dossier"]
    return ["Start", "Progress checkpoint", "Complete"]


def evaluate_goals(
    profile: CareerProfile,
    goals: list[dict],
) -> list[CareerGoal]:
    """
    Evaluate a list of goal dicts against the current profile.

    Each goal dict must have:
      goal_type: str (GoalType value)
      description: str
      target_value: int/float (optional)
      current_value: int/float (optional — inferred from profile if absent)
      deadline_months: int (default 12)
    """
    evaluated: list[CareerGoal] = []
    for raw in goals:
        try:
            gtype = GoalType(raw.get("goal_type", "publication"))
        except ValueError:
            gtype = GoalType.PUBLICATION

        current = raw.get("current_value") if raw.get("current_value") is not None \
            else _infer_current(gtype, profile)
        target  = raw.get("target_value")
        deadline = int(raw.get("deadline_months") or 12)

        prog     = _progress_from_values(current, target) if target is not None else 0.0
        status   = _status(prog, deadline)

        goal = CareerGoal(
            goal_type=gtype,
            description=raw.get("description") or gtype.value.replace("_", " ").title(),
            target_value=target,
            current_value=current,
            deadline_months=deadline,
            status=status,
            progress=round(prog, 3),
        )
        goal.milestones = _infer_milestones(goal, profile)
        goal.recommendation = _recommendation(goal, profile)
        evaluated.append(goal)

    return evaluated


def infer_default_goals(profile: CareerProfile) -> list[CareerGoal]:
    """
    Auto-generate sensible default goals based on career stage when the user
    has no explicit goals defined.
    """
    from .models import CareerStage

    goals: list[dict] = []

    if profile.career_stage in (CareerStage.PHD_CANDIDATE, CareerStage.POSTDOC):
        goals.append({"goal_type": "publication", "description": "Publish 3 peer-reviewed papers",
                      "target_value": max(profile.publication_count + 3, 3), "deadline_months": 24})
        goals.append({"goal_type": "h_index", "description": "Achieve h-index ≥ 5",
                      "target_value": max(profile.h_index + 3, 5), "deadline_months": 36})

    elif profile.career_stage in (CareerStage.ASSISTANT_PROF, CareerStage.LECTURER):
        goals.append({"goal_type": "publication", "description": "Publish 4+ papers this year",
                      "target_value": profile.publication_count + 4, "deadline_months": 12})
        goals.append({"goal_type": "grant", "description": "Win a competitive grant",
                      "target_value": profile.grant_count + 1, "deadline_months": 18})
        goals.append({"goal_type": "promotion", "description": "Prepare for associate professor",
                      "deadline_months": 36})

    elif profile.career_stage in (CareerStage.ASSOCIATE_PROF, CareerStage.PROFESSOR,
                                  CareerStage.SENIOR_RESEARCHER):
        goals.append({"goal_type": "h_index", "description": "Grow h-index",
                      "target_value": profile.h_index + 5, "deadline_months": 24})
        goals.append({"goal_type": "collaboration", "description": "Expand international network",
                      "target_value": profile.collaboration_count + 5, "deadline_months": 18})
    else:
        goals.append({"goal_type": "publication", "description": "Increase publication output",
                      "target_value": profile.publication_count + 2, "deadline_months": 12})

    return evaluate_goals(profile, goals)
