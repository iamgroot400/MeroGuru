from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = ""
    starting_level: str = "beginner"
    target_date: date | None = None
    minutes_per_day: int = Field(default=30, gt=0, le=600)
    study_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    preferred_formats: list[str] = Field(default_factory=lambda: ["mixed"])


class GoalOut(BaseModel):
    id: UUID
    title: str
    description: str
    starting_level: str
    target_date: date | None
    minutes_per_day: int
    study_days: list[int]
    preferred_formats: list[str]
    status: str
    created_at: datetime
    active_plan_id: UUID | None = None
    job_id: UUID | None = None

    class Config:
        from_attributes = True


class ConceptOut(BaseModel):
    id: UUID
    external_key: str
    title: str
    description: str
    difficulty: str
    estimated_minutes: int
    prerequisite_keys: list[str]

    class Config:
        from_attributes = True
