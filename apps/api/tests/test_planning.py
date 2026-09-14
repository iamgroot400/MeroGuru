from __future__ import annotations

from datetime import date

from packages.learning_engine.concept_mapping import Concept
from packages.learning_engine.planning import build_plan


def _concept(id_, minutes, prereqs=None):
    return Concept(id=id_, title=id_, description="", difficulty="beginner", estimated_minutes=minutes, prerequisite_ids=prereqs or [])


def test_plan_never_exceeds_daily_budget_by_more_than_10_percent():
    concepts = [_concept(f"c{i}", 20) for i in range(10)]
    result = build_plan(
        concepts=concepts,
        start_date=date(2026, 1, 5),  # Monday
        minutes_per_day=30,
        study_days=[0, 1, 2, 3, 4],
        horizon_days=7,
    )
    for lesson in result.lessons:
        assert lesson.estimated_minutes <= 30 * 1.10


def test_plan_only_schedules_on_study_days():
    concepts = [_concept(f"c{i}", 20) for i in range(3)]
    result = build_plan(
        concepts=concepts,
        start_date=date(2026, 1, 5),  # Monday
        minutes_per_day=30,
        study_days=[1, 3],  # Tue, Thu only
        horizon_days=3,
    )
    for lesson in result.lessons:
        assert lesson.scheduled_date.weekday() in (1, 3)


def test_oversized_concept_gets_its_own_day_with_a_warning():
    concepts = [_concept("big", 500)]
    result = build_plan(
        concepts=concepts,
        start_date=date(2026, 1, 5),
        minutes_per_day=30,
        study_days=[0, 1, 2, 3, 4],
        horizon_days=7,
    )
    assert len(result.lessons) == 1
    assert result.lessons[0].concept_ids == ["big"]
    assert any("exceeds the daily budget" in w for w in result.warnings)


def test_all_concepts_get_scheduled_when_they_fit():
    concepts = [_concept(f"c{i}", 10) for i in range(5)]
    result = build_plan(
        concepts=concepts,
        start_date=date(2026, 1, 5),
        minutes_per_day=30,
        study_days=[0, 1, 2, 3, 4],
        horizon_days=7,
    )
    assert result.unscheduled_concept_ids == []
