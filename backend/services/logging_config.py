"""Structured logging configuration.

In APP_ENV=production: JSON lines on stdout with stable field names so log
aggregators (Datadog/Loki/CloudWatch) can index them. In dev: pretty plain
text (preserves human readability).

Logged fields (prod): ts, level, logger, msg, request_id?, trace_id?, path?, user_id?
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any


def _is_prod() -> bool:
    return os.environ.get("APP_ENV", "development").lower() in ("prod", "production")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": int(time.time() * 1000),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Carry exception info
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Promote contextual fields if set via logger.info("...", extra={...})
        for k in ("request_id", "trace_id", "path", "method", "user_id", "status"):
            v = getattr(record, k, None)
            if v is not None:
                payload[k] = v
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    # Clear handlers configured by uvicorn / basicConfig
    for h in list(root.handlers):
        root.removeHandler(h)

    _env_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, _env_level, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if _is_prod():
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s — %(message)s"))

    root.addHandler(handler)
    root.setLevel(level)

    # Tame noisy libraries
    for noisy in ("pymongo", "asyncio", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
