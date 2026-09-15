from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentQuestion
from app.models.goal import Concept, ConceptDependency, GoalConcept, LearningGoal
from app.models.mastery import MasteryRecord
from app.models.plan import Lesson, LessonActivity, LearningPlan
from app.models.resource import Resource
from app.services.credential_service import get_active_ai_provider, get_youtube_api_key
from packages.ai_providers.base import GenerationRequest
from packages.connectors.base import SearchRequest
from packages.connectors.mediawiki import MediaWikiConnector
from packages.connectors.youtube import YouTubeConnector
from packages.learning_engine.concept_mapping import ConceptGraphError, generate_concept_map
from packages.learning_engine.planning import build_plan
from packages.learning_engine.resource_selection import select_best_resource
from prompts.lesson import LESSON_CONTENT_SCHEMA, SYSTEM_PROMPT as LESSON_SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class PlanGenerationError(RuntimeError):
    pass


async def generate_roadmap_and_plan(db: Session, goal_id: UUID) -> LearningPlan:
    goal = db.get(LearningGoal, goal_id)
    if goal is None:
        raise PlanGenerationError(f"goal {goal_id} not found")

    provider = get_active_ai_provider(db)

    try:
        concepts = await generate_concept_map(
            provider=provider,
            goal_title=goal.title,
            goal_description=goal.description,
            starting_level=goal.starting_level,
        )
    except ConceptGraphError as exc:
        raise PlanGenerationError(f"concept map generation failed: {exc}") from exc

    key_to_db_id: dict[str, UUID] = {}
    db_concepts: dict[str, Concept] = {}
    for i, concept in enumerate(concepts):
        row = Concept(
            goal_id=goal.id,
            external_key=concept.id,
            title=concept.title,
            description=concept.description,
            difficulty=concept.difficulty,
            estimated_minutes=concept.estimated_minutes,
        )
        db.add(row)
        db.flush()
        key_to_db_id[concept.id] = row.id
        db_concepts[concept.id] = row
        db.add(GoalConcept(goal_id=goal.id, concept_id=row.id, sequence_hint=i, required=True))
        db.add(MasteryRecord(goal_id=goal.id, concept_id=row.id, mastery_score=0.0, mastery_state="not_started"))

    for concept in concepts:
        for prereq_key in concept.prerequisite_ids:
            db.add(
                ConceptDependency(
                    concept_id=key_to_db_id[concept.id],
                    prerequisite_concept_id=key_to_db_id[prereq_key],
                )
            )
    db.flush()

    plan_result = build_plan(
        concepts=concepts,
        start_date=date.today(),
        minutes_per_day=goal.minutes_per_day,
        study_days=goal.study_days,
        horizon_days=7,
    )
    if plan_result.warnings:
        logger.warning("plan generation warnings for goal %s: %s", goal_id, plan_result.warnings)

    plan = LearningPlan(
        goal_id=goal.id,
        version=1,
        start_date=plan_result.lessons[0].scheduled_date if plan_result.lessons else date.today(),
        end_date=plan_result.lessons[-1].scheduled_date if plan_result.lessons else date.today(),
        status="active",
        generation_metadata={
            "warnings": plan_result.warnings,
            "unscheduled_concept_ids": plan_result.unscheduled_concept_ids,
        },
    )
    db.add(plan)
    db.flush()

    youtube_key = get_youtube_api_key(db)
    youtube = YouTubeConnector(youtube_key) if youtube_key else None
    mediawiki = MediaWikiConnector()

    for scheduled in plan_result.lessons:
        lesson_concepts = [db_concepts[cid] for cid in scheduled.concept_ids]
        lesson = Lesson(
            plan_id=plan.id,
            scheduled_date=scheduled.scheduled_date,
            title=" & ".join(c.title for c in lesson_concepts),
            objective=f"Understand and apply: {', '.join(c.title for c in lesson_concepts)}",
            estimated_minutes=scheduled.estimated_minutes,
            sequence_number=scheduled.day_index,
            concept_ids=scheduled.concept_ids,
        )
        db.add(lesson)
        db.flush()

        content_request = GenerationRequest(
            system_prompt=LESSON_SYSTEM_PROMPT,
            user_prompt=build_user_prompt(
                concept_titles=[c.title for c in lesson_concepts],
                concept_descriptions=[c.description for c in lesson_concepts],
                source_excerpt=None,
            ),
            max_tokens=3500,
        )
        content = await provider.generate_structured(content_request, LESSON_CONTENT_SCHEMA)

        seq = 0
        if content.valid:
            takeaways = content.data.get("key_takeaways") or []
            takeaways_md = "\n".join(f"- {item}" for item in takeaways)
            explanation_text = content.data["explanation"]
            if takeaways_md:
                explanation_text = f"{explanation_text}\n\n## Key takeaways\n{takeaways_md}"
            db.add(
                LessonActivity(
                    lesson_id=lesson.id,
                    activity_type="explanation",
                    title="Explanation",
                    instructions=explanation_text,
                    estimated_minutes=max(5, scheduled.estimated_minutes // 3),
                    sequence_number=seq,
                )
            )
            seq += 1
        else:
            logger.warning("lesson content generation invalid for lesson %s: %s", lesson.id, content.validation_errors)
            db.add(
                LessonActivity(
                    lesson_id=lesson.id,
                    activity_type="explanation",
                    title="Explanation unavailable",
                    instructions=(
                        "The AI-generated explanation failed validation. Review the linked "
                        "resource directly for this concept, or retry plan generation."
                    ),
                    estimated_minutes=max(5, scheduled.estimated_minutes // 3),
                    sequence_number=seq,
                )
            )
            seq += 1

        primary_resource: Resource | None = None
        all_candidates: list = []
        concept_query = lesson_concepts[0].title

        if youtube is not None:
            try:
                all_candidates.extend(
                    await youtube.search(SearchRequest(query=concept_query, max_results=5))
                )
            except Exception as exc:  # connector failure must not block plan generation
                logger.warning("youtube search failed for concept %s: %s", concept_query, exc)

        try:
            all_candidates.extend(
                await mediawiki.search(SearchRequest(query=concept_query, max_results=3))
            )
        except Exception as exc:
            logger.warning("mediawiki search failed for concept %s: %s", concept_query, exc)

        best = select_best_resource(all_candidates, lesson_concepts[0], language="en")
        if best is not None:
            candidate, resource_score = best
            primary_resource = Resource(
                provider=candidate.provider,
                external_id=candidate.external_id,
                url=candidate.url,
                title=candidate.title,
                author=candidate.author,
                description=candidate.metadata.get("description", "") or candidate.metadata.get("snippet", ""),
                content_type=candidate.content_type,
                language=candidate.language,
                duration_seconds=candidate.duration_seconds,
                license_name=candidate.license_name,
                content_access=candidate.content_access.value,
                embeddable=candidate.embeddable,
                metadata_json={
                    **candidate.metadata,
                    "ranking_score": resource_score.total,
                    "ranking_components": resource_score.components,
                    "candidates_considered": len(all_candidates),
                },
            )
            db.add(primary_resource)
            db.flush()

        if primary_resource is not None:
            verb = "Watch" if primary_resource.content_type == "video" else "Read"
            db.add(
                LessonActivity(
                    lesson_id=lesson.id,
                    activity_type="resource",
                    title=primary_resource.title,
                    instructions=f"{verb}: {primary_resource.url}",
                    estimated_minutes=(primary_resource.duration_seconds or 600) // 60,
                    resource_id=primary_resource.id,
                    sequence_number=seq,
                )
            )
            seq += 1

        if content.valid:
            db.add(
                LessonActivity(
                    lesson_id=lesson.id,
                    activity_type="practice",
                    title="Practice",
                    instructions=content.data["practice_task"],
                    estimated_minutes=max(10, scheduled.estimated_minutes // 3),
                    sequence_number=seq,
                )
            )
            seq += 1

            assessment = Assessment(lesson_id=lesson.id, assessment_type="quiz", passing_score=0.70, generation_source="ai")
            db.add(assessment)
            db.flush()
            for q in content.data["quiz"]:
                db.add(
                    AssessmentQuestion(
                        assessment_id=assessment.id,
                        concept_id=lesson_concepts[0].id,
                        question_type="multiple_choice",
                        prompt=q["prompt"],
                        options_json=q["options"],
                        expected_answer=q["correct_answer"],
                        explanation=q["explanation"],
                        difficulty=lesson_concepts[0].difficulty,
                    )
                )

    db.commit()
    db.refresh(plan)
    return plan
