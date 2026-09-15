"""Builds the correct AIProvider instance for a user's stored (decrypted) credential
or falls back to the deployment's local Ollama instance when the user has none.

This is the single place that knows about concrete provider classes; the rest of
the codebase (learning engine, API routes) only ever sees the AIProvider interface.
"""
from __future__ import annotations

from packages.ai_providers.base import AIProvider
from packages.ai_providers.ollama import OllamaProvider
from packages.ai_providers.openai_compatible import AnthropicProvider, OpenAICompatibleProvider

SUPPORTED_PROVIDERS = {"openai", "anthropic", "groq", "openai_compatible", "ollama"}


def build_provider(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
    chat_model: str | None = None,
    embedding_model: str | None = None,
) -> AIProvider:
    if provider == "openai":
        if not api_key:
            raise ValueError("openai provider requires an api_key")
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1",
            chat_model=chat_model or "gpt-4o-mini",
            embedding_model=embedding_model or "text-embedding-3-small",
        )
    if provider == "openai_compatible":
        if not api_key or not base_url:
            raise ValueError("openai_compatible provider requires api_key and base_url")
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url,
            chat_model=chat_model or "gpt-4o-mini",
            embedding_model=embedding_model or "text-embedding-3-small",
        )
    if provider == "groq":
        if not api_key:
            raise ValueError("groq provider requires an api_key")
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url or "https://api.groq.com/openai/v1",
            chat_model=chat_model or "llama-3.3-70b-versatile",
            embedding_model=embedding_model or "text-embedding-3-small",
        )
    if provider == "anthropic":
        if not api_key:
            raise ValueError("anthropic provider requires an api_key")
        return AnthropicProvider(api_key=api_key, chat_model=chat_model or "claude-sonnet-5")
    if provider == "ollama":
        return OllamaProvider(
            base_url=base_url or "http://ollama:11434",
            chat_model=chat_model or "llama3.1",
            embedding_model=embedding_model or "nomic-embed-text",
        )
    raise ValueError(f"unsupported provider: {provider}")
