"""Orchestrates one full adaptation pass: floor + AI estimator + verdict +
conservative mastery scoring, in that order. This is the single entry point
the brain service exposes over HTTP -- the same call sequence that used to run
in-process inside the API before the orchestrator/brain split.
"""
from __future__ import annotations

from dataclasses import dataclass

from packages.ai_providers.base import AIProvider
from packages.learning_engine.adaptation.deterministic_rules import evaluate_floor, new_mastery_score
from packages.learning_engine.adaptation.estimator import propose_adaptation
from packages.learning_engine.adaptation.signals import AssessmentEvent, compute_signals
from packages.learning_engine.adaptation.verdict import combine


@dataclass
class AdaptationResult:
    mastery_score: float
    mastery_state: str
    floor_reasons: list[str]
    additional_support: list[str]
    adaptation_source: str
    suggestion_rejected_reason: str | None


async def run_adaptation(
    provider: AIProvider,
    concept_id: str,
    previous_mastery: float,
    practice_completion: float,
    current: AssessmentEvent,
    history: list[AssessmentEvent],
) -> AdaptationResult:
    all_events = [*history, current]
    signals = compute_signals(concept_id, all_events)
    floor = evaluate_floor(signals, previous_mastery=previous_mastery)

    # A failed or low-confidence AI call must never block the deterministic
    # floor from applying -- fall back to the floor alone (verdict.combine
    # already treats suggestion=None this way).
    try:
        suggestion = await propose_adaptation(provider, signals)
    except Exception:
        suggestion = None
    verdict = combine(floor, suggestion)

    mastery_score = new_mastery_score(previous_mastery, signals, practice_completion)

    if floor.allow_mastered:
        mastery_state = "mastered"
    elif floor.advance_toward_proficiency:
        mastery_state = "proficient"
    elif floor.schedule_normal_review or floor.schedule_near_term_review:
        mastery_state = "practicing"
    elif floor.insert_easier_explanation:
        mastery_state = "needs_review"
    else:
        mastery_state = "not_started"

    return AdaptationResult(
        mastery_score=mastery_score,
        mastery_state=mastery_state,
        floor_reasons=floor.reasons,
        additional_support=verdict.additional_support,
        adaptation_source=verdict.source,
        suggestion_rejected_reason=verdict.suggestion_rejected_reason,
    )
