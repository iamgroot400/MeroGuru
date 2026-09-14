"""Combines the deterministic floor with the AI's suggestion: the floor always wins
on required actions, and the AI may only add supplementary support on top. Mirrors
the Monitor of Monitors verdict stage's max(floor, estimate) with a hard ceiling.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from packages.learning_engine.adaptation.deterministic_rules import RequiredAction
from packages.learning_engine.adaptation.estimator import Suggestion

CONFIDENCE_THRESHOLD = 0.5


class AdaptationViolation(RuntimeError):
    """Raised if a suggestion is combined in a way that would weaken the floor.

    This should never actually surface to a caller -- combine() filters violating
    suggestions out before returning -- but it exists so a bug that tries to bypass
    the filter fails loudly instead of silently weakening a learner's plan.
    """


@dataclass
class AdaptationVerdict:
    required: RequiredAction
    additional_support: list[str] = field(default_factory=list)
    source: str = "floor"
    suggestion_rejected_reason: str | None = None


def combine(floor: RequiredAction, suggestion: Suggestion | None) -> AdaptationVerdict:
    if suggestion is None:
        return AdaptationVerdict(required=floor, source="floor")

    if suggestion.confidence < CONFIDENCE_THRESHOLD:
        return AdaptationVerdict(
            required=floor, source="floor", suggestion_rejected_reason="low confidence"
        )

    if suggestion.removes_prerequisite or suggestion.lowers_target_mastery:
        return AdaptationVerdict(
            required=floor,
            source="floor",
            suggestion_rejected_reason="suggestion attempted to weaken floor requirements",
        )

    return AdaptationVerdict(
        required=floor,
        additional_support=suggestion.additional_support,
        source="floor+estimator",
    )


def is_material_change(previous_verdict: AdaptationVerdict | None, new_verdict: AdaptationVerdict) -> bool:
    """Dedup gate: don't regenerate/notify on every quiz if nothing has actually
    changed, mirroring the Monitor of Monitors deduplication-against-current-state step."""
    if previous_verdict is None:
        return True
    prev = previous_verdict.required
    new = new_verdict.required
    fields = [
        "insert_easier_explanation", "schedule_near_term_review", "schedule_normal_review",
        "advance_toward_proficiency", "allow_mastered", "inspect_prerequisites",
        "offer_challenge_assessment",
    ]
    if any(getattr(prev, f) != getattr(new, f) for f in fields):
        return True
    if set(previous_verdict.additional_support) != set(new_verdict.additional_support):
        return True
    return False
