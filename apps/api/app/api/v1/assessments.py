from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentAttempt
from app.models.plan import Lesson, LearningPlan
from app.schemas.assessment import AssessmentOut, AttemptResult, AttemptSubmit
from app.services.mastery_service import grade_attempt, record_attempt_and_update_mastery

router = APIRouter(tags=["assessments"])


@router.get("/lessons/{lesson_id}/assessment", response_model=AssessmentOut)
def get_assessment_for_lesson(lesson_id: UUID, db: Session = Depends(get_db)) -> Assessment:
    assessment = (
        db.query(Assessment)
        .options(joinedload(Assessment.questions))
        .filter(Assessment.lesson_id == lesson_id)
        .first()
    )
    if assessment is None:
        raise HTTPException(404, "no assessment for this lesson")
    return assessment


@router.post("/assessments/{assessment_id}/attempts", response_model=AttemptResult)
async def submit_attempt(assessment_id: UUID, payload: AttemptSubmit, db: Session = Depends(get_db)) -> AttemptResult:
    assessment = (
        db.query(Assessment)
        .options(joinedload(Assessment.questions))
        .filter(Assessment.id == assessment_id)
        .first()
    )
    if assessment is None:
        raise HTTPException(404, "assessment not found")

    score, per_question, explanations = grade_attempt(assessment, payload.answers)

    from datetime import datetime, timezone

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        answers_json=payload.answers,
        score=score,
        confidence=payload.confidence,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(attempt)

    lesson = db.get(Lesson, assessment.lesson_id)
    plan = db.get(LearningPlan, lesson.plan_id) if lesson else None
    concept_id = assessment.questions[0].concept_id if assessment.questions else None

    if lesson is not None and plan is not None:
        await record_attempt_and_update_mastery(
            db=db,
            goal_id=plan.goal_id,
            concept_id=concept_id,
            lesson_id=lesson.id,
            score=score,
            confidence=payload.confidence,
            time_spent_minutes=lesson.estimated_minutes,
            estimated_minutes=lesson.estimated_minutes,
        )
    else:
        db.commit()

    return AttemptResult(
        score=score,
        passed=score >= assessment.passing_score,
        per_question=per_question,
        explanations=explanations,
    )
