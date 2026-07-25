"""Live workspace presence (Workspace redesign Phase 9).

An authenticated WebSocket that broadcasts who's currently viewing a
workspace, what they're looking at (tasks board, timeline, a specific wiki
page, ...), and whether they're actively typing — following the same
accept-then-authenticate JWT-cookie pattern already proven in
routers/messaging.py and routers/wiki_collab.py.

This is intentionally a pure in-memory presence layer (like wiki_collab.py's
room registry) — presence is inherently ephemeral, nothing here is meant to
be durable, so there is no database table for it. The one disclosed
limitation is the same as wiki_collab.py: in-process only, does not fan out
across multiple horizontally-scaled replicas.

Security: the workspace_id in the URL is only ever used to look up the real
`workspaces` document server-side and check real membership — a connection
that isn't a member never joins the room and never sees its broadcast
traffic. A client's own claimed `view`/`context_id` is broadcast as-is (it's
just "what tab am I on" for other members' benefit), never trusted for
authorization of anything.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import jwt
from bson import ObjectId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from db import get_db

logger = logging.getLogger("synaptiq.presence")
router = APIRouter(tags=["presence"])

JWT_ALGORITHM = "HS256"
RATE_LIMIT_MSGS_PER_SEC = 10
HEARTBEAT_TIMEOUT = 30       # seconds between receive attempts before we re-check staleness
ACTIVE_WINDOW = 45           # seconds since last message to still count as "active" vs "idle"
STALE_AFTER = 120            # seconds of total silence before the server force-closes the connection

# workspace_id -> {connection_key: {"ws": WebSocket, "user_id", "full_name",
# "avatar_url", "view", "context_id", "typing", "last_active": monotonic float}}
_rooms: dict[str, dict[str, dict]] = defaultdict(dict)


def _ws_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        logger.error("JWT_SECRET env var not set — presence WebSocket auth will fail")
    return secret


async def _authorized_member_or_none(workspace_id: str, user_id: str) -> bool:
    db = get_db()
    try:
        oid = ObjectId(workspace_id)
    except Exception:
        return False
    ws = await db.workspaces.find_one({"_id": oid})
    if not ws:
        return False
    return user_id in (ws.get("members") or []) or ws.get("owner_id") == user_id


def _snapshot(workspace_id: str) -> dict:
    now = time.monotonic()
    users = []
    for state in _rooms[workspace_id].values():
        idle_for = now - state["last_active"]
        users.append({
            "user_id": state["user_id"],
            "full_name": state["full_name"],
            "avatar_url": state["avatar_url"],
            "view": state["view"],
            "context_id": state["context_id"],
            "typing": state["typing"] and idle_for < ACTIVE_WINDOW,
            "status": "active" if idle_for < ACTIVE_WINDOW else "idle",
            "last_active": state["last_active_iso"],
        })
    return {"type": "presence_snapshot", "users": users}


async def _broadcast(workspace_id: str):
    snapshot = _snapshot(workspace_id)
    dead = []
    for key, state in _rooms[workspace_id].items():
        try:
            await state["ws"].send_json(snapshot)
        except Exception:
            dead.append(key)
    for k in dead:
        _rooms[workspace_id].pop(k, None)


async def presence_sweep_loop():
    """Background safety net (started at app startup): purges connections
    that went silent past STALE_AFTER without a clean WebSocket close (e.g.
    a crashed tab or a dropped connection that never sent a close frame)."""
    while True:
        await asyncio.sleep(30)
        now = time.monotonic()
        for workspace_id in list(_rooms.keys()):
            room = _rooms[workspace_id]
            stale_keys = [k for k, s in room.items() if now - s["last_active"] > STALE_AFTER]
            if not stale_keys:
                continue
            for k in stale_keys:
                state = room.pop(k, None)
                if state:
                    try:
                        await state["ws"].close(code=1000)
                    except Exception:
                        pass
            if not room:
                _rooms.pop(workspace_id, None)
            else:
                await _broadcast(workspace_id)


@router.websocket("/api/ws/workspace/{workspace_id}/presence")
async def ws_workspace_presence(websocket: WebSocket, workspace_id: str):
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
        is_member = await _authorized_member_or_none(workspace_id, user_id)
    except Exception as exc:
        logger.error("WS presence/%s: DB error during authorization: %s", workspace_id, str(exc)[:160])
        await websocket.close(code=1011)
        return
    if not is_member:
        await websocket.close(code=4403)
        return

    db = get_db()
    user_doc = None
    try:
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)}, {"full_name": 1, "avatar_url": 1})
    except Exception:
        pass

    conn_key = f"{user_id}:{id(websocket)}"
    now_mono = time.monotonic()
    _rooms[workspace_id][conn_key] = {
        "ws": websocket,
        "user_id": user_id,
        "full_name": (user_doc or {}).get("full_name", "Someone"),
        "avatar_url": (user_doc or {}).get("avatar_url"),
        "view": None,
        "context_id": None,
        "typing": False,
        "last_active": now_mono,
        "last_active_iso": datetime.now(timezone.utc).isoformat(),
    }
    await _broadcast(workspace_id)
    logger.info("Presence: user=%s joined workspace=%s (room size=%d)", user_id[:8], workspace_id, len(_rooms[workspace_id]))

    msg_times: list[float] = []
    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=HEARTBEAT_TIMEOUT)
            except asyncio.TimeoutError:
                state = _rooms[workspace_id].get(conn_key)
                if not state:
                    break
                if time.monotonic() - state["last_active"] > STALE_AFTER:
                    break
                await _broadcast(workspace_id)  # push idle-state transitions to peers
                continue

            now = time.monotonic()
            msg_times.append(now)
            msg_times[:] = [t for t in msg_times if now - t < 1.0]
            if len(msg_times) > RATE_LIMIT_MSGS_PER_SEC:
                logger.warning("Presence: user=%s exceeded rate limit in workspace=%s — closing", user_id[:8], workspace_id)
                await websocket.close(code=1008)
                break

            try:
                payload = json.loads(raw)
            except Exception:
                continue
            state = _rooms[workspace_id].get(conn_key)
            if not state:
                break
            if "view" in payload:
                state["view"] = payload.get("view")
            if "context_id" in payload:
                state["context_id"] = payload.get("context_id")
            state["typing"] = bool(payload.get("typing", False))
            state["last_active"] = now
            state["last_active_iso"] = datetime.now(timezone.utc).isoformat()
            await _broadcast(workspace_id)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Presence: connection error in workspace=%s: %s", workspace_id, str(exc)[:160])
    finally:
        room = _rooms.get(workspace_id)
        if room and conn_key in room:
            del room[conn_key]
            if not room:
                _rooms.pop(workspace_id, None)
            else:
                await _broadcast(workspace_id)
        logger.info("Presence: user=%s left workspace=%s", user_id[:8], workspace_id)
