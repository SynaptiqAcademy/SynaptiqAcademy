"""Base connector — all ingestion connectors extend this."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("lkg.ingestion")


@dataclass
class IngestionResult:
    connector:    str
    nodes_added:  int = 0
    edges_added:  int = 0
    nodes_updated: int = 0
    edges_updated: int = 0
    errors:       list[str] = field(default_factory=list)
    skipped:      int = 0
    started_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at:  Optional[datetime] = None

    def finish(self) -> "IngestionResult":
        self.finished_at = datetime.now(timezone.utc)
        return self

    def to_dict(self) -> dict:
        return {
            "connector":      self.connector,
            "nodes_added":    self.nodes_added,
            "edges_added":    self.edges_added,
            "nodes_updated":  self.nodes_updated,
            "edges_updated":  self.edges_updated,
            "errors":         self.errors,
            "skipped":        self.skipped,
            "started_at":     self.started_at.isoformat(),
            "finished_at":    self.finished_at.isoformat() if self.finished_at else None,
            "duration_s":     (
                (self.finished_at - self.started_at).total_seconds()
                if self.finished_at else None
            ),
        }


class BaseConnector(ABC):
    """
    All LKG connectors implement this interface.
    Each connector is responsible for:
      - Fetching raw data from its source
      - Converting to LKGNode / LKGEdge objects
      - Calling graph_store.upsert_node / upsert_edge
      - Returning an IngestionResult summary
    """
    name: str = "base"
    source: str = "unknown"
    description: str = ""

    @abstractmethod
    async def ingest(self, db: Any, **kwargs) -> IngestionResult:
        """Run a full ingestion pass. Must be idempotent (upsert, not insert)."""
        ...

    def _log(self, result: IngestionResult, msg: str, level: str = "info") -> None:
        getattr(logger, level)("[%s] %s", self.name, msg)
