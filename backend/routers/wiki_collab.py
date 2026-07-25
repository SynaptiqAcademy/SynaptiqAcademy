"""Wiki real-time collaborative editing (Workspace redesign Phase 5).

An authenticated WebSocket relay for Yjs sync + awareness messages, following
the exact auth pattern already used and proven in routers/messaging.py's
`/ws/conversations/{conv_id}` (accept-then-authenticate, JWT from the
`access_token` cookie, real DB-backed membership check). The server never
decodes the Yjs binary protocol — it's opaque bytes relayed between clients
in the same "room" (one room per wiki page), which is exactly how Yjs's own
reference server (y-websocket) works. Document content itself is persisted
through the existing wiki save path (PATCH /api/items/{id}, debounced
client-side autosave) — this endpoint's job is only real-time sync between
currently-connected editors, not storage.

Security:
  - Never trusts a client-supplied workspace_id: the room is keyed by
    page_id only, and the page's workspace (and therefore who may join) is
    always looked up server-side from the real workspace_items document.
  - A connection that isn't a member of the page's workspace is rejected
    (WS close code 4403) before joining the room — it never sees any
    broadcast traffic for that room.
  - Per-connection rate limiting on the message loop (default 50 msg/s)
    guards against a single misbehaving/compromised client flooding a room.

Known limitation (disclosed, not silently skipped): this relay is
in-process only, matching the additive scope of this feature — it does not
fan out across multiple horizontally-scaled backend replicas the way
services/realtime.py's Redis pub/sub messaging layer does. Single-process
deployments (the current one) are fully correct; a multi-replica deployment
would need the same Redis fan-out pattern added here.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict

import jwt
from bson import ObjectId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from db import get_db

logger = logging.getLogger("synaptiq.wiki_collab")
router = APIRouter(tags=["wiki-collab"])

JWT_ALGORITHM = "HS256"
RATE_LIMIT_MSGS_PER_SEC = 50

# page_id -> set of connected websockets. In-process only — see module
# docstring for the multi-replica caveat.
_rooms: dict[str, set[WebSocket]] = defaultdict(set)


def _ws_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        logger.error("JWT_SECRET env var not set — wiki collab WebSocket auth will fail")
    return secret


async def _authorized_page_or_none(page_id: str, user_id: str) -> dict | None:
    """Resolve page_id -> its workspace server-side and verify membership.
    Never trusts anything the client claims about workspace/document
    ownership — everything here comes from the database."""
    db = get_db()
    try:
        oid = ObjectId(page_id)
    except Exception:
        return None
    page = await db.workspace_items.find_one({"_id": oid, "item_type": "wiki_page", "deleted_at": None})
    if not page:
        return None
    ws = await db.workspaces.find_one({"_id": ObjectId(page["workspace_id"])})
    if not ws:
        return None
    is_member = user_id in (ws.get("members") or []) or ws.get("owner_id") == user_id
    return page if is_member else None


@router.websocket("/api/ws/wiki/{page_id}")
async def ws_wiki_page(websocket: WebSocket, page_id: str):
    # Accept BEFORE auth checks — ASGI spec: closing pre-accept surfaces as a
    # generic HTTP 403 to the client with no way to tell auth vs not-found
    # apart. Closing post-accept with a specific code lets the client react
    # correctly (e.g. redirect to login vs show "no access").
    await websocket.accept()

    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=4401)
        return

    secret = _ws_jwt_secret()
    if not secret:
        await websocket.close(code=1011)
        return

    try:
        data = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        if data.get("type") != "access":
            await websocket.close(code=4401)
            return
        user_id = data["sub"]
    except jwt.ExpiredSignatureError:
        await websocket.close(code=4401)
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=4401)
        return

    try:
        page = await _authorized_page_or_none(page_id, user_id)
    except Exception as exc:
        logger.error("WS /ws/wiki/%s: DB error during authorization: %s", page_id, str(exc)[:160])
        await websocket.close(code=1011)
        return

    if not page:
        # Covers both "page doesn't exist" and "not a member" — deliberately
        # not distinguished, so this endpoint can't be used to probe for the
        # existence of pages in workspaces the caller isn't a member of.
        await websocket.close(code=4403)
        return

    _rooms[page_id].add(websocket)
    logger.info("Wiki collab: user=%s joined page=%s (room size=%d)", user_id[:8], page_id, len(_rooms[page_id]))

    msg_times: list[float] = []
    try:
        while True:
            msg = await websocket.receive_bytes()

            # Rate limit: drop the connection if it's flooding the room.
            now = time.monotonic()
            msg_times.append(now)
            msg_times[:] = [t for t in msg_times if now - t < 1.0]
            if len(msg_times) > RATE_LIMIT_MSGS_PER_SEC:
                logger.warning("Wiki collab: user=%s exceeded rate limit on page=%s — closing", user_id[:8], page_id)
                await websocket.close(code=1008)
                break

            dead = []
            for peer in _rooms[page_id]:
                if peer is websocket:
                    continue
                try:
                    await peer.send_bytes(msg)
                except Exception:
                    dead.append(peer)
            for d in dead:
                _rooms[page_id].discard(d)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Wiki collab: connection error on page=%s: %s", page_id, str(exc)[:160])
    finally:
        _rooms[page_id].discard(websocket)
        if not _rooms[page_id]:
            del _rooms[page_id]
        logger.info("Wiki collab: user=%s left page=%s", user_id[:8], page_id)
