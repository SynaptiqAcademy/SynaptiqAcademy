"""MessagingRepository — repository for conversations and messages."""
from __future__ import annotations

from .base  import BaseRepository, PermissionError
from .specs import Specs, QuerySpec
from .cache import SHORT_TTL


class ConversationRepository(BaseRepository):
    collection   = "conversations"
    event_prefix = "conversation"
    cache_ttl    = SHORT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["members"] = self._ctx.user_id
        return filters

    async def list_conversations(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = Specs.active().with_sort(("updated_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_conversation(self, conv_id: str) -> dict | None:
        return await self.find_one(doc_id=conv_id)

    async def create_conversation(self, data: dict) -> dict:
        uid = self._ctx.user_id
        data.setdefault("members", [uid])
        return await self.create(data)


class MessageRepository(BaseRepository):
    collection   = "messages"
    event_prefix = "message"
    cache_ttl    = SHORT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        # Messages are scoped via conversation membership — caller adds conv filter
        return filters

    async def list_messages(
        self, conversation_id: str, *, page: int = 1, page_size: int = 50
    ) -> list[dict]:
        spec = QuerySpec(
            {"conversation_id": conversation_id},
            [("created_at", 1)],
        ).page(page, page_size)
        return await self.find_many(spec)

    async def send_message(self, conversation_id: str, data: dict) -> dict:
        data["conversation_id"] = conversation_id
        data.setdefault("sender_id", self._ctx.user_id)
        return await self.create(data)
