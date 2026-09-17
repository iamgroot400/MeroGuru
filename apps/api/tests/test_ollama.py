import asyncio
import json

import httpx
import pytest

from packages.ai_providers.base import AIProviderError, GenerationRequest
from packages.ai_providers.ollama import OllamaProvider


@pytest.mark.parametrize("structured", [False, True])
def test_chat_contract(monkeypatch, structured):
    schema = {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}}}
    def handler(request):
        payload = json.loads(request.content)
        assert payload["options"]["num_predict"] == 123
        assert payload["keep_alive"] == "15m"
        if structured:
            assert payload["format"] == schema
        else:
            assert "format" not in payload
        return httpx.Response(200, json={"message": {"content": '{"answer":"ok"}'}})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    provider = OllamaProvider()
    request = GenerationRequest(system_prompt="Test", user_prompt="Test", max_tokens=123)
    result = asyncio.run(provider.generate_structured(request, schema) if structured else provider.generate_text(request))
    assert result.valid if structured else bool(result.text)


@pytest.mark.parametrize("content", ['{"answer": 1}', '{"answer":'])
def test_structured_output_still_validates_invalid_or_truncated_json(monkeypatch, content):
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"message": {"content": content}}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    result = asyncio.run(OllamaProvider().generate_structured(
        GenerationRequest(system_prompt="Test", user_prompt="Test"),
        {"type": "object", "properties": {"answer": {"type": "string"}}},
    ))
    assert not result.valid


def test_http_failure_is_not_valid_content(monkeypatch):
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(503, text="unavailable"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    with pytest.raises(AIProviderError):
        asyncio.run(OllamaProvider().generate_text(GenerationRequest(system_prompt="Test", user_prompt="Test")))
