"""Public, unauthenticated landing-page demo endpoint(s).

No auth dependency anywhere in this file — that's deliberate, it's the
public marketing site. See services/public_demo/research_preview.py for
why this can never become an AI-cost or real-people-exposure surface.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from rate_limit import check_public_demo_rate_limit
from services.public_demo.research_preview import preview_research_themes, _MAX_QUERY_LEN

log = logging.getLogger("synaptiq.public_demo")

router = APIRouter(prefix="/api/public/research-preview", tags=["public-demo"])


class PreviewRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def query_bounds(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Describe what you're researching first.")
        if len(v) > _MAX_QUERY_LEN:
            raise ValueError(f"Please keep this under {_MAX_QUERY_LEN} characters.")
        return v


def _client_ip(request: Request) -> str:
    """Rate-limit key: the trusted client address (services/client_ip.py)."""
    from services.client_ip import client_ip
    return client_ip(request) or "unknown"


@router.post("")
async def research_preview(payload: PreviewRequest, request: Request):
    ip = _client_ip(request)
    check_public_demo_rate_limit(ip)

    # Safe logging (§19): log length + a truncated, non-identifying prefix
    # for abuse monitoring, never the full free-text query verbatim into
    # long-lived logs.
    log.info("public research-preview request: ip=%s len=%d", ip, len(payload.query))

    result = preview_research_themes(payload.query)
    return result
