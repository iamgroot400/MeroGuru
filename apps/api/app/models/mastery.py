from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MasteryRecord(Base):
    __tablename__ = "mastery_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    goal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_goals.id", ondelete="CASCADE"))
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"))
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    mastery_state: Mapped[str] = mapped_column(String(20), default="not_started")
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    goal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_goals.id", ondelete="CASCADE"))
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50))
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
