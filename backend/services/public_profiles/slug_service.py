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
    """Return user_id for a given slug, or None."""
    doc = await db.public_profiles.find_one({"slug": slug}, {"user_id": 1})
    return doc["user_id"] if doc else None
