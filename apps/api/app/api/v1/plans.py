from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.plan import Lesson, LearningPlan
from app.schemas.plan import LessonFeedback, LessonOut, PlanOut

router = APIRouter(tags=["plans"])


@router.get("/plans/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: UUID, db: Session = Depends(get_db)) -> LearningPlan:
    plan = (
        db.query(LearningPlan)
        .options(joinedload(LearningPlan.lessons).joinedload(Lesson.activities))
        .filter(LearningPlan.id == plan_id)
        .first()
    )
    if plan is None:
        raise HTTPException(404, "plan not found")
    return plan


@router.get("/plans/{plan_id}/today", response_model=LessonOut)
def get_todays_lesson(plan_id: UUID, db: Session = Depends(get_db)) -> Lesson:
    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.activities))
        .filter(Lesson.plan_id == plan_id, Lesson.scheduled_date <= date.today())
        .order_by(Lesson.scheduled_date.desc())
        .first()
    )
    if lesson is None:
        raise HTTPException(404, "no lesson scheduled yet for today or earlier")
    return lesson


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: UUID, db: Session = Depends(get_db)) -> Lesson:
    lesson = db.query(Lesson).options(joinedload(Lesson.activities)).filter(Lesson.id == lesson_id).first()
    if lesson is None:
        raise HTTPException(404, "lesson not found")
    return lesson


@router.post("/lessons/{lesson_id}/complete", response_model=LessonOut)
def complete_lesson(lesson_id: UUID, db: Session = Depends(get_db)) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, "lesson not found")
    if lesson.status == "completed":
        return lesson  # completed lesson history is immutable; no-op rather than error
    lesson.status = "completed"
    lesson.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.post("/lessons/{lesson_id}/feedback", status_code=204)
def submit_lesson_feedback(lesson_id: UUID, payload: LessonFeedback, db: Session = Depends(get_db)) -> None:
    from app.models.mastery import LearningEvent

    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, "lesson not found")

    plan = db.get(LearningPlan, lesson.plan_id)
    db.add(
        LearningEvent(
            goal_id=plan.goal_id,
            lesson_id=lesson.id,
            event_type="lesson_feedback",
            event_data=payload.model_dump(),
        )
    )
    db.commit()
