"""Abstract base class for all local AI providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class LocalModelInfo:
    model_id: str
    provider: str
    display_name: str
    family: str          # llama | qwen | mistral | gemma | deepseek | phi | other
    parameter_size: str  # "7B" | "13B" | "70B" | ""
    context_window: int  # 0 = unknown
    available: bool = True
    enabled: bool = True
    avg_latency_ms: float = 0.0
    size_bytes: int = 0

    @property
    def ram_estimate_gb(self) -> float:
        """Rough VRAM/RAM estimate based on parameter count (4-bit quantized)."""
        mapping = {
            "1B": 1.0, "1.5B": 1.5, "2B": 2.0, "3B": 3.0, "4B": 4.0,
            "7B": 5.0, "8B": 5.5, "9B": 6.0, "13B": 9.0, "14B": 9.5,
            "24B": 14.0, "30B": 18.0, "32B": 20.0, "34B": 22.0,
            "40B": 25.0, "65B": 40.0, "70B": 42.0, "72B": 44.0,
        }
        return mapping.get(self.parameter_size, 0.0)

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "family": self.family,
            "parameter_size": self.parameter_size,
            "context_window": self.context_window,
            "available": self.available,
            "enabled": self.enabled,
            "avg_latency_ms": self.avg_latency_ms,
            "ram_estimate_gb": self.ram_estimate_gb,
        }


@dataclass
class LocalProviderHealth:
    provider_name: str
    available: bool
    latency_ms: int = 0
    models: list[LocalModelInfo] = field(default_factory=list)
    error: str = ""
    version: str = ""

    def to_dict(self) -> dict:
        return {
            "provider": self.provider_name,
            "available": self.available,
            "latency_ms": self.latency_ms,
            "model_count": len(self.models),
            "error": self.error,
            "version": self.version,
        }


def detect_model_family(model_id: str) -> str:
    name = model_id.lower()
    if any(k in name for k in ("qwen", "qwq")):
        return "qwen"
    if any(k in name for k in ("llama", "llama3", "llama2", "llama-3")):
        return "llama"
    if any(k in name for k in ("mistral", "mixtral", "mistral-nemo")):
        return "mistral"
    if "gemma" in name:
        return "gemma"
    if any(k in name for k in ("deepseek", "deep-seek")):
        return "deepseek"
    if any(k in name for k in ("phi", "phi-3", "phi3")):
        return "phi"
    if "falcon" in name:
        return "falcon"
    if any(k in name for k in ("vicuna", "alpaca", "wizard")):
        return "llama"
    if "codellama" in name:
        return "llama"
    if "starcoder" in name:
        return "starcoder"
    if "command" in name:
        return "command"
    return "other"


def detect_parameter_size(model_id: str) -> str:
    import re
    name = model_id.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", name)
    if m:
        val = m.group(1)
        # Normalize: "7.0" → "7B", "1.5" → "1.5B"
        num = float(val)
        if num == int(num):
            return f"{int(num)}B"
        return f"{val}B"
    return ""


class LocalAIProvider(ABC):
    """Abstract base for all local AI providers (Ollama, vLLM, LM Studio, etc.)."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def base_url(self) -> str: ...

    @abstractmethod
    async def list_models(self) -> list[LocalModelInfo]: ...

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: list[dict],
        system: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> tuple[str, int, int]:
        """Generate a response. Returns (text, input_tokens, output_tokens)."""
        ...

    @abstractmethod
    async def stream_chat(
        self,
        model: str,
        messages: list[dict],
        system: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> AsyncIterator[str]:
        """Stream a response token by token."""
        ...

    @abstractmethod
    async def health_check(self) -> LocalProviderHealth: ...

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)
