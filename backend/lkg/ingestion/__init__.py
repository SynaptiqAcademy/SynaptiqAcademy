"""LKG ingestion connectors — each connector runs independently."""
from .base_connector import BaseConnector, IngestionResult
from .internal import InternalConnector
from .openalex import OpenAlexConnector
from .crossref import CrossRefConnector

__all__ = [
    "BaseConnector",
    "IngestionResult",
    "InternalConnector",
    "OpenAlexConnector",
    "CrossRefConnector",
]
