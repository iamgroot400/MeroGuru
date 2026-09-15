from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.services import brain_client
from packages.learning_engine.adaptation.signals import AssessmentEvent


def test_adapt_raises_when_brain_unreachable(monkeypatch):
    """mastery_service relies on this raising (not silently returning a bad
    result) so its except-block can fall back to the local deterministic floor."""
    monkeypatch.setattr(settings, "brain_base_url", "http://unreachable.invalid:8100")
    event = AssessmentEvent(
        concept_id="c1", score=0.9, confidence=0.8,
        completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        time_spent_minutes=20, estimated_minutes=20,
    )
    with pytest.raises(Exception):
        import asyncio

        asyncio.run(
            brain_client.adapt(
                provider_config={"provider": "ollama"},
                concept_id="c1",
                previous_mastery=0.4,
                practice_completion=1.0,
                current=event,
                history=[],
            )
        )


def test_analytics_raises_when_brain_unreachable(monkeypatch):
    monkeypatch.setattr(settings, "brain_base_url", "http://unreachable.invalid:8100")
    with pytest.raises(Exception):
        import asyncio

        asyncio.run(
            brain_client.analytics(
                [{"event_type": "assessment_completed", "event_data": {}, "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)}]
            )
        )
