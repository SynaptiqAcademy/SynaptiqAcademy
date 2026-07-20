"""Cursor and offset pagination utilities — Phase XXXV.7."""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from fastapi import Query


# ── Params ────────────────────────────────────────────────────────────────────

@dataclass
class PaginationParams:
    page:    int = 1
    limit:   int = 20
    cursor:  str | None = None

    def offset(self) -> int:
        return (self.page - 1) * self.limit

    @classmethod
    def from_query(
        cls,
        page:   int = Query(1, ge=1, le=10_000),
        limit:  int = Query(20, ge=1, le=200),
        cursor: str | None = Query(None),
    ) -> "PaginationParams":
        return cls(page=page, limit=limit, cursor=cursor)


@dataclass
class PageResult:
    items:       list
    total:       int
    page:        int
    per_page:    int
    has_more:    bool
    cursor_next: str | None = None

    def to_dict(self) -> dict:
        d = {
            "items":    self.items,
            "total":    self.total,
            "page":     self.page,
            "per_page": self.per_page,
            "has_more": self.has_more,
        }
        if self.cursor_next:
            d["cursor_next"] = self.cursor_next
        return d


# ── Cursor encode / decode ────────────────────────────────────────────────────

def encode_cursor(data: dict) -> str:
    payload = json.dumps(data, separators=(",", ":"), default=str)
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> dict:
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        return json.loads(payload)
    except Exception:
        return {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def paginate_list(items: list, params: PaginationParams) -> PageResult:
    """Paginate an in-memory list using offset pagination."""
    total    = len(items)
    start    = params.offset()
    page_items = items[start : start + params.limit]
    has_more = (start + len(page_items)) < total
    return PageResult(
        items    = page_items,
        total    = total,
        page     = params.page,
        per_page = params.limit,
        has_more = has_more,
    )


async def paginate_query(
    collection: Any,
    query_filter: dict,
    params: PaginationParams,
    sort_field:  str = "_id",
    sort_asc:    bool = True,
    projection:  dict | None = None,
) -> PageResult:
    """Paginate a Motor collection query using offset pagination."""
    from motor.motor_asyncio import AsyncIOMotorCollection  # type hint only
    direction = 1 if sort_asc else -1
    total     = await collection.count_documents(query_filter)
    cursor    = (
        collection.find(query_filter, projection or {})
        .sort(sort_field, direction)
        .skip(params.offset())
        .limit(params.limit)
    )
    items = []
    async for doc in cursor:
        doc.pop("_id", None)
        items.append(doc)

    has_more = (params.offset() + len(items)) < total
    return PageResult(
        items    = items,
        total    = total,
        page     = params.page,
        per_page = params.limit,
        has_more = has_more,
    )
