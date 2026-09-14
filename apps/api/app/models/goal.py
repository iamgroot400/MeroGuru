from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LearningGoal(Base):
    __tablename__ = "learning_goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    starting_level: Mapped[str] = mapped_column(String(50), default="beginner")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    minutes_per_day: Mapped[int] = mapped_column(Integer, default=30)
    study_days: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    preferred_formats: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    concepts: Mapped[list["GoalConcept"]] = relationship(back_populates="goal", cascade="all, delete-orphan")
    plans: Mapped[list["LearningPlan"]] = relationship(back_populates="goal", cascade="all, delete-orphan")


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    goal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_goals.id", ondelete="CASCADE"))
    external_key: Mapped[str] = mapped_column(String(100))  # the "id" the LLM assigned, unique per goal
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)


class GoalConcept(Base):
    __tablename__ = "goal_concepts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    goal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_goals.id", ondelete="CASCADE"))
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"))
    sequence_hint: Mapped[int] = mapped_column(Integer, default=0)
    required: Mapped[bool] = mapped_column(default=True)
    target_mastery: Mapped[float] = mapped_column(default=0.85)

    goal: Mapped[LearningGoal] = relationship(back_populates="concepts")
    concept: Mapped[Concept] = relationship()


class ConceptDependency(Base):
    __tablename__ = "concept_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"))
    prerequisite_concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"))
