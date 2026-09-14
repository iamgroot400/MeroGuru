from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class LessonActivityOut(BaseModel):
    id: UUID
    activity_type: str
    title: str
    instructions: str
    estimated_minutes: int
    resource_id: UUID | None
    sequence_number: int

    class Config:
        from_attributes = True


class LessonOut(BaseModel):
    id: UUID
    scheduled_date: date
    title: str
    objective: str
    estimated_minutes: int
    sequence_number: int
    status: str
    concept_ids: list[str]
    completed_at: datetime | None = None
    activities: list[LessonActivityOut] = []

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: UUID
    goal_id: UUID
    version: int
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    lessons: list[LessonOut] = []

    class Config:
        from_attributes = True


class LessonFeedback(BaseModel):
    difficulty: str  # too_easy | just_right | too_difficult
    usefulness: int  # 1-5
    confidence: float  # 0.0-1.0
    time_spent_minutes: int
