"""
NotificationRepository — bounded-context repository for user notifications.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .base   import BaseRepository
from .cache  import SHORT_TTL
from .specs  import QuerySpec, Specs


class NotificationRepository(BaseRepository):
    collection   = "notifications"
    event_prefix = "notification"
    cache_ttl    = SHORT_TTL  # notifications change frequently

    def _scope_query(self, filters: dict) -> dict:
        # Users always see only their own notifications
        if self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    async def list_notifications(
        self,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        filt: dict = {}
        if unread_only:
            filt["read"] = False
        spec = QuerySpec(filt, sort=[("created_at", -1)], limit=limit)
        return await self.find_many(spec)

    async def mark_read(self, notification_id: str) -> dict:
        return await self.update(notification_id, {"read": True, "read_at": datetime.now(timezone.utc)})

    async def mark_all_read(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self._col.update_many(
            {"user_id": self._ctx.user_id, "read": False},
            {"$set": {"read": True, "read_at": now}},
        )
        await self._cache.invalidate_collection()
        return result.modified_count

    async def unread_count(self) -> int:
        return await self.count(Specs.unread_notifications())

    async def create_notification(
        self,
        user_id: str,
        *,
        title: str,
        message: str,
        type: str = "info",
        link: str | None = None,
        meta: dict | None = None,
    ) -> dict:
        return await self.create({
            "user_id": user_id,
            "title":   title,
            "message": message,
            "type":    type,
            "link":    link,
            "meta":    meta or {},
            "read":    False,
        })
