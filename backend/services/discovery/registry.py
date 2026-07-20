"""Discovery provider registry. Centralized so the runner & admin endpoints
can introspect available sources without import gymnastics elsewhere."""
from __future__ import annotations

from typing import Iterable

from services.discovery.base import (
    BaseDiscoveryProvider, JournalProvider, ConferenceProvider, GrantProvider,
)
from services.discovery.providers.openalex_journals import OpenAlexJournalsProvider
from services.discovery.providers.doaj_journals import DOAJJournalsProvider
from services.discovery.providers.crossref_journals import CrossrefJournalsProvider
from services.discovery.providers.wikicfp_conferences import WikiCFPConferencesProvider
from services.discovery.providers.openaire_grants import OpenAIREGrantsProvider
from services.discovery.providers.nih_reporter_grants import NIHReporterGrantsProvider
from services.discovery.providers.ukri_grants import UKRIGrantsProvider


_REGISTRY: list[BaseDiscoveryProvider] = [
    OpenAlexJournalsProvider(),
    DOAJJournalsProvider(),
    CrossrefJournalsProvider(),
    WikiCFPConferencesProvider(),
    OpenAIREGrantsProvider(),
    NIHReporterGrantsProvider(),
    UKRIGrantsProvider(),
]


def all_providers() -> list[BaseDiscoveryProvider]:
    return list(_REGISTRY)


def providers_for(kind: str, *, names: Iterable[str] | None = None,
                  only_default: bool = False) -> list[BaseDiscoveryProvider]:
    selected = [p for p in _REGISTRY if p.kind == kind]
    if names is not None:
        names = set(names); selected = [p for p in selected if p.name in names]
    if only_default:
        selected = [p for p in selected if p.enabled_by_default]
    return selected


def provider_summary() -> list[dict]:
    return [
        {"name": p.name, "kind": p.kind, "enabled_by_default": p.enabled_by_default}
        for p in _REGISTRY
    ]
