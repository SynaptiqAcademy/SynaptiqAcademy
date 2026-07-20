"""Local AI Engine configuration — fully driven by environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LocalAIConfig:
    # ── Provider endpoints ────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str = "http://localhost:8000"
    lm_studio_base_url: str = "http://localhost:1234"
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = "local"

    # ── Routing ───────────────────────────────────────────────────────────────
    default_provider: str = "ollama"   # ollama | vllm | lm_studio | openai_compatible
    preferred_model: str = ""          # empty → auto-select from registry
    model_family_preference: list[str] = field(
        default_factory=lambda: ["qwen", "llama", "mistral", "gemma", "deepseek"]
    )

    # ── Limits ────────────────────────────────────────────────────────────────
    max_context_tokens: int = 4096
    max_output_tokens: int = 1024
    timeout_seconds: float = 60.0
    temperature: float = 0.3
    max_parallel_requests: int = 4
    max_retries: int = 1
    retry_delay_seconds: float = 1.0

    # ── Streaming ─────────────────────────────────────────────────────────────
    enable_streaming: bool = True

    # ── Cache ─────────────────────────────────────────────────────────────────
    cache_ttl_seconds: float = 300.0
    cache_max_size: int = 1000

    # ── Health ────────────────────────────────────────────────────────────────
    health_check_interval_seconds: float = 60.0

    # ── Discovery ────────────────────────────────────────────────────────────
    auto_discover: bool = True
    discovery_timeout_seconds: float = 5.0

    @classmethod
    def from_env(cls) -> "LocalAIConfig":
        return cls(
            ollama_base_url=os.environ.get("LOCAL_AI_OLLAMA_URL", "http://localhost:11434"),
            vllm_base_url=os.environ.get("LOCAL_AI_VLLM_URL", "http://localhost:8000"),
            lm_studio_base_url=os.environ.get("LOCAL_AI_LM_STUDIO_URL", "http://localhost:1234"),
            openai_compatible_base_url=os.environ.get("LOCAL_AI_OPENAI_COMPAT_URL", ""),
            openai_compatible_api_key=os.environ.get("LOCAL_AI_OPENAI_COMPAT_KEY", "local"),
            default_provider=os.environ.get("LOCAL_AI_DEFAULT_PROVIDER", "ollama"),
            preferred_model=os.environ.get("LOCAL_AI_PREFERRED_MODEL", ""),
            max_context_tokens=int(os.environ.get("LOCAL_AI_MAX_CONTEXT", "4096") or "4096"),
            max_output_tokens=int(os.environ.get("LOCAL_AI_MAX_OUTPUT", "1024") or "1024"),
            timeout_seconds=float(os.environ.get("LOCAL_AI_TIMEOUT", "60") or "60"),
            temperature=float(os.environ.get("LOCAL_AI_TEMPERATURE", "0.3") or "0.3"),
            max_parallel_requests=int(os.environ.get("LOCAL_AI_MAX_PARALLEL", "4") or "4"),
            max_retries=int(os.environ.get("LOCAL_AI_MAX_RETRIES", "1") or "1"),
            retry_delay_seconds=float(os.environ.get("LOCAL_AI_RETRY_DELAY", "1.0") or "1.0"),
            enable_streaming=os.environ.get("LOCAL_AI_STREAMING", "1") == "1",
            cache_ttl_seconds=float(os.environ.get("LOCAL_AI_CACHE_TTL", "300") or "300"),
            cache_max_size=int(os.environ.get("LOCAL_AI_CACHE_MAX_SIZE", "1000") or "1000"),
            health_check_interval_seconds=float(
                os.environ.get("LOCAL_AI_HEALTH_INTERVAL", "60") or "60"
            ),
            auto_discover=os.environ.get("LOCAL_AI_AUTO_DISCOVER", "1") == "1",
            discovery_timeout_seconds=float(
                os.environ.get("LOCAL_AI_DISCOVERY_TIMEOUT", "5") or "5"
            ),
        )


_config: LocalAIConfig | None = None


def load_local_config() -> LocalAIConfig:
    global _config
    if _config is None:
        _config = LocalAIConfig.from_env()
    return _config


def reload_local_config() -> LocalAIConfig:
    global _config
    _config = LocalAIConfig.from_env()
    return _config
