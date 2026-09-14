from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"))
    assessment_type: Mapped[str] = mapped_column(String(30), default="quiz")
    passing_score: Mapped[float] = mapped_column(Float, default=0.70)
    generation_source: Mapped[str] = mapped_column(String(30), default="ai")

    questions: Mapped[list["AssessmentQuestion"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"))
    concept_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("concepts.id"), nullable=True)
    question_type: Mapped[str] = mapped_column(String(20))  # multiple_choice | short_answer
    prompt: Mapped[str] = mapped_column(Text)
    options_json: Mapped[list] = mapped_column(JSONB, default=list)
    expected_answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("source_chunks.id"), nullable=True)

    assessment: Mapped[Assessment] = relationship(back_populates="questions")


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"))
    answers_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    grading_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
