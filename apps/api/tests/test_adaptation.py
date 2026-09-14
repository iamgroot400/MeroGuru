from __future__ import annotations

from datetime import datetime, timezone

from packages.learning_engine.adaptation.deterministic_rules import evaluate_floor, new_mastery_score
from packages.learning_engine.adaptation.estimator import Suggestion
from packages.learning_engine.adaptation.signals import AssessmentEvent, compute_signals
from packages.learning_engine.adaptation.verdict import combine


def _events(scores, confidences=None):
    confidences = confidences or [0.5] * len(scores)
    return [
        AssessmentEvent(
            concept_id="c1",
            score=s,
            confidence=c,
            completed_at=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
            time_spent_minutes=20,
            estimated_minutes=20,
        )
        for i, (s, c) in enumerate(zip(scores, confidences))
    ]


def test_low_score_requires_easier_explanation():
    signals = compute_signals("c1", _events([0.3]))
    floor = evaluate_floor(signals, previous_mastery=0.0)
    assert floor.insert_easier_explanation


def test_high_score_advances_toward_proficiency():
    signals = compute_signals("c1", _events([0.9]))
    floor = evaluate_floor(signals, previous_mastery=0.5)
    assert floor.advance_toward_proficiency


def test_two_strong_attempts_on_separate_days_allows_mastered():
    signals = compute_signals("c1", _events([0.9, 0.92]))
    floor = evaluate_floor(signals, previous_mastery=0.75)
    assert floor.allow_mastered


def test_consecutive_low_scores_flags_prerequisite_inspection():
    signals = compute_signals("c1", _events([0.2, 0.3]))
    floor = evaluate_floor(signals, previous_mastery=0.1)
    assert floor.inspect_prerequisites


def test_mastery_update_is_conservative_not_a_single_question_jump():
    signals = compute_signals("c1", _events([1.0]))
    new_score = new_mastery_score(previous_mastery=0.0, signals=signals, practice_completion=1.0)
    assert new_score < 1.0  # one perfect question must not immediately mean mastered
    assert new_score > 0.0


def test_ai_suggestion_cannot_remove_prerequisite():
    floor = evaluate_floor(compute_signals("c1", _events([0.9])), previous_mastery=0.5)
    malicious_suggestion = Suggestion(
        confidence=0.99, additional_support=[], removes_prerequisite=True, lowers_target_mastery=False
    )
    verdict = combine(floor, malicious_suggestion)
    assert verdict.required is floor
    assert verdict.source == "floor"
    assert verdict.suggestion_rejected_reason is not None


def test_low_confidence_suggestion_is_ignored():
    floor = evaluate_floor(compute_signals("c1", _events([0.9])), previous_mastery=0.5)
    weak_suggestion = Suggestion(confidence=0.2, additional_support=["add_practice_set"])
    verdict = combine(floor, weak_suggestion)
    assert verdict.additional_support == []
    assert verdict.source == "floor"


def test_valid_suggestion_adds_support_without_overriding_floor():
    floor = evaluate_floor(compute_signals("c1", _events([0.9])), previous_mastery=0.5)
    suggestion = Suggestion(confidence=0.8, additional_support=["add_worked_example"])
    verdict = combine(floor, suggestion)
    assert verdict.required is floor
    assert verdict.additional_support == ["add_worked_example"]
    assert verdict.source == "floor+estimator"
