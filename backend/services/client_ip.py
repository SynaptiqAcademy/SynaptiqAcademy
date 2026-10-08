"""The client's IP address, from headers only a trusted proxy can set.

The leftmost X-Forwarded-For entry is whatever the client sent, so it is never
used: rate limits, IP blocks, audit logs and device records keyed on it could
be bypassed or forged by sending a different value on every request.

Resolution order (configurable, see CLIENT_IP_SOURCE):
  1. X-Real-IP — Railway's edge sets it to the client's remote address
     (docs.railway.com → Networking → Specs & Limits).
  2. The X-Forwarded-For entry appended by the nearest trusted proxy: the
     TRUSTED_PROXY_HOPS-th entry from the right (default 1).
  3. The TCP peer address (local development, tests, no proxy).

Env:
  CLIENT_IP_SOURCE    "x-real-ip" (default) — X-Real-IP, then XFF, then peer
                      "xff"                 — XFF from the right, then peer
                      "peer"                — ignore forwarding headers (no proxy)
  TRUSTED_PROXY_HOPS  number of trusted proxies that append to XFF (default 1)

After a deploy, GET /api/admin/security/client-ip (super admin) shows what the backend
resolved and which forwarding headers arrived, so a spoofed header can be
checked against the real address.
"""
from __future__ import annotations

import ipaddress
import os

from starlette.requests import HTTPConnection


def _valid(ip: str) -> str:
    ip = (ip or "").strip()
    if not ip:
        return ""
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        return ""


def _hops() -> int:
    try:
        return max(0, int(os.environ.get("TRUSTED_PROXY_HOPS", "1")))
    except ValueError:
        return 1


def _source() -> str:
    s = os.environ.get("CLIENT_IP_SOURCE", "x-real-ip").strip().lower()
    return s if s in ("x-real-ip", "xff", "peer") else "x-real-ip"


def _from_xff(header: str, hops: int) -> str:
    parts = [p.strip() for p in (header or "").split(",") if p.strip()]
    if hops <= 0 or len(parts) < hops:
        return ""
    return _valid(parts[-hops])


def client_ip(request: HTTPConnection) -> str:
    """Best trustworthy client address; "" when nothing usable is present."""
    source = _source()
    headers = request.headers
    if source == "x-real-ip":
        ip = _valid(headers.get("x-real-ip", ""))
        if ip:
            return ip
    if source in ("x-real-ip", "xff"):
        ip = _from_xff(headers.get("x-forwarded-for", ""), _hops())
        if ip:
            return ip
    return request.client.host if request.client else ""


def describe(request: HTTPConnection) -> dict:
    """Diagnostics for the admin check (addresses only, no other headers)."""
    return {
        "resolved_ip": client_ip(request),
        "source": _source(),
        "trusted_proxy_hops": _hops(),
        "x_real_ip": request.headers.get("x-real-ip"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "peer": request.client.host if request.client else None,
    }
