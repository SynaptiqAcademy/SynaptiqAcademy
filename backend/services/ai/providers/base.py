"""Abstract base class that every AI provider must implement."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from services.ai.engine.types import AIRequest, AIResponse, ProviderHealth


class AIProvider(ABC):
    """Contract every AI provider must fulfil.

    Implementations must be stateless with respect to requests; shared state
    (e.g. the HTTP client) is held as instance attributes and must be
    initialised lazily and thread-safely.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier: anthropic | openai | local | mock."""

    @abstractmethod
    async def generate(self, request: "AIRequest") -> "AIResponse":
        """Non-streaming completion. Returns the full assistant text."""

    @abstractmethod
    async def stream(self, request: "AIRequest") -> AsyncIterator[str]:
        """Streaming completion; yields text chunks as they arrive."""

    @abstractmethod
    async def health(self) -> "ProviderHealth":
        """Lightweight liveness probe. Must complete within ~5 s."""

    @abstractmethod
    def estimate_tokens(self, messages: list[dict]) -> int:
        """Rough token estimate used for budget pre-checks."""

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimated cost in USD for the given token usage."""

    @abstractmethod
    async def validate(self) -> bool:
        """Return True if the provider is properly configured and reachable."""
