"""Regression tests for the obs_logs retention safeguard.

Covers: StructuredHandler.emit() now stores `timestamp` as a BSON Date
(via a native tz-aware datetime) instead of an ISO string, so a TTL index
on obs_logs.timestamp can actually expire old records; all other log
fields are unchanged; and the obs_logs_timestamp_ttl index exists with
the approved 7-day (604800s) retention configuration.

No business/user data, matching logic, AI credits, Research Record, or
Manuscript Intelligence code was touched by this change.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import pytest

from obs.logger import StructuredHandler
from repo.shim import DBProxy


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


def _make_record(msg: str = "test warning") -> logging.LogRecord:
    return logging.LogRecord(
        name="synaptiq.test_obs_logs_retention",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


class TestLoggerProducesBsonDate:
    # NOTE: emit() only queues a record for DB flush when self._db is not
    # None (see StructuredHandler.emit) — a plain non-None sentinel is
    # enough here since these tests never call flush_to_db().
    def test_emit_stores_timestamp_as_datetime_not_string(self):
        handler = StructuredHandler(db=object())
        record = _make_record()
        handler.emit(record)
        assert handler._pending, "WARNING-level record should be queued for DB flush"
        doc = handler._pending[-1]
        assert isinstance(doc["timestamp"], datetime)
        assert not isinstance(doc["timestamp"], str)

    def test_emit_timestamp_is_utc_aware(self):
        handler = StructuredHandler(db=object())
        record = _make_record()
        handler.emit(record)
        doc = handler._pending[-1]
        assert doc["timestamp"].tzinfo is not None
        assert doc["timestamp"].tzinfo.utcoffset(doc["timestamp"]).total_seconds() == 0

    def test_existing_log_fields_unchanged(self):
        handler = StructuredHandler(db=object())
        record = _make_record("hello world")
        handler.emit(record)
        doc = handler._pending[-1]
        assert doc["level"] == "WARNING"
        assert doc["logger"] == "synaptiq.test_obs_logs_retention"
        assert doc["component"] == "synaptiq"
        assert "hello world" in doc["message"]
        assert doc["module"] == "test_obs_logs_retention"
        assert isinstance(doc["line"], int)


class TestLiveMongoRoundTripStoresBsonDate:
    @pytest.mark.asyncio
    async def test_flushed_record_reads_back_as_datetime(self):
        raw = _RawDB()
        try:
            # Wrap in the same DBProxy every real caller uses (get_db()
            # never hands out a raw motor database) — a raw motor Database's
            # __bool__ deliberately raises NotImplementedError (pymongo 4.x
            # safety guard), which DBProxy doesn't inherit since it has no
            # __bool__ of its own (defaults to always-truthy).
            handler = StructuredHandler(db=DBProxy(raw.db))
            marker = f"phase6-retention-verify-{os.getpid()}"
            handler.emit(_make_record(marker))
            flushed = await handler.flush_to_db()
            assert flushed >= 1

            doc = await raw.db.obs_logs.find_one({"message": {"$regex": marker}})
            assert doc is not None
            assert isinstance(doc["timestamp"], datetime), (
                f"expected BSON Date, got {type(doc['timestamp'])}"
            )
        finally:
            await raw.db.obs_logs.delete_many({"message": {"$regex": "phase6-retention-verify"}})
            raw.close()


class TestTtlIndexConfiguration:
    @pytest.mark.asyncio
    async def test_obs_logs_timestamp_ttl_index_exists_with_7_day_expiry(self):
        raw = _RawDB()
        try:
            indexes = {idx["name"]: idx async for idx in raw.db.obs_logs.list_indexes()}
            ttl_indexes = [
                idx for idx in indexes.values()
                if "expireAfterSeconds" in idx and list(idx["key"].items()) == [("timestamp", 1)]
            ]
            assert ttl_indexes, f"no TTL index found on obs_logs.timestamp; indexes={list(indexes)}"
            assert ttl_indexes[0]["expireAfterSeconds"] == 604800
        finally:
            raw.close()
