from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProviderCredential(Base):
    """One BYOK secret per provider. Single-tenant deployment: no owning user,
    since this app has no accounts. encrypted_secret is never returned by the API;
    only masked_label is exposed to callers."""

    __tablename__ = "provider_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(30))  # openai | anthropic | openai_compatible | ollama | youtube
    encrypted_secret: Mapped[str] = mapped_column(Text)
    masked_label: Mapped[str] = mapped_column(String(20))
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(20), default="untested")  # untested|ok|failed
    validation_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active_provider: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
