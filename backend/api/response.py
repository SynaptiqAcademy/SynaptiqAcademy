"""Standard response envelope — Phase XXXV.7."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .versioning import API_VERSION_CURRENT


@dataclass
class ApiResponse:
    data:    Any
    ok:      bool   = True
    message: str    = ""
    meta:    dict   = field(default_factory=dict)
    version: str    = API_VERSION_CURRENT

    def to_dict(self) -> dict:
        d: dict = {
            "ok":      self.ok,
            "version": self.version,
            "data":    self.data,
        }
        if self.message:
            d["message"] = self.message
        if self.meta:
            d["meta"] = self.meta
        return d


@dataclass
class PaginatedResponse:
    items:       list
    total:       int
    page:        int | None = None
    per_page:    int | None = None
    cursor_next: str | None = None
    has_more:    bool       = False
    version:     str        = API_VERSION_CURRENT

    def to_dict(self) -> dict:
        d: dict = {
            "ok":      True,
            "version": self.version,
            "data": {
                "items":    self.items,
                "total":    self.total,
                "has_more": self.has_more,
            },
        }
        if self.page is not None:
            d["data"]["page"]     = self.page
            d["data"]["per_page"] = self.per_page
        if self.cursor_next:
            d["data"]["cursor_next"] = self.cursor_next
        return d


def wrap(data: Any, *, message: str = "", meta: dict | None = None) -> dict:
    """Wrap a value in the standard response envelope."""
    return ApiResponse(data=data, message=message, meta=meta or {}).to_dict()


def wrap_error(message: str, code: str = "ERROR", status: int = 400) -> dict:
    """Wrap an error in the standard response envelope."""
    return {
        "ok":      False,
        "version": API_VERSION_CURRENT,
        "error": {
            "code":    code,
            "message": message,
            "status":  status,
        },
    }
