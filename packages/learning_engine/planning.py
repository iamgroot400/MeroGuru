"""Deterministic scheduler: turns a concept graph into a day-by-day plan that respects
the learner's declared time budget. The AI proposes lesson content; this module owns
the scheduling math so a plan can never silently exceed what the learner asked for.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from packages.learning_engine.concept_mapping import Concept, topological_order

TRANSITION_ALLOWANCE_MINUTES = 5


@dataclass
class ScheduledLesson:
    day_index: int
    scheduled_date: date
    concept_ids: list[str]
    estimated_minutes: int


@dataclass
class PlanResult:
    lessons: list[ScheduledLesson]
    unscheduled_concept_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def build_plan(
    concepts: list[Concept],
    start_date: date,
    minutes_per_day: int,
    study_days: list[int],
    horizon_days: int = 7,
) -> PlanResult:
    """study_days: 0=Monday .. 6=Sunday, the weekdays the learner actually studies."""
    if minutes_per_day <= 0:
        raise ValueError("minutes_per_day must be positive")
    if not study_days:
        raise ValueError("at least one study day is required")

    ordered = topological_order(concepts)
    study_dates = _next_study_dates(start_date, study_days, horizon_days)

    lessons: list[ScheduledLesson] = []
    warnings: list[str] = []
    remaining = list(ordered)
    day_index = 0

    for scheduled_date in study_dates:
        if not remaining:
            break
        budget = minutes_per_day
        todays_concepts: list[str] = []
        while remaining:
            candidate = remaining[0]
            cost = candidate.estimated_minutes + TRANSITION_ALLOWANCE_MINUTES
            if cost > minutes_per_day:
                warnings.append(
                    f"concept '{candidate.id}' ({candidate.estimated_minutes}min) exceeds the "
                    f"daily budget of {minutes_per_day}min on its own; scheduled anyway as its own day"
                )
                todays_concepts.append(remaining.pop(0).id)
                budget = 0
                break
            if cost > budget:
                break
            todays_concepts.append(remaining.pop(0).id)
            budget -= cost
        if todays_concepts:
            used = minutes_per_day - budget if budget >= 0 else minutes_per_day
            lessons.append(
                ScheduledLesson(
                    day_index=day_index,
                    scheduled_date=scheduled_date,
                    concept_ids=todays_concepts,
                    estimated_minutes=used,
                )
            )
            day_index += 1

    for lesson in lessons:
        if lesson.estimated_minutes > minutes_per_day * 1.10:
            warnings.append(
                f"day {lesson.day_index} estimated at {lesson.estimated_minutes}min, "
                f"over the {minutes_per_day}min budget by more than 10%"
            )

    return PlanResult(
        lessons=lessons,
        unscheduled_concept_ids=[c.id for c in remaining],
        warnings=warnings,
    )


def _next_study_dates(start_date: date, study_days: list[int], horizon_days: int) -> list[date]:
    dates: list[date] = []
    cursor = start_date
    # Look ahead enough calendar days to fill horizon_days worth of study sessions.
    max_lookahead = horizon_days * 3 + 14
    for _ in range(max_lookahead):
        if cursor.weekday() in study_days:
            dates.append(cursor)
            if len(dates) >= horizon_days:
                break
        cursor += timedelta(days=1)
    return dates
