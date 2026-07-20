"""Academic Copilot — Proactive Advisor (Phase XI).

Scans the user's platform context and generates unsolicited, prioritised
suggestions without waiting for the user to ask.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta

from .models import ProactiveSuggestion, SuggestionCategory, Urgency


def _days_until(date_str: str | None) -> int | None:
    """Return days until a deadline string, or None if unparseable."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(date_str[:19], fmt).replace(tzinfo=timezone.utc)
            return (dt - datetime.now(timezone.utc)).days
        except ValueError:
            continue
    return None


def _deadline_urgency(days: int | None) -> Urgency | None:
    if days is None:
        return None
    if days < 0:
        return None  # already passed
    if days <= 7:
        return Urgency.CRITICAL
    if days <= 21:
        return Urgency.HIGH
    if days <= 60:
        return Urgency.MEDIUM
    return Urgency.LOW


def _manuscript_suggestions(context: dict) -> list[ProactiveSuggestion]:
    suggestions: list[ProactiveSuggestion] = []
    manuscripts = context.get("manuscripts") or []

    for ms in manuscripts[:10]:
        status = ms.get("status", "")
        title  = ms.get("title", "Untitled manuscript")
        mid    = ms.get("id", "")

        if status in ("draft", "in_progress"):
            word_count = ms.get("word_count", 0)
            if word_count and word_count < 3000:
                suggestions.append(ProactiveSuggestion(
                    category=SuggestionCategory.MANUSCRIPT,
                    title=f'"{title}" needs more content',
                    description=(
                        f"Your manuscript has only {word_count:,} words. "
                        "A full research article typically requires 6,000–10,000 words."
                    ),
                    urgency=Urgency.MEDIUM,
                    confidence=0.80,
                    action_type="open_manuscript",
                    action_params={"manuscript_id": mid},
                    rationale="Detected low word count in active draft.",
                ))

        if status == "under_review":
            last_updated = ms.get("updated_at", "")
            days = _days_until(last_updated)
            # If not updated in 60+ days while under review — might be stuck
            if days is not None and abs(days) >= 60:
                suggestions.append(ProactiveSuggestion(
                    category=SuggestionCategory.MANUSCRIPT,
                    title=f'"{title}" — no update in 60+ days',
                    description=(
                        "Your manuscript has been under review for over 60 days with no update. "
                        "Consider following up with the editorial office."
                    ),
                    urgency=Urgency.MEDIUM,
                    confidence=0.70,
                    action_type="open_manuscript",
                    action_params={"manuscript_id": mid},
                    rationale="Long review period with no status change.",
                ))

        if status == "revision_required":
            suggestions.append(ProactiveSuggestion(
                category=SuggestionCategory.MANUSCRIPT,
                title=f'"{title}" — revision required',
                description=(
                    "Your manuscript has revisions requested. "
                    "Use the Manuscript Copilot to plan your response strategy."
                ),
                urgency=Urgency.HIGH,
                confidence=0.95,
                action_type="review_manuscript",
                action_params={"manuscript_id": mid},
                rationale="Status is revision_required.",
            ))

    return suggestions


def _grant_suggestions(context: dict) -> list[ProactiveSuggestion]:
    suggestions: list[ProactiveSuggestion] = []
    grants = context.get("grants_applied") or []

    for g in grants[:10]:
        deadline = g.get("deadline") or g.get("application_deadline")
        title    = g.get("grant_title") or g.get("title", "Grant")
        gid      = g.get("grant_id") or g.get("id", "")
        status   = g.get("status", "")

        if status in ("submitted", "under_review"):
            days = _days_until(deadline)
            urgency = _deadline_urgency(days)
            if urgency in (Urgency.CRITICAL, Urgency.HIGH):
                suggestions.append(ProactiveSuggestion(
                    category=SuggestionCategory.GRANT,
                    title=f'"{title}" — decision expected soon',
                    description=(
                        f"Your grant application is under review. "
                        f"Expected decision in ~{days} days."
                    ),
                    urgency=urgency,
                    confidence=0.75,
                    action_type="view_grant",
                    action_params={"grant_id": gid},
                    rationale=f"Deadline in {days} days.",
                ))

        if status == "draft":
            days = _days_until(deadline)
            urgency = _deadline_urgency(days)
            if urgency is not None:
                suggestions.append(ProactiveSuggestion(
                    category=SuggestionCategory.GRANT,
                    title=f'"{title}" deadline approaching',
                    description=(
                        f"Your grant proposal is still a draft. "
                        f"Deadline: {deadline} ({days} days remaining)."
                    ),
                    urgency=urgency,
                    confidence=0.90,
                    action_type="open_grant",
                    action_params={"grant_id": gid},
                    rationale=f"Draft grant with {days} days to deadline.",
                ))

    return suggestions


