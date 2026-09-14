from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    content_type: Mapped[str] = mapped_column(String(30))
    language: Mapped[str] = mapped_column(String(10), default="en")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    license_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_access: Mapped[str] = mapped_column(String(40), default="metadata-only")
    embeddable: Mapped[bool] = mapped_column(default=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    status: Mapped[str] = mapped_column(String(20), default="active")


class ResourceConcept(Base):
    __tablename__ = "resource_concepts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"))
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"))
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty_score: Mapped[float] = mapped_column(Float, default=0.0)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0)


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"))
    content_hash: Mapped[str] = mapped_column(String(64))
    permission_basis: Mapped[str] = mapped_column(String(40))
    ingestion_method: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    citation_locator: Mapped[str] = mapped_column(String(255), default="")
