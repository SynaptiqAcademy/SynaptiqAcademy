"""SYNAPTIQ Discovery Suite — shared HTTP client.

A single asyncio-shared httpx.AsyncClient with:
  - polite User-Agent + From header (recommended by OpenAlex / Crossref)
  - sensible timeout (20s read, 5s connect)
  - HTTP/2 disabled (compatibility with strict proxies)
  - exponential backoff retry on 429 / 5xx / network errors (max 3 attempts)

Use `await get_http().get(url, params=...)` from any provider. Never instantiate
your own httpx client elsewhere — that would defeat the connection pool and
make rate-limit accounting impossible.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import Optional

import httpx

logger = logging.getLogger("synaptiq.discovery.http")

_client: Optional[httpx.AsyncClient] = None
_lock = asyncio.Lock()

CONTACT_EMAIL = os.environ.get("DISCOVERY_CONTACT_EMAIL", "admin@synaptiq.academy")
USER_AGENT = f"SYNAPTIQ/0.5 (https://synaptiq.academy; mailto:{CONTACT_EMAIL})"


def _build_client() -> httpx.AsyncClient:
    headers = {
        "User-Agent": USER_AGENT,
        "From": CONTACT_EMAIL,
        "Accept": "application/json,application/xml;q=0.5,*/*;q=0.1",
    }
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=10.0)
    limits = httpx.Limits(max_connections=32, max_keepalive_connections=16)
    return httpx.AsyncClient(headers=headers, timeout=timeout, limits=limits, follow_redirects=True)


async def get_http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                _client = _build_client()
    return _client


async def close_http() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def fetch_json(url: str, *, params: dict | None = None, max_attempts: int = 3) -> dict | list | None:
    """GET → JSON with exponential backoff. Returns None on terminal failure."""
    client = await get_http()
    delay = 0.6
    last_err: Optional[str] = None
    for attempt in range(1, max_attempts + 1):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 429:
                # honour Retry-After when present
                wait = float(r.headers.get("Retry-After", delay))
                await asyncio.sleep(min(wait, 8.0))
                continue
            if r.status_code >= 500:
                last_err = f"HTTP {r.status_code}"
                await asyncio.sleep(delay + random.random() * 0.3)
                delay *= 2
                continue
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            last_err = str(e)
            if attempt < max_attempts:
                await asyncio.sleep(delay + random.random() * 0.3)
                delay *= 2
            continue
    logger.warning("[discovery:http] giving up url=%s err=%s", url, last_err)
    return None


async def fetch_text(url: str, *, params: dict | None = None, max_attempts: int = 3) -> Optional[str]:
    client = await get_http()
    delay = 0.6
    for attempt in range(1, max_attempts + 1):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 429:
                await asyncio.sleep(min(float(r.headers.get("Retry-After", delay)), 8.0))
                continue
            if r.status_code >= 500:
                await asyncio.sleep(delay); delay *= 2; continue
            r.raise_for_status()
            return r.text
        except httpx.HTTPError:
            if attempt < max_attempts:
                await asyncio.sleep(delay); delay *= 2
    return None
