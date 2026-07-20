"""Local AI Engine — provider-independent local inference subsystem.

Primary entry points:
  get_local_engine()       — singleton LocalAIEngine
  LocalGenerateRequest     — input dataclass
  LocalAIResponse          — output dataclass
  LocalAIConfig            — configuration

Supported providers (auto-discovered):
  • Ollama   — http://localhost:11434
  • vLLM     — http://localhost:8000
  • LM Studio — http://localhost:1234
  • Any OpenAI-compatible endpoint via LOCAL_AI_OPENAI_COMPAT_URL
"""
from services.local_ai.config import LocalAIConfig, load_local_config, reload_local_config
from services.local_ai.engine import (
    LocalAIEngine,
    LocalAIResponse,
    LocalGenerateRequest,
    get_local_engine,
    reset_local_engine,
)

__all__ = [
    "LocalAIEngine",
    "LocalGenerateRequest",
    "LocalAIResponse",
    "LocalAIConfig",
    "load_local_config",
    "reload_local_config",
    "get_local_engine",
    "reset_local_engine",
]
