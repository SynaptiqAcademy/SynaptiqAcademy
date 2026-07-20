"""
API Versioning — Phase XXXV.7

Introduces /api/v1/ as a stable, versioned API surface.

Strategy:
  - V1CompatMiddleware rewrites /api/v1/X → /api/X at the ASGI level
  - Existing /api/X routes are unchanged and continue to work
  - Clients using /api/v1/ get the same handlers with version headers added
  - Future /api/v2/ routes will coexist without touching v1

DeprecationRegistry tracks endpoint lifecycle so developer tools and
the Operations Center can surface sunset information.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Current stable API version
API_VERSION_CURRENT = "v1"
API_VERSION_LATEST  = "v1"
API_VERSIONS        = ("v1",)   # grow as new versions land

_REWRITES = {
    f"/api/{v}/": "/api/" for v in API_VERSIONS
}


# ── ASGI middleware ───────────────────────────────────────────────────────────

class V1CompatMiddleware:
    """
    Transparent ASGI middleware that rewrites versioned API paths.

    /api/v1/<rest>  →  /api/<rest>

    The response gains X-Api-Version and X-Api-Deprecated headers.
    No business logic is touched; only the scope path changes.
    """

    def __init__(self, app: Any) -> None:
        self._app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        matched_version: str | None = None

        for ver in API_VERSIONS:
            prefix = f"/api/{ver}/"
            if path.startswith(prefix):
                new_path = "/api/" + path[len(prefix):]
                scope = dict(scope)
                scope["path"]     = new_path
                scope["raw_path"] = new_path.encode()
                matched_version   = ver
                break
            # Handle exact /api/v1 (no trailing slash)
            if path == f"/api/{ver}":
                new_path = "/api"
                scope = dict(scope)
                scope["path"]     = new_path
                scope["raw_path"] = new_path.encode()
                matched_version   = ver
                break

        if matched_version:
            async def send_with_headers(message: dict) -> None:
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-api-version", matched_version.encode()))
                    headers.append((b"x-api-latest",  API_VERSION_LATEST.encode()))
                    message = {**message, "headers": headers}
                await send(message)
            await self._app(scope, receive, send_with_headers)
        else:
            await self._app(scope, receive, send)


# ── Deprecation registry ──────────────────────────────────────────────────────

@dataclass
class DeprecatedEndpoint:
    path:            str
    method:          str
    deprecated_in:   str           # e.g. "v1"
    removal_version: str | None    # e.g. "v3"
    sunset_date:     str | None    # ISO date
    replacement:     str | None    # new path
    migration_guide: str | None
    reason:          str = ""
    registered_at:   str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class DeprecationRegistry:

    def __init__(self) -> None:
        self._entries: dict[str, DeprecatedEndpoint] = {}

    def register(
        self,
        path:            str,
        method:          str = "GET",
        deprecated_in:   str = "v1",
        removal_version: str | None = None,
        sunset_date:     str | None = None,
        replacement:     str | None = None,
        migration_guide: str | None = None,
        reason:          str = "",
    ) -> None:
        key = f"{method.upper()}:{path}"
        self._entries[key] = DeprecatedEndpoint(
            path=path, method=method.upper(),
            deprecated_in=deprecated_in,
            removal_version=removal_version,
            sunset_date=sunset_date,
            replacement=replacement,
            migration_guide=migration_guide,
            reason=reason,
        )
        logger.debug("Deprecated: %s %s → %s", method.upper(), path, replacement)

    def is_deprecated(self, method: str, path: str) -> bool:
        return f"{method.upper()}:{path}" in self._entries

    def get(self, method: str, path: str) -> DeprecatedEndpoint | None:
        return self._entries.get(f"{method.upper()}:{path}")

    def all(self) -> list[dict]:
        return [e.to_dict() for e in self._entries.values()]


# ── Decorators ────────────────────────────────────────────────────────────────

def deprecate(
    path:            str,
    method:          str = "GET",
    deprecated_in:   str = "v1",
    removal_version: str | None = None,
    sunset_date:     str | None = None,
    replacement:     str | None = None,
    migration_guide: str | None = None,
    reason:          str = "",
):
    """Decorator that registers an endpoint as deprecated."""
    def decorator(fn):
        _registry.register(
            path=path, method=method, deprecated_in=deprecated_in,
            removal_version=removal_version, sunset_date=sunset_date,
            replacement=replacement, migration_guide=migration_guide,
            reason=reason,
        )
        fn._deprecated = True
        fn._deprecated_info = {"path": path, "replacement": replacement}
        return fn
    return decorator


# ── Singleton ─────────────────────────────────────────────────────────────────

_registry = DeprecationRegistry()


def get_deprecation_registry() -> DeprecationRegistry:
    return _registry


def get_version_info() -> dict:
    return {
        "current":     API_VERSION_CURRENT,
        "latest":      API_VERSION_LATEST,
        "supported":   list(API_VERSIONS),
        "deprecated":  [],
        "base_urls": {v: f"/api/{v}" for v in API_VERSIONS},
    }
