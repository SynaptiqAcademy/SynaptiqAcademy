"""TeachingRepository — bounded-context repository for teaching hub operations."""
from __future__ import annotations

from .base  import BaseRepository, NotFoundError, PermissionError
from .specs import Specs
from .cache import DEFAULT_TTL


class TeachingWorkspaceRepository(BaseRepository):
    collection   = "teaching_workspaces"
    event_prefix = "teaching_workspace"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        uid = self._ctx.user_id
        filters["$or"] = [
            {"user_id": uid},
            {"owner_id": uid},
            {"members": uid},
        ]
        return filters

    async def list_workspaces(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = Specs.active().with_sort(("updated_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_workspace(self, ws_id: str) -> dict | None:
        return await self.find_one(doc_id=ws_id)

    async def create_workspace(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)

    async def update_workspace(self, ws_id: str, updates: dict) -> dict:
        return await self.update(ws_id, updates)

    async def delete_workspace(self, ws_id: str) -> dict:
        return await self.delete(ws_id)


class TeachingLessonRepository(BaseRepository):
    collection   = "teaching_lessons"
    event_prefix = "teaching_lesson"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    async def list_lessons(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = Specs.active().with_sort(("created_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_lesson(self, lesson_id: str) -> dict | None:
        return await self.find_one(doc_id=lesson_id)

    async def create_lesson(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)

    async def update_lesson(self, lesson_id: str, updates: dict) -> dict:
        return await self.update(lesson_id, updates)

    async def delete_lesson(self, lesson_id: str) -> dict:
        return await self.delete(lesson_id)


class TeachingAssessmentRepository(BaseRepository):
    collection   = "teaching_assessments"
    event_prefix = "teaching_assessment"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    async def list_assessments(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = Specs.active().with_sort(("created_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_assessment(self, assessment_id: str) -> dict | None:
        return await self.find_one(doc_id=assessment_id)

    async def create_assessment(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)
