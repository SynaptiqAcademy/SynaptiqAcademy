"""Endpoint contract registry — Phase XXXV.7.

The @contract() decorator attaches a typed contract to a route function.
ContractRegistry tracks all contracts for the /api/platform/contracts endpoint.
"""
from __future__ import annotations

import functools
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class EndpointContract:
    path:           str
    method:         str
    summary:        str          = ""
    version:        str          = "v1"
    stability:      str          = "stable"   # stable | beta | alpha | deprecated
    breaking_after: str | None   = None       # ISO date after which removing this is OK
    auth_required:  bool         = True
    scopes:         list[str]    = field(default_factory=list)
    rate_limit:     int | None   = None       # requests/minute
    tags:           list[str]    = field(default_factory=list)
    registered_at:  str          = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "path":           self.path,
            "method":         self.method,
            "summary":        self.summary,
            "version":        self.version,
            "stability":      self.stability,
            "breaking_after": self.breaking_after,
            "auth_required":  self.auth_required,
            "scopes":         self.scopes,
            "rate_limit":     self.rate_limit,
            "tags":           self.tags,
            "registered_at":  self.registered_at,
        }


class ContractRegistry:

    def __init__(self) -> None:
        self._contracts: dict[str, EndpointContract] = {}

    def register(self, c: EndpointContract) -> None:
        key = f"{c.method.upper()}:{c.path}"
        self._contracts[key] = c

    def get(self, method: str, path: str) -> EndpointContract | None:
        return self._contracts.get(f"{method.upper()}:{path}")

    def all(self) -> list[dict]:
        return [c.to_dict() for c in self._contracts.values()]

    def by_stability(self, stability: str) -> list[dict]:
        return [c.to_dict() for c in self._contracts.values() if c.stability == stability]

    def __len__(self) -> int:
        return len(self._contracts)


# ── Singleton ─────────────────────────────────────────────────────────────────

_registry = ContractRegistry()


def get_contract_registry() -> ContractRegistry:
    return _registry


# ── Decorator ─────────────────────────────────────────────────────────────────

def contract(
    path:           str,
    method:         str       = "GET",
    summary:        str       = "",
    version:        str       = "v1",
    stability:      str       = "stable",
    breaking_after: str | None = None,
    auth_required:  bool      = True,
    scopes:         list[str] | None = None,
    rate_limit:     int | None = None,
    tags:           list[str] | None = None,
) -> Callable:
    """Decorator that registers an endpoint contract and attaches it to the function."""
    def decorator(fn: Callable) -> Callable:
        c = EndpointContract(
            path           = path,
            method         = method.upper(),
            summary        = summary or (fn.__doc__ or "").strip().splitlines()[0] if (fn.__doc__ or "").strip() else "",
            version        = version,
            stability      = stability,
            breaking_after = breaking_after,
            auth_required  = auth_required,
            scopes         = scopes or [],
            rate_limit     = rate_limit,
            tags           = tags or [],
        )
        _registry.register(c)
        fn._contract = c

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await fn(*args, **kwargs)

        wrapper._contract = c  # type: ignore[attr-defined]
        return wrapper
    return decorator