def _collaboration_suggestions(context: dict) -> list[ProactiveSuggestion]:
    suggestions: list[ProactiveSuggestion] = []
    collabs = context.get("collaborations") or []
    profile  = context.get("profile") or {}

    if len(collabs) == 0:
        research_areas = profile.get("research_areas") or []
        if research_areas:
            suggestions.append(ProactiveSuggestion(
                category=SuggestionCategory.COLLABORATION,
                title="Start your first collaboration",
                description=(
                    "You have no active collaborations. "
                    "Collaborative research receives 10× more citations on average. "
                    "Browse the Researcher Marketplace to find collaborators in "
                    + (", ".join(research_areas[:2]) or "your field") + "."
                ),
                urgency=Urgency.LOW,
                confidence=0.70,
                action_type="browse_marketplace",
                action_params={},
                rationale="No active collaborations detected.",
            ))

    return suggestions


def _impact_suggestions(context: dict) -> list[ProactiveSuggestion]:
    suggestions: list[ProactiveSuggestion] = []
    impact     = context.get("impact") or {}
    reputation = context.get("reputation") or {}

    sis = impact.get("sis_total", 0) or 0
    pub_count = impact.get("publication_count", 0) or 0
    h_index = impact.get("h_index", 0) or 0

    if pub_count == 0:
        suggestions.append(ProactiveSuggestion(
            category=SuggestionCategory.MANUSCRIPT,
            title="No publications recorded yet",
            description=(
                "Your impact score is 0 because no publications are linked to your profile. "
                "Import your ORCID publications or add them manually to get a Research Impact Score."
            ),
            urgency=Urgency.MEDIUM,
            confidence=0.90,
            action_type="import_publications",
            action_params={},
            rationale="Zero publication count on profile.",
        ))
    elif sis < 100 and pub_count > 0:
        suggestions.append(ProactiveSuggestion(
            category=SuggestionCategory.CAREER,
            title="Boost your Research Impact Score",
            description=(
                f"Your SIS is {sis}/10,000 with an H-index of {h_index}. "
                "Publishing in higher-quartile journals and increasing citation visibility "
                "can significantly improve your academic standing."
            ),
            urgency=Urgency.LOW,
            confidence=0.65,
            action_type="view_impact",
            action_params={},
            rationale=f"Low SIS ({sis}) despite {pub_count} publications.",
        ))

    rep_score = reputation.get("overall_score", 0) or 0
    if rep_score < 30 and pub_count > 0:
        suggestions.append(ProactiveSuggestion(
            category=SuggestionCategory.CAREER,
            title="Grow your academic reputation",
            description=(
                f"Your Reputation Score is {rep_score}/100. "
                "Completing peer reviews, mentoring peers, and engaging in collaborations "
                "will earn you reputation badges and increase visibility."
            ),
            urgency=Urgency.LOW,
            confidence=0.60,
            action_type="view_reputation",
            action_params={},
            rationale=f"Low reputation score ({rep_score}).",
        ))

    return suggestions


def _memory_suggestions(context: dict) -> list[ProactiveSuggestion]:
    suggestions: list[ProactiveSuggestion] = []
    memory_items = context.get("memory") or []
    memory_types = {m.get("memory_type") for m in memory_items}

    if "target_journal" not in memory_types:
        suggestions.append(ProactiveSuggestion(
            category=SuggestionCategory.JOURNAL,
            title="Set a target journal",
            description=(
                "You haven't told me your target journal yet. "
                "Say 'I'm targeting Nature Medicine' (or any journal) "
                "and I'll remember it for future recommendations."
            ),
            urgency=Urgency.LOW,
            confidence=0.55,
            action_type="save_memory",
            action_params={"memory_type": "target_journal"},
            rationale="No target_journal in user memory.",
        ))

    if "research_goal" not in memory_types:
        suggestions.append(ProactiveSuggestion(
            category=SuggestionCategory.CAREER,
            title="Tell me your research goal",
            description=(
                "Share your main research goal and I'll personalise every recommendation. "
                "Example: 'My research goal is to study AI in healthcare diagnostics.'"
            ),
            urgency=Urgency.LOW,
            confidence=0.55,
            action_type="save_memory",
            action_params={"memory_type": "research_goal"},
            rationale="No research_goal in user memory.",
        ))

    return suggestions


# ── Public API ────────────────────────────────────────────────────────────────

def generate_suggestions(context: dict) -> list[ProactiveSuggestion]:
    """Generate all proactive suggestions for the given user context."""
    all_suggestions: list[ProactiveSuggestion] = []
    all_suggestions += _manuscript_suggestions(context)
    all_suggestions += _grant_suggestions(context)
    all_suggestions += _collaboration_suggestions(context)
    all_suggestions += _impact_suggestions(context)
    all_suggestions += _memory_suggestions(context)

    # Sort: critical first, then by confidence descending
    _urgency_rank = {
        Urgency.CRITICAL: 0,
        Urgency.HIGH: 1,
        Urgency.MEDIUM: 2,
        Urgency.LOW: 3,
    }
    all_suggestions.sort(
        key=lambda s: (_urgency_rank[s.urgency], -s.confidence)
    )

    # Cap to avoid overwhelming the user
    return all_suggestions[:10]
