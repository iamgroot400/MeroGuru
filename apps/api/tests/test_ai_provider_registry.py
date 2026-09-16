from __future__ import annotations

import pytest

from packages.ai_providers.openai_compatible import OpenAICompatibleProvider
from packages.ai_providers.registry import build_provider


def test_groq_defaults_to_groq_base_url_and_model():
    provider = build_provider(provider="groq", api_key="gsk_test")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://api.groq.com/openai/v1"
    assert provider.chat_model == "llama-3.3-70b-versatile"


def test_groq_requires_api_key():
    with pytest.raises(ValueError):
        build_provider(provider="groq")


def test_groq_respects_explicit_model_override():
    provider = build_provider(provider="groq", api_key="gsk_test", chat_model="openai/gpt-oss-120b")
    assert provider.chat_model == "openai/gpt-oss-120b"


def test_gemini_defaults_to_gemini_base_url_and_model():
    provider = build_provider(provider="gemini", api_key="AIza_test")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert provider.chat_model == "gemini-2.5-flash"
    assert provider.embedding_model == "gemini-embedding-001"


def test_gemini_requires_api_key():
    with pytest.raises(ValueError):
        build_provider(provider="gemini")


def test_gemini_respects_explicit_model_override():
    provider = build_provider(provider="gemini", api_key="AIza_test", chat_model="gemini-3-flash")
    assert provider.chat_model == "gemini-3-flash"
