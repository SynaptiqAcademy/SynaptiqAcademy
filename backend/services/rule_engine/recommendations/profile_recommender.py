"""Rule-based profile improvement recommendations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Recommendation:
    priority: int    # 1 (highest) → 5 (lowest)
    category: str
    title: str
    description: str
    action: str = ""
    action_url: str = ""
    impact: str = ""  # 'high' | 'medium' | 'low'

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "action": self.action,
            "action_url": self.action_url,
            "impact": self.impact,
        }


def get_profile_recommendations(profile: dict) -> list[Recommendation]:
    """Return ordered list of profile improvement recommendations."""
    recs: list[Recommendation] = []

    if not profile.get("orcid_id"):
        recs.append(Recommendation(
            priority=1, category="verification", impact="high",
            title="Connect ORCID iD",
            description="ORCID iD is the single most impactful profile enhancement — it verifies your identity and auto-imports publications.",
            action="Connect ORCID",
            action_url="/profile/settings#orcid",
        ))

    if not profile.get("avatar_url"):
        recs.append(Recommendation(
            priority=2, category="visibility", impact="medium",
            title="Add a profile photo",
            description="Profiles with photos receive 3× more collaboration requests.",
            action="Upload photo",
            action_url="/profile/settings#photo",
        ))

    bio = profile.get("bio") or ""
    if len(bio) < 50:
        recs.append(Recommendation(
            priority=2, category="discoverability", impact="high",
            title="Write a biography",
            description="A complete biography (100+ words) significantly improves discoverability in search and collaboration matching.",
            action="Edit biography",
            action_url="/profile/edit",
        ))
    elif len(bio) < 150:
        recs.append(Recommendation(
            priority=4, category="discoverability", impact="low",
            title="Expand your biography",
            description="Consider expanding your bio to 150+ words to describe your research focus and goals.",
            action="Edit biography",
            action_url="/profile/edit",
        ))

    if not profile.get("institution"):
        recs.append(Recommendation(
            priority=2, category="credibility", impact="high",
            title="Add your institution",
            description="Institution affiliation is required for collaboration requests and grant applications.",
            action="Add institution",
            action_url="/profile/edit",
        ))

    keywords = profile.get("research_keywords") or []
    if len(keywords) < 3:
        recs.append(Recommendation(
            priority=3, category="discoverability", impact="high",
            title="Add research keywords",
            description="Keywords drive your discoverability in journal, grant, and collaborator matching algorithms.",
            action="Add keywords",
            action_url="/profile/edit",
        ))
    elif len(keywords) < 6:
        recs.append(Recommendation(
            priority=4, category="discoverability", impact="medium",
            title="Add more research keywords",
            description=f"You have {len(keywords)} keywords; adding 6–10 improves matching accuracy.",
            action="Add keywords",
            action_url="/profile/edit",
        ))

    if not profile.get("research_methods"):
        recs.append(Recommendation(
            priority=3, category="expertise", impact="medium",
            title="Add research methods",
            description="Listing your methodological expertise improves reviewer and collaboration matching.",
            action="Add methods",
            action_url="/profile/edit",
        ))

    if not profile.get("employment"):
        recs.append(Recommendation(
            priority=3, category="credibility", impact="medium",
            title="Add employment history",
            description="Employment history builds credibility and improves institutional ranking.",
            action="Add employment",
            action_url="/profile/edit",
        ))

    if not profile.get("education"):
        recs.append(Recommendation(
            priority=4, category="credibility", impact="low",
            title="Add education history",
            description="Education history completes your academic CV.",
            action="Add education",
            action_url="/profile/edit",
        ))

    if not profile.get("social_links"):
        recs.append(Recommendation(
            priority=5, category="visibility", impact="low",
            title="Add external profile links",
            description="Link to Google Scholar, ResearchGate, LinkedIn, or your personal website.",
            action="Add links",
            action_url="/profile/edit",
        ))

    if profile.get("orcid_id") and not profile.get("openalex_id"):
        recs.append(Recommendation(
            priority=2, category="publications", impact="high",
            title="Import publications from ORCID",
            description="Import your publication record to unlock citation metrics, h-index, and impact scoring.",
            action="Import publications",
            action_url="/profile/publications",
        ))

    return sorted(recs, key=lambda r: r.priority)


def get_quick_wins(profile: dict) -> list[Recommendation]:
    """Return only the top 3 highest-impact recommendations."""
    return get_profile_recommendations(profile)[:3]
