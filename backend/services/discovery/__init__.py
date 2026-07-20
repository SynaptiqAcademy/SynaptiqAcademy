"""Re-exports for the discovery package."""
from services.discovery.base import (
    BaseDiscoveryProvider, JournalProvider, ConferenceProvider, GrantProvider,
)
from services.discovery.registry import all_providers, providers_for, provider_summary
from services.discovery.ingest import run_kind, run_provider, ensure_indexes
from services.discovery.scheduler import start_scheduler, stop_scheduler, is_enabled as scheduler_enabled

__all__ = [
    "BaseDiscoveryProvider", "JournalProvider", "ConferenceProvider", "GrantProvider",
    "all_providers", "providers_for", "provider_summary",
    "run_kind", "run_provider", "ensure_indexes",
    "start_scheduler", "stop_scheduler", "scheduler_enabled",
]
