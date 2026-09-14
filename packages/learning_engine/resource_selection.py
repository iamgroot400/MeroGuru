"""Picks the best resource candidate for a concept using the explainable scoring
formula in validation.py, instead of blindly taking the first search result.

The heuristics here are intentionally simple and every input comes only from data
actually present on a ResourceCandidate -- no invented signals. The resulting score
components are stored on the persisted Resource so a selection can always be
explained (plan.md 13: "Resource ranking must be explainable through stored score
components").
"""
from __future__ import annotations

from packages.connectors.base import ResourceCandidate
from packages.learning_engine.concept_mapping import Concept
from packages.learning_engine.validation import ResourceScore, ResourceScoreInputs, score_resource


def _keyword_overlap(a: str, b: str) -> float:
    a_words = {w.lower() for w in a.split() if len(w) > 2}
    b_words = {w.lower() for w in b.split() if len(w) > 2}
    if not a_words:
        return 0.0
    return len(a_words & b_words) / len(a_words)


def _duration_match(duration_seconds: int | None, estimated_minutes: int) -> float:
    """1.0 when the video's length is roughly proportionate to the concept's time
    budget (0.4x-2x); decays toward 0 for wildly mismatched lengths."""
    if duration_seconds is None or estimated_minutes <= 0:
        return 0.4
    ratio = duration_seconds / (estimated_minutes * 60)
    if 0.4 <= ratio <= 2.0:
        return 1.0
    if ratio < 0.4:
        return max(0.0, ratio / 0.4)
    return max(0.0, 1.0 - (ratio - 2.0) / 3.0)


def score_candidate(candidate: ResourceCandidate, concept: Concept, language: str) -> ResourceScore:
    inputs = ResourceScoreInputs(
        relevance=max(_keyword_overlap(concept.title, candidate.title), 0.3),
        credibility=0.6,  # no independent credibility signal available yet (plan.md 13.3)
        level_match=0.6,  # no learner-level-vs-content-level signal available yet
        coverage=max(_keyword_overlap(concept.description, candidate.metadata.get("description", "")), 0.3),
        language_match=1.0 if candidate.language.startswith(language) else 0.4,
        practical_value=0.5,
        duration_match=_duration_match(candidate.duration_seconds, concept.estimated_minutes),
        accessibility=1.0 if candidate.embeddable else 0.0,
        license_clarity=1.0 if candidate.license_name else 0.5,
        duplication_penalty=0.0,
        availability_penalty=0.0 if candidate.embeddable else 0.5,
    )
    return score_resource(inputs)


def select_best_resource(
    candidates: list[ResourceCandidate], concept: Concept, language: str = "en"
) -> tuple[ResourceCandidate, ResourceScore] | None:
    if not candidates:
        return None
    scored = [(c, score_candidate(c, concept, language)) for c in candidates]
    scored.sort(key=lambda pair: pair[1].total, reverse=True)
    return scored[0]
