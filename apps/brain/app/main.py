"""MeroGuru brain service: the adaptation engine and learner-data processing,
split out from the orchestrator (apps/api) so the two concerns scale and fail
independently. Stateless by design -- no database of its own. The orchestrator
owns all persistence and passes this service exactly the context it needs for
each call, then persists whatever comes back.

Two responsibilities live here:
1. /brain/v1/adapt -- the floor/estimator/verdict adaptation pipeline
   (packages/learning_engine/adaptation/) that decides how a learner's plan
   should react to a quiz result.
2. /brain/v1/analytics -- turning the raw learning_events log into the
   time-series shapes the Progress page charts.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.schemas import AdaptRequest, AdaptResponse, AnalyticsRequest, AnalyticsResponse
from packages.ai_providers.base import AIProviderError
from packages.ai_providers.registry import build_provider
from packages.learning_engine.adaptation.apply import run_adaptation
from packages.learning_engine.adaptation.signals import AssessmentEvent
from packages.learning_engine.analytics import RawEvent, compute_analytics

app = FastAPI(title="MeroGuru Brain", version="0.1.0")


@app.get("/health/live")
def health_live() -> dict:
    return {"status": "ok"}


def _to_assessment_event(concept_id: str, e) -> AssessmentEvent:
    return AssessmentEvent(
        concept_id=concept_id,
        score=e.score,
        confidence=e.confidence,
        completed_at=e.completed_at,
        time_spent_minutes=e.time_spent_minutes,
        estimated_minutes=e.estimated_minutes,
    )


@app.post("/brain/v1/adapt", response_model=AdaptResponse)
async def adapt(payload: AdaptRequest) -> AdaptResponse:
    try:
        provider = build_provider(
            provider=payload.provider.provider,
            api_key=payload.provider.api_key,
            base_url=payload.provider.base_url,
            chat_model=payload.provider.chat_model,
            embedding_model=payload.provider.embedding_model,
        )
    except (ValueError, AIProviderError) as exc:
        raise HTTPException(422, f"could not build AI provider: {exc}") from exc

    result = await run_adaptation(
        provider=provider,
        concept_id=payload.concept_id,
        previous_mastery=payload.previous_mastery,
        practice_completion=payload.practice_completion,
        current=_to_assessment_event(payload.concept_id, payload.current),
        history=[_to_assessment_event(payload.concept_id, e) for e in payload.history],
    )
    return AdaptResponse(
        mastery_score=result.mastery_score,
        mastery_state=result.mastery_state,
        floor_reasons=result.floor_reasons,
        additional_support=result.additional_support,
        adaptation_source=result.adaptation_source,
        suggestion_rejected_reason=result.suggestion_rejected_reason,
    )


@app.post("/brain/v1/analytics", response_model=AnalyticsResponse)
def analytics(payload: AnalyticsRequest) -> AnalyticsResponse:
    raw = [RawEvent(event_type=e.event_type, event_data=e.event_data, created_at=e.created_at) for e in payload.events]
    result = compute_analytics(raw)
    return AnalyticsResponse(**result)
