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
