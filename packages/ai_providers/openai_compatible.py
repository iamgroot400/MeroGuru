"""Adapter for OpenAI, Anthropic, and any OpenAI-compatible chat-completions endpoint.

One adapter covers all of these because the request/response shape is near-identical
once a caller supplies base_url + api_key + model names. Anthropic's native API differs
slightly (messages endpoint, no /chat/completions), so it gets its own thin subclass.
"""
from __future__ import annotations

import json
from typing import Any

import httpx
import jsonschema

from packages.ai_providers.base import (
    AIProvider,
    AIProviderError,
    GenerationRequest,
    GenerationResult,
    ProviderHealth,
    StructuredResult,
)

DEFAULT_TIMEOUT = 60.0


class OpenAICompatibleProvider(AIProvider):
    provider_name = "openai_compatible"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        chat_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def generate_text(self, request: GenerationRequest) -> GenerationResult:
        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions", headers=self._headers(), json=payload
            )
        if resp.status_code >= 400:
            raise AIProviderError(f"provider error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return GenerationResult(text=text, raw_response=data, model=self.chat_model)

    async def generate_structured(
        self, request: GenerationRequest, json_schema: dict[str, Any]
    ) -> StructuredResult:
        schema_instruction = (
            "\n\nRespond with ONLY valid JSON matching this JSON Schema. "
            "No prose, no markdown fences.\n" + json.dumps(json_schema)
        )
        augmented = GenerationRequest(
            system_prompt=request.system_prompt + schema_instruction,
            user_prompt=request.user_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        result = await self.generate_text(augmented)
        return _validate_json(result.text, json_schema, result.raw_response)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self.embedding_model, "input": texts}
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings", headers=self._headers(), json=payload
            )
        if resp.status_code >= 400:
            raise AIProviderError(f"provider error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

    async def healthcheck(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self._headers())
            if resp.status_code >= 400:
                return ProviderHealth(ok=False, detail=f"status {resp.status_code}")
            return ProviderHealth(ok=True)
        except httpx.HTTPError as exc:
            return ProviderHealth(ok=False, detail=str(exc))


class AnthropicProvider(AIProvider):
    provider_name = "anthropic"

    def __init__(self, api_key: str, chat_model: str = "claude-sonnet-5") -> None:
        self.api_key = api_key
        self.chat_model = chat_model
        self.base_url = "https://api.anthropic.com/v1"

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def generate_text(self, request: GenerationRequest) -> GenerationResult:
        payload = {
            "model": self.chat_model,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/messages", headers=self._headers(), json=payload
            )
        if resp.status_code >= 400:
            raise AIProviderError(f"provider error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        text = "".join(block.get("text", "") for block in data.get("content", []))
        return GenerationResult(text=text, raw_response=data, model=self.chat_model)

    async def generate_structured(
        self, request: GenerationRequest, json_schema: dict[str, Any]
    ) -> StructuredResult:
        schema_instruction = (
            "\n\nRespond with ONLY valid JSON matching this JSON Schema. "
            "No prose, no markdown fences.\n" + json.dumps(json_schema)
        )
        augmented = GenerationRequest(
            system_prompt=request.system_prompt + schema_instruction,
            user_prompt=request.user_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        result = await self.generate_text(augmented)
        return _validate_json(result.text, json_schema, result.raw_response)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise AIProviderError("Anthropic does not expose an embeddings endpoint")

    async def healthcheck(self) -> ProviderHealth:
        try:
            result = await self.generate_text(
                GenerationRequest(system_prompt="Reply with OK.", user_prompt="ping", max_tokens=5)
            )
            return ProviderHealth(ok=bool(result.text))
        except (AIProviderError, httpx.HTTPError) as exc:
            return ProviderHealth(ok=False, detail=str(exc))


def _validate_json(
    text: str, json_schema: dict[str, Any], raw_response: dict[str, Any]
) -> StructuredResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return StructuredResult(data={}, valid=False, validation_errors=[f"invalid JSON: {exc}"])
    try:
        jsonschema.validate(data, json_schema)
    except jsonschema.ValidationError as exc:
        return StructuredResult(
            data=data, valid=False, validation_errors=[exc.message], raw_response=raw_response
        )
    return StructuredResult(data=data, valid=True, raw_response=raw_response)
