"""Derives adaptation signals from a learner's recent activity, mirroring the
observation sub-brain pattern: a hot window (recent) plus authoritative mastery
state (durable), reduced to the handful of features the floor and estimator need.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AssessmentEvent:
    concept_id: str
    score: float  # 0.0-1.0
    confidence: float  # learner self-reported, 0.0-1.0
    completed_at: datetime
    time_spent_minutes: int
    estimated_minutes: int


@dataclass
class LearnerSignals:
    concept_id: str
    latest_score: float
    score_trend: float  # positive = improving, negative = declining
    attempts_on_distinct_days: int
    avg_confidence_gap: float  # confidence - actual score; positive = overconfident
    time_ratio: float  # actual / estimated; >1 = slower than expected
    consecutive_low_scores: int


def compute_signals(concept_id: str, events: list[AssessmentEvent]) -> LearnerSignals:
    if not events:
        return LearnerSignals(
            concept_id=concept_id,
            latest_score=0.0,
            score_trend=0.0,
            attempts_on_distinct_days=0,
            avg_confidence_gap=0.0,
            time_ratio=1.0,
            consecutive_low_scores=0,
        )

    ordered = sorted(events, key=lambda e: e.completed_at)
    latest = ordered[-1]
    distinct_days = len({e.completed_at.date() for e in ordered})

    score_trend = 0.0
    if len(ordered) >= 2:
        score_trend = ordered[-1].score - ordered[-2].score

    avg_confidence_gap = sum(e.confidence - e.score for e in ordered) / len(ordered)
    avg_time_ratio = sum(
        (e.time_spent_minutes / e.estimated_minutes) for e in ordered if e.estimated_minutes > 0
    ) / max(1, len(ordered))

    consecutive_low = 0
    for event in reversed(ordered):
        if event.score < 0.5:
            consecutive_low += 1
        else:
            break

    return LearnerSignals(
        concept_id=concept_id,
        latest_score=latest.score,
        score_trend=score_trend,
        attempts_on_distinct_days=distinct_days,
        avg_confidence_gap=avg_confidence_gap,
        time_ratio=avg_time_ratio,
        consecutive_low_scores=consecutive_low,
    )
