from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SECRET = "test-brain-secret"
AUTH = {"X-Brain-Auth": SECRET}


@pytest.fixture(autouse=True)
def _brain_secret(monkeypatch):
    monkeypatch.setenv("BRAIN_SHARED_SECRET", SECRET)


def test_health_live():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_adapt_falls_back_to_floor_when_ai_call_fails():
    """An unreachable/invalid provider must never break grading -- the floor
    always applies on its own, mirroring run_adaptation's fail-safe try/except
    around propose_adaptation."""
    payload = {
        "concept_id": "c1",
        "previous_mastery": 0.4,
        "practice_completion": 1.0,
        "current": {
            "score": 0.9,
            "confidence": 0.8,
            "completed_at": "2026-01-01T00:00:00Z",
            "time_spent_minutes": 20,
            "estimated_minutes": 20,
        },
        "history": [],
        "provider": {
            "provider": "ollama",
            "base_url": "http://unreachable.invalid:11434",
            "chat_model": "llama3.1",
            "embedding_model": "nomic-embed-text",
        },
    }
    response = client.post("/brain/v1/adapt", json=payload, headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["adaptation_source"] == "floor"
    assert body["additional_support"] == []
    assert "85%" in body["floor_reasons"][0] or body["floor_reasons"]


def test_adapt_rejects_unknown_provider():
    payload = {
        "concept_id": "c1",
        "previous_mastery": 0.4,
        "practice_completion": 1.0,
        "current": {
            "score": 0.9,
            "confidence": 0.8,
            "completed_at": "2026-01-01T00:00:00Z",
            "time_spent_minutes": 20,
            "estimated_minutes": 20,
        },
        "history": [],
        "provider": {"provider": "not-a-real-provider"},
    }
    response = client.post("/brain/v1/adapt", json=payload, headers=AUTH)
    assert response.status_code == 422


def test_analytics_derives_score_trend_and_time_spent():
    payload = {
        "events": [
            {
                "event_type": "assessment_completed",
                "event_data": {"concept_id": "c1", "score": 0.9, "new_mastery_state": "mastered"},
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "event_type": "lesson_feedback",
                "event_data": {"time_spent_minutes": 15},
                "created_at": "2026-01-01T12:00:00Z",
            },
        ]
    }
    response = client.post("/brain/v1/analytics", json=payload, headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["score_trend"] == [{"date": "2026-01-01", "score": 0.9, "concept_id": "c1"}]
    assert body["mastery_progress"] == [{"date": "2026-01-01", "mastered_count": 1}]
    assert body["time_spent_by_day"] == [{"date": "2026-01-01", "minutes": 15}]


def _minimal_payload(base_url: str = "http://unreachable.invalid:11434") -> dict:
    return {
        "concept_id": "c1",
        "previous_mastery": 0.4,
        "practice_completion": 1.0,
        "current": {
            "score": 0.9,
            "confidence": 0.8,
            "completed_at": "2026-01-01T00:00:00Z",
            "time_spent_minutes": 20,
            "estimated_minutes": 20,
        },
        "history": [],
        "provider": {"provider": "ollama", "base_url": base_url, "chat_model": "llama3.1"},
    }


def test_adapt_rejects_unauthenticated_callers():
    """The adapt endpoint issues outbound HTTP using the base_url and api_key in
    the request body. Unauthenticated, it is an open SSRF proxy that also lets
    the caller choose the Authorization header it sends."""
    response = client.post("/brain/v1/adapt", json=_minimal_payload())
    assert response.status_code == 401


def test_adapt_rejects_wrong_secret():
    response = client.post(
        "/brain/v1/adapt", json=_minimal_payload(), headers={"X-Brain-Auth": "wrong"}
    )
    assert response.status_code == 401


def test_analytics_rejects_unauthenticated_callers():
    response = client.post("/brain/v1/analytics", json={"events": []})
    assert response.status_code == 401


def test_brain_fails_closed_when_secret_unset(monkeypatch):
    """An unset secret must refuse everything rather than silently reverting to
    open access."""
    monkeypatch.delenv("BRAIN_SHARED_SECRET", raising=False)
    response = client.post("/brain/v1/adapt", json=_minimal_payload(), headers=AUTH)
    assert response.status_code == 503


def test_adapt_refuses_link_local_provider_url():
    """Even an authenticated caller cannot aim the brain at instance metadata."""
    response = client.post(
        "/brain/v1/adapt",
        json=_minimal_payload(base_url="http://169.254.169.254/latest"),
        headers=AUTH,
    )
    assert response.status_code == 422
    assert "link-local" in response.json()["detail"]


def test_health_live_needs_no_auth():
    assert client.get("/health/live").status_code == 200
