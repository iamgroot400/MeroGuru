from __future__ import annotations

from datetime import datetime, timezone

from workers.tasks import enrich_adaptation_task


def test_task_is_registered_with_expected_name():
    """Sanity check that the task imports cleanly and is wired up under the
    name mastery_service.record_attempt_and_update_mastery calls via .delay()."""
    assert enrich_adaptation_task.name == "enrich_adaptation_task"


def test_task_handles_brain_failure_without_raising(monkeypatch):
    """The whole point of this task is best-effort enrichment: a failure here
    (brain down, bad provider, DB error) must never surface as a Celery
    failure/retry storm -- the floor-only event is already correct and final."""
    import app.services.brain_client as brain_client_module

    async def _boom(**kwargs):
        raise RuntimeError("brain unreachable")

    monkeypatch.setattr(brain_client_module, "adapt", _boom)

    # .run() executes the task body synchronously without a broker.
    enrich_adaptation_task.run(
        learning_event_id="00000000-0000-0000-0000-000000000000",
        concept_id="c1",
        previous_mastery=0.4,
        practice_completion=1.0,
        current_event={
            "score": 0.9,
            "confidence": 0.8,
            "completed_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
            "time_spent_minutes": 20,
            "estimated_minutes": 20,
        },
        history=[],
    )
