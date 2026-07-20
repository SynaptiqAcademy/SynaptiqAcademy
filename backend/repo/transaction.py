"""
Transaction support helper.

MongoDB multi-document transactions require a replica set.  In single-node
development (or Atlas free tier) transactions are available but sessions may
not be; this module provides a transparent fallback.

Usage (two-phase example):
    async with Tx(db) as tx:
        await user_repo.create(user_data, session=tx.session)
        await workspace_repo.create(ws_data, session=tx.session)
        # auto-commit on clean exit; rollback on exception
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)


class Tx:
    """
    Async context manager for MongoDB sessions / transactions.

    If the client does not support sessions (e.g. mongomock in tests),
    falls back to a no-op session so repositories still work.
    """

    def __init__(self, db) -> None:
        self._db      = db
        self._client  = getattr(db, "client", None)
        self._session = None
        self._in_tx   = False

    @property
    def session(self):
        return self._session

    async def __aenter__(self) -> "Tx":
        if self._client is None:
            return self  # no session support — run without transactions

        try:
            self._session = await self._client.start_session()
            self._session.start_transaction()
            self._in_tx = True
        except Exception as exc:
            logger.debug("Transaction start failed (no-op fallback): %s", exc)
            self._session = None
            self._in_tx   = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if not self._session:
            return False  # nothing to close

        try:
            if exc_type is None and self._in_tx:
                await self._session.commit_transaction()
            elif self._in_tx:
                await self._session.abort_transaction()
        except Exception as exc:
            logger.warning("Transaction commit/rollback error: %s", exc)
        finally:
            try:
                await self._session.end_session()
            except Exception:
                pass
            self._session = None
            self._in_tx   = False

        return False  # don't suppress exceptions


@asynccontextmanager
async def transaction(db):
    """Convenience async context manager (alternative to `async with Tx(db)`)."""
    async with Tx(db) as tx:
        yield tx
