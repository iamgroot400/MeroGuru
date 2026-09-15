from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentAttempt, AssessmentQuestion
from app.models.mastery import LearningEvent, MasteryRecord
from packages.learning_engine.adaptation.deterministic_rules import evaluate_floor, new_mastery_score
from packages.learning_engine.adaptation.signals import AssessmentEvent, compute_signals


def grade_attempt(assessment: Assessment, answers: dict[str, str]) -> tuple[float, dict[str, bool], dict[str, str]]:
    per_question: dict[str, bool] = {}
    explanations: dict[str, str] = {}
    correct = 0
    for question in assessment.questions:
        qid = str(question.id)
        given = answers.get(qid, "")
        is_correct = given.strip().lower() == question.expected_answer.strip().lower()
        per_question[qid] = is_correct
        explanations[qid] = question.explanation
        if is_correct:
            correct += 1
    score = correct / len(assessment.questions) if assessment.questions else 0.0
    return score, per_question, explanations


def _load_past_events(db: Session, goal_id: UUID, concept_id: UUID) -> list[AssessmentEvent]:
    """Reconstructs prior assessment history for this concept from the append-only
    learning_events log, so signals (trend, consecutive lows, distinct days) reflect
    real history rather than only the attempt just submitted."""
    rows = (
        db.query(LearningEvent)
        .filter(
            LearningEvent.goal_id == goal_id,
            LearningEvent.event_type == "assessment_completed",
            LearningEvent.event_data["concept_id"].astext == str(concept_id),
        )
        .order_by(LearningEvent.created_at.asc())
        .all()
    )
    events = []
    for row in rows:
        data = row.event_data
        events.append(
            AssessmentEvent(
                concept_id=str(concept_id),
                score=float(data.get("score", 0.0)),
                confidence=float(data.get("confidence", 0.5)),
                completed_at=row.created_at,
                time_spent_minutes=int(data.get("time_spent_minutes", 0)),
                estimated_minutes=int(data.get("estimated_minutes", 1)),
            )
        )
    return events


def _floor_mastery_state(floor) -> str:
    if floor.allow_mastered:
        return "mastered"
    if floor.advance_toward_proficiency:
        return "proficient"
    if floor.schedule_normal_review or floor.schedule_near_term_review:
        return "practicing"
    if floor.insert_easier_explanation:
        return "needs_review"
    return "not_started"


async def record_attempt_and_update_mastery(
    db: Session,
    goal_id: UUID,
    concept_id: UUID | None,
    lesson_id: UUID,
    score: float,
    confidence: float,
    time_spent_minutes: int,
    estimated_minutes: int,
) -> MasteryRecord | None:
    """Grades and updates mastery using the deterministic floor ONLY, with no
    network/AI call on this path -- this is what the learner's quiz submission
    waits on, so it must return in milliseconds regardless of how fast (or slow,
    or unreachable) an LLM backend is. The AI's optional supplementary
    suggestion is enriched afterward by enrich_adaptation_task, out of the
    request path entirely; the floor result below is never revised by it."""
    if concept_id is None:
        return None

    mastery = (
        db.query(MasteryRecord)
        .filter(MasteryRecord.goal_id == goal_id, MasteryRecord.concept_id == concept_id)
        .first()
    )
    if mastery is None:
        mastery = MasteryRecord(goal_id=goal_id, concept_id=concept_id, mastery_score=0.0, mastery_state="not_started")
        db.add(mastery)
        db.flush()

    now = datetime.now(timezone.utc)
    past_events = _load_past_events(db, goal_id, concept_id)
    current_event = AssessmentEvent(
        concept_id=str(concept_id),
        score=score,
        confidence=confidence,
        completed_at=now,
        time_spent_minutes=time_spent_minutes,
        estimated_minutes=estimated_minutes,
    )
    practice_completion = 1.0 if time_spent_minutes > 0 else 0.0

    previous_mastery = mastery.mastery_score
    signals = compute_signals(str(concept_id), [*past_events, current_event])
    floor = evaluate_floor(signals, previous_mastery=previous_mastery)

    mastery.mastery_score = new_mastery_score(previous_mastery, signals, practice_completion)
    mastery.mastery_state = _floor_mastery_state(floor)
    mastery.evidence_count += 1
    mastery.last_practiced_at = now

    event = LearningEvent(
        goal_id=goal_id,
        lesson_id=lesson_id,
        event_type="assessment_completed",
        event_data={
            "concept_id": str(concept_id),
            "score": score,
            "confidence": confidence,
            "time_spent_minutes": time_spent_minutes,
            "estimated_minutes": estimated_minutes,
            "floor_reasons": floor.reasons,
            "additional_support": [],
            "adaptation_source": "floor",
            "suggestion_rejected_reason": None,
            "new_mastery_score": mastery.mastery_score,
            "new_mastery_state": mastery.mastery_state,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(mastery)
    db.refresh(event)

    from workers.tasks import enrich_adaptation_task

    enrich_adaptation_task.delay(
        learning_event_id=str(event.id),
        concept_id=str(concept_id),
        previous_mastery=previous_mastery,
        practice_completion=practice_completion,
        current_event={
            "score": score,
            "confidence": confidence,
            "completed_at": now.isoformat(),
            "time_spent_minutes": time_spent_minutes,
            "estimated_minutes": estimated_minutes,
        },
        history=[
            {
                "score": e.score,
                "confidence": e.confidence,
                "completed_at": e.completed_at.isoformat(),
                "time_spent_minutes": e.time_spent_minutes,
                "estimated_minutes": e.estimated_minutes,
            }
            for e in past_events
        ],
    )

    return mastery
