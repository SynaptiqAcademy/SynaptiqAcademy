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


async def apply_defaults_to_untouched(db) -> int:
    """Public pages created before these defaults made every section public.
    Where the member never changed the settings (updated_at == created_at),
    apply the opt-in defaults. Pages a member has configured are left alone."""
    n = 0
    async for d in db.public_profiles.find({}, {"visibility_settings": 1, "created_at": 1, "updated_at": 1}):
        if d.get("updated_at") and d.get("created_at") and d["updated_at"] != d["created_at"]:
            continue
        vs = dict(d.get("visibility_settings") or {})
        changed = {k: "private" for k in OPT_IN_SECTIONS if vs.get(k, "public") != "private"}
        if changed:
            vs.update(changed)
            await db.public_profiles.update_one({"_id": d["_id"]}, {"$set": {"visibility_settings": vs}})
            n += 1
    return n
