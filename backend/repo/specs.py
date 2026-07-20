"""
Query Specifications — reusable, composable filter objects.

Instead of repeating MongoDB filter dicts throughout the codebase, every
commonly-used query is expressed as a named Spec. Specs can be combined
with and_() / or_() and are always passed to repository methods, never
constructed inline in routers.

Usage:
    missions = await repo.find_many(
        Specs.active().and_(Specs.by_status("running"))
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class QuerySpec:
    """Composable query specification: filter + sort + projection + pagination hint."""
    filters:    dict             = field(default_factory=dict)
    sort:       list[tuple]      = field(default_factory=list)   # [(field, direction), ...]
    projection: dict | None      = None
    limit:      int              = 20
    skip:       int              = 0

    def and_(self, other: "QuerySpec") -> "QuerySpec":
        """Combine two specs with AND logic."""
        merged_filters = {**self.filters}
        for k, v in other.filters.items():
            if k in merged_filters:
                # Both have the same key — wrap in $and
                return QuerySpec(
                    filters={"$and": [self.filters, other.filters]},
                    sort=other.sort or self.sort,
                    projection=other.projection or self.projection,
                    limit=other.limit if other.limit != 20 else self.limit,
                    skip=other.skip or self.skip,
                )
            merged_filters[k] = v
        return QuerySpec(
            filters=merged_filters,
            sort=other.sort or self.sort,
            projection=other.projection or self.projection,
            limit=other.limit if other.limit != 20 else self.limit,
            skip=other.skip or self.skip,
        )

    def or_(self, other: "QuerySpec") -> "QuerySpec":
        """Combine two specs with OR logic."""
        return QuerySpec(
            filters={"$or": [self.filters, other.filters]},
            sort=other.sort or self.sort,
            projection=other.projection or self.projection,
        )

    def with_limit(self, limit: int) -> "QuerySpec":
        return QuerySpec(self.filters, self.sort, self.projection, limit, self.skip)

    def with_skip(self, skip: int) -> "QuerySpec":
        return QuerySpec(self.filters, self.sort, self.projection, self.limit, skip)

    def with_sort(self, *sort_pairs: tuple) -> "QuerySpec":
        return QuerySpec(self.filters, list(sort_pairs), self.projection, self.limit, self.skip)

    def page(self, page: int, page_size: int = 20) -> "QuerySpec":
        return QuerySpec(
            self.filters, self.sort, self.projection,
            page_size, (page - 1) * page_size,
        )


# ── Spec factory ───────────────────────────────────────────────────────────────

class Specs:
    """Named specifications for common query patterns."""

    # ── Generic ───────────────────────────────────────────────────────────────

    @staticmethod
    def active() -> QuerySpec:
        """Non-deleted documents."""
        return QuerySpec({"deleted_at": None})

    @staticmethod
    def all_including_deleted() -> QuerySpec:
        return QuerySpec({})

    @staticmethod
    def deleted() -> QuerySpec:
        return QuerySpec({"deleted_at": {"$ne": None}})

    @staticmethod
    def by_id(doc_id: str) -> QuerySpec:
        from bson import ObjectId
        return QuerySpec({"_id": ObjectId(doc_id)})

    @staticmethod
    def by_user(user_id: str) -> QuerySpec:
        return QuerySpec({"user_id": user_id})

    @staticmethod
    def by_status(status: str | list) -> QuerySpec:
        if isinstance(status, list):
            return QuerySpec({"status": {"$in": status}})
        return QuerySpec({"status": status})

    @staticmethod
    def by_institution(institution: str) -> QuerySpec:
        return QuerySpec({"institution": institution})

    @staticmethod
    def created_after(dt: datetime) -> QuerySpec:
        return QuerySpec({"created_at": {"$gt": dt}})

    @staticmethod
    def created_before(dt: datetime) -> QuerySpec:
        return QuerySpec({"created_at": {"$lt": dt}})

    @staticmethod
    def recent(limit: int = 10) -> QuerySpec:
        return QuerySpec({}, sort=[("created_at", -1)], limit=limit)

    # ── Missions ──────────────────────────────────────────────────────────────

    @staticmethod
    def running_missions() -> QuerySpec:
        return QuerySpec({"status": {"$in": ["running", "queued", "retrying"]}})

    @staticmethod
    def pending_approval() -> QuerySpec:
        return QuerySpec({"status": "awaiting_human"})

    @staticmethod
    def completed_missions() -> QuerySpec:
        return QuerySpec({"status": "completed"})

    @staticmethod
    def stale_missions(expiry_seconds: int = 60) -> QuerySpec:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=expiry_seconds)
        return QuerySpec({
            "status": {"$in": ["running", "retrying"]},
            "$or": [{"heartbeat": {"$lt": cutoff}}, {"heartbeat": None}],
        })

    # ── Publications ──────────────────────────────────────────────────────────

    @staticmethod
    def published_papers() -> QuerySpec:
        return QuerySpec({"status": "published"})

    @staticmethod
    def draft_papers() -> QuerySpec:
        return QuerySpec({"status": {"$in": ["draft", "in_review"]}})

    # ── Grants ────────────────────────────────────────────────────────────────

    @staticmethod
    def active_grants() -> QuerySpec:
        return QuerySpec({"status": {"$in": ["open", "draft"]}})

    @staticmethod
    def due_grants(before: datetime | None = None) -> QuerySpec:
        deadline = before or datetime.now(timezone.utc)
        return QuerySpec({"deadline": {"$lte": deadline}, "status": "open"})

    # ── Users ─────────────────────────────────────────────────────────────────

    @staticmethod
    def active_users() -> QuerySpec:
        return QuerySpec({"status": "active", "deleted_at": None})

    @staticmethod
    def by_role(role: str) -> QuerySpec:
        return QuerySpec({"role": role})

    @staticmethod
    def institution_members(institution: str) -> QuerySpec:
        return QuerySpec({"institution": institution, "status": "active"})

    @staticmethod
    def high_reputation(min_score: int = 80) -> QuerySpec:
        return QuerySpec({"reputation_score": {"$gte": min_score}})

    # ── Notifications ─────────────────────────────────────────────────────────

    @staticmethod
    def unread_notifications() -> QuerySpec:
        return QuerySpec({"read": False})

    # ── Schedules ─────────────────────────────────────────────────────────────

    @staticmethod
    def due_schedules() -> QuerySpec:
        now = datetime.now(timezone.utc)
        return QuerySpec({"active": True, "next_run_at": {"$lte": now}})
