from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CredentialCreate(BaseModel):
    provider: str = Field(pattern="^(openai|anthropic|openai_compatible|ollama|youtube)$")
    api_key: str = Field(min_length=1)
    base_url: str | None = None
    chat_model: str | None = None
    embedding_model: str | None = None


class CredentialOut(BaseModel):
    id: UUID
    provider: str
    masked_label: str
    base_url: str | None
    chat_model: str | None
    validation_status: str
    validation_detail: str | None
    is_active_provider: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CredentialTestResult(BaseModel):
    ok: bool
    detail: str
