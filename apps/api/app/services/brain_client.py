from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from packages.learning_engine.adaptation.signals import AssessmentEvent


def _event_to_json(e: AssessmentEvent) -> dict:
    return {
        "score": e.score,
        "confidence": e.confidence,
        "completed_at": e.completed_at.isoformat(),
        "time_spent_minutes": e.time_spent_minutes,
        "estimated_minutes": e.estimated_minutes,
    }


async def adapt(
    provider_config: dict,
    concept_id: str,
    previous_mastery: float,
    practice_completion: float,
    current: AssessmentEvent,
    history: list[AssessmentEvent],
) -> dict:
    """Calls the brain service's adaptation pipeline. Raises on transport/HTTP
    failure -- callers decide whether to fall back (the brain itself already
    falls back to the deterministic floor for AI-side failures; this is for
    the brain being unreachable entirely)."""
    payload = {
        "concept_id": concept_id,
        "previous_mastery": previous_mastery,
        "practice_completion": practice_completion,
        "current": _event_to_json(current),
        "history": [_event_to_json(e) for e in history],
        "provider": provider_config,
    }
    async with httpx.AsyncClient(base_url=settings.brain_base_url, timeout=60.0) as client:
        response = await client.post("/brain/v1/adapt", json=payload)
        response.raise_for_status()
        return response.json()


async def analytics(events: list[dict]) -> dict:
    """events: raw {event_type, event_data, created_at} dicts as read straight
    off LearningEvent rows -- created_at must already be an ISO string or a
    datetime (httpx/pydantic will serialize either via json.dumps below)."""
    payload = {
        "events": [
            {
                "event_type": e["event_type"],
                "event_data": e["event_data"],
                "created_at": e["created_at"].isoformat() if isinstance(e["created_at"], datetime) else e["created_at"],
            }
            for e in events
        ]
    }
    async with httpx.AsyncClient(base_url=settings.brain_base_url, timeout=30.0) as client:
        response = await client.post("/brain/v1/analytics", json=payload)
        response.raise_for_status()
        return response.json()
