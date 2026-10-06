"""One-time, versioned migration of legacy public-Passport visibility.

Why: until 6 October 2026 every public page was created with all sections
public, and the settings panel saved every toggle together, so a stored
"public" for contact, grants, projects or collaborations does not show that
the member chose to publish that section.

Evidence of an explicit choice:
- ``visibility_explicit.<section>``: written by PUT /api/profiles/me/visibility
  only for the sections whose value actually changed in that request (from
  this release on). Nothing earlier records a per-section decision: no audit
  event, and the data-access trail stores only "public_profiles was updated".
- ``contact_opt_in_at`` (from 4a6dee4) is NOT trusted: an open panel loaded
  before that release could resend a stale "public" value.

Migration ``public_visibility_v2``: for each sensitive section stored as
"public" without ``visibility_explicit.<section>``, set it to "private".
The previous values are kept on the document (``visibility_migrations.v2``)
so the change is auditable and reversible. A summary is written to
``migrations``. It runs at most once (global marker + per-document marker)
and never touches a section with explicit evidence, so later choices survive.

A project's own ``visibility: "public"`` is chosen per project by its owner
(default "team"); it is left alone. Public projects appear on the public page
only if the member also turns the projects section on.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("synaptiq.visibility_migration")

MIGRATION_ID = "public_visibility_v2"
SENSITIVE = ("contact", "grants", "projects", "collaborations")

# Enabled after the production dry run (6 Oct 2026): 4 public pages; 2 with
# grants, projects and collaborations public, 0 with explicit evidence;
# email public on 0.
ENABLED = True


def _ambiguous(section: str) -> dict:
    return {f"visibility_settings.{section}": "public", f"visibility_explicit.{section}": {"$exists": False}}


async def report(db) -> dict:
    """Aggregate counts only: no identities."""
    pp = db.public_profiles
    out = {"public_profiles": await pp.count_documents({})}
    for s in SENSITIVE:
        out[f"{s}_public"] = await pp.count_documents({f"visibility_settings.{s}": "public"})
        out[f"{s}_ambiguous"] = await pp.count_documents(_ambiguous(s))
        out[f"{s}_explicit"] = await pp.count_documents({f"visibility_explicit.{s}": {"$exists": True}})
    out["profiles_with_any_ambiguous"] = await pp.count_documents({"$or": [_ambiguous(s) for s in SENSITIVE]})
    out["contact_opt_in_at_untrusted"] = await pp.count_documents({"contact_opt_in_at": {"$exists": True}})
    out["projects_marked_public"] = await db.projects.count_documents({"visibility": "public"})
    out["already_migrated_docs"] = await pp.count_documents({"visibility_migrations.v2": {"$exists": True}})
    return out


async def migrate(db) -> dict:
    """Apply once. Returns aggregate counts."""
    if await db.migrations.find_one({"_id": MIGRATION_ID}):
        return {"skipped": "already applied"}
    now = datetime.now(timezone.utc).isoformat()
    # Claim the migration atomically: with several workers starting at once,
    # exactly one inserts this record and applies it.
    try:
        await db.migrations.insert_one({"_id": MIGRATION_ID, "status": "running", "started_at": now})
    except Exception:
        return {"skipped": "already claimed"}
    before = await report(db)
    changed_docs, per_section = 0, {s: 0 for s in SENSITIVE}
    flt = {"visibility_migrations.v2": {"$exists": False}, "$or": [_ambiguous(s) for s in SENSITIVE]}
    async for d in db.public_profiles.find(flt, {"visibility_settings": 1, "visibility_explicit": 1}):
        vs = d.get("visibility_settings") or {}
        explicit = d.get("visibility_explicit") or {}
        sections = [s for s in SENSITIVE if vs.get(s) == "public" and s not in explicit]
        if not sections:
            continue
        sets = {f"visibility_settings.{s}": "private" for s in sections}
        sets["visibility_migrations.v2"] = {"at": now, "sections": sections,
                                             "previous": {s: vs.get(s) for s in sections}}
        res = await db.public_profiles.update_one({"_id": d["_id"], "visibility_migrations.v2": {"$exists": False}},
                                                  {"$set": sets})
        if res.modified_count:
            changed_docs += 1
            for s in sections:
                per_section[s] += 1
    summary = {"profiles_changed": changed_docs, **{f"{s}_set_private": n for s, n in per_section.items()}}
    await db.migrations.update_one({"_id": MIGRATION_ID}, {"$set": {
        "status": "done", "applied_at": now, "before": before, "summary": summary}}, upsert=True)
    return summary


async def run_at_startup(db) -> dict:
    """Dry run (log counts) until ENABLED; then apply once."""
    existing = await db.migrations.find_one({"_id": MIGRATION_ID})
    if existing:
        return {"status": existing.get("status", "done")}
    counts = await report(db)
    logger.info("visibility_migration %s dry_run %s", MIGRATION_ID, counts)
    if not ENABLED:
        return {"status": "dry_run", **counts}
    summary = await migrate(db)
    logger.info("visibility_migration %s applied %s", MIGRATION_ID, summary)
    return {"status": "applied", **summary}
