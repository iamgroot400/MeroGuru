from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProviderConfig(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    chat_model: str | None = None
    embedding_model: str | None = None


class AssessmentEventIn(BaseModel):
    score: float
    confidence: float
    completed_at: datetime
    time_spent_minutes: int
    estimated_minutes: int


class AdaptRequest(BaseModel):
    concept_id: str
    previous_mastery: float
    practice_completion: float
    current: AssessmentEventIn
    history: list[AssessmentEventIn] = []
    provider: ProviderConfig


class AdaptResponse(BaseModel):
    mastery_score: float
    mastery_state: str
    floor_reasons: list[str]
    additional_support: list[str]
    adaptation_source: str
    suggestion_rejected_reason: str | None = None


class RawEvent(BaseModel):
    event_type: str
    event_data: dict
    created_at: datetime


class AnalyticsRequest(BaseModel):
    events: list[RawEvent]


class AnalyticsResponse(BaseModel):
    score_trend: list[dict]
    mastery_progress: list[dict]
    time_spent_by_day: list[dict]
