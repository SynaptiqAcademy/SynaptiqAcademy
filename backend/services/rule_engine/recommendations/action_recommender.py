"""Rule-based next-action recommendations based on user activity state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionRecommendation:
    priority: int
    category: str
    title: str
    description: str
    cta: str = ""
    url: str = ""
    badge: str = ""  # Optional badge label: 'new' | 'trending' | 'deadline'

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "cta": self.cta,
            "url": self.url,
            "badge": self.badge,
        }


def get_next_actions(
    profile: dict,
    stats: dict | None = None,
) -> list[ActionRecommendation]:
    """Generate prioritised next-action recommendations.

    profile: User document
    stats: Optional dict with activity stats:
        {
            manuscript_count, project_count, collaboration_count,
            grant_count, review_count, lesson_count, days_since_last_login,
            credits_balance, storage_used_pct, upcoming_deadlines
        }
    """
    s = stats or {}
    actions: list[ActionRecommendation] = []
    user_type = profile.get("user_type") or "researcher"

    # ── Onboarding priority ────────────────────────────────────────────────
    if not profile.get("orcid_id"):
        actions.append(ActionRecommendation(
            priority=1, category="onboarding",
            title="Connect your ORCID iD",
            description="Unlock publication import, citation metrics, and verified identity.",
            cta="Connect ORCID", url="/profile/settings#orcid", badge="new",
        ))

    bio = profile.get("bio") or ""
    if len(bio) < 50:
        actions.append(ActionRecommendation(
            priority=1, category="onboarding",
            title="Complete your profile",
            description="A complete profile is required before collaborators can find you.",
            cta="Complete profile", url="/profile/edit",
        ))

    # ── Research actions ────────────────────────────────────────────────────
    ms_count = int(s.get("manuscript_count") or 0)
    if ms_count == 0:
        actions.append(ActionRecommendation(
            priority=2, category="research",
            title="Start your first manuscript",
            description="Use the AI writing assistant to draft, structure, and reference your first paper.",
            cta="Create manuscript", url="/manuscripts/new",
        ))

    proj_count = int(s.get("project_count") or 0)
    if proj_count == 0:
        actions.append(ActionRecommendation(
            priority=2, category="research",
            title="Create a research project",
            description="Projects organize your research and make it visible to collaborators.",
            cta="Create project", url="/projects/new",
        ))

    # ── Collaboration actions ────────────────────────────────────────────────
    collab_count = int(s.get("collaboration_count") or 0)
    if collab_count == 0:
        actions.append(ActionRecommendation(
            priority=3, category="collaboration",
            title="Post a collaboration opportunity",
            description="Reach qualified researchers who match your expertise.",
            cta="Post collaboration", url="/collaborations/new",
        ))
    elif collab_count > 0:
        actions.append(ActionRecommendation(
            priority=4, category="collaboration",
            title="Explore collaboration requests",
            description="Check incoming collaboration applications and respond to requests.",
            cta="View requests", url="/collaborations",
        ))

    # ── Grant actions ────────────────────────────────────────────────────────
    if user_type in ("researcher", "university_faculty", "postdoctoral_researcher"):
        grant_count = int(s.get("grant_count") or 0)
        if grant_count == 0:
            actions.append(ActionRecommendation(
                priority=3, category="funding",
                title="Explore grant opportunities",
                description="AI-powered grant matching finds opportunities aligned with your research profile.",
                cta="Discover grants", url="/funding",
            ))

    # ── Review actions ────────────────────────────────────────────────────────
    review_count = int(s.get("review_count") or 0)
    if review_count == 0:
        actions.append(ActionRecommendation(
            priority=4, category="community",
            title="Join the reviewer marketplace",
            description="Peer reviewing earns reputation points and recognition in your field.",
            cta="Become a reviewer", url="/reviewer-marketplace",
        ))

    # ── Teaching actions ─────────────────────────────────────────────────────
    if user_type in ("educator", "university_faculty", "trainer"):
        lesson_count = int(s.get("lesson_count") or 0)
        if lesson_count == 0:
            actions.append(ActionRecommendation(
                priority=2, category="teaching",
                title="Create your first lesson",
                description="Use the Teaching Hub AI to generate structured lessons and assessments.",
                cta="Create lesson", url="/teaching",
            ))

    # ── Deadline urgency ────────────────────────────────────────────────────
    deadlines = s.get("upcoming_deadlines") or []
    for d in deadlines[:2]:
        actions.append(ActionRecommendation(
            priority=1, category="deadline",
            title=f"Upcoming deadline: {d.get('title', 'Task')}",
            description=f"Due {d.get('due', 'soon')} — action required.",
            cta="View", url=d.get("url", ""), badge="deadline",
        ))

    # ── Credits warning ─────────────────────────────────────────────────────
    credits = int(s.get("credits_balance") or 999)
    if credits < 10:
        actions.append(ActionRecommendation(
            priority=2, category="account",
            title="Low AI credits",
            description=f"You have {credits} credit(s) remaining. Top up to continue using AI features.",
            cta="Add credits", url="/billing", badge="new",
        ))

    return sorted(actions, key=lambda a: a.priority)[:8]
