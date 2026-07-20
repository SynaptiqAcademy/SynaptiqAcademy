"""Local router — selects the best provider + model for each request."""
from __future__ import annotations

import logging

from services.local_ai.models.model_registry import ManagedModel, ModelRegistry
from services.local_ai.providers.base import LocalAIProvider

logger = logging.getLogger("synaptiq.local_ai.router")

# Model family preference per task feature
_FEATURE_FAMILY_PREFERENCE: dict[str, list[str]] = {
    "summarization":              ["qwen", "llama", "mistral", "gemma", "deepseek"],
    "document_summarization":     ["qwen", "llama", "mistral", "gemma"],
    "section_summarization":      ["qwen", "llama", "mistral"],
    "paragraph_summarization":    ["qwen", "mistral", "llama", "gemma"],
    "grammar_correction":         ["qwen", "mistral", "llama", "gemma"],
    "academic_proofreading":      ["qwen", "mistral", "llama"],
    "academic_rewriting":         ["qwen", "llama", "mistral", "gemma"],
    "paraphrasing":               ["qwen", "mistral", "llama", "gemma"],
    "translation":                ["qwen", "llama", "mistral"],
    "title_generation":           ["qwen", "llama", "mistral", "gemma", "deepseek"],
    "subtitle_generation":        ["qwen", "llama", "mistral"],
    "keyword_extraction_local":   ["qwen", "mistral", "llama"],
    "outline_generation":         ["qwen", "llama", "mistral", "gemma"],
    "bullet_points":              ["qwen", "llama", "mistral"],
    "plain_language_explanation": ["qwen", "llama", "gemma", "mistral"],
    "research_brainstorming":     ["llama", "qwen", "deepseek", "mistral"],
    "writing_improvement":        ["qwen", "mistral", "llama", "gemma"],
    "academic_tone":              ["qwen", "mistral", "llama"],
    "email_drafting":             ["qwen", "llama", "mistral", "gemma"],
    "teaching_simplification":    ["llama", "qwen", "gemma", "mistral"],
    "teaching_explanation":       ["llama", "qwen", "gemma"],
    "local_chat":                 ["llama", "qwen", "mistral", "gemma", "deepseek"],
}

_DEFAULT_FAMILY_PREFERENCE = ["qwen", "llama", "mistral", "gemma", "deepseek"]


class LocalRouter:
    """Stateless router — select (provider, model) for a given request."""

    def select(
        self,
        feature: str,
        context_tokens: int,
        registry: ModelRegistry,
        providers: dict[str, LocalAIProvider],
        preferred_model: str = "",
    ) -> tuple[LocalAIProvider, str] | None:
        """Return (provider, model_id) or None if nothing is available."""
        if preferred_model:
            return self._resolve_preferred(preferred_model, registry, providers)

        family_pref = _FEATURE_FAMILY_PREFERENCE.get(feature, _DEFAULT_FAMILY_PREFERENCE)
        managed = registry.get_best_model(
            family_preference=family_pref,
            min_context_window=context_tokens,
        )
        if managed is None:
            logger.debug("local_router: no model available for feature=%s", feature)
            return None

        provider = providers.get(managed.info.provider)
        if provider is None:
            logger.debug(
                "local_router: model %s has unknown provider %s",
                managed.info.model_id, managed.info.provider,
            )
            return None

        logger.debug(
            "local_router: feature=%s → provider=%s model=%s family=%s",
            feature, managed.info.provider, managed.info.model_id, managed.info.family,
        )
        return provider, managed.info.model_id

    def _resolve_preferred(
        self,
        model_id: str,
        registry: ModelRegistry,
        providers: dict[str, LocalAIProvider],
    ) -> tuple[LocalAIProvider, str] | None:
        managed = registry.get_by_model_id(model_id)
        if managed and managed.enabled and managed.info.available:
            provider = providers.get(managed.info.provider)
            if provider:
                return provider, model_id
        # Exact model not found — try as-is through preferred provider
        for p in providers.values():
            return p, model_id
        return None
