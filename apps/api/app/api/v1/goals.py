from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.goal import Concept, ConceptDependency, GoalConcept, LearningGoal
from app.models.job import BackgroundJob
from app.models.mastery import MasteryRecord
from app.models.plan import LearningPlan
from app.schemas.goal import ConceptOut, GoalCreate, GoalOut

router = APIRouter(prefix="/goals", tags=["goals"])


def _to_goal_out(db: Session, goal: LearningGoal) -> GoalOut:
    active_plan = (
        db.query(LearningPlan)
        .filter(LearningPlan.goal_id == goal.id)
        .order_by(LearningPlan.version.desc())
        .first()
    )
    pending_job = (
        db.query(BackgroundJob)
        .filter(
            BackgroundJob.entity_type == "learning_goal",
            BackgroundJob.entity_id == goal.id,
            BackgroundJob.status.in_(["queued", "running", "retrying"]),
        )
        .order_by(BackgroundJob.created_at.desc())
        .first()
    )
    return GoalOut(
        **{c.name: getattr(goal, c.name) for c in goal.__table__.columns},
        active_plan_id=active_plan.id if active_plan else None,
        job_id=pending_job.id if pending_job else None,
    )


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(payload: GoalCreate, db: Session = Depends(get_db)) -> GoalOut:
    goal = LearningGoal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _to_goal_out(db, goal)


@router.get("", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db)) -> list[GoalOut]:
    goals = db.query(LearningGoal).order_by(LearningGoal.created_at.desc()).all()
    return [_to_goal_out(db, g) for g in goals]


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: UUID, db: Session = Depends(get_db)) -> GoalOut:
    goal = db.get(LearningGoal, goal_id)
    if goal is None:
        raise HTTPException(404, "goal not found")
    return _to_goal_out(db, goal)


@router.post("/{goal_id}/generate-plan", status_code=202)
def trigger_plan_generation(goal_id: UUID, db: Session = Depends(get_db)) -> dict:
    goal = db.get(LearningGoal, goal_id)
    if goal is None:
        raise HTTPException(404, "goal not found")

    job = BackgroundJob(job_type="generate_plan", entity_type="learning_goal", entity_id=goal_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    from workers.tasks import generate_plan_task

    generate_plan_task.delay(str(goal_id), str(job.id))
    return {"job_id": str(job.id)}


@router.get("/{goal_id}/concept-map", response_model=list[ConceptOut])
def get_concept_map(goal_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    concepts = db.query(Concept).filter(Concept.goal_id == goal_id).all()
    deps = db.query(ConceptDependency).join(Concept, ConceptDependency.concept_id == Concept.id).filter(
        Concept.goal_id == goal_id
    ).all()
    prereqs_by_concept: dict[UUID, list[str]] = {}
    id_to_key = {c.id: c.external_key for c in concepts}
    for dep in deps:
        prereqs_by_concept.setdefault(dep.concept_id, []).append(id_to_key.get(dep.prerequisite_concept_id, ""))

    return [
        {
            "id": c.id,
            "external_key": c.external_key,
            "title": c.title,
            "description": c.description,
            "difficulty": c.difficulty,
            "estimated_minutes": c.estimated_minutes,
            "prerequisite_keys": prereqs_by_concept.get(c.id, []),
        }
        for c in concepts
    ]


@router.get("/{goal_id}/mastery")
def get_mastery(goal_id: UUID, db: Session = Depends(get_db)) -> dict:
    from app.models.assessment import Assessment, AssessmentAttempt
    from app.models.plan import Lesson, LearningPlan

    records = db.query(MasteryRecord).filter(MasteryRecord.goal_id == goal_id).all()
    concepts = {c.id: c for c in db.query(Concept).filter(Concept.goal_id == goal_id).all()}
    mastery_out = [
        {
            "concept_id": str(r.concept_id),
            "concept_title": concepts[r.concept_id].title if r.concept_id in concepts else "",
            "mastery_score": r.mastery_score,
            "mastery_state": r.mastery_state,
            "evidence_count": r.evidence_count,
            "last_practiced_at": r.last_practiced_at.isoformat() if r.last_practiced_at else None,
        }
        for r in records
    ]

    attempts = (
        db.query(AssessmentAttempt, Lesson.title)
        .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
        .join(Lesson, Assessment.lesson_id == Lesson.id)
        .join(LearningPlan, Lesson.plan_id == LearningPlan.id)
        .filter(LearningPlan.goal_id == goal_id)
        .order_by(AssessmentAttempt.completed_at.desc())
        .limit(50)
        .all()
    )
    history = [
        {
            "id": str(attempt.id),
            "title": lesson_title,
            "score": attempt.score,
            "created_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
        }
        for attempt, lesson_title in attempts
    ]

    return {"concepts": mastery_out, "assessment_history": history}
