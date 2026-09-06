import re
from datetime import datetime, timezone
from bson import ObjectId


def generate_slug_from_name(full_name: str) -> str:
    """Convert 'Jane Smith' → 'jane-smith'"""
    slug = full_name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "researcher"


async def ensure_unique_slug(base_slug: str, exclude_user_id: str, db) -> str:
    """Try base_slug, then base_slug-2, base_slug-3, ... until unique"""
    slug = base_slug
    counter = 2
    while True:
        existing = await db.public_profiles.find_one(
            {"slug": slug, "user_id": {"$ne": exclude_user_id}}
        )
        if not existing:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


async def get_or_create_profile(user_id: str, db) -> dict:
    """Get existing public_profiles doc or create one with auto-slug."""
    existing = await db.public_profiles.find_one({"user_id": user_id})
    if existing:
        existing["_id"] = str(existing["_id"])
        return existing
    # Create
    user = await db.users.find_one({"_id": ObjectId(user_id)}, {"full_name": 1})
    full_name = (user or {}).get("full_name", "researcher")
    base_slug = generate_slug_from_name(full_name)
    slug = await ensure_unique_slug(base_slug, user_id, db)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "user_id": user_id,
        "slug": slug,
        "visibility_settings": {
            "publications": "public",
            "impact": "public",
            "projects": "public",
            "grants": "public",
            "collaborations": "public",
            "teaching": "public",
            "reputation": "public",
            "timeline": "public",
            "contact": "public",
        },
        "view_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.public_profiles.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def claim_custom_slug(user_id: str, desired_slug: str, db) -> dict:
    """Set a custom slug, validating uniqueness and format."""
    cleaned = generate_slug_from_name(desired_slug)
    if len(cleaned) < 3:
        raise ValueError("Slug must be at least 3 characters")
    if len(cleaned) > 60:
        raise ValueError("Slug must be 60 characters or fewer")
    # Check uniqueness
    existing = await db.public_profiles.find_one(
        {"slug": cleaned, "user_id": {"$ne": user_id}}
    )
    if existing:
        raise ValueError(f"Slug '{cleaned}' is already taken")
    now = datetime.now(timezone.utc).isoformat()
    await db.public_profiles.update_one(
        {"user_id": user_id},
        {"$set": {"slug": cleaned, "updated_at": now}},
        upsert=True,
    )
    return {"slug": cleaned}


async def get_user_id_by_slug(slug: str, db) -> str | None:
    """Return user_id for a given slug, or None.

    Every "view profile" link across the app (Researchers, Discover,
    Leaderboards, Reviewer Marketplace card footers) is built client-side
    from generate_slug_from_name-equivalent logic before a public_profiles
    document necessarily exists — that document is normally only created
    on-demand, the first time a user visits their OWN profile (GET
    /profiles/me) or explicitly claims a custom slug. A user who has never
    done either (which, before this fix, was effectively everyone) has no
    resolvable slug, so every "View Profile" click 404s.

    Self-heal here instead of requiring a backfill migration: if no
    public_profiles doc matches, look for a real user whose name produces
    this same slug and auto-provision their default public profile.
    """
    doc = await db.public_profiles.find_one({"slug": slug}, {"user_id": 1})
    if doc:
        return doc["user_id"]

    candidates = await db.users.find(
        {"is_demo": {"$ne": True}}, {"full_name": 1},
    ).to_list(5000)
    for cand in candidates:
        if generate_slug_from_name(cand.get("full_name", "")) == slug:
            user_id = str(cand["_id"])
            await get_or_create_profile(user_id, db)
            return user_id
    return None
