from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


@celery_app.task(name="generate_plan_task", bind=True, max_retries=MAX_RETRIES)
def generate_plan_task(self, goal_id: str, job_id: str) -> None:
    from app.db.session import SessionLocal
    from app.models.job import BackgroundJob
    from app.services.plan_service import PlanGenerationError, generate_roadmap_and_plan

    db = SessionLocal()
    job = db.get(BackgroundJob, job_id)
    try:
        if job is not None:
            job.status = "running"
            job.attempt_count += 1
            db.commit()

        asyncio.run(generate_roadmap_and_plan(db, goal_id))

        if job is not None:
            job.status = "completed"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    except PlanGenerationError as exc:
        logger.error("plan generation failed for goal %s: %s", goal_id, exc)
        if job is not None:
            job.status = "failed"
            job.error_code = "plan_generation_failed"
            job.error_summary = str(exc)[:500]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as exc:  # unexpected errors still leave a visible, recoverable job state
        db.rollback()
        logger.exception("unexpected error generating plan for goal %s", goal_id)
        job = db.get(BackgroundJob, job_id)
        if job is not None:
            if job.attempt_count < MAX_RETRIES:
                job.status = "retrying"
                job.error_summary = str(exc)[:500]
                db.commit()
                raise self.retry(exc=exc, countdown=10)
            job.status = "failed"
            job.error_code = "unexpected_error"
            job.error_summary = str(exc)[:500]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@celery_app.task(name="enrich_adaptation_task", max_retries=1)
def enrich_adaptation_task(
    learning_event_id: str,
    concept_id: str,
    previous_mastery: float,
    practice_completion: float,
    current_event: dict,
    history: list[dict],
) -> None:
    """Runs the AI estimator's supplementary suggestion out of the request path.
    Quiz grading already committed the deterministic floor result synchronously
    (see mastery_service.record_attempt_and_update_mastery) and returned to the
    learner instantly; this task only ever adds additional_support metadata onto
    that already-final learning_event, never revises mastery_score/mastery_state.
    A failure here (brain down, AI call fails, timeout) just leaves the event at
    its floor-only defaults -- there is nothing to roll back."""
    def _to_event(e: dict):
        from packages.learning_engine.adaptation.signals import AssessmentEvent

        return AssessmentEvent(
            concept_id=concept_id,
            score=e["score"],
            confidence=e["confidence"],
            completed_at=datetime.fromisoformat(e["completed_at"]),
            time_spent_minutes=e["time_spent_minutes"],
            estimated_minutes=e["estimated_minutes"],
        )

    db = None
    try:
        from app.db.session import SessionLocal
        from app.models.mastery import LearningEvent
        from app.services import brain_client
        from app.services.credential_service import get_active_ai_provider_config

        db = SessionLocal()
        provider_config = get_active_ai_provider_config(db)
        result = asyncio.run(
            brain_client.adapt(
                provider_config=provider_config,
                concept_id=concept_id,
                previous_mastery=previous_mastery,
                practice_completion=practice_completion,
                current=_to_event(current_event),
                history=[_to_event(e) for e in history],
            )
        )
        if not result["additional_support"] and result["adaptation_source"] == "floor":
            return  # nothing to add -- leave the event at its already-correct defaults

        event = db.get(LearningEvent, learning_event_id)
        if event is None:
            return
        event.event_data = {
            **event.event_data,
            "additional_support": result["additional_support"],
            "adaptation_source": result["adaptation_source"],
            "suggestion_rejected_reason": result["suggestion_rejected_reason"],
        }
        db.commit()
    except Exception:
        logger.exception("adaptation enrichment failed for learning_event %s", learning_event_id)
    finally:
        if db is not None:
            db.close()
