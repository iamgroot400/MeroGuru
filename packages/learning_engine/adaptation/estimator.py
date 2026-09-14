"""The AI layer: proposes richer replanning (reorder concepts, swap resource format,
insert a review session) on top of the deterministic floor. Every suggestion is
range-checked before it can reach the verdict stage -- see range_guard.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from packages.ai_providers.base import AIProvider, GenerationRequest
from packages.learning_engine.adaptation.signals import LearnerSignals

SUGGESTION_SCHEMA = {
    "type": "object",
    "required": ["confidence", "additional_support", "removes_prerequisite", "lowers_target_mastery", "rationale"],
    "properties": {
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "additional_support": {
            "type": "array",
            "items": {"type": "string", "enum": [
                "add_worked_example", "add_practice_set", "swap_resource_format",
                "insert_review_session", "suggest_alternate_explanation",
            ]},
        },
        "removes_prerequisite": {"type": "boolean"},
        "lowers_target_mastery": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
}

SYSTEM_PROMPT = """You suggest supplementary adaptations to a learner's plan based on \
their recent performance signals. You may only ADD support (extra examples, practice, \
a different resource format, a review session). You must never propose removing a \
required prerequisite or lowering the target mastery bar -- if you believe that is \
warranted, set removes_prerequisite or lowers_target_mastery to true so a human/rules \
layer can reject the suggestion; do not just omit the concept. Set confidence low \
(below 0.5) if the learner's signal pattern is unusual or you are not confident your \
suggestion is well-grounded in the data provided."""


@dataclass
class Suggestion:
    confidence: float
    additional_support: list[str] = field(default_factory=list)
    removes_prerequisite: bool = False
    lowers_target_mastery: bool = False
    rationale: str = ""


async def propose_adaptation(provider: AIProvider, signals: LearnerSignals) -> Suggestion | None:
    user_prompt = (
        f"concept_id={signals.concept_id} latest_score={signals.latest_score:.2f} "
        f"score_trend={signals.score_trend:+.2f} attempts_on_distinct_days={signals.attempts_on_distinct_days} "
        f"avg_confidence_gap={signals.avg_confidence_gap:+.2f} time_ratio={signals.time_ratio:.2f} "
        f"consecutive_low_scores={signals.consecutive_low_scores}"
    )
    request = GenerationRequest(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, max_tokens=500)
    result = await provider.generate_structured(request, SUGGESTION_SCHEMA)
    if not result.valid:
        return None
    return Suggestion(**result.data)
