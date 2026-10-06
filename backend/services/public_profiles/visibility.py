"""Public Passport visibility: what anonymous visitors may see.

Privacy by default. Academic information (publications, impact, teaching,
reputation, timeline) is public unless the member hides it. Grant
applications, projects and collaborations describe unpublished work, so
they are shown only if the member turns them on, and so is the email address
("contact").
"""
from __future__ import annotations

DEFAULT_VISIBILITY = {
    "publications": "public",
    "impact": "public",
    "teaching": "public",
    "reputation": "public",
    "timeline": "public",
    "projects": "private",
    "grants": "private",
    "collaborations": "private",
    "contact": "private",
}
OPT_IN_SECTIONS = ("projects", "grants", "collaborations", "contact")


def section_visibility(settings: dict | None, section: str) -> str:
    return (settings or {}).get(section) or DEFAULT_VISIBILITY.get(section, "private")
