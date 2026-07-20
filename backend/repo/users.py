"""
UserRepository — bounded-context repository for user accounts.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from .base             import BaseRepository, NotFoundError, PermissionError, _serialize
from .cache            import LONG_TTL
from .specs            import QuerySpec, Specs


class UserRepository(BaseRepository):
    collection   = "users"
    event_prefix = "user"
    cache_ttl    = LONG_TTL  # user profiles change infrequently

    # ── Scoping: users can read their own; admins can read all ────────────────

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        # Researchers can only see their own profile through this repo
        # (public profile reads go through a separate public endpoint, not here)
        filters["_id"] = ObjectId(self._ctx.user_id)
        return filters

    def _can_read(self, doc: dict) -> bool:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return True
        return str(doc.get("_id") or doc.get("id", "")) == self._ctx.user_id

    def _can_write(self, doc: dict) -> bool:
        if self._ctx.is_admin:
            return True
        return str(doc.get("_id") or doc.get("id", "")) == self._ctx.user_id

    # ── Redaction ─────────────────────────────────────────────────────────────

    @staticmethod
    def _redact(doc: dict | None) -> dict | None:
        """Remove sensitive fields before returning to caller."""
        if not doc:
            return None
        out = dict(doc)
        for field in ("password", "hashed_password", "totp_secret", "backup_codes", "token"):
            out.pop(field, None)
        return out

    # ── Named methods ─────────────────────────────────────────────────────────

    async def get_me(self) -> dict | None:
        doc = await self.find_one(doc_id=self._ctx.user_id)
        return self._redact(doc)

    async def get_by_id(self, user_id: str) -> dict | None:
        doc = await self.find_one(doc_id=user_id)
        return self._redact(doc)

    async def get_by_email(self, email: str) -> dict | None:
        filt = self._scope_query({"email": email.lower().strip(), "deleted_at": None})
        doc  = await self._col.find_one(filt)
        return self._redact(_serialize(doc))

    async def update_profile(self, user_id: str, updates: dict) -> dict:
        allowed = {
            "name", "bio", "title", "institution", "department",
            "research_interests", "expertise_areas", "website",
            "orcid_id", "google_scholar_id", "avatar_url", "preferences",
            "notification_settings", "privacy_settings",
        }
        safe = {k: v for k, v in updates.items() if k in allowed}
        doc  = await self.update(user_id, safe)
        return self._redact(doc)

    async def list_institution_members(
        self,
        institution: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict]:
        if not self._ctx.is_admin:
            raise PermissionError("Only admins can list institution members")
        spec = Specs.institution_members(institution).page(page, page_size)
        docs = await self.find_many(spec)
        return [self._redact(d) for d in docs]

    async def search_users(self, query: str, *, limit: int = 20) -> list[dict]:
        if not self._ctx.is_admin:
            raise PermissionError("User search requires admin role")
        filt = {
            "$or": [
                {"name":  {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}},
            ],
            "deleted_at": None,
        }
        cursor = self._col.find(filt).limit(limit)
        docs   = await cursor.to_list(length=limit)
        return [self._redact(_serialize(d)) for d in docs]

    async def admin_list(self, page: int = 1, page_size: int = 50) -> list[dict]:
        if not self._ctx.is_admin:
            raise PermissionError("Admin required")
        spec = Specs.active_users().with_sort(("created_at", -1)).page(page, page_size)
        docs = await self.find_many(spec, bypass_cache=True)
        return [self._redact(d) for d in docs]
