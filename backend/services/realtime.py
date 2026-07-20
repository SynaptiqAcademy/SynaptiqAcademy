"""WebSocket connection manager with Redis Pub/Sub fan-out.

Local WebSocket handles are kept in per-process dicts.
Events are published to Redis so every replica receives them and
forwards to its own locally-connected clients.

Graceful degradation: if Redis is unavailable, events are delivered
to local WebSockets only (single-instance behavior, no data loss for
single-server deployments).

Channels:
  synaptiq:conv:{conversation_id}  — conversation events (typing, presence)
  synaptiq:user:{user_id}          — per-user events (notifications, unread)
  synaptiq:admin                   — admin-only live feed (Admin OS)
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger("synaptiq.realtime")


class ConnectionManager:
    def __init__(self) -> None:
        self._conv_conns: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._user_conns: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._user_per_conn: Dict[WebSocket, str] = {}
        self._admin_conns: Set[WebSocket] = set()
        self._pubsub_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]

    # ------------------------------------------------------------------ lifecycle

    async def start(self) -> None:
        """Start the Redis pub/sub background listener. Call at server startup."""
        if self._pubsub_task is None or self._pubsub_task.done():
            self._pubsub_task = asyncio.create_task(self._pubsub_listener())
            logger.info("WebSocket pub/sub listener task started")

    async def stop(self) -> None:
        """Cancel the listener. Call at server shutdown."""
        if self._pubsub_task and not self._pubsub_task.done():
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

    # ------------------------------------------------------------------ connect / disconnect

    async def connect(self, conversation_id: str, user_id: str, ws: WebSocket) -> None:
        # NOTE: does not call ws.accept() — every caller already accepts the
        # socket unconditionally before auth checks (so failed auth gets a
        # clean WS close code instead of an HTTP 403), so by the time this is
        # called the socket is already in the CONNECTED state. A second
        # accept() here raised "Expected ASGI message websocket.send or
        # websocket.close, but got websocket.accept" and silently killed the
        # connection immediately after opening it — a real, previously
        # undetected bug (found while verifying the new admin WS channel).
        self._conv_conns[conversation_id].add(ws)
        self._user_per_conn[ws] = user_id

    async def connect_user(self, user_id: str, ws: WebSocket) -> None:
        self._user_conns[user_id].add(ws)
        self._user_per_conn[ws] = user_id

    def disconnect(self, conversation_id: str, ws: WebSocket) -> None:
        self._conv_conns.get(conversation_id, set()).discard(ws)
        self._user_per_conn.pop(ws, None)
        if conversation_id in self._conv_conns and not self._conv_conns[conversation_id]:
            self._conv_conns.pop(conversation_id, None)

    def disconnect_user(self, user_id: str, ws: WebSocket) -> None:
        self._user_conns.get(user_id, set()).discard(ws)
        self._user_per_conn.pop(ws, None)
        if user_id in self._user_conns and not self._user_conns[user_id]:
            self._user_conns.pop(user_id, None)

    async def connect_admin(self, ws: WebSocket) -> None:
        # See the note in connect() — the handler already accepts before this is called.
        self._admin_conns.add(ws)

    def disconnect_admin(self, ws: WebSocket) -> None:
        self._admin_conns.discard(ws)

    # ------------------------------------------------------------------ broadcast

    async def broadcast(
        self,
        conversation_id: str,
        event: dict,
        exclude_ws: Optional[WebSocket] = None,
    ) -> None:
        """Send event to all conversation members across all replicas.

        When Redis is available the event is published and every replica
        (including this one) receives it via the pub/sub listener, then
        forwards to locally connected sockets.

        When Redis is unavailable, falls back to local-only delivery
        (single-instance semantics preserved).
        """
        from services.redis_client import get_redis

        r = await get_redis()
        if r is not None:
            try:
                await r.publish(
                    f"synaptiq:conv:{conversation_id}",
                    json.dumps({"event": event}),
                )
                return
            except Exception as exc:
                logger.warning("Redis publish failed; falling back to local: %s", exc)
        # Fallback: local delivery only
        await self._local_conv_broadcast(conversation_id, event, exclude_ws)

    async def broadcast_user(self, user_id: str, event: dict) -> None:
        """Send event to a specific user across all replicas."""
        from services.redis_client import get_redis

        r = await get_redis()
        if r is not None:
            try:
                await r.publish(
                    f"synaptiq:user:{user_id}",
                    json.dumps({"event": event}),
                )
                return
            except Exception as exc:
                logger.warning("Redis user publish failed; falling back to local: %s", exc)
        await self._local_user_broadcast(user_id, event)

    async def broadcast_admin(self, event: dict) -> None:
        """Send event to all connected admin sessions across all replicas."""
        from services.redis_client import get_redis

        r = await get_redis()
        if r is not None:
            try:
                await r.publish("synaptiq:admin", json.dumps({"event": event}))
                return
            except Exception as exc:
                logger.warning("Redis admin publish failed; falling back to local: %s", exc)
        await self._local_admin_broadcast(event)

    # ------------------------------------------------------------------ internal helpers

    async def _local_conv_broadcast(
        self,
        conversation_id: str,
        event: dict,
        exclude_ws: Optional[WebSocket] = None,
    ) -> None:
        dead = []
        for ws in list(self._conv_conns.get(conversation_id, set())):
            if ws is exclude_ws:
                continue
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(conversation_id, ws)

    async def _local_user_broadcast(self, user_id: str, event: dict) -> None:
        dead = []
        for ws in list(self._user_conns.get(user_id, set())):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_user(user_id, ws)

    async def _local_admin_broadcast(self, event: dict) -> None:
        dead = []
        for ws in list(self._admin_conns):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._admin_conns.discard(ws)

    # ------------------------------------------------------------------ Redis pub/sub listener

    async def _pubsub_listener(self) -> None:
        """Long-running background task: subscribe and forward events to local sockets."""
        from services.redis_client import get_redis

        while True:
            try:
                r = await get_redis()
                if r is None:
                    await asyncio.sleep(5)
                    continue

                pubsub = r.pubsub()
                await pubsub.psubscribe("synaptiq:conv:*", "synaptiq:user:*")
                await pubsub.subscribe("synaptiq:admin")
                logger.info(
                    "Redis pub/sub subscribed to synaptiq:conv:*, synaptiq:user:*, synaptiq:admin"
                )
                async for message in pubsub.listen():
                    msg_type = message.get("type")
                    if msg_type not in ("pmessage", "message"):
                        continue
                    channel: str = message.get("channel", "")
                    try:
                        payload = json.loads(message["data"])
                        event = payload["event"]
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue

                    if channel.startswith("synaptiq:conv:"):
                        conv_id = channel[len("synaptiq:conv:"):]
                        await self._local_conv_broadcast(conv_id, event)
                    elif channel.startswith("synaptiq:user:"):
                        user_id = channel[len("synaptiq:user:"):]
                        await self._local_user_broadcast(user_id, event)
                    elif channel == "synaptiq:admin":
                        await self._local_admin_broadcast(event)

            except asyncio.CancelledError:
                logger.info("WebSocket pub/sub listener cancelled")
                return
            except Exception as exc:
                logger.warning(
                    "Redis pub/sub listener error (reconnecting in 3 s): %s", exc
                )
                await asyncio.sleep(3)


manager = ConnectionManager()
