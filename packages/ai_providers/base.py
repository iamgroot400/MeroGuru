"""Provider-agnostic interface every AI backend (BYOK remote or local Ollama) must implement.

The learning engine depends only on this interface, never on a specific vendor SDK,
so a user's OpenAI/Anthropic/compatible key or a local Ollama model are interchangeable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenerationRequest:
    system_prompt: str
    user_prompt: str
    temperature: float = 0.2
    max_tokens: int = 2000
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    text: str
    raw_response: dict[str, Any] = field(default_factory=dict)
    model: str | None = None


@dataclass
class StructuredResult:
    data: dict[str, Any]
    valid: bool
    validation_errors: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderHealth:
    ok: bool
    detail: str = ""


class AIProviderError(RuntimeError):
    """Raised when a provider call fails in a way callers must handle explicitly."""


class AIProvider(ABC):
    provider_name: str

    @abstractmethod
    async def generate_text(self, request: GenerationRequest) -> GenerationResult:
        ...

    @abstractmethod
    async def generate_structured(
        self, request: GenerationRequest, json_schema: dict[str, Any]
    ) -> StructuredResult:
        """Ask the model for JSON matching json_schema and validate the result.

        Implementations must validate the returned JSON against the schema before
        returning valid=True. Invalid output is returned with valid=False rather
        than raised, so callers can decide whether to repair-retry.
        """

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def healthcheck(self) -> ProviderHealth:
        ...
