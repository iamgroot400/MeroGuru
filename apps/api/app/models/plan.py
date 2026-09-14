from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    goal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_goals.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    generation_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    goal = relationship("LearningGoal", back_populates="plans")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_plans.id", ondelete="CASCADE"))
    scheduled_date: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(255))
    objective: Mapped[str] = mapped_column(Text)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    sequence_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    concept_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped[LearningPlan] = relationship(back_populates="lessons")
    activities: Mapped[list["LessonActivity"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")


class LessonActivity(Base):
    __tablename__ = "lesson_activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"))
    activity_type: Mapped[str] = mapped_column(String(30))  # explanation | resource | practice | assessment
    title: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text, default="")
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("resources.id"), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer)

    lesson: Mapped[Lesson] = relationship(back_populates="activities")
