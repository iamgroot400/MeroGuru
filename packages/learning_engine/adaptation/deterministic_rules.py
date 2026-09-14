"""The adaptation floor: fixed, auditable rules from plan.md section 14.4.

This is the safety-core equivalent from the Monitor of Monitors architecture.
No AI-generated suggestion may ever weaken what this module requires; it may
only add supplementary support on top. See verdict.py for how the two combine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from packages.learning_engine.adaptation.signals import LearnerSignals

RULES_VERSION = "1.0.0"


class MasteryState(str, Enum):
    NOT_STARTED = "not_started"
    INTRODUCED = "introduced"
    LEARNING = "learning"
    PRACTICING = "practicing"
    PROFICIENT = "proficient"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"


@dataclass
class RequiredAction:
    insert_easier_explanation: bool = False
    schedule_near_term_review: bool = False
    schedule_normal_review: bool = False
    advance_toward_proficiency: bool = False
    allow_mastered: bool = False
    inspect_prerequisites: bool = False
    offer_challenge_assessment: bool = False
    reasons: list[str] = field(default_factory=list)


def evaluate_floor(signals: LearnerSignals, previous_mastery: float) -> RequiredAction:
    """Pure function of signals -> the minimum required response. Deterministic,
    versioned (RULES_VERSION), and independent of any AI provider."""
    action = RequiredAction()
    score = signals.latest_score

    if score < 0.50:
        action.insert_easier_explanation = True
        action.reasons.append(f"score {score:.2f} below 50%")
    elif score < 0.70:
        action.schedule_near_term_review = True
        action.reasons.append(f"score {score:.2f} in 50-69% band")
    elif score < 0.85:
        action.schedule_normal_review = True
        action.reasons.append(f"score {score:.2f} in 70-84% band")
    else:
        action.advance_toward_proficiency = True
        action.reasons.append(f"score {score:.2f} at or above 85%")

    if signals.attempts_on_distinct_days >= 2 and score >= 0.85 and previous_mastery >= 0.70:
        action.allow_mastered = True
        action.reasons.append("two strong attempts on separate days")

    if signals.consecutive_low_scores >= 2:
        action.inspect_prerequisites = True
        action.reasons.append(f"{signals.consecutive_low_scores} consecutive scores below 50%")

    if score >= 0.95 and signals.avg_confidence_gap <= 0.05:
        action.offer_challenge_assessment = True
        action.reasons.append("near-perfect score with accurate self-confidence")

    return action


def new_mastery_score(previous_mastery: float, signals: LearnerSignals, practice_completion: float) -> float:
    """plan.md 14.3: evidence-weighted, conservative update. Never jumps to mastered
    from a single easy question."""
    normalized_confidence = max(0.0, min(1.0, 1.0 - abs(signals.avg_confidence_gap)))
    evidence = (
        0.70 * signals.latest_score
        + 0.15 * normalized_confidence
        + 0.15 * practice_completion
    )
    return round(0.65 * previous_mastery + 0.35 * evidence, 4)
