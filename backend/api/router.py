"""Enterprise API Platform router — Phase XXXV.7.

All endpoints are at /api/platform/* and are super-admin only.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, JSONResponse

from db import get_db
from services.permissions import require_super_admin

from .response import wrap
from .versioning import get_version_info, get_deprecation_registry
from .contracts import get_contract_registry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/platform",
    tags=["api-platform"],
    dependencies=[Depends(require_super_admin)],
)


# ── Version info ──────────────────────────────────────────────────────────────

@router.get("/version")
async def get_version():
    """Return current API version and supported versions."""
    return wrap(get_version_info())


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.get("/keys")
async def list_keys(
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Any = Depends(get_db),
):
    """List all API keys (admin view)."""
    from .keys import get_key_manager
    mgr  = get_key_manager()
    docs = await mgr.admin_list(limit=limit, skip=skip)
    return wrap({"keys": docs, "count": len(docs)})


@router.post("/keys")
async def create_key(body: dict, db: Any = Depends(get_db)):
    """Create a new API key."""
    from .keys import get_key_manager
    mgr = get_key_manager()
    raw_key, record = await mgr.create(
        name         = body.get("name", "API Key"),
        user_id      = body.get("user_id", "admin"),
        scopes       = body.get("scopes", ["read"]),
        expires_at   = body.get("expires_at"),
        workspace_id = body.get("workspace_id"),
        metadata     = body.get("metadata", {}),
    )
    return wrap({**record, "key": raw_key}, message="Key created — save the raw key, it will not be shown again")


@router.get("/keys/{key_id}")
async def get_key(key_id: str, db: Any = Depends(get_db)):
    """Get API key details."""
    from .keys import get_key_manager
    mgr = get_key_manager()
    rec = await mgr.get(key_id)
    if not rec:
        return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})
    return wrap(rec)


@router.delete("/keys/{key_id}")
async def revoke_key(key_id: str, body: dict = {}, db: Any = Depends(get_db)):
    """Revoke an API key."""
    from .keys import get_key_manager
    mgr = get_key_manager()
    ok  = await mgr.revoke(key_id, user_id=body.get("user_id", "admin"))
    return wrap({"revoked": ok})


@router.post("/keys/{key_id}/rotate")
async def rotate_key(key_id: str, body: dict = {}, db: Any = Depends(get_db)):
    """Rotate an API key (revoke + new)."""
    from .keys import get_key_manager
    mgr = get_key_manager()
    raw_key, record = await mgr.rotate(key_id, user_id=body.get("user_id", "admin"))
    if not record:
        return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})
    return wrap({**record, "key": raw_key}, message="Key rotated")


# ── Webhooks ──────────────────────────────────────────────────────────────────

@router.get("/webhooks")
async def list_webhooks(user_id: str = Query(...), db: Any = Depends(get_db)):
    """List webhooks for a user."""
    from .webhooks import get_webhook_engine
    engine = get_webhook_engine()
    hooks  = await engine.list_for_user(user_id)
    return wrap({"webhooks": hooks})


@router.post("/webhooks")
async def create_webhook(body: dict, db: Any = Depends(get_db)):
    """Register a new webhook."""
    from .webhooks import get_webhook_engine
    engine = get_webhook_engine()
    result = await engine.create(
        user_id  = body.get("user_id", "admin"),
        url      = body["url"],
        events   = body.get("events", []),
        name     = body.get("name", ""),
        metadata = body.get("metadata", {}),
    )
    return wrap(result, message="Webhook created — save the secret, it will not be shown again")


@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, body: dict, db: Any = Depends(get_db)):
    """Update a webhook's URL, events, or active status."""
    from .webhooks import get_webhook_engine
    engine = get_webhook_engine()
    ok     = await engine.update(webhook_id, user_id=body.get("user_id", "admin"), **body)
    return wrap({"updated": ok})


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, user_id: str = Query(...), db: Any = Depends(get_db)):
    """Delete a webhook."""
    from .webhooks import get_webhook_engine
    engine = get_webhook_engine()
    ok     = await engine.delete(webhook_id, user_id)
    return wrap({"deleted": ok})


@router.get("/webhooks/{webhook_id}/deliveries")
async def webhook_deliveries(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Any = Depends(get_db),
):
    """List delivery attempts for a webhook."""
    from .webhooks import get_webhook_engine
    engine    = get_webhook_engine()
    deliveries = await engine.deliveries(webhook_id, limit=limit)
    return wrap({"deliveries": deliveries})


# ── SDK download ──────────────────────────────────────────────────────────────

@router.get("/sdk/python", response_class=PlainTextResponse)
async def download_python_sdk():
    """Download the auto-generated Python SDK."""
    from fastapi.openapi.utils import get_openapi  # noqa: F401
    # We generate from a minimal spec to avoid importing the whole app
    from .sdk_gen import generate_python_sdk
    spec = {"info": {"title": "Synaptiq", "version": "v1"}, "paths": {}}
    return PlainTextResponse(generate_python_sdk(spec), media_type="text/x-python")


@router.get("/sdk/typescript", response_class=PlainTextResponse)
async def download_typescript_sdk():
    """Download the auto-generated TypeScript SDK."""
    from .sdk_gen import generate_typescript_sdk
    spec = {"info": {"title": "Synaptiq", "version": "v1"}, "paths": {}}
    return PlainTextResponse(generate_typescript_sdk(spec), media_type="text/typescript")


# ── Contracts ─────────────────────────────────────────────────────────────────

@router.get("/contracts")
async def list_contracts(stability: str | None = Query(None)):
    """List all registered endpoint contracts."""
    reg = get_contract_registry()
    if stability:
        contracts = reg.by_stability(stability)
    else:
        contracts = reg.all()
    return wrap({"contracts": contracts, "total": len(contracts)})


# ── Deprecations ──────────────────────────────────────────────────────────────

@router.get("/deprecations")
async def list_deprecations():
    """List all deprecated endpoints."""
    reg  = get_deprecation_registry()
    deps = reg.all()
    return wrap({"deprecated": deps, "total": len(deps)})


# ── Usage stats ───────────────────────────────────────────────────────────────

@router.get("/usage")
async def get_usage_stats(db: Any = Depends(get_db)):
    """Return basic API usage metrics."""
    try:
        from obs import get_metrics, M_API_REQUESTS, M_AI_REQUESTS, M_API_ERRORS
        m      = get_metrics()
        snap   = m.snapshot()
        result = {
            "api_requests": snap.get(M_API_REQUESTS, {}).get("value", 0),
            "ai_requests":  snap.get(M_AI_REQUESTS,  {}).get("value", 0),
            "api_errors":   snap.get(M_API_ERRORS,   {}).get("value", 0),
        }
    except Exception:
        result = {}
    keys_count = 0
    try:
        keys_count = await db["api_keys"].count_documents({"revoked": False})
    except Exception:
        pass
    hooks_count = 0
    try:
        hooks_count = await db["api_webhooks"].count_documents({"active": True})
    except Exception:
        pass
    result["active_api_keys"] = keys_count
    result["active_webhooks"] = hooks_count
    return wrap(result)
