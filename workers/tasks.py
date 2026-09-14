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
