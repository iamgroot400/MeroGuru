"""Pure functions deriving time-series analytics from the learning_events log.

Lives here (not directly in an API route) so both the orchestrator and the
brain service can share one implementation without duplicating the logic.
Takes no database dependency -- callers pass in already-fetched event rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawEvent:
    event_type: str
    event_data: dict
    created_at: datetime


def compute_analytics(events: list[RawEvent]) -> dict:
    ordered = sorted(events, key=lambda e: e.created_at)
    assessment_events = [e for e in ordered if e.event_type == "assessment_completed"]
    feedback_events = [e for e in ordered if e.event_type == "lesson_feedback"]

    score_trend = [
        {
            "date": e.created_at.date().isoformat(),
            "score": e.event_data.get("score"),
            "concept_id": e.event_data.get("concept_id"),
        }
        for e in assessment_events
        if e.event_data.get("score") is not None
    ]

    mastered_concepts: set[str] = set()
    mastery_progress: list[dict] = []
    for e in assessment_events:
        concept_id = e.event_data.get("concept_id")
        if e.event_data.get("new_mastery_state") == "mastered" and concept_id not in mastered_concepts:
            mastered_concepts.add(concept_id)
            mastery_progress.append(
                {"date": e.created_at.date().isoformat(), "mastered_count": len(mastered_concepts)}
            )

    time_by_day: dict[str, int] = {}
    for e in feedback_events:
        minutes = e.event_data.get("time_spent_minutes")
        if minutes is None:
            continue
        day = e.created_at.date().isoformat()
        time_by_day[day] = time_by_day.get(day, 0) + int(minutes)
    time_spent_by_day = [{"date": d, "minutes": m} for d, m in sorted(time_by_day.items())]

    return {
        "score_trend": score_trend,
        "mastery_progress": mastery_progress,
        "time_spent_by_day": time_spent_by_day,
    }
