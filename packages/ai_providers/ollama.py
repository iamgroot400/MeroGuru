"""Local-inference adapter so the platform works with zero paid AI keys.

Default provider per the plan: a self-hoster who never configures a remote key
should still get working roadmap generation via a local Ollama model.
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
from packages.ai_providers.openai_compatible import _upstream_error, _validate_json

DEFAULT_TIMEOUT = 300.0


class OllamaProvider(AIProvider):
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str = "http://ollama:11434",
        chat_model: str = "llama3.1",
        embedding_model: str = "nomic-embed-text",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model

    async def generate_text(self, request: GenerationRequest) -> GenerationResult:
        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        if resp.status_code >= 400:
            raise _upstream_error("ollama error", resp)
        data = resp.json()
        text = data.get("message", {}).get("content", "")
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
        embeddings: list[list[float]] = []
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            for text in texts:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                )
                if resp.status_code >= 400:
                    raise AIProviderError(f"ollama embed error {resp.status_code}")
                embeddings.append(resp.json()["embedding"])
        return embeddings

    async def healthcheck(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
            if resp.status_code >= 400:
                return ProviderHealth(ok=False, detail=f"status {resp.status_code}")
            tags = [m["name"] for m in resp.json().get("models", [])]
            if not any(self.chat_model in t for t in tags):
                return ProviderHealth(
                    ok=False, detail=f"model {self.chat_model} not pulled; run `ollama pull {self.chat_model}`"
                )
            return ProviderHealth(ok=True)
        except httpx.HTTPError as exc:
            return ProviderHealth(ok=False, detail=str(exc))
